---
classification: public
project: proj-lessons
doc_type: lesson
---

## Lesson: Exit code 255 after a timedemo is normal

**What happened.** From the first smoke tests onward, every DEMO1 run of `src/chocolate-heretic -iwad wads/blasphem.wad -timedemo demo1 -nodraw -nosound` ended with exit code 255, even when the demo played perfectly. The engine finishes a timedemo through its error exit, so a successful run and a broken run can both return a non-zero code. In an early run the agent also misread a good result as a failure, because the game prints its `timed` line on error output, ahead of the buffered startup messages.

**What we learned.** Exit code 255 at the end of a timedemo is the normal end-of-demo exit, not a crash, and it is not a FAIL (decision-006). The result is decided by the `timed N gametics` line: DEMO1 passes at `timed 4227 gametics`. Realtics change from run to run (132, 120 and 121 were all seen) while gametics stay at 4227, so gametics are the number to compare, never wall time or realtics.

**How to apply it.** Any script or agent that runs a timedemo should accept exit code 0 or 255 and then judge the run from the `timed` line, the way `scripts/demo1-check.sh` and `scripts/demo-suite.sh` do. Pipe the engine output through `grep timed` so the result line is unambiguous. Do not report a run as failed, and do not rebuild or retry, just because the engine exited with 255.
