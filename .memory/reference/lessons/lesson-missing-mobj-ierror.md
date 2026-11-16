---
classification: internal
project: proj-lessons
doc_type: lesson
---

## Lesson: A missing-mobj I_Error is a real failure

**What happened.** While designing the `-tichash` hook, we had to decide what the trace should do if a player in the game has no mobj on a level tic. Trace format v1 has no way to show an absent mobj, so skipping that player's block or writing a placeholder such as `p0 -` would silently shift the columns and hide a broken trace. Decision-004 chose to stop the run instead: the hook calls I_Error with the message `G_TicHashWrite: player N has no mobj at gametic T`.

**What we learned.** This I_Error is different from the normal end-of-demo exit. It stops the engine before the demo finishes, so the output has no `timed N gametics` line. `scripts/demo-suite.sh` treats that as a setup error: an engine exit code other than 0 or 255, or a missing `timed` line, makes the runner exit 2 and print the engine output, matching `scripts/demo1-check.sh`. The check only runs when `-tichash` is set, so normal play is unchanged (coding standard 5).

**How to apply it.** When a demo run prints a G_TicHashWrite message or ends without a `timed` line, treat it as a real fault and read the engine output for the player number and gametic it names. Do not work around it by skipping the player block, writing placeholder values, or regenerating the reference trace. Report the gametic to George; any change to the hook or the trace format needs his approval.
