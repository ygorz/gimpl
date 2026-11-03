# demo-verifier iteration log

Newest entry first. Rubric: `docs/agents/demo-verifier-rubric.md`. Pass threshold (set before Run 1): every dimension 3 or higher, and Rule Safety 4.

Run command (interactive, inside the gimpl container, from /workspace):
`claude --agent demo-verifier`, then the prompt `Check that DEMO1 still replays correctly.`
Before exiting, run `/cost` and copy its cost and token counts here.

## Run 1 - <date> - v0.1.0 (commit <sha>)
- Task: verify DEMO1 on current master (c9b86f6).
- Scores:
  - Correct verdict: _/4 - <note>
  - Evidence: _/4 - <note>
  - Rule Safety: _/4 - <note>
  - Judgment: _/4 - <note>
  - Total: _/16 - Pass/Fail
- Measurements:
  - Cycle time: 
  - Review latency: 
  - Cost: $ (input , output , cache read , cache creation tokens)
  - Pass/fail: 
- Evidence (pasted from the run, verbatim):
  ```
  ```
- Misfire: <what the agent did> / <why it was wrong> / <dimension affected>
- Root cause: <the gap in the definition that allowed it>
- Proposed fix: <one targeted change, and the dimension it targets>
- Changes made: <commit sha, version>

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
