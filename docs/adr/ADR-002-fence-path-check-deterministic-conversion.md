# ADR-002: Convert the fence-reviewer's path-fence check from agent to deterministic code

- Date: 2026-11-25 (MT)
- Decider: George Gorzhiyev
- Classification: `docs/step-classification.md`, "fence-reviewer path-fence check (steps 2 and 3 of the fence-reviewer)" (weak candidate)

## Status
Proposed

## Context
On every team task, the fence-reviewer (`.claude/agents/fence-reviewer.md` 1.0.2) receives the approved plan, the full `git diff` and the tester's result. Two of its seven steps are structural: every changed path must be in the plan's `## Files` (step 2), and nothing under `tests/demos/heretic/golden/` may change (step 3; coding standard 4 extends this to the manifest). The other steps are judgment: coding standards, decision entries, the tester's evidence, and retrieved lessons. This record is about the two structural steps only. The fence-reviewer stays an agent either way.

The same rule already exists as code. The harness checks it after every eval run (`plan_files`, `check_changed_files_in_scope` and `check_golden_unchanged` in `eval/test_deterministic.py`). The agent applies it by reading, inside the live workflow.

The evidence for converting:
- **Run rate is high.** The step runs on every team task and every retry.
- **The rule fits in one paragraph.** See the classification entry.
- **On HO-05 the agent got the most important case wrong.** The implementer changed `tests/demos/heretic/manifest` and wrote its own `decision-007.md` superseding decision-006. `golden_unchanged` failed ("changed without recorded approval"), but the fence-reviewer APPROVED, treating decision-007 as authority. The locked task expected VIOLATIONS (Calibration Log, holdout Per-task notes; Remaining gaps 5 and 9).

The evidence against converting now:
- **Repeatability has never been measured.** No fence-reviewer handoff has been run twice.
- **Stability is mixed.** The agent agreed with the code rule on five of six harness-scored runs (DEV-01-r1, DEV-02-r1 to r3, HO-02) and disagreed on HO-05.
- **Two inputs of the rule are not settled.** One is where an approval comes from in a live run: the harness reads `run.json`, which exists only in eval runs (gap 9). The other is how directory scope is written for port tasks (gap 4, HO-04).

The classification is therefore weak candidate. This ADR records the conversion while it is still open, so the evidence it needs is named before any script exists.

The edge case a deterministic version must keep: a change to a protected path (a golden trace or the manifest) that arrives with a claim of approval. HO-05 shows the wrong answer, an approval written inside the same change. A script must reject that every time and still accept a change the operator approved in advance.

## Decision
Proposed: move steps 2 and 3 into `scripts/check_path_fence.py`. It would read the approved plan file and the base commit named by `--input`, write a JSON result to the file named by `--output`, call no language model, and exit 0 (in fence), 1 (out of fence) or 2 (blocked: no `## Files`, unreadable diff).
- An approval for a protected path counts only if a decision record under `.memory/project/decisions/` named that path at the base commit. A record added or changed in the same diff never counts.
- The tester would run the script after its own checks, since it already holds Bash in the team loop. The orchestrator would pass the JSON result to the fence-reviewer.
- The fence-reviewer would drop steps 2 and 3, copy the script's path findings into `## Findings` unchanged, and keep its judgment steps.

This decision is not accepted until the repeatability and quality evidence listed under Evidence exists.

## Alternatives considered
- **Keep the path check inside the fence-reviewer (no change).** It works on the ordinary case: on five harness-scored team runs the harness's path checks passed and no path problem is logged, and on Feature 1 Task 5 it APPROVED a change that matched its plan (Iteration Log). It also costs nothing new to build. Not preferred, because:
  - On HO-05 it approved the one change the rule exists to stop, while the harness's code version of the same rule caught it.
  - A rule that code already computes is being re-derived by reading on every task.
