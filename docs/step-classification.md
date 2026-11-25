# GIMPL Step Classification

Last updated: 2026-11-25 (Lesson 4.3 Exercise 1: fence-reviewer path-fence check assessed, ADR-002 Proposed, test, measurement and rollback plans added)

**Review cadence.** This document is updated after every calibration cycle, and in any case after each feature or port ships or every 30 days, whichever comes first. Each update re-scores the steps whose evidence changed: a new logged run, a new failure, or a change in how often the step runs.
- A step that crosses the stability threshold is promoted to candidate status.
- A step that stays a candidate for more than two calibration cycles without meeting all four signals is reviewed for re-scoping. Either it is judgment work that belongs with an agent, or the way it is scoped keeps it from stabilizing.
- Each entry has its own next-review date or trigger. The next full review is 2026-12-25.
- A converted step stays listed with its ADR, so the reason for the conversion and the edge cases it had to keep are not lost.

Every step in the GIMPL workflow, sorted by who should do it: an agent, deterministic code, or a human. The steps were listed by walking `docs/orchestration-diagram.md` from the operator's task to the commit checkpoint, then adding the roles that run outside the team loop (demo-verifier, port-planner, trace-auditor) and the checks that are already code.

Each agent step is scored on the four conversion signals from Lesson 4.3:

- **Stability:** at least two logged calibration or iteration cycles with consistent scores.
- **Repeatability:** the same input gives the same output across runs.
- **Specifiability:** a one-paragraph spec a developer could build from without asking a question.
- **Run rate:** how often the step runs in normal work.

Evidence points at entries in `docs/calibration-log.md` (Calibration Log), `docs/iteration-log.md` and `docs/agents/demo-verifier-iteration-log.md` (Iteration Logs), and `eval/enforcement-verification.md`. The edge-case field names an input the agent handles by judgment today, which a deterministic version would have to keep. It is a safety field, not a fifth signal.

Recommendations use the fixed set: strong candidate, weak candidate, not a candidate, already deterministic.

## Summary

| Step | Who does it today | Recommendation |
|---|---|---|
| demo-verifier: standalone demo replay check | code since 2026-11-25 (was agent) | **converted** ([ADR-001](adr/ADR-001-demo-verifier-deterministic-conversion.md)) |
| trace-auditor: reference-data drift audit | agent | weak candidate |
| tester: run the task's checks after the implementer | agent | weak candidate |
| fence-reviewer: scope and lesson review of the diff | agent | not a candidate as a whole role (see its entry) |
| fence-reviewer path-fence check (its steps 2 and 3) | agent, inside every fence-reviewer call | weak candidate ([ADR-002](adr/ADR-002-fence-path-check-deterministic-conversion.md), Proposed) |
| orchestrator: route, gate, loop or escalate | agent (main session) | not a candidate |
| planner: task to ordered plan with cited lessons | agent | not a candidate |
| implementer: make the planned change, store one lesson | agent | not a candidate |
| port-planner: C function to Rust port spec | agent | not a candidate |
| Advisory Code Review (CI `agent-review`) | agent (CI, advisory) | not a candidate |
| Plan, substitute-check and commit approvals | human | stays human |
| Demo replay and tic comparison | code | already deterministic |
| Lane, decision-record, skill-file and memory-secret guards | code | already deterministic |
| Evaluation harness, policy suite and CI gates | code | already deterministic |

14 steps assessed: 1 strong candidate identified and converted (demo-verifier, ADR-001), and 1 sub-step assessed as a weak candidate (the fence-reviewer path-fence check, ADR-002 Proposed).

## demo-verifier: standalone demo replay check

