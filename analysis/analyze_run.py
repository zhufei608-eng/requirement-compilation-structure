"""Summarize one ARC run: time, tokens and retries per stage / activity / call.

Usage:  python analyze_run.py <run_dir> <out_dir>
  run_dir  the compile output dir (contains model_calls.jsonl, compiler.log, .arc/)
  out_dir  where calls.csv, stages.csv, activities.csv, summary.md are written
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def stage_key(stage):
    m = re.match(r"Stage (\d+)", stage or "")
    return m.group(1) if m else "??"


def split_activity(activity):
    # "REQ-4 / API-logout (uses: REQ-4) / Test Generation | Edit round 3/10"
    parts = [p.strip() for p in activity.split("|")]
    step = parts[-1] if len(parts) > 1 else ""
    task = " | ".join(parts[:-1]) if len(parts) > 1 else parts[0]
    if "Read files" in step:
        kind = "read_files"
    elif "Context query" in step:
        kind = "context_query"
    elif "Edit round" in step:
        kind = "edit_round"
    elif "Model proposal" in step:
        kind = "proposal"
    else:
        kind = "other"
    rnd = re.search(r"(\d+)/(\d+)", step)
    return task, step, kind, int(rnd.group(1)) if rnd and kind in ("edit_round", "proposal") else None


def load_calls(path):
    calls = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        c = calls.setdefault(r["call_id"], {"call_id": r["call_id"]})
        if r["event"] == "request":
            args = r["arguments"]
            c.update(stage=r["stage"], activity=r["activity"], start=r["timestamp"],
                     model=args.get("model"), reasoning_effort=args.get("reasoning_effort"),
                     n_messages=len(args.get("messages", [])),
                     request_chars=len(json.dumps(args.get("messages", []), ensure_ascii=False)))
        elif r["event"] == "http_response":
            c["status_code"] = r.get("status_code")
        elif r["event"] == "response":
            resp = r.get("response") or {}
            u = resp.get("usage") or {}
            ch = (resp.get("choices") or [{}])[0]
            msg = ch.get("message") or {}
            c.update(end=r["timestamp"], elapsed_s=r.get("elapsed_seconds"),
                     finish_reason=ch.get("finish_reason"),
                     prompt_tokens=u.get("prompt_tokens") or 0,
                     cached_tokens=(u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
                     completion_tokens=u.get("completion_tokens") or 0,
                     reasoning_tokens=(u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0,
                     output_chars=len(msg.get("content") or ""))
    rows = []
    for c in calls.values():
        task, step, kind, rnd = split_activity(c.get("activity", ""))
        c.update(stage_id=stage_key(c.get("stage")), task=task, step=step, kind=kind, round=rnd)
        c["uncached_prompt_tokens"] = c.get("prompt_tokens", 0) - c.get("cached_tokens", 0)
        rows.append(c)
    rows.sort(key=lambda c: c.get("start", ""))
    return rows


def parse_log(path):
    """Stage wall times and git outcome tags from compiler.log."""
    text = open(path, encoding="utf-8", errors="replace").read()
    stage_wall, stage_name = {}, {}
    for m in re.finditer(r"\[DONE\] Stage (\d+) \| ([^│\n]+?)\s*│.*?Completed in ([\d.]+)s", text, re.S):
        stage_wall[m.group(1)] = float(m.group(3))
        stage_name[m.group(1)] = m.group(2).strip()
    outcomes = defaultdict(Counter)
    for m in re.finditer(r"^\[GIT\] \S+ \[(?:Stage )?(\d+)[^\]]*\] (.*)\(([A-Z_]+)\)\s*$", text, re.M):
        outcomes[m.group(1)][m.group(3)] += 1
    exhausted = re.findall(r"^Agent exhausted \d+ rounds for (.+)$", text, re.M)
    # [CHECK] <cmd> | 2.12 s | exit 0   -- tool/test commands run by the compiler
    checks = defaultdict(lambda: [0, 0.0, 0])
    stage = "00"
    for line in text.splitlines():
        m = re.search(r"\[START\] Stage (\d+)", line)
        if m:
            stage = m.group(1)
        m = re.match(r"\[CHECK\] (.+?) \| ([\d.]+) s \| exit (\S+)", line)
        if m:
            cmd = m.group(1)
            kind = next((k for k in ("test-e2e", "test-api", "playwright", "tsc", "install", "build")
                         if k in cmd), "other")
            c = checks[(stage, kind)]
            c[0] += 1
            c[1] += float(m.group(2))
            c[2] += m.group(3) != "0"
    return stage_wall, stage_name, outcomes, sorted(set(exhausted)), checks


def agg(rows):
    return {
        "calls": len(rows),
        "llm_s": round(sum(r.get("elapsed_s") or 0 for r in rows), 1),
        "prompt_tok": sum(r.get("prompt_tokens", 0) for r in rows),
        "cached_tok": sum(r.get("cached_tokens", 0) for r in rows),
        "completion_tok": sum(r.get("completion_tokens", 0) for r in rows),
        "reasoning_tok": sum(r.get("reasoning_tokens", 0) for r in rows),
        "max_round": max([r["round"] for r in rows if r.get("round")] or [0]),
    }


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(run_dir, out_dir):
    run_dir, out_dir = Path(run_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    calls = load_calls(run_dir / "model_calls.jsonl")
    wall, names, outcomes, exhausted, checks = parse_log(run_dir / "compiler.log")

    write_csv(out_dir / "calls.csv", calls,
              ["start", "stage_id", "task", "step", "kind", "round", "model", "reasoning_effort",
               "elapsed_s", "prompt_tokens", "cached_tokens", "uncached_prompt_tokens",
               "completion_tokens", "reasoning_tokens", "output_chars", "n_messages",
               "request_chars", "finish_reason", "status_code", "call_id"])

    by_stage = defaultdict(list)
    for c in calls:
        by_stage[c["stage_id"]].append(c)
    stage_rows = []
    for sid in sorted(set(wall) | set(by_stage)):
        a = agg(by_stage.get(sid, []))
        w = wall.get(sid)
        a.update(stage_id=sid, name=names.get(sid, ""), wall_s=w,
                 non_llm_s=round(w - a["llm_s"], 1) if w is not None else None,
                 outcomes=" ".join(f"{k}={v}" for k, v in sorted(outcomes[sid].items())))
        stage_rows.append(a)
    stage_fields = ["stage_id", "name", "wall_s", "llm_s", "non_llm_s", "calls", "prompt_tok",
                    "cached_tok", "completion_tok", "reasoning_tok", "max_round", "outcomes"]
    write_csv(out_dir / "stages.csv", stage_rows, stage_fields)

    by_task = defaultdict(list)
    for c in calls:
        by_task[(c["stage_id"], c["task"])].append(c)
    task_rows = []
    for (sid, task), rs in by_task.items():
        a = agg(rs)
        a.update(stage_id=sid, task=task,
                 kinds=" ".join(f"{k}={v}" for k, v in sorted(Counter(r["kind"] for r in rs).items())),
                 exhausted=task in exhausted)
        task_rows.append(a)
    task_rows.sort(key=lambda r: -r["llm_s"])
    write_csv(out_dir / "activities.csv", task_rows,
              ["stage_id", "task", "calls", "kinds", "max_round", "exhausted", "llm_s", "prompt_tok",
               "cached_tok", "completion_tok", "reasoning_tok"])

    # ---- summary.md ----
    tot = agg(calls)
    t0 = datetime.fromisoformat(calls[0]["start"])
    t1 = datetime.fromisoformat(max(c.get("end", c["start"]) for c in calls))
    total_wall = sum(v for v in wall.values())
    comp = run_dir / ".arc" / "compilation.json"
    status = json.load(open(comp, encoding="utf-8")).get("status") if comp.exists() else "unknown (no compilation.json)"
    kinds = defaultdict(list)
    for c in calls:
        kinds[c["kind"]].append(c)

    L = []
    L.append(f"# ARC run summary: `{run_dir.name}`\n")
    L.append(f"- Final status: **{status}**")
    L.append(f"- Models: {dict(Counter(c.get('model') for c in calls))}, reasoning_effort: "
             f"{dict(Counter(c.get('reasoning_effort') for c in calls))}")
    L.append(f"- Wall clock (sum of stage times): **{total_wall/60:.1f} min**; first→last LLM call: "
             f"{(t1 - t0).total_seconds()/60:.1f} min")
    L.append(f"- LLM calls: **{tot['calls']}**, sequential LLM time {tot['llm_s']/60:.1f} min "
             f"({100*tot['llm_s']/total_wall:.0f}% of wall)")
    L.append(f"- Tokens: prompt {tot['prompt_tok']:,} (cached {tot['cached_tok']:,} = "
             f"{100*tot['cached_tok']/max(tot['prompt_tok'],1):.0f}%), completion {tot['completion_tok']:,} "
             f"(of which reasoning {tot['reasoning_tok']:,} = "
             f"{100*tot['reasoning_tok']/max(tot['completion_tok'],1):.0f}%)")
    L.append(f"- Agents that exhausted their round budget: {exhausted or 'none'}\n")

    L.append("## Per stage\n")
    L.append("| Stage | Name | Wall s | LLM s | Non-LLM s | Calls | Prompt tok | Compl tok | Max round | Outcomes |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in stage_rows:
        L.append(f"| {r['stage_id']} | {r['name']} | {r['wall_s']} | {r['llm_s']} | {r['non_llm_s']} | "
                 f"{r['calls']} | {r['prompt_tok']:,} | {r['completion_tok']:,} | {r['max_round']} | {r['outcomes']} |")

    L.append("\n## Tool/test commands ([CHECK] lines; npm install itself is not timed)\n")
    L.append("| Stage | Command | Runs | Total s | Non-zero exits |")
    L.append("|---|---|---:|---:|---:|")
    for (sid, kind), (n, t, f) in sorted(checks.items()):
        L.append(f"| {sid} | {kind} | {n} | {t:.1f} | {f} |")

    L.append("\n## By call kind\n")
    L.append("| Kind | Calls | LLM s | Prompt tok | Compl tok | Avg prompt tok |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for k, rs in sorted(kinds.items(), key=lambda kv: -agg(kv[1])["llm_s"]):
        a = agg(rs)
        L.append(f"| {k} | {a['calls']} | {a['llm_s']} | {a['prompt_tok']:,} | {a['completion_tok']:,} | "
                 f"{a['prompt_tok']//a['calls']:,} |")

    L.append("\n## Top 12 activities by LLM time\n")
    L.append("| Stage | Activity | Calls | Kinds | Max round | LLM s | Prompt tok | Compl tok |")
    L.append("|---|---|---:|---|---:|---:|---:|---:|")
    for r in task_rows[:12]:
        flag = " ⚠ exhausted" if r["exhausted"] else ""
        L.append(f"| {r['stage_id']} | {r['task'][:70]}{flag} | {r['calls']} | {r['kinds']} | {r['max_round']} | "
                 f"{r['llm_s']} | {r['prompt_tok']:,} | {r['completion_tok']:,} |")

    L.append("\n## Slowest 10 single calls\n")
    L.append("| Stage | Activity | s | Prompt tok | Compl tok | Reasoning tok | Finish |")
    L.append("|---|---|---:|---:|---:|---:|---|")
    for c in sorted(calls, key=lambda c: -(c.get("elapsed_s") or 0))[:10]:
        L.append(f"| {c['stage_id']} | {c['activity'][:80].replace('|', '·')} | {c.get('elapsed_s', 0):.0f} | "
                 f"{c.get('prompt_tokens', 0):,} | {c.get('completion_tokens', 0):,} | "
                 f"{c.get('reasoning_tokens', 0):,} | {c.get('finish_reason')} |")

    (out_dir / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:3])
