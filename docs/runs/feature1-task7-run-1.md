# Run summary: Feature 1 Task 7 (failure-path runs), run 1

- Task: Feature 1 Task 7 in `docs/smoke-tests/demo-suite.md`: record a PASS run and forced FAIL runs (edited trace, bad sha256) of `scripts/demo-suite.sh`, as done for `demo1-check.sh`.
- Branch: feature/per-tic-demo-suite
- Date: 2026-11-16 (given by George; America/Denver)
- Outcome: **Accepted**. Stopped at the commit checkpoint.
- Agent versions: orchestrator 1.1.1 (main session, CLAUDE.md v0.1.7); planner 1.0.1, implementer 1.0.1, tester 1.0.1, fence-reviewer 1.0.1 (all sonnet).
- Evidence: real `scripts/demo-suite.sh` output (DEMO1 at 4227 gametics). No evidence gap and no substitute check.

## Human approvals
George approved the plan on 2026-11-16 and answered its open questions:
1. Tester runs before and after the Implementer, for this task only: the Implementer can't run anything and the Tester can't edit, so the evidence must come from the Tester's real output.
2. The Tester may delete only the `mktemp -d` folder it created and must show it is gone. Nothing else.
3. Run the two required failures plus the optional cases O1-O5, clearly marked optional.
4. File name `docs/smoke-tests/demo-suite-failure-paths.md`, no suffix.
5. Write this run summary. Plan step 8 dropped: the main session updates `current-state.md` and `MEMORY_INDEX.md` only after George approves the commit.

Also: list each retrieve query and whether it matched by vector or fallback (below).

## Phases
| Phase | Result | Gate decision |
|---|---|---|
| planner | 8-step plan. Files: `docs/smoke-tests/demo-suite-failure-paths.md`, `docs/smoke-tests/demo-suite.md`. Temp-tree route: the runner resolves ROOT from its own location, so a copy at `$T/scripts/demo-suite.sh` runs against a `mktemp -d` tree with no script change. 5 open questions. | Passed apart from the open questions, which George answered. Orchestrator flagged step 8 (memory writes by the Orchestrator) as outside its write grant; George dropped it. |
| tester run 1 (recording) | PASS. A: `timed 4227 gametics`, `engine exit code: 255`, `PASS: demo1 4227 gametics, trace matches`, `PASS: 1 demo(s)`, EXIT=0; `demo1-check.sh` EXIT=0. B (temp trace gametic 100 p0 armor 0 -> 50, temp manifest sha updated): `gametic 100: p0.armor expected 50 got 0`, EXIT=1. C (temp manifest sha 64 `a`): `sha256 mismatch`, no `timed` line, EXIT=2. O1-O5 (optional): exits 2, 2, 1, 2, 2 as expected. Golden sha256 537e8a1f…2f30 and manifest sha256 88b799ac…5ca3 identical before/after. No rebuild. | Passed. Orchestrator `git status`/`git diff` clean apart from the pre-existing untracked `lesson-4-lab-submission.patch`. |
| implementer | Wrote both planned files from the Tester's verbatim evidence. `## Not done`: None. Lesson stored: entry_id `ed414a8c-7ce0-4e35-981f-c429a6217a1e`, "Forced edited-trace FAIL needs temp manifest sha256 updated; suite runs from a temp tree" (internal). | Passed. `git status`/`git diff` showed only `docs/smoke-tests/demo-suite.md` (item 7 only) and the new doc. Recorded results checked against Tester run 1. |
| tester run 2 | PASS. `demo-suite.sh` 4227 gametics, EXIT=0; `demo1-check.sh` EXIT=0; sha256s unchanged; `git status` shows only the two planned docs (plus the pre-existing patch file). | Passed. |
| fence-reviewer | APPROVE. Findings: none blocking. Three minor notes (below). | Passed. |

Retries: none. Escalations: none. Golden traces and manifest: unchanged.

