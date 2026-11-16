# GIMPL Orchestration Diagram

How work moves through the GIMPL agent team for one task. The first task run through it is Feature 1 on `feature/per-tic-demo-suite`: Task 4 (the `tests/demos/heretic/manifest`) and Task 5 (the real `scripts/demo-suite.sh` runner). The same loop is the skeleton for later Rust ports.

The Orchestrator is the main Claude Code session (instructions in `CLAUDE.md`, definition in `.claude/agents/orchestrator.md`). The four subagents live in `.claude/agents/`. Full tool grants and the risk behind each withheld tool are in `docs/routing-and-tool-grant-map.md`.

Solid arrows are handoffs through the Orchestrator. Dotted arrows to the two cylinders are MCP calls to the storage and retrieval servers (Module 3.2). No agent reads the corpus or the storage database directly; `.claude/settings.json` denies those reads.

```mermaid
flowchart TD
    H([George: human]) -->|"task: Feature 1 Task 4 manifest / Task 5 runner"| O[Orchestrator<br/>main session: routes work, checks each result<br/>does not edit code itself, no storage or retrieval tools]

    O -->|"task + SCOPE.md + current-state.md + decision-004/006"| P[Planner<br/>ordered step plan + files to touch<br/>read-only]
    P -.->|"retrieve first: proj-lessons, ceiling internal"| R[(Retrieval server<br/>mcp__retrieval__retrieve<br/>corpus .memory/reference/lessons/<br/>ceiling clamped to internal server-side)]
    R -.->|"chunks cited by source_document + chunk_index"| P
    P -->|"plan: steps, file list, done criteria, open questions, citations"| O

    O -->|"plan for approval"| PA{{"HUMAN APPROVAL: PLAN<br/>George approves the plan before any file is written<br/>Task 4: approval names the manifest with decision-006 values"}}
    PA -->|"rejected, with notes: re-plan"| O
    PA -->|"approved"| EG{"Orchestrator: can real demo-suite.sh<br/>output prove this task?"}

    EG -->|"yes"| I
    EG -->|"no: runner is a stub, missing or broken<br/>stop before the implementer"| SC{{"HUMAN APPROVAL: SUBSTITUTE CHECK<br/>Orchestrator names the gap and proposes a check<br/>George approves it as a one-off for this task<br/>a stub's output is never evidence"}}
    SC -->|"approved: recorded in the run summary"| I
    SC -->|"not approved"| X([Stop and report to George])

    I[Implementer<br/>edits scripts/ and drafts the manifest<br/>NO golden trace edits, NO task_tracker]
    I -.->|"write_entry: one lesson, proj-lessons, internal, calling_role implementer"| S[(Storage server<br/>mcp__storage__write_entry only<br/>storage.db + storage-audit.log)]
    S -.->|"entry_id, audit line written"| I
    I -->|"diff + notes + lesson entry_id"| O

    O -->|"diff + how to run demo-suite.sh (or the approved substitute check)"| T[Tester<br/>runs the real scripts/demo-suite.sh<br/>NO file writes, no storage or retrieval]
    T -->|"PASS/FAIL + gametics + first mismatched tic"| O

    O -->|"diff + test result + any approved substitute check"| F[Fence-reviewer<br/>checks scope and that golden files are untouched<br/>read-only, cannot fix]
    F -.->|"retrieve: proj-lessons, ceiling internal"| R
    R -.->|"cited lessons to check against"| F
    F -->|"approve / list of violations + lessons checked"| O

    O -->|"FAIL or violation: send back with the evidence, max 2 retries"| I
    O -->|"still failing after 2 retries"| X

    O -->|"all checks pass"| A{{"HUMAN APPROVAL: COMMIT<br/>George reviews the diff, evidence and verdict<br/>before commit and before merge to master"}}
    A -->|"approved"| M[Commit on feature branch, merge before 3.3]
    A -->|"rejected, with notes"| O

    T -.->|"reads only, never writes"| G[(Golden trace tests/demos/heretic/golden/demo1.tics<br/>read-only for every agent, only George re-records)]
```

## What the Orchestrator checks on each return

| Returned by | Passes when | If not |
|---|---|---|
| Planner | Every step names its files, done criteria are testable, nothing touches golden traces, and `## Citations` lists what `retrieve` returned (or "None returned") | Re-invoke the Planner once with the gap named; if still unclear, ask George |
| Implementer | The diff touches only files in the approved plan and no file under `tests/demos/heretic/golden/`, and `## Lesson stored` gives an `entry_id` (or says why none was stored) | Send back with the out-of-scope paths (counts as a retry) |
| Tester | `demo-suite.sh` reports DEMO1 at 4227 gametics, decided from the output, not the exit code (255 is normal per decision-006), or the substitute check George approved for this task passes. A stub's output never counts | Send the failure and first mismatched tic to the Implementer (counts as a retry) |
| Fence-reviewer | Approves with no violations, and `## Lessons checked` lists what `retrieve` returned (or "None returned") | Send the violation list to the Implementer (counts as a retry) |

After 2 retries the Orchestrator stops and reports to George instead of looping. No agent re-records or edits a golden trace. If a run seems to need that, the Orchestrator stops and asks George (coding standard 4).

Two checkpoints come before the Implementer starts. George approves the plan before any file is written. Then, if real `demo-suite.sh` output can't prove the task (the runner is a stub, missing or broken), the Orchestrator stops, names the gap and proposes a substitute check. The run goes on only after George approves that check, and the run summary records it as a one-off for that task, never a standing rule.