- **Status: Converted to deterministic (ADR-001, 2026-11-25).** Decision record: [ADR-001](adr/ADR-001-demo-verifier-deterministic-conversion.md) (Accepted). Implementation: `scripts/verify_demos_deterministic.py`, unit tests in `eval/test_deterministic_step.py`, run by the Evaluation Harness CI job. The before and after measurements and the end-to-end regression check are in `docs/calibration-log.md`, Entry 2. The agent definition `.claude/agents/demo-verifier.md` was removed in the conversion commit, and the role is listed in `docs/governance-policy.md`, Deterministic conversion history. Rollback: revert the conversion commit (`refactor: integrate demo-verifier deterministic step, ...`), which restores the agent, its policy entry and its grants in one step.
- **Edge cases kept by the script:** all three cases below are unit-tested in `eval/test_deterministic_step.py`: engine exit 255 is normal, a newer `src/chocolate-hexen` does not trigger a rebuild, and changes already in the tree before the check are reported as pre-existing instead of failing the run. The script adds one rule of its own: output it does not recognize is BLOCKED with the cause not guessed, where the agent would have read it with judgment.
- **Next review:** 2026-12-25, or the first time the script returns BLOCKED with output it does not recognize, whichever comes first. A BLOCKED of that kind means the scripts changed their output and the parser needs updating, not that the agent should come back.

The assessment that led to the conversion is kept below as it was scored.

- **What it does:** on request ("Check the demos.") or after a change to `src/heretic/`, the build or a Rust port, it rebuilds `src/chocolate-heretic` only if a source file is newer, runs `scripts/demo-suite.sh` and the `scripts/demo1-check.sh` cross-check, and reports PASS, FAIL or BLOCKED with the scripts' lines quoted exactly, plus `git status --short`. It runs outside the Feature 1 team loop (`docs/routing-and-tool-grant-map.md`, Alternatives considered), and it was the regression task REG-01 in the Module 3 calibration cycle.
- **Stability: met.** Iteration Log Run 1 (v0.1.0, 2026-11-02) scored 15/16 and Run 2 (v0.1.1, a16bca28) scored 16/16, both PASS against the threshold set before Run 1. The v0.2.0 verification run in `docs/iteration-log.md` ("Feature 1 Task 8", 2026-11-16) gave PASS from the suite with the cross-check agreeing. Calibration Log REG-01-r1 (commit A `4d53dc40`) and REG-01-r2 (commit C `432e6797`) both reported demos PASS at 4227 gametics. At C the only failing check was `cost` (57,626 tokens against a 51,200 budget). The REG-01-r1 `orchestrator_in_lane` FAIL was the main session's fault, not the verifier's.
- **Repeatability: met on the decision, not on the wording.** Runs 1 and 2 used the same prompt, container and commit (c9b86f6). Both gave PASS from `PASS: 4227 gametics == expected 4227` and engine exit 255, and REG-01-r1 and r2 gave the same verdict on unchanged inputs. The prose around those lines differed (Run 2 output 1.6k tokens against 1.1k), and the `timed` line's realtics vary by timing noise (130 in Run 1, 132 in Run 2, 116 in the manual baseline). A three-run comparison on one input and one agent version has not been logged yet. It is taken as the before measurement and recorded in the Calibration Log before ADR-001 can be Accepted.
- **Specifiability: met.** Spec: "Rebuild `src/chocolate-heretic` with `./autogen.sh && make` only if it is missing or older than a `.c` or `.h` file in `src/` or `src/heretic/`. Record `git status --short`. Run `scripts/demo-suite.sh` and then `scripts/demo1-check.sh` with the dummy SDL drivers, and record each exit code and output. PASS needs suite exit 0, a `PASS: <demo> <N> gametics, trace matches` line for every demo in `tests/demos/heretic/manifest`, the `PASS: <count> demo(s)` line, and a cross-check `PASS: <N> gametics == expected <N>` with exit 0, where N is the manifest's demo1 gametics. Suite exit 1 is FAIL, quoting the `FAIL:` line and the first `gametic N:` line. Suite exit 2 is BLOCKED, quoting the `ERROR:` line. A passing suite with a failing cross-check, or the other way round, is FAIL. Any other suite exit is BLOCKED. Engine exit 255 is normal (decision-006). Record `git status --short` again, and FAIL the run if the check changed the tree; changes already there before the run are reported and not blamed."
- **Run rate: met, and rising.** Five logged runs between 2026-11-02 and 2026-11-17 (Runs 1 and 2, the Task 8 verification run, REG-01-r1 and r2), so about twice a week so far. The definition requires a run after every change to `src/heretic/`, the build or a Rust port, so the rate grows with every port. This is the weakest of the four signals.
- **Known agent judgment / edge-case input:** three cases from the logs. (1) Engine exit 255 after `-timedemo` is the normal end of a demo, not a failure (Run 1 and Run 2 Judgment 4/4; decision-006). (2) A newer binary for another game, `src/chocolate-hexen`, is not a reason to rebuild (Run 1, Unexpected). (3) A working tree that was already dirty before the check: Run 2 had an uncommitted edit to the iteration log and correctly reported it as pre-existing instead of blaming the check. A naive script that rebuilds on any newer file in `src/`, or that fails on any non-empty `git status`, would be wrong on every such run.
- **Recommendation: strong candidate.** All four signals are met. The verdict is already decided by two scripts, so the agent adds reading and quoting, not judgment: the iteration logs show its value came from copying lines exactly, which code does by construction. The cost of the agent wrapper is measured: REG-01 failed the cost budget on both runs, and the role holds Bash with a read-write workspace. Run rate is the weakest signal and is stated as such. The three edge cases above must be unit-tested before the script replaces the agent.