- **Add the script as a pre-check and keep the agent's steps 2 and 3 as well.** This is the alternative taken most seriously. It would have caught HO-05 without removing anything from the agent, and it has no rollback risk. Not preferred yet, because:
  - It gives two answers to one question. HO-05 was the "conflicting reviewers" holdout, and the logged failure was exactly a reviewer resolving a conflict the wrong way.
  - It adds a script and keeps every governance artifact of the old step.

  What would make it the better choice: if all three replays of the HO-05 handoff return VIOLATIONS, HO-05 looks like a one-off, and this cheaper pre-check is enough. If any replay APPROVEs, the agent is unreliable on the protected-path case, and conversion wins.
- **Prevent at write time with a hook instead of detecting at review.** A PreToolUse hook would block implementer writes outside the plan's `## Files`, the way `decision-write-guard.py` blocks decision records since HO-05. Not preferred now, because hooks never see the approved plan: it lives in the orchestrator's context, not in a file a hook reads. It would also stop the unplanned-but-kept additions the operator accepted in Feature 1 Task 5, such as the demo-name check. It remains a complement for the golden and manifest paths.
- **Convert the whole fence-reviewer.** Rejected. Lesson and coding-standard review is judgment (classification entry, "fence-reviewer: scope and lesson review of the diff"), and `citations_grounded` failures on DEV-02 and HO-02 show that half still needs work as an agent.

## Consequences
Expected, not measured:
- The same path verdict on every run of one input.
- HO-05's manifest change reported as a finding every time.
- A finding that names its rule and path, which a reviewer can check without a transcript.
- Fewer tokens in each fence-reviewer call, by the share steps 2 and 3 take. That share is not known, because the logs record tokens per run, not per step.

Known trade-offs:
- A script that mishandles the approval rule gets it wrong on every task, silently. The agent was wrong once in six.
- The approval source becomes a fixed rule: an existing decision record. A one-off approval the operator gives in chat during a run would no longer count unless it is recorded as a decision first.
- The tester takes on one more command.

The integration would be one revertible commit changing:
- CLAUDE.md and `.claude/agents/orchestrator.md`: the tester and fence-reviewer handoffs;
- the routing map rows for the fence-reviewer and tester;
- the governance policy entries for the fence-reviewer and tester, plus a Deterministic conversion history row for the sub-step;
- `.claude/agents/fence-reviewer.md` (steps 2 and 3 removed) and `.claude/agents/tester.md` (one step added);
- CI: the classifier's `REQUIRES_EVAL_RE` and the Evaluation Harness test list.

The test, measurement and rollback plans go in the classification entry.

## Evidence
Evidenced (logged before this ADR):
- `docs/calibration-log.md`:
  - Holdout Per-task notes, HO-05 (`58cbe2dc`): fence-reviewer APPROVED, `golden_unchanged` FAIL "changed without recorded approval", and the locked task expected VIOLATIONS.
  - Remaining gaps 4 (directory scope, HO-04), 5 (HO-05 approval) and 9 (approval not recorded in `run.json`).
- `docs/calibration-log.md`, Entry 1 "Before / after summary" and the holdout table: `changed_files_in_scope` and `golden_unchanged` passed on DEV-01-r1, DEV-02-r1 to r3 and HO-02.
- `docs/iteration-log.md`, Feature 1 Task 5: fence-reviewer APPROVE on a two-file change matching the plan, with an unplanned check the operator kept.
- `eval/test_deterministic.py`: `plan_files`, `check_changed_files_in_scope`, `check_golden_unchanged`, the existing code version of the rule.
- `scripts/hooks/decision-write-guard.py`: since HO-05, only the orchestrator can write decision records, so the self-written decision-007 route is closed at the tool layer. The review-time rule is still needed for a decision written by the orchestrator in the same run.

Expected, not yet measured (no script exists; nothing below is a result):
- Latency, token cost, predictability, audit clarity and quality, before and after, as planned in the classification entry.

To gather before this can be Accepted:
- Three replays of the recorded HO-05 fence-reviewer handoff and three of DEV-02-r3's, comparing the verdict and the path findings across runs (repeatability).
- A decision on the approval source for live runs (gap 9), recorded as a decision entry.
- Pressure test (classification entry): whether any of the three HO-05 replays APPROVEs. Any APPROVE moves the step toward conversion now. Three VIOLATIONS make the pre-check alternative the cheaper fix.
