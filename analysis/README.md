# analysis/

Tools for measuring runs of the requirement compiler (`main.py` in this repo):
time, tokens, retries and outcome per stage. Use them to compare the baseline with modified versions.

## Files

| File | Purpose |
|---|---|
| `arc_run.py` | Runs `uv run main.py <args>`, then runs `analyze_run.py` on the output |
| `analyze_run.py` | Analyzes an existing run dir |
| `runs/<date_time>_<output-name>/` | One folder per analyzed run (see below) |
| `npm_cache/` | Warm `node_modules` + `package-lock.json` used by `--seed-modules` (about 128 MB) |

## Usage

From the repo root:

```
python analysis/arc_run.py input --output-dir outputs/run1 --model-log --seed-modules
python analysis/arc_run.py input --output-dir outputs/dev  --model-log --seed-modules --fresh
```

- Use the same arguments as `main.py`. `--fresh` and `--seed-modules` are handled by the wrapper and
  are not passed to `main.py`.
- `--seed-modules` copies `npm_cache/` into the output dir before compiling. That takes about 7 s,
  instead of a cold `npm install` of about 14 min in the baseline (stages 04 and 08).
  - The compiler is unchanged. Its own `npm install` calls still run, but they find nothing to do.
  - npm workspace links (`node_modules/@arc/*`) are junctions into the run dir. They are never cached;
    they are re-created to point at the new run.
  - If `npm_cache/` is missing, the run installs cold and fills the cache afterwards. Delete
    `npm_cache/` to refresh it.
  - If the agent changes dependencies, the wrapper prints a note, and `meta.json` records
    `lock_differs_from_cache: true`.
- A non-empty output dir is refused. The compiler appends to an existing `compiler.log` and
  `model_calls.jsonl`, and builds on the old generated code, so a reused dir mixes two runs.
  Use a new `--output-dir`, or add `--fresh` to delete the old one first.
- `--model-log` is required. Without it there is no `model_calls.jsonl` to analyze.
- Don't run it with `python -I`, which stops `arc_run.py` from importing `analyze_run.py`.

To analyze an existing run dir: `python analyze_run.py <run_dir> <out_dir>`

## Output per run

| File | Contents |
|---|---|
| `summary.md` | Headline numbers and tables: per stage, tool/test commands, call kinds, top activities, slowest calls |
| `stages.csv` | Per stage: wall time, LLM time, non-LLM time, calls, tokens, max round, outcome counts |
| `activities.csv` | Per task (e.g. `Independent acceptance / REQ-4 / Generation`): calls by kind, rounds, whether the round budget ran out |
| `calls.csv` | One row per LLM call: timing, prompt, cached, completion and reasoning tokens, finish reason |
| `meta.json` | Command, cwd, git commit, start/end time, exit code, whether `node_modules` was seeded (only when run through `arc_run.py`) |
| `NOTES.md` | Your own interpretation (written by hand) |

## Reading the numbers

- **Data sources:**
  - `model_calls.jsonl` gives per-call tokens and `elapsed_seconds`.
  - `compiler.log` gives stage wall time (`Completed in Xs`), `[CHECK]` command timings, `[GIT]` outcome
    tags and "Agent exhausted N rounds".
  - `.arc/compilation.json` gives the final status.
- **LLM time and non-LLM time:** LLM time is the sum of call durations (calls run sequentially).
  Non-LLM time is wall time minus LLM time: npm installs, builds, tsc and test runs.
- **npm install is not timed** by `[CHECK]`. Check the log for `added N packages in Xm`.
  In the baseline, installs took about 14 of 53 min.
- **Call kinds:**
  - `proposal`: a single-shot design call.
  - `read_files`, `context_query`, `edit_round`: the agent loop.
  - A high `max_round` means a loop is iterating. Reaching the full budget (10) means it gave up.
- **Compiler status vs. real quality:** the compiler's status reflects its *own* generated tests.
  Score real quality with ARC-Bench's validation tests.

## Methodology reminders

- Run every configuration at least 3 times and compare means and spread, not single runs.
- Change one thing per experiment, and give the output dir a descriptive name (`baseline_r2`, `stallfix_r1`).
- Keep the environment identical across runs you compare, including npm caching. The first baseline
  (`2026-11-06_demo_baseline`) was a cold install; re-run the baseline with `--seed-modules` before comparing times.
- Disk: about 168 MB per run, of which 128 MB is `node_modules`. Deleting it from old runs leaves about 40 MB.