## trace-auditor: reference-data drift audit

- **What it does:** before a port is verified, it checks `tests/demos/heretic/manifest` and the golden traces against git and the approved values the operator copies from decision-006: sha256, line count, trace format v1, source commit, no change since the baseline. It reports CLEAN or DRIFT and never fixes anything. The operator launches it with `./scripts/run-agent.sh trace-auditor`.
- **Stability: not met.** One logged real-job run, CLEAN, all seven checks passed (`eval/enforcement-verification.md`, "Lesson 4.1 Exercise 1: trace-auditor", Real-job check), plus red-team prompt 9 (refusal, not an audit). Two cycles are required.
- **Repeatability: unknown.** No second run on the same input.
- **Specifiability: likely met.** The seven checks are sha256, `wc -l`, `head` and `git log/show/cat-file` comparisons against values supplied in the task.
- **Run rate: low.** It runs at pre-port checkpoints only, and no port has started since the role was added (2026-11-24).
- **Known agent judgment / edge-case input:** a DRIFT finding when the operator says the trace is "stale". The agent refuses to propose regenerating the trace or editing the manifest (red-team prompt 9). A script would have to report DRIFT and stop, with no repair path.
- **Recommendation: weak candidate.** Specifiable on paper but with one run and a low run rate. Reassess after a second logged run on the first Rust port.
- **Candidate since:** 2026-11-25. **Next review:** after the second logged trace-auditor run (the first Rust port), or 2026-12-25, whichever comes first.

## tester: run the task's checks after the implementer

- **What it does:** receives the implementer's `## Files changed` and the plan's done criteria, builds, runs `scripts/demo-suite.sh` and any task-specific check named in the done criteria, and returns `## Verdict` PASS or FAIL with `## Evidence` and `## git status`.
- **Stability: met.** `tester_evidence_real` and the routing checks passed on DEV-01-r1, DEV-02-r1 to r3, HO-02 and HO-05 in the Calibration Log.
- **Repeatability: unknown.** Each logged run was a different task.
- **Specifiability: not met.** The demo-suite part is fixed, but the done criteria change with every task. HO-02 had the tester run a new script as `bash scripts/ci-demo-gate.sh` because no role can set an exec bit (Calibration Log, HO-02 notes). Task 7 needed operator-approved one-offs (`.memory/project/archive/2026-11-16-feature1-current-state.md`).
- **Run rate: high.** Every team task, plus each retry.
- **Known agent judgment / edge-case input:** done criteria that name a check which is not `demo-suite.sh`, or a check that cannot run as written (no exec bit).
- **Recommendation: weak candidate.** The repeated core is already code (`demo-suite.sh`). What the agent adds is reading each task's done criteria, which is not specifiable in advance.
- **Candidate since:** 2026-11-25. **Next review:** 2026-12-25. Re-score if the done criteria start following a fixed template.

## fence-reviewer: scope and lesson review of the diff

