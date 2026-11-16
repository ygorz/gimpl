---
classification: internal
project: proj-lessons
doc_type: lesson
---

## Lesson: Halt on an evidence gap before implementing

**What happened.** In Feature 1 Task 4, Run 1, the acceptance rule required real `scripts/demo-suite.sh` output, but the runner was still a stub. The workflow had no branch for that case. The run could only be accepted through a one-off decision George made mid-run: `scripts/demo1-check.sh` plus the trace sha256 check stood in as DEMO1 evidence for that task only. It worked only because the planner happened to raise it as an open question.

**What we learned.** A stub's output is never evidence. When the planned evidence can't exist yet, the workflow has to notice before any code is written, not after. CLAUDE.md v0.1.6 and orchestrator 1.1.0 added an "Evidence gap" branch, let the tester gate accept a substitute check only when George approves it for that task, and say the exception is recorded in the run summary and never becomes a standing rule.

**How to apply it.** If a task's evidence can't come from real `scripts/demo-suite.sh` output because the runner is a stub, missing or broken, halt before invoking the implementer. Name the gap, propose a substitute check, and continue only after George approves it. Record the substitute in `docs/runs/` as a one-off for that task. From Task 5 on, acceptance needs real runner output at 4227 gametics.
