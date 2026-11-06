# ARC run summary: `demo`

- Final status: **COMPLETED_WITH_FAILURES**
- Models: {'deepseek-flash': 150}, reasoning_effort: {'low': 150}
- Wall clock (sum of stage times): **52.7 min**; first→last LLM call: 52.8 min
- LLM calls: **150**, sequential LLM time 28.3 min (54% of wall)
- Tokens: prompt 1,619,099 (cached 969,088 = 60%), completion 185,209 (of which reasoning 118,982 = 64%)
- Agents that exhausted their round budget: ['Independent acceptance / REQ-1 / Generation', 'Independent acceptance / REQ-4 / Generation']

## Per stage

| Stage | Name | Wall s | LLM s | Non-LLM s | Calls | Prompt tok | Compl tok | Max round | Outcomes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 00 | Initialize project | 2.1 | 0 | 2.1 | 0 | 0 | 0 | 0 | COMPLETED=1 GREEN=1 RUNNING=1 |
| 01 | Read requirements and analyze reference images | 142.1 | 134.1 | 8.0 | 3 | 3,972 | 8,232 | 1 | COMPLETED=1 GREEN=7 RUNNING=1 |
| 02 | Design database schema | 46.4 | 42.9 | 3.5 | 6 | 15,879 | 2,459 | 1 | COMPLETED=1 GREEN=4 RUNNING=1 |
| 03 | Infer database read/write obligations | 67.1 | 63.8 | 3.3 | 4 | 9,022 | 4,435 | 1 | COMPLETED=1 GREEN=4 RUNNING=1 |
| 04 | Implement database | 530.6 | 55.1 | 475.5 | 6 | 26,760 | 2,488 | 1 | COMPLETED=1 GREEN=9 PROPOSED=6 RUNNING=1 |
| 05 | Design backend APIs including P/Q | 131.9 | 128.3 | 3.6 | 4 | 18,785 | 16,634 | 1 | COMPLETED=1 GREEN=4 RUNNING=1 |
| 06 | Implement backend with test-first acceptance | 312.6 | 240.8 | 71.8 | 33 | 319,673 | 26,700 | 3 | COMPLETED=1 GREEN=16 PROPOSED=8 RED_CONFIRMED=4 REJECTED=3 RUNNING=1 |
| 07 | Design UI and frontend data | 119.9 | 116.4 | 3.5 | 4 | 18,099 | 16,569 | 1 | COMPLETED=1 GREEN=4 RUNNING=1 |
| 08 | Implement UI and run existence tests | 722.5 | 230.8 | 491.7 | 12 | 158,010 | 32,567 | 5 | COMPLETED=1 GREEN=10 PROPOSED=3 REJECTED=4 RUNNING=1 TESTS_READY=3 |
| 09 | Design frontend triggers | 134.6 | 130.8 | 3.8 | 4 | 21,669 | 19,325 | 1 | COMPLETED=1 GREEN=4 RUNNING=1 |
| 10 | Implement triggers and run end-to-end tests | 953.8 | 556.0 | 397.8 | 74 | 1,027,230 | 55,800 | 10 | COMPLETED=1 COMPLETED_WITH_FAILURES=1 FAILED=4 GREEN=26 PROPOSED=12 REJECTED=25 REPAIR_REQUIRED=4 RUNNING=1 |

## Tool/test commands ([CHECK] lines; npm install itself is not timed)

| Stage | Command | Runs | Total s | Non-zero exits |
|---|---|---:|---:|---:|
| 04 | build | 1 | 2.1 | 0 |
| 04 | other | 1 | 5.5 | 0 |
| 06 | build | 1 | 2.0 | 0 |
| 06 | test-api | 12 | 31.4 | 4 |
| 06 | tsc | 9 | 13.5 | 0 |
| 08 | build | 1 | 8.6 | 0 |
| 08 | playwright | 8 | 92.3 | 3 |
| 08 | tsc | 7 | 16.6 | 0 |
| 10 | build | 1 | 6.8 | 0 |
| 10 | playwright | 7 | 35.2 | 0 |
| 10 | test-api | 1 | 4.0 | 0 |
| 10 | test-e2e | 13 | 266.3 | 6 |
| 10 | tsc | 15 | 27.8 | 0 |