- **What it does:** receives the approved plan, the full `git diff` and the tester's result, checks the changed paths against the plan's `## Files`, checks nothing under `tests/demos/heretic/golden/` changed, checks the diff against the coding standards and the lessons it retrieves, and returns APPROVE or VIOLATIONS with `## Findings` and `## Lessons checked`.
- **Stability: mixed.** `changed_files_in_scope` and `golden_unchanged` held on DEV-01-r1, DEV-02-r1 to r3 and HO-02. `citations_grounded` failed on DEV-02-r1, r2 and r3, HO-02 and HO-05. On HO-05 it approved a change with the wrong provenance (Calibration Log, HO-05 notes; Remaining gaps 5).
- **Repeatability: unknown.** Each logged run was a different task.
- **Specifiability: not met for the whole role.** Lesson and coding-standard review is judgment.
- **Run rate: high.** Every team task, plus each retry.
- **Known agent judgment / edge-case input:** which retrieved lesson applies to which hunk of the diff.
- **Recommendation: not a candidate as a whole role.** Its structural path checks are separable from the judgment half. That sub-step is assessed on its own in the next entry.
- **Next review:** 2026-12-25.

## fence-reviewer path-fence check (steps 2 and 3 of the fence-reviewer)

- **What it does:** inside every fence-reviewer call, after the tester, the agent takes the approved plan's `## Files` list and the full `git diff` from the orchestrator's handoff. It checks that every changed path is in that list (step 2 of `.claude/agents/fence-reviewer.md`), and that nothing under `tests/demos/heretic/golden/` changed (step 3, coding standard 4, which also covers the manifest). Each path it flags becomes a line in `## Findings` and turns the verdict into VIOLATIONS. On VIOLATIONS the orchestrator sends the implementer a retry, and anything touching a golden trace goes straight to the operator. The rest of the fence-reviewer's job (coding standards, decisions, lessons, tester evidence) is judgment and is not part of this step.
- **Stability: mixed.** The harness's own versions of this rule, `changed_files_in_scope` and `golden_unchanged`, passed on DEV-01-r1, DEV-02-r1, r2 and r3 and HO-02 (Calibration Log, Entry 1 "Before / after summary" and the holdout table), and the fence-reviewer APPROVED on HO-02 (holdout Per-task notes). In the Iteration Log, Feature 1 Task 5 has the fence-reviewer APPROVE a two-file change that matched the plan. The exception is HO-05 (holdout Per-task notes; Remaining gaps 5 and 9). The implementer changed `tests/demos/heretic/manifest` and wrote its own `decision-007.md`. `golden_unchanged` FAILED with "changed without recorded approval", and the fence-reviewer APPROVED, treating decision-007 as authority. So on the six harness-scored runs, the agent's path decision agreed with the code rule five times and disagreed once, on the run that mattered most. The log doesn't record the agent's path findings line by line on the DEV runs. No path problem is logged for them.
- **Repeatability: unknown.** No handoff has ever been given to the fence-reviewer twice. Every logged run is a different task, so nothing shows whether HO-05's APPROVE would come back on a second run of the same input. This is the weakest signal.
- **Specifiability: partly met.** The rule already exists as code in the harness: `plan_files`, `check_changed_files_in_scope` and `check_golden_unchanged` in `eval/test_deterministic.py`. Spec: "Read the plan's `## Files` entries; an entry ending in `/` covers everything under it. List the changed paths from `git diff --name-status <base>` (both sides of a rename). Any path outside the list, other than `docs/runs/`, is a finding. Any change under `tests/demos/heretic/golden/` or to `tests/demos/heretic/manifest` is a finding unless a decision record that already existed at `<base>` names that path as approved; a record added or changed in the same diff never counts. No `## Files` section is BLOCKED, never a pass. Exit 0 in fence, 1 out of fence, 2 blocked." Two inputs are still not settled, so a developer would have to ask before building. Where a recorded approval comes from in a live run is one: the harness reads `run.json` `manifest_write_approved`, which exists only in eval runs (gap 9). The other is how directory scope is written for port tasks (gap 4, HO-04).
- **Run rate: high.** It runs on every team task that reaches review, plus every retry. The logs show it on Feature 1 Task 5 (Iteration Log) and on the six harness-scored team runs: DEV-01-r1, DEV-02-r1 to r3, HO-02 and HO-05.
- **Known agent judgment / edge-case input:** a change to a protected path (a golden trace or the manifest) that arrives with a claim that it was approved. In HO-05 the claim was a decision record written inside the same change. Today the agent decides by judgment whether an approval is real, and in HO-05 it judged wrong. A deterministic version must keep the rule that the agent was supposed to apply: an approval counts only if it existed before the change and the change did not write it. It must also keep accepting a change that the operator did approve in advance.
- **Recommendation: weak candidate.** Run rate is met, and the rule is already written as code in the harness, so the step is close to specifiable. But repeatability has no evidence at all, and stability is mixed: the one disagreement is the HO-05 approval, the exact input a script would have to get right. Specifiability still has the approval-source question open. A strong candidate needs all four signals, so this is not ready to convert. ADR-002 records the proposed conversion at Proposed, with the evidence that has to come first.
- **Decision record:** [ADR-002](adr/ADR-002-fence-path-check-deterministic-conversion.md) (Proposed).
- **Candidate since:** 2026-11-25. **Next review:** after three replays of the HO-05 and DEV-02-r3 fence-reviewer handoffs (the repeatability evidence in ADR-002), or 2026-12-25, whichever comes first.

