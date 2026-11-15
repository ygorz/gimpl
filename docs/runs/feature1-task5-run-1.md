# Run summary: Feature 1 Task 5 (runner), run 1

- Task: Feature 1 Task 5 in `docs/smoke-tests/demo-suite.md`: replace the stub body of `scripts/demo-suite.sh` with the real runner.
- Branch: feature/per-tic-demo-suite
- Date: 2026-11-14 (given by George; America/Denver)
- Outcome: **Accepted**. Stopped at the commit checkpoint.
- Agent versions: orchestrator 1.1.0 (main session, CLAUDE.md v0.1.6); planner 1.0.0, implementer 1.0.0, tester 1.0.0, fence-reviewer 1.0.0 (all sonnet).
- Evidence: real `scripts/demo-suite.sh` output. There was no evidence gap, because this task builds the runner, so no substitute check was needed. The Task 4 one-off exception did not apply.

## Human approvals
After the planner, George approved the plan and answered its open questions:
1. No env overrides for paths or the binary now. Forced-failure runs wait for Task 7 and use temp copies outside the repo.
2. An engine exit code other than 0 or 255, or no `timed N gametics` line (for example a missing-mobj `I_Error`), exits 2 and prints the engine output, matching `demo1-check.sh`.
3. On a tic count mismatch, the runner still runs the per-tic comparison and names the first differing tic.
4. The runner loops over every manifest line.
5. The "Done" date in `demo-suite.md` is 2026-11-14. The container clock (UTC) read a day ahead.

## Phases
| Phase | Result | Gate decision |
|---|---|---|
| planner | 7-step plan. Files: `scripts/demo-suite.sh`, `docs/smoke-tests/demo-suite.md`. 5 open questions. | Passed apart from the open questions, which George answered (above). Plan approved. |
| implementer | Wrote both files. `## Not done`: None. | Passed. `git status`/`git diff` showed only the two planned files changed. The script is still executable. No diff under `tests/`, `src/`, `.memory/` or `scripts/demo1-check.sh`. |
| tester | PASS. `demo-suite.sh`: `IWAD OK`, `trace OK` (537e8a1f…2f30), `timed 4227 gametics`, `engine exit code: 255`, `PASS: demo1 4227 gametics, trace matches`, `PASS: 1 demo(s)`, script exit 0. Cross-check `demo1-check.sh`: `PASS: 4227 gametics == expected 4227`, exit 0. `grep -c 537e8a1f scripts/demo-suite.sh` = 0. Golden sha256 unchanged. In temp copies outside the repo: missing binary, exit 2; trace sha mismatch, exit 2; forced FAIL `gametic 100: p0.armor expected 99 got 0`, exit 1. No rebuild was needed. The tester changed nothing. | Passed. |
| fence-reviewer | APPROVE. Findings: none. Noted that the doc title still said "Feature 1 stub", which the plan did not cover. Not a violation. | Passed. |

Retries: none. Escalations: none. Golden traces: unchanged.

## Unplanned addition (accepted)
The implementer added a check the plan did not list: a manifest demo name must match `^[A-Za-z0-9_]+$`, otherwise the runner exits 2. The fence-reviewer accepted it, and George accepted it on 2026-11-14 because the demo name becomes a file path (`tests/demos/heretic/golden/<demo>.tics` and the temp trace path). It stays.

## Post-review change (doc only)
After the fence-reviewer's APPROVE, George asked for the title fix on 2026-11-14. The implementer changed line 1 of `docs/smoke-tests/demo-suite.md` from `# Per-tic demo suite (`scripts/demo-suite.sh`) - Feature 1 stub` to `# Per-tic demo suite (`scripts/demo-suite.sh`)`. The Orchestrator checked `git diff` and confirmed line 1 is the only new hunk in that file. The change is doc-only: no script, test or golden change. The tester and fence-reviewer were not re-run for it.

## Memory update
George approved it on 2026-11-14. The Orchestrator updated `.memory/project/current-state.md`:
- Task 5 is done and the runner is real.
- The Task 4 exception is now described in the past tense.
- `demo1-check.sh` is kept as a cross-check.
- The next action is Task 7.

The Orchestrator also updated the matching current-state pointer in `.memory/project/MEMORY_INDEX.md`. No commit SHA is recorded for this change.

## What George decided
1. George commits these together, in one commit: `scripts/demo-suite.sh`, `docs/smoke-tests/demo-suite.md`, this run summary, `.memory/project/current-state.md` and `.memory/project/MEMORY_INDEX.md`. George runs git himself. `lesson-4-lab-submission.patch` stays out.

## Next in the task list
Feature 1 Task 7 (recorded failure-path runs) is next in `docs/smoke-tests/demo-suite.md`. It has not been started.