## By call kind

| Kind | Calls | LLM s | Prompt tok | Compl tok | Avg prompt tok |
|---|---:|---:|---:|---:|---:|
| proposal | 23 | 607.8 | 81,397 | 67,518 | 3,539 |
| read_files | 59 | 607.7 | 761,384 | 73,032 | 12,904 |
| edit_round | 61 | 420.8 | 701,811 | 37,724 | 11,505 |
| context_query | 7 | 62.8 | 74,507 | 6,935 | 10,643 |

## Top 12 activities by LLM time

| Stage | Activity | Calls | Kinds | Max round | LLM s | Prompt tok | Compl tok |
|---|---|---:|---|---:|---:|---:|---:|
| 08 | UI 2/3 registration / Implementation | 7 | edit_round=5 read_files=2 | 5 | 149.4 | 96,263 | 21,043 |
| 10 | Independent acceptance / REQ-4 / Generation ⚠ exhausted | 18 | edit_round=10 read_files=8 | 10 | 93.4 | 216,955 | 6,100 |
| 10 | Independent acceptance / REQ-1 / Generation ⚠ exhausted | 15 | edit_round=10 read_files=5 | 10 | 74.4 | 165,915 | 4,776 |
| 10 | E2E requirement 1/4 REQ-1 / Test Generation | 5 | edit_round=1 read_files=4 | 1 | 68.5 | 73,680 | 8,421 |
| 09 | Trigger design REQ-2 | 1 | proposal=1 | 1 | 60.0 | 7,347 | 9,698 |
| 05 | Backend API design REQ-2 | 1 | proposal=1 | 1 | 59.2 | 4,016 | 8,819 |
| 01 | Visual analysis register.png | 1 | proposal=1 | 1 | 57.2 | 1,327 | 2,871 |
| 08 | UI 1/3 home / Implementation | 3 | context_query=1 edit_round=1 read_files=1 | 1 | 56.4 | 36,359 | 7,301 |
| 10 | E2E requirement 2/4 REQ-2 / Interaction Implementation | 2 | edit_round=1 read_files=1 | 1 | 54.7 | 62,069 | 7,827 |
| 07 | UI/data design 2/4 REQ-2 | 1 | proposal=1 | 1 | 54.5 | 3,743 | 7,393 |
| 10 | Independent acceptance / REQ-3 / Generation | 9 | edit_round=5 read_files=4 | 5 | 51.7 | 90,710 | 4,907 |
| 10 | Independent acceptance / REQ-2 / Generation | 7 | edit_round=2 read_files=5 | 2 | 50.1 | 92,575 | 5,950 |

## Slowest 10 single calls

| Stage | Activity | s | Prompt tok | Compl tok | Reasoning tok | Finish |
|---|---|---:|---:|---:|---:|---|
| 09 | Trigger design REQ-2 · Model proposal 1/10 | 60 | 7,347 | 9,698 | 8,875 | stop |
| 05 | Backend API design REQ-2 · Model proposal 1/10 | 59 | 4,016 | 8,819 | 6,738 | stop |
| 01 | Visual analysis register.png · Model proposal 1/10 | 57 | 1,327 | 2,871 | 2,186 | stop |
| 08 | UI 2/3 registration / Implementation · Read files | 55 | 13,123 | 6,571 | 1,550 | stop |
| 07 | UI/data design 2/4 REQ-2 · Model proposal 1/10 | 54 | 3,743 | 7,393 | 5,106 | stop |
| 09 | Trigger design REQ-3 · Model proposal 1/10 | 46 | 5,576 | 6,482 | 5,775 | stop |
| 08 | UI 1/3 home / Implementation · Context query | 41 | 12,217 | 6,225 | 3,245 | stop |
| 01 | Visual analysis homepage.png · Model proposal 1/10 | 40 | 1,318 | 3,066 | 2,335 | stop |
| 10 | E2E requirement 2/4 REQ-2 / Interaction Implementation · Read files | 39 | 31,187 | 5,843 | 4,972 | stop |
| 01 | Visual analysis login.png · Model proposal 1/10 | 37 | 1,327 | 2,295 | 1,559 | stop |