## Disclosed deviations
- Case B first attempt: the Tester edited field 10 (p0 momy) instead of field 12 (armor). The runner correctly reported `gametic 100: p0.momy expected 999 got 00000000`, EXIT=1. Case B was rerun with field 12. Both are recorded in the doc.
- Two `mktemp -d` folders, not one, because of that rerun (`/tmp/tmp.qFd8syCGjK`, `/tmp/tmp.9kOLqfUPvM`). Both were the Tester's own, both were deleted and shown gone (`test -e` exit 1), nothing else was deleted. The fence-reviewer judged this within George's approval; George's answer said "the mktemp -d folder", singular, so it is noted here.
- Sequence reorder (Tester, Implementer, Tester): one-off for this task, approved by George. Not a standing rule.

## Fence-reviewer minor notes (non-blocking)
1. The doc's "Exact commands (repeatable…)" section includes `cp` restore commands taken from the Orchestrator's brief; the Tester said it restored fresh copies before each case but did not print its exact commands. A note such as "reconstructed from the brief" would be more accurate. Applied after review (see below).
2. The "No build was done" claim was not in the summary the fence-reviewer received. It is in Tester run 1's Step 1 evidence (binary dated 2026-11-07 21:23:48 UTC, no newer `.c`/`.h`/`.am` under `src/`); the gap was in the Orchestrator's brief, not the doc.
3. O1, O2 and O4 appear as key lines in the table only, without full output blocks. Acceptable because the table is not labelled verbatim.

## Post-review change (doc only)
George asked on 2026-11-16 for fence note 1 to be applied. The implementer changed one line of `docs/smoke-tests/demo-suite-failure-paths.md` (line 149) from "Restore fresh copies before each forced case:" to "Restore fresh copies before each forced case (reconstructed from the Orchestrator's brief; the Tester reported restoring fresh copies before each case but did not print its exact restore commands):". The `cp` commands are unchanged. Lesson stored: None (one-line wording fix). Because the file is untracked, the Orchestrator checked it with a read-only `git diff --no-index` of the whole file against the previously reviewed text: exactly one changed line, still 197 lines. The change is doc-only (no script, test, manifest or golden change), so, as in Task 5, the tester and fence-reviewer were not re-run for it.

## Retrieve queries
All calls used `project_id: "proj-lessons"`, `classification_ceiling: "internal"`. The server reported every result as `retrieval_method: "keyword"` with `similarity_score: null`. No result matched by vector. (The planner's plan wrote "fallback" for these; the server's label is "keyword".)

| Role | Query | top_k | Results (source_document, chunk_index) | Match |
|---|---|---|---|---|
| planner | "forced failure runs temp copies manifest exit codes evidence recording" | 5 | lesson-exit-255-normal.md 0; lesson-missing-mobj-ierror.md 1; lesson-evidence-gap-substitute-check.md 2; lesson-exit-255-normal.md 2; lesson-manifest-format.md 0 | all keyword, score null |
| planner | "dates container clock UTC ahead; record evidence verbatim tester implementer" | 4 | lesson-container-clock-utc.md 0; lesson-container-clock-utc.md 1; lesson-evidence-gap-substitute-check.md 2; lesson-evidence-gap-substitute-check.md 1 | all keyword, score null |
| fence-reviewer | "forced failure runs in temp copies, exit codes, recording evidence verbatim, dates in docs" | 5 | lesson-evidence-gap-substitute-check.md 2; lesson-exit-255-normal.md 0; lesson-missing-mobj-ierror.md 1; lesson-exit-255-normal.md 2; lesson-evidence-gap-substitute-check.md 1 | all keyword, score null |

The query texts and per-result methods are as each subagent reported them from its tool results; the Orchestrator has no retrieval tools and did not see the raw results.

## What George must decide next
1. Commit: review the diff (`docs/smoke-tests/demo-suite.md` item 7, new `docs/smoke-tests/demo-suite-failure-paths.md`, this run summary) and commit if approved. George runs git himself.
2. After the commit: approve the main session updating `.memory/project/current-state.md` (Task 7 done, next action Task 8) and the `MEMORY_INDEX.md` pointer.
3. The untracked `lesson-4-lab-submission.patch` is not part of this task and was left alone.
