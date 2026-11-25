# Current State - Module 4 on master

**Scope:** Workflow (Module 4 lessons and exercises; archive when Module 4 is done and the Capstone branch starts)
**Branch:** master
**Last updated:** 2026-11-25 (commit status of anything below: check git, which wins over this file; CLAUDE.md v0.1.10)

## Where things stand
- Feature 1 (per-tic demo suite) merged to master in 89cab71b (2026-11-16). Its final state is archived in `archive/2026-11-16-feature1-current-state.md`.
- Module 3 calibration merged in dc39e0ad (2026-11-17): evaluation harness v3, the orchestrator guard hook, and `docs/calibration-log.md` (Entry 1 and the holdout pass at 432e6797).
- Module 4 governance merged in 52769703 (2026-11-24): `docs/governance-policy.md` v1.4.0 with one entry for each of the 8 roles in `.claude/agents/`, two-layer enforcement (container permissions in `scripts/run-agent.sh` plus the storage and retrieval `_authorize()` allow-lists), red-team prompts 9 of 9 blocked, `eval/test_policy.py`, and the trace-auditor role (Lesson 4.1 Exercise 1). `docs/adr/ADR-000-module-4-repo-decision.md` records that GIMPL stays the Module 4 repository.
- Module 4 CI merged through PRs #1, #2, #4 and #5 (2026-11-25): `.github/workflows/ci.yml` has six jobs (Change Classifier, Policy Test Suite, Evaluation Harness, Advisory Code Review, Pipeline Integrity Check, audit trail), designed in `docs/ci-step-design.md`. Branch protection on master requires the Change Classifier, Policy Test Suite, Evaluation Harness and Pipeline Integrity Check. The advisory reviewer's key is read only from `CI_REVIEWER_OPENROUTER_KEY`.
- Lesson 4.3 on branch `m4/convert-demo-verifier` (2026-11-25): `docs/step-classification.md` classifies 13 workflow steps; `demo-verifier` was converted to `scripts/verify_demos_deterministic.py` under `docs/adr/ADR-001-demo-verifier-deterministic-conversion.md` (Accepted). `docs/governance-policy.md` is v1.5.0 with 7 roles; the evidence is in `docs/calibration-log.md` Entry 2. Merge status: check git.
- Open calibration gaps are listed in `docs/calibration-log.md`, "Remaining gaps". That log and git win over this file.

## Next action
Lesson 4.3 Exercise 1: assess the fence-reviewer's structural path checks as a second conversion candidate in `docs/step-classification.md` and record ADR-002 at Proposed only, on branch `m4/ex-second-conversion`. Next step-classification review: 2026-12-25.

## Deferred (do not reopen without a human decision)
- Pinned C reference build (Approach 2): deferred in decision-001.
- DEMO2 and DEMO3: out until DEMO1 works end to end.

## Open questions
- DEMO3 is still deferred (2582 gametics, not yet pinned). Open: when to pin it.
- Rebuild before trace: whether "clean rebuild at a recorded commit before generating any reference trace" becomes a standing rule (for example an amendment to decision-004, or a check in the runner). Not a rule yet; needs a human decision.
