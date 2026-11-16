---
classification: public
project: proj-lessons
doc_type: lesson
---

## Lesson: The container clock is UTC, so never date entries from it

**What happened.** In Run 001 on 2026-10-24 the agent's results file was dated 2026-10-25, because the sandbox container's clock runs on UTC and was already past midnight. The same gap came back later: before Task 5 the container clock read 2026-11-15 while George's date was 2026-11-14. The build also printed make "clock skew detected" warnings because the Mac and the UTC container disagree about file timestamps.

**What we learned.** George works in America/Denver, and the container clock can read a day ahead of his local date. A date taken from `date` inside the container can quietly move a memory entry, run summary or decision a day into the future. In Task 4 the orchestrator handled this correctly by leaving the run summary date blank instead of using the container clock, and filled it in after George gave the date.

**How to apply it.** Never take a date for memory, run summaries or decision entries from the container clock. Use the latest date already in `.memory/`, or ask George. Never move a date forward just because the clock is later (CLAUDE.md, memory write rules). Treat clock skew warnings from make as a timezone side effect, not a build failure.