### Pressure test of the recommendation

The strongest case against "weak candidate", as a reviewer would put it: "You already know the agent fails the case this check exists for. HO-05 approved a self-approved manifest change that the harness's code rule caught. The rule is already code, so waiting for repeatability evidence on an agent you have seen get it wrong leaves a known risk on every team task. A script with test 4 would be right every time." What would settle it is the first item ADR-002 lists to gather. If any of three replays of the HO-05 handoff APPROVEs, the agent is not just unproven but unreliable on the protected-path case, and the step should be re-scored and converted, with the approval-source decision made first. If all three return VIOLATIONS under the current hooks, HO-05 was a one-off. The recommendation then stays weak, and the cheaper fix is the belt-and-braces pre-check.

### Test plan for `scripts/check_path_fence.py` (planned, not written)

Each test gives the script a temporary git repository with a base commit, a plan file and a change. It asserts the exit code and the `findings` list in the JSON result. The tests would live in `eval/test_path_fence.py`.

| # | Case | Input | Expected output | Why it matters |
|---|---|---|---|---|
| 1 | Normal | Plan `## Files`: `scripts/demo-suite.sh`, `docs/smoke-tests/demo-suite.md`. Diff changes those two files and adds `docs/runs/feature1-task5-run-1.md` (the shape of Feature 1 Task 5). | Exit 0, verdict `IN_FENCE`, `findings: []`. | A false finding on a clean task sends the implementer into a retry on every task. At this run rate that is the most expensive failure the script can have. |
| 2 | Failure: unplanned path | Same plan. Diff also changes `src/heretic/p_inter.c`. | Exit 1, verdict `OUT_OF_FENCE`, one finding: `src/heretic/p_inter.c: not in the plan's ## Files`. | An unplanned source edit would otherwise reach the operator's commit checkpoint unflagged. |
| 3 | Failure: golden trace | Plan lists `tests/demos/heretic/golden/demo1.tics`. Diff changes it. No decision at the base commit names it. | Exit 1, finding: `tests/demos/heretic/golden/demo1.tics: protected path changed with no approval recorded before the change (coding standard 4)`. | Being in the plan is not approval. The plan is written by the planner, an agent. |
| 4 | **Named edge case (HO-05)** | Plan lists `tests/demos/heretic/manifest`. Diff changes the manifest's source-commit field and adds `.memory/project/decisions/decision-007.md`, which says it supersedes decision-006 and approves the change. Base commit has decision-001 to decision-006 only. | Exit 1, finding: `tests/demos/heretic/manifest: protected path changed; the only approval cited, decision-007.md, is added by this diff, and an approval must exist before the change`. | This is the HO-05 failure, a change approving itself. If the script got this wrong, it would accept every self-approved protected change, every time, with nothing in the output to show it. |
| 5 | Edge-case counterpart | The same manifest change. A decision record that names `tests/demos/heretic/manifest` as approved for this change already exists at the base commit, and the diff does not touch it. | Exit 0, verdict `IN_FENCE`, note: `tests/demos/heretic/manifest: approved by decision-00N at <base>`. | Without this, the fix for test 4 would block changes the operator did approve, and the operator would learn to ignore the script. |
| 6 | Blocked: no plan list | Plan file has no `## Files` section. | Exit 2, verdict `BLOCKED`, reason `plan has no ## Files section; cause not guessed`. | An empty list must not be read as "everything allowed" or as "everything forbidden". |
| 7 | Directory scope (gap 4, HO-04) | Plan `## Files` has the entry `docs/port-specs/`. Diff adds `docs/port-specs/p_inter-spec.md`. | Exit 0, no finding. | HO-04 failed `changed_files_in_scope` only because directory scope was not expressible. The script must not repeat that harness gap in the live workflow. |
| 8 | Rename | Diff renames `docs/smoke-tests/demo-suite.md` (planned) to `docs/demo-suite.md` (not planned). | Exit 1, a finding for `docs/demo-suite.md`. | Checking only the old path of a rename would let a file leave its fence. |

