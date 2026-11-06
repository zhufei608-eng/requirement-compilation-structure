# Baseline run 2026-11-06 (demo, ticket-booking login/register): interpretation

Source: `outputs/demo` of a cold run (`uv run main.py input --output-dir outputs/demo --model-log`, commit a0ad1a4).
The whole output dir, minus node_modules/ and its .git, is archived in `demo_raw.tar.gz`. It holds
model_calls.jsonl, compiler.log, .arc/ and the generated app. To re-analyze it:

    mkdir -p outputs/demo && tar -xzf analysis/runs/2026-11-06_demo_baseline/demo_raw.tar.gz -C outputs/demo
    python analysis/analyze_run.py outputs/demo analysis/runs/2026-11-06_demo_baseline

Numbers: see summary.md / stages.csv / activities.csv / calls.csv.

## Headline
- Status COMPLETED_WITH_FAILURES. Stages 00–09 GREEN. Stage 10's functional E2E smoke had 0 failures;
  the failure comes from **Independent acceptance**: REQ-1 and REQ-4 used all 10 rounds and FAILED.
- 52.7 min wall time, 150 LLM calls (all deepseek-flash, reasoning_effort=low, sequential).
- LLM time is 28.3 min (54%). The other ~24 min is install, tests and builds.
- 1.62M prompt tokens (60% cached) vs 185k completion tokens (64% of those are reasoning tokens).

## Where time/tokens go
- Stage 10 alone: 30% of wall time, **63% of prompt tokens** (1.03M), 74/150 calls.
- The two exhausted independent-acceptance loops (REQ-1, REQ-4): 33 calls, ~383k prompt tokens
  (~24% of the whole run) and produced nothing usable.
- Non-LLM time:
  - stage 04 has ~475 s, nearly all the first (cold) `npm install`; the timed checks there add up to only ~8 s.
  - stage 08 has ~490 s, of which ~118 s are Playwright/tsc checks; the rest is likely frontend
    install/setup, which the log doesn't time.
  - stage 10 has ~400 s, mostly E2E test runs (13 runs, 266 s, 6 non-zero exits).
- Call kinds:
  - read_files: 59 calls, 47% of prompt tokens, avg 12.9k tokens per call.
  - edit_round: 61 calls, 43% of prompt tokens.
  - Design proposals are cheap on input (~3.5k tokens) but slow (40–60 s each), because they generate
    7–10k completion tokens, mostly reasoning.
- All 23 design proposals were accepted on attempt 1. The proposal retry budget was never used.
  Iteration only happens in the edit/TDD loops:
  - stage 06 REQ-4 tests: 3 rounds.
  - stage 08 registration UI: 5 rounds, the costliest single activity (149 s).
  - stage 10 acceptance: 10, 2, 5 and 10 rounds for REQ-1 to REQ-4.

## Improvement hypotheses suggested by the numbers (not yet verified)
1. Detect a stalled loop. If the same test fails the same way for k rounds, stop or escalate
   (re-plan, more context, a stronger model) instead of burning 10 rounds.
2. Trim the read_files/edit context. Prompts are 9× the outputs, and each round re-sends ~11–13k tokens.
3. Run independent work in parallel. Examples: the 3 image analyses take 134 s sequentially, and some per-REQ steps don't depend on each other.
4. Pre-warm or cache node_modules. That saves about 8 min per run, which matters when running many runs.
5. Check whether the failing acceptance tests are *wrong tests* or a *wrong app* before fixing the coder.
