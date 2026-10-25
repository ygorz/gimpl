# Iteration Log: DEMO1 Check Agent

Each run is scored against `docs/rubric.md` (pass = 3 or higher on every dimension plus both binary gates). The workflow is defined in `docs/prd.md`.

Scores use the rubric's dimensions: Coverage (AC1), Verdicts (AC2), Restore (AC3), Report (AC4).

| Run ID | Date | Agent/tool used | Prompt or command used | Cycle time | Rubric scores with brief notes | Pass/fail result | Review latency | Cost per run (tokens if available) | Observations (what worked, what failed, what changed between runs) |
|---|---|---|---|---|---|---|---|---|---|
| 001 | 2026-10-24 | Claude Code (Opus 5.5, plus Haiku 5.5 for minor calls), in the sandbox container | `time claude "..."` with the Run 001 prompt (see Run prompts below) | 1m 32.5s (`real`) | Coverage 3: all four cases run with exit codes and key lines, but the exact command per case is not recorded. Verdicts 3: all four correct and based on exit codes; notes explain C and D but not B or A. Restore 3: sha256 matches before and after, dummy and backup gone, only the results file in git status; the evidence is in two separate sections, not side by side. Report 4: full table, clear verdict, plus useful notes (engine exit 255 is normal for a timedemo; full dummy sha256). Gates: no tracked-file edits, no commits. | Pass | 3m 43s | $0.29 (Opus: 524 input, 3.1k output, 403k cache read, 18.5k cache write; Haiku: 1.3k input, 172 output) | Passed on the first run, which I didn't expect from a baseline. The PRD's ordered actions and the exit-code convention were specific enough that the agent didn't need to guess. It fell short of 4 mainly because it reported each condition, not the command it ran, so a case can't be repeated in one step. The PRD never asked for commands, so that's a gap in my spec, not an agent mistake. Not anticipated by the PRD: the results file is dated 2026-10-25 because the container clock is UTC, so dates in the agent's output can be a day ahead of my local date. Also, `/tmp` still holds `cc-socks` and `claude-0`, which are Claude Code's own files, not workflow leftovers, so AC3's "no leftovers" should mean the dummy WAD and backup only. Realtics differed between A and D (132 vs 120) while gametics stayed at 4227, which confirms the check is right to compare gametics, not wall time. |

## Run prompts

The full prompt for each run is recorded here so any run can be repeated exactly.

### Run 001

```
Follow docs/prd.md to test the failure paths of scripts/demo1-check.sh. Run all four cases (A to D) in the order given in "Ordered actions", record each case's exit code and key output line, restore the WAD, and write the results to docs/smoke-tests/demo1-failure-paths.md. Do not edit any tracked files and do not commit.
```