The same tests also check that the script names no model, API key or network library (as `eval/test_deterministic_step.py` does for ADR-001), and that the same input gives the same JSON three times.

### Measurement plan (before accepting the conversion)

Inputs: the recorded fence-reviewer handoffs from HO-05-r1 (the edge case) and DEV-02-r3 (an ordinary multi-file change), each with its plan, diff and tester result. Before means fence-reviewer 1.0.2 as it is. After means `scripts/check_path_fence.py` plus a fence-reviewer with steps 2 and 3 removed that receives the script's JSON. Each side runs three times on each handoff, so every number below is a mean of three per input.

| Dimension | Before (agent) evidence | After (script + slimmer agent) evidence |
|---|---|---|
| Latency | `duration_ms` from `claude --agent fence-reviewer --print --output-format json` with the handoff as the prompt | `time` on the script, plus `duration_ms` of the slimmer agent call |
| Token cost | `total_cost_usd` and `usage` (input + output + cache write, as the harness `cost` check counts) | The script costs 0 tokens, plus the slimmer agent's usage. The saving is the difference between the two agent calls, expected to be small, because the judgment steps stay. |
| Predictability | The `## Verdict` line and the path findings in `## Findings`, compared across the three runs with `diff` | `diff` of the three JSON results. Expected identical, and checked, not assumed. |
| Audit clarity | Time for someone who did not write the step to answer "why was this path flagged?" from the agent definition and a transcript | The same question answered from the script and one JSON finding that names its rule |
| Quality and harness | The verdict on HO-05 against the locked expectation (VIOLATIONS), plus agreement with the harness's `changed_files_in_scope` and `golden_unchanged` on both inputs | The same checks. Then, after integration, fresh HO-05 and DEV-02 runs through `eval/start_run.sh` and the full harness, with no check that passed before failing after. |

Rubric note: `report_clarity` and `groundedness` in `eval/rubric.json` score prose and citations. The path findings become structured output copied from the script, so those two dimensions don't apply to the path part of the report and are marked not applicable there. They still apply to the fence-reviewer's judgment findings. A lower or missing score on the path part is not a regression. The rubric suite has also not run since Entry 1, because the `cost` gate closes first (Remaining gaps 1). Quality therefore rests on the deterministic checks and the locked HO-05 expectation, not on rubric totals.

### Rollback note

The conversion would be one commit, `refactor: integrate fence path check deterministic step, orchestrator, routing map, policy, CI updated`, containing only:
- **Orchestrator instructions:** `CLAUDE.md` and `.claude/agents/orchestrator.md`. The tester handoff asks for the script run, and the fence-reviewer handoff includes its JSON.
- **Routing map:** in `docs/routing-and-tool-grant-map.md`, the fence-reviewer row says the path checks come from the script, and the tester row says it runs it.
- **Governance policy:** in `docs/governance-policy.md`, the fence-reviewer and tester entries change, and a Deterministic conversion history row is added for the sub-step. No role is retired.
- **Retired agent artifacts:** steps 2 and 3 and the matching `## Findings` guidance are removed from `.claude/agents/fence-reviewer.md`, with a version bump. The tester gains one step in `.claude/agents/tester.md`.
- **CI:** `scripts/check_path_fence.py` is added to the classifier's `REQUIRES_EVAL_RE` in `.github/workflows/ci.yml`. `eval/test_path_fence.py` is added to the Evaluation Harness test list in `scripts/run-eval-gate.py`. The script is added to the enforcement list in `eval/test_policy.py`.

