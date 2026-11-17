# Run summary: Feature 1 Task 4 (manifest), run 1

- Task: Feature 1 Task 4 in `docs/smoke-tests/demo-suite.md`: add `tests/demos/heretic/manifest`.
- Branch: feature/per-tic-demo-suite
- Date: 2026-11-14 (given by George)
- Outcome: **Accepted**, under a one-off Task 4 exception (below). Stopped at the commit checkpoint.
- Agent versions: orchestrator 1.0.0 (main session); planner 1.0.0, implementer 1.0.0, tester 1.0.0, fence-reviewer 1.0.0 (all sonnet).

## Human approvals
- Before the run: George approved writing `tests/demos/heretic/manifest` with the values in decision-006, under coding standard 4. He did not approve any change to `tests/demos/heretic/golden/`.
- After the planner, George answered the plan's open questions:
  1. Format approved: `#` comment lines, then one line per demo with 4 space-separated fields, `<demo> <gametics> <trace_sha256> <source_commit>`.
  2. Full 40-character source commit SHA, matching decision-006.
  3. **One-off exception, not a rule change:** for Task 4 only, `scripts/demo1-check.sh` plus the trace sha256 check is accepted as DEMO1 evidence. `scripts/demo-suite.sh` is still a stub until Task 5. The workflow's "real demo-suite.sh output at 4227 gametics" criterion still applies to every other task.
  4. `lesson-4-lab-submission.patch` stays out of this change.

## Phases
| Phase | Result | Gate decision |
|---|---|---|
| planner | Plan: create the manifest; mark item 4 Done in demo-suite.md. Files: `tests/demos/heretic/manifest`, `docs/smoke-tests/demo-suite.md`. 4 open questions. | Passed apart from the open questions, which George answered. Plan approved. |
| implementer | Wrote both files. `## Not done`: None. | Passed: `git status`/`git diff` showed only the two planned files changed, the manifest matched the approved content byte for byte, and nothing changed under golden/, src/, scripts/ or .memory/. |
| tester | PASS. Manifest data line correct (4 fields). `sha256sum golden/demo1.tics` = `537e8a1fd73967c0099d1ee55c0586e353d5240d27dd3a41dfa15ac3757d2f30` = manifest field 3. Source commit exists. `demo1-check.sh`: `timed 4227 gametics`, engine exit 255 (normal, decision-006), `PASS: 4227 gametics == expected 4227`, script exit 0. demo-suite.sh stub exit 0, not DEMO1 evidence. Tester changed nothing. | Passed under the Task 4 exception. |
| fence-reviewer | APPROVE. Findings: none. | Passed. |

Retries: none. Escalations: none. Golden traces: unchanged.

## What George decided next
1. George commits these together, in one commit: `tests/demos/heretic/manifest`, `docs/smoke-tests/demo-suite.md`, this run summary, `.memory/project/current-state.md` and `.memory/project/MEMORY_INDEX.md`. George runs git himself. `lesson-4-lab-submission.patch` stays out.
2. George approved the memory update to `.memory/project/current-state.md` (Task 4 done, manifest is the source of truth for the trace sha256 and source commit per decision-006, next action Task 5). The Orchestrator made it on 2026-11-14, with no commit SHA recorded. The current-state pointer in `MEMORY_INDEX.md` was updated to match so it is not stale.
