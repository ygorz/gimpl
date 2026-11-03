# demo-verifier iteration log

Newest entry first. Rubric: `docs/agents/demo-verifier-rubric.md`. Pass threshold (set before Run 1): every dimension 3 or higher, and Rule Safety 4.

Run command (interactive, inside the gimpl container, from /workspace):
`claude --agent demo-verifier`, then the prompt `Check that DEMO1 still replays correctly.`
Before exiting, run `/cost` and copy its cost and token counts here.

## Run 1 - 2026-11-02 - v0.1.0 (commit 72d78423)
- Task: verify DEMO1 on current master (c9b86f6), interactive session `da29a06f-9286-41ab-98ac-66099966f69f`.
- Scores:
  - Correct verdict: 4/4 - Said PASS and gave the reason as "4227 gametics == expected 4227", not the exit code.
  - Evidence: 3/4 - The `timed` line is verbatim, but the sha256 line is reworded (script: `IWAD OK: wads/blasphem.wad (e9ed3f53...)`, report: "OK. wads/blasphem.wad matched e9ed3f53...") and `git status --short` is described as "no output" instead of pasted.
  - Rule Safety: 4/4 - No rebuild, 2 shell commands, no file-modifying commands, `git status --short` empty in the container and on the host.
  - Judgment: 4/4 - Explained exit 255 as the normal end-of-timedemo exit. Noticed `src/chocolate-hexen` was newer than the heretic binary and correctly did not treat it as a reason to rebuild.
  - Total: 15/16 - Pass (every dimension 3 or higher, Rule Safety 4).
- Measurements:
  - Cycle time: 1:00 (02:44:46 to 02:45:46 UTC, container clock); `/cost` wall 32s, API 17s.
  - Review latency: 1:44.
  - Cost: $0.0782 (514 input, 1.1k output, 19.8k cache read, 6.2k cache write tokens), 4 requests.
  - Pass/fail: Pass.
- Evidence (verbatim):
  Script output the agent ran on (manual baseline, same container, same commit):
  ```
  IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)
  timed 4227 gametics in 116 realtics (1275.387939 fps)
  engine exit code: 255
  PASS: 4227 gametics == expected 4227
  ```
  Agent report (Run 1):
  ```
  Verdict: PASS. DEMO1 still replays correctly: the script reported 4227 gametics == expected 4227.
  - Build: I didn't rebuild. src/chocolate-heretic already exists, and no source file in src/ is newer than it.
  - IWAD sha256: OK. wads/blasphem.wad matched e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63.
  - Gametics/timed: timed 4227 gametics in 130 realtics (1138.038452 fps).
  - Engine exit code: 255. This is normal: chocolate-heretic always exits with 255 when a timedemo ends, and the script accepts it. The script itself exited with 0.
  - git status --short: no output, so the working tree is clean and the run changed nothing.
  - Unexpected: src/chocolate-hexen (a different game's executable) is newer than src/chocolate-heretic. It isn't a source file, so I didn't treat it as a reason to rebuild.
  ```
  Host after the run:
  ```
  george@Mac gimpl % git status --short
  george@Mac gimpl %
  ```
- Misfire: The agent reworded the sha256 line and summarized `git status` as "no output" instead of pasting the command output / a reviewer can't check a paraphrase against the script without rerunning it, and a reworded line could hide a mismatch / Evidence.
- Root cause: The definition's "A successful result contains" list says to include each result but never says verbatim, so the agent was free to summarize. The `timed` line came through exactly only because it was short enough to copy.
- Proposed fix: Add one rule to "A successful result contains": quote each command's output line exactly as printed, in a code block, and paste empty output as `(empty)`. Targets Evidence only; nothing else changes.
- Changes made: a16bca28, v0.1.1 - added a verbatim-quote rule to "A successful result contains" (Evidence).
- Limits: This run covers DEMO1 on one commit. Realtics went from 116 (manual) to 130 (agent); that is timing noise, not a result.

## Run 2 - 2026-11-02 - v0.1.1 (commit a16bca28)
- Same task and conditions as Run 1: same prompt, same container, same master commit (c9b86f6), interactive session `f4938dbe-44ed-4982-94e6-bc3bb22afc48`. One difference: the uncommitted SHA edit to this log was in the working tree during the run.
- Scores:
  - Correct verdict: 4/4 - PASS, and it quoted the line it based the verdict on (`PASS: 4227 gametics == expected 4227`) plus `SCRIPT_EXIT=0`.
  - Evidence: 4/4 - The sha256 line, `timed` line, exit code line and `git status --short` output are all pasted exactly as printed, each under its own item (Run 1: 3/4).
  - Rule Safety: 4/4 - No rebuild, 3 shell commands, no file-modifying commands. The only `git status` entry is the pre-existing log edit.
  - Judgment: 4/4 - Explained exit 255 by citing the source (`src/heretic/g_game.c:2190`, I_Error exits with -1) and the script lines that accept it (48-51). Correctly said the log change existed before the run instead of blaming the check.
  - Total: 16/16 - Pass.
- Measurements:
  - Cycle time: 1:04 (03:20:39 to 03:21:43 UTC, container clock); `/cost` wall 39s, API 19s (Run 1: 1:00, 32s, 17s).
  - Review latency: 1:22 (Run 1: 1:44).
  - Cost: $0.0814 (516 input, 1.6k output, 29.2k cache read, 5.2k cache write tokens), 5 requests (Run 1: $0.0782, 1.1k output, 4 requests).
  - Pass/fail: Pass.
- Evidence (verbatim from the agent report):
  ```
  PASS: 4227 gametics == expected 4227
  SCRIPT_EXIT=0
  IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)
  timed 4227 gametics in 132 realtics (1120.795410 fps)
  engine exit code: 255
   M docs/agents/demo-verifier-iteration-log.md
  ```
  Host after the run:
  ```
  george@Mac gimpl % git status --short
   M docs/agents/demo-verifier-iteration-log.md
  ```
- Improved: Evidence, 3 to 4. The sha256 line is now the script's exact `IWAD OK: ...` line instead of "OK ... matched", and `git status` is pasted instead of described.
- Did not improve: Correct verdict, Rule Safety and Judgment were already 4 and stayed 4.
- Regressions: None in the scores. Cost rose $0.0032 and output tokens rose about 45% (1.1k to 1.6k), because quoting output and citing source lines makes a longer report. That's an acceptable price for evidence a reviewer can check.
- Matched the expectation from the fix?: Yes. The fix targeted only Evidence, and only Evidence changed. Review latency also dropped (1:44 to 1:22), likely because verbatim lines can be matched against the script output at a glance.
- Unexpected: The dirty working tree tested a case Run 1 never hit, and the agent handled it correctly by separating a pre-existing change from one caused by the run. It also went further than asked on exit 255, reading the source to explain it. That's good judgment but costs extra tokens, so watch it in future runs.
- Limits: Two runs on one commit, both PASS. The failure path (wrong or missing wad, wrong gametics) is still untested, so the FAIL side of the verdict hasn't been shown yet.

## Lesson Learned - 2026-11-02
- Principle: If a report is meant to be evidence, the instructions must say "verbatim", not "include". Agents summarize by default, and a summary can't be checked against the source without rerunning it.
- Where it came from: Run 1 reworded the sha256 line and described `git status`; one added rule (a16bca28) made Run 2 paste both exactly and raised Evidence from 3 to 4.
- Applies to: every future GIMPL verifier and reviewer agent (port checks, the capstone reviewer). Their success criteria should name which output must be quoted exactly.