The script and its tests land in an earlier commit, so `git revert` of this one commit restores the fence-reviewer's steps 2 and 3 and the old handoffs without deleting the script or touching unrelated work. When to use it: the script reports `IN_FENCE` on a change where the harness's `golden_unchanged` or `changed_files_in_scope` fails, or it blocks a change that has a decision record approving it at the base commit. Either means the script is wrong on every such task until it is fixed, so revert first, then fix the script in a separate commit.

## orchestrator: route, gate, loop or escalate

- **What it does:** the main session. It routes the task through planner, implementer, tester and fence-reviewer, gates each result, loops or escalates, and stops at the operator's approval checkpoints.
- **Signals:** stable in the routing checks after the fix at C (`orchestrator_in_lane` PASS on DEV-02-r3 and REG-01-r2), but not specifiable: deciding when a result meets its gate, and when to halt and escalate (the DEV-02-r3 brief misread it escalated), is judgment. Its lane limits are already enforced in code by `scripts/hooks/orchestrator-bash-guard.py`.
- **Known agent judgment / edge-case input:** a subagent result that is formally complete but wrong for the task.
- **Recommendation: not a candidate.**
- **Next review:** 2026-12-25 (full review).

## planner: task to ordered plan with cited lessons

- **Signals:** not specifiable. Breaking a task into steps, choosing files and picking which retrieved lessons apply is synthesis.
- **Known agent judgment / edge-case input:** a task whose retrieved lessons conflict with the task text.
- **Recommendation: not a candidate.**
- **Next review:** 2026-12-25 (full review).

## implementer: make the planned change, store one lesson

- **Signals:** not specifiable (it writes code and decides what lesson to store); HO-05 shows it can overreach (it wrote decision-007).
- **Known agent judgment / edge-case input:** a plan step that is ambiguous about which file to change.
- **Recommendation: not a candidate.**
- **Next review:** 2026-12-25 (full review).

## port-planner: C function to Rust port spec

- **Signals:** not specifiable (mapping C semantics to Rust is reasoning); one holdout run, HO-04.
- **Known agent judgment / edge-case input:** C behavior that depends on undefined or platform-specific semantics.
- **Recommendation: not a candidate.**
- **Next review:** after the first Rust port has used it, or 2026-12-25.

## Advisory Code Review (CI `agent-review`)

- **Signals:** no evidence. The job is advisory, and no key is set in `CI_REVIEWER_OPENROUTER_KEY`, so it has never produced a review. Code review is judgment.
- **Recommendation: not a candidate.**
- **Next review:** after the advisory reviewer has produced its first reviews, or 2026-12-25.

## Human steps

Plan approval, substitute-check approval, commit and merge approval, and any golden-trace change stay with the operator (`CLAUDE.md`, Human-in-the-loop checkpoints; coding standard 4). Each carries accountability, and a wrong call costs more than the operator's time.

## Already deterministic

- `scripts/demo-suite.sh` and `scripts/demo1-check.sh`: demo replay, tic count and per-tic trace comparison (exit 0, 1 or 2).
- `scripts/hooks/orchestrator-bash-guard.py`, `decision-write-guard.py`, `skill-file-guard.py` and `memory-secret-guard.py`, and `scripts/hooks/pre-commit`.
- `scripts/run-agent.sh`: container permissions per role.
- `scripts/verify_demos_deterministic.py`: the standalone demo check, converted from the demo-verifier agent (ADR-001). Listed in full above.
- `eval/test_deterministic.py` (harness checks), `eval/test_policy.py` (policy suite), `scripts/check-pipeline-integrity.py`, `scripts/run-eval-gate.py` and `scripts/build-audit-trail.py` (CI gates and audit trail).
