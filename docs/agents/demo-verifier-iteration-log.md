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
- Changes made: <commit sha>, v0.1.1
- Limits: This run covers DEMO1 on one commit. Realtics went from 116 (manual) to 130 (agent); that is timing noise, not a result.

## Run 2 - <date> - v0.1.1 (commit <sha>)
- Same task and conditions as Run 1.
- Scores: (same dimensions, with notes)
- Measurements: (same four)
- Evidence (verbatim):
- Improved:
- Did not improve:
- Regressions:
- Matched the expectation from the fix?:
- Unexpected:

## Lesson Learned
- <general principle for future agents>
