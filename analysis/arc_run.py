"""Run the compiler, then analyze the run.

Usage (from the repo root), same args as main.py:
  python analysis/arc_run.py input --output-dir outputs/demo --model-log [--fresh] [--seed-modules]

Runs `uv run main.py <args>`, then writes analysis to analysis/runs/<timestamp>_<output-name>/
(even if the compile failed, as long as model_calls.jsonl exists).

Wrapper-only flags (not passed to main.py):
  --fresh         The compiler appends to an existing output dir's logs and builds on its old
                  code, so a non-empty output dir is refused; --fresh deletes it first.
  --seed-modules  Copy a warm node_modules + package-lock.json from analysis/npm_cache/ into the
                  output dir before compiling, skipping the slow cold npm install. If the cache
                  does not exist yet, this run is cold and fills it afterwards. Delete
                  analysis/npm_cache/ to refresh it.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from analyze_run import main as analyze

CACHE = Path(__file__).resolve().parent / "npm_cache"


def output_dir_from(args):
    for i, a in enumerate(args):
        if a in ("-o", "--output-dir") and i + 1 < len(args):
            return Path(args[i + 1])
        if a.startswith("--output-dir="):
            return Path(a.split("=", 1)[1])
    sys.exit("arc_run: --output-dir / -o is required")


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def rmtree(path):
    def force(func, p, _):  # .git objects are read-only on Windows
        Path(p).chmod(stat.S_IWRITE)
        func(p)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=force)
    else:
        shutil.rmtree(path, onerror=force)


def remove_run_dir(run_dir):
    # Only delete something that looks like a previous compile output.
    if not ((run_dir / ".arc").is_dir() or (run_dir / "compiler.log").is_file()):
        sys.exit(f"arc_run: {run_dir} does not look like a compiler output dir; not deleting it")
    print(f"arc_run: --fresh, deleting {run_dir}")
    rmtree(run_dir)


def is_link(path):
    return path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path))


def workspace_links(node_modules):
    """npm workspace links (e.g. @arc/backend) are junctions with absolute targets into the run dir."""
    links = []
    for entry in node_modules.iterdir():
        for p in (entry.iterdir() if entry.name.startswith("@") and entry.is_dir() and not is_link(entry) else [entry]):
            if is_link(p):
                links.append((p.relative_to(node_modules).as_posix(),
                              Path(os.path.realpath(p)).relative_to(node_modules.parent.resolve()).as_posix()))
    return links


def make_link(link, target):
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":  # a junction needs no admin rights, and its target need not exist yet
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
    else:
        os.symlink(target, link, target_is_directory=True)


def copy_modules(src, dst):
    # Never copy links: they point into the run they came from.
    shutil.copytree(src, dst, symlinks=True, ignore=lambda d, names: [n for n in names if is_link(Path(d, n))])


def save_cache(run_dir):
    if not (run_dir / "node_modules").is_dir() or not (run_dir / "package-lock.json").is_file():
        print("arc_run: run has no node_modules/package-lock.json, npm cache not saved")
        return
    print(f"arc_run: saving npm cache from {run_dir} to {CACHE}")
    tmp = CACHE.with_name(CACHE.name + ".tmp")
    if tmp.exists():
        rmtree(tmp)
    copy_modules(run_dir / "node_modules", tmp / "node_modules")
    shutil.copy2(run_dir / "package-lock.json", tmp / "package-lock.json")
    (tmp / "links.json").write_text(json.dumps(workspace_links(run_dir / "node_modules"), indent=2), encoding="utf-8")
    (tmp / "source.json").write_text(json.dumps({"from": str(run_dir.resolve()),
                                                 "saved": datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")
    if CACHE.exists():
        rmtree(CACHE)
    tmp.rename(CACHE)


def seed_from_cache(run_dir):
    print(f"arc_run: seeding {run_dir} from {CACHE}")
    t = time.perf_counter()
    copy_modules(CACHE / "node_modules", run_dir / "node_modules")
    shutil.copy2(CACHE / "package-lock.json", run_dir / "package-lock.json")
    for rel_link, rel_target in json.loads((CACHE / "links.json").read_text(encoding="utf-8")):
        make_link(run_dir.resolve() / "node_modules" / rel_link, run_dir.resolve() / rel_target)
    return round(time.perf_counter() - t, 1)


def main(args):
    fresh = "--fresh" in args
    seed = "--seed-modules" in args
    args = [a for a in args if a not in ("--fresh", "--seed-modules")]
    run_dir = output_dir_from(args)
    if run_dir.is_dir() and any(run_dir.iterdir()):
        if not fresh:
            sys.exit(f"arc_run: {run_dir} is not empty; the compiler would append to its logs and reuse "
                     f"its old code.\n  Use a new --output-dir, or add --fresh to delete it first.")
        remove_run_dir(run_dir)
    if "--model-log" not in args and "--debug-model-io" not in args:
        print("arc_run: warning, without --model-log there is no model_calls.jsonl to analyze")

    seeded, seed_s = False, None
    if seed and (CACHE / "links.json").is_file():
        seed_s, seeded = seed_from_cache(run_dir), True
    elif seed:
        print(f"arc_run: no npm cache at {CACHE} yet; this run installs cold and fills it afterwards")

    started = datetime.now()
    cmd = ["uv", "run", "main.py", *args]
    try:
        code = subprocess.call(cmd)
    except KeyboardInterrupt:
        code = "interrupted"
    finished = datetime.now()

    stale = None
    if seeded:
        # The agent may have changed dependencies; then the cache no longer matches fresh runs.
        lock = run_dir / "package-lock.json"
        stale = not lock.is_file() or lock.read_bytes() != (CACHE / "package-lock.json").read_bytes()
        if stale:
            print("arc_run: note, this run's package-lock.json differs from the npm cache "
                  "(dependencies changed); delete analysis/npm_cache/ to refresh it")
    elif seed and code == 0:
        save_cache(run_dir)

    if not (run_dir / "model_calls.jsonl").exists():
        print(f"arc_run: no {run_dir / 'model_calls.jsonl'}, skipping analysis")
        sys.exit(code if isinstance(code, int) else 1)

    out_dir = Path(__file__).resolve().parent / "runs" / f"{started:%Y-%m-%d_%H%M}_{run_dir.name}"
    print(f"\narc_run: compile exited with {code}; analyzing into {out_dir}\n")
    analyze(run_dir, out_dir)
    meta = {
        "command": cmd,
        "cwd": str(Path.cwd()),
        "git_commit": git_commit(),
        "started": started.isoformat(timespec="seconds"),
        "finished": finished.isoformat(timespec="seconds"),
        "wall_s": round((finished - started).total_seconds(), 1),
        "exit_code": code,
        "seeded_node_modules": seeded,
        "seed_s": seed_s,
        "lock_differs_from_cache": stale,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    sys.exit(code if isinstance(code, int) else 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
