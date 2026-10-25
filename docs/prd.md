# PRD: DEMO1 Check Agent

## Workflow description
This workflow checks that `scripts/demo1-check.sh` handles failure correctly by running it under four controlled conditions (a good, missing, or wrong game data file, called the WAD, plus a forced tic-count mismatch), reporting whether each gives the expected exit code, and restoring the repo afterward.

## Why this task
- It tests the failure paths of `demo1-check.sh`, which were flagged as untested in Lesson 1.2 (only the PASS path has been run).
- It is narrow enough to score from one run: one agent, one existing script, no code changes, and every result is an exit code or a line of output.
- It was chosen over porting a function such as `P_GiveArtifact`, which would edit `src/`, need multi-file planning, and be hard to score in a single run. That work is deferred to Feature 2.

## Trigger
A developer (me) starts the workflow manually by invoking Claude Code from the repo root with the run prompt recorded for each run in `docs/iteration-log.md`. The condition is that the engine is already built (`src/chocolate-heretic` exists). There is no automated hook for this module.

## Decision events
The script's exit code decides each case (from its header: 0 = PASS, 1 = FAIL, 2 = setup or precondition error).
- If the real wad is in place and the demo runs 4227 tics (Case A), the script should exit 0 with `PASS`, and the agent records it as a match.
- If the wad is missing (Case B), the script should exit 2 with `ERROR: wads/blasphem.wad is missing`, and the agent records it as a match.
- If the wad's sha256 doesn't match the pinned value (Case C), the script should exit 2 with a `sha256 mismatch` error before running the demo, and the agent records it as a match.
- If the tic count doesn't match `EXPECTED_TICS` (Case D, forced with `EXPECTED_TICS=1`), the script should exit 1 with `FAIL`, and the agent records it as a match.
- If any actual result differs from what's expected, the agent reports it as a mismatch and keeps going with the remaining cases. It does not edit the script or attempt a fix.

## Ordered actions
1. Record the sha256 of `wads/blasphem.wad`.
2. Record the output of `git status --short`.
3. Case A: run `scripts/demo1-check.sh` with the real wad and record the exit code and key output line.
4. Move the real wad to `/tmp/blasphem.wad.bak`.
5. Case B: run the script with the wad missing and record the exit code and key output line.
6. Create a small dummy file at `wads/blasphem.wad`.
7. Case C: run the script with the dummy wad and record the exit code and key output line.
8. Delete the dummy file and move the real wad back from `/tmp/blasphem.wad.bak`.
9. Recompute the wad's sha256 and confirm it matches step 1.
10. Case D: run `EXPECTED_TICS=1 scripts/demo1-check.sh` and record the exit code and key output line.
11. Run `git status --short` again and compare it with step 2.
12. Write `docs/smoke-tests/demo1-failure-paths.md` with a results table (case, condition, expected exit, actual exit, key output line, match yes/no) and a one-line overall verdict.

## Acceptance criteria
- **AC1 Coverage:** all four cases are run, and each one has its exit code and key output line recorded.
- **AC2 Correct verdicts:** A exits 0 with 4227 tics; B and C exit 2 with the matching `ERROR` message; D exits 1 with a `FAIL` line. Each match/mismatch call agrees with the actual exit code.
- **AC3 Clean restore:** afterward, the wad's sha256 equals `e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63`, no dummy file or backup is left behind, and the only change in `git status` is the new results file.
- **AC4 Clear report:** `docs/smoke-tests/demo1-failure-paths.md` exists, every table cell is filled, and a reader can tell the outcome of each case without rerunning anything.

## Edge cases (settled)
- "Restored" means the sha256 matches the pinned value, not just that a file with the right name exists.
- Exit code is the source of truth. The words PASS, FAIL, or ERROR alone don't count.
- Missing and wrong wads are expected to exit 2 (setup error), not 1. A run that calls them "FAIL with exit 1" is wrong on AC2.
- If the agent edits `scripts/`, `src/`, or any tracked file, the run fails AC3, even if the verdicts look right.
- A case that hangs, or a run that opens a window, counts as a failed case.
- If the agent commits anything, the run fails AC3. Only I commit, on the host.

## Out of scope
- Changing `demo1-check.sh` or any engine code.
- Testing other demos or wads.
- Build failures. A missing binary is a precondition, not a case.
