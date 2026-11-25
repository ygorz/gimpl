# ADR-001: Convert the demo-verifier step from agent to deterministic code

- Date: 2026-11-25 (MT)
- Decider: George Gorzhiyev
- Classification: `docs/step-classification.md`, "demo-verifier: standalone demo replay check" (strong candidate)

## Status
Proposed

## Context
The demo-verifier is a governed subagent (`.claude/agents/demo-verifier.md` v0.2.1, `docs/governance-policy.md` "Role: demo-verifier") that answers one question: does the Chocolate Heretic build still replay every pinned demo tic for tic? It does not decide the answer itself. `scripts/demo-suite.sh` decides it (exit 0 PASS, 1 FAIL, 2 setup error), `scripts/demo1-check.sh` cross-checks the gametic count, and the agent rebuilds if needed, runs both, quotes their lines and reports PASS, FAIL or BLOCKED.

The step classification marks it a strong candidate on all four signals. Two Iteration Log runs scored 15/16 and 16/16, and the Calibration Log regression task REG-01 reported demos PASS at 4227 gametics on both runs. Its verdict was the same on every logged run, and only the wording changed. Its rules fit in one paragraph. It runs after every change to `src/heretic/`, the build or a Rust port, and that rate grows with every port.

The agent wrapper has a measured cost: REG-01-r1 used 57,861 tokens and REG-01-r2 used 57,626 against a 51,200 budget, so the `cost` check failed on both. The role also holds Bash with a read-write workspace, which is the broadest grant a subagent has.

The classification names three edge cases the agent handles by judgment today, and a deterministic version must keep all three: engine exit 255 after `-timedemo` is normal (decision-006); a newer binary for another game such as `src/chocolate-hexen` is not a reason to rebuild; and a working tree that was already dirty before the check is reported, not blamed.

## Decision
Replace the demo-verifier agent with `scripts/verify_demos_deterministic.py`, which reads a request file named by `--input`, runs the same two scripts, writes the same report content as structured JSON to the file named by `--output`, exits 0 for PASS, 1 for FAIL and 2 for BLOCKED, and calls no language model.

## Alternatives considered
- **Keep the agentic step.** Rejected. The before-conversion entry in Calibration Log Entry 2 (`f454c21c`) shows the agent averaged 29.9 s and $0.1147 (9,168 tokens) per run across three runs on "Check the demos.", with verdict PASS each time. Earlier runs agree: Iteration Log Runs 1 and 2 cost $0.0782 and $0.0814 at 1:00 and 1:04, and REG-01 failed the cost budget on both runs (57,861 and 57,626 tokens against 51,200). The verdict on every run came from script output the agent copied, and the one quality problem it had, Run 1 paraphrasing the sha256 line and `git status`, was a copying problem, which code removes by construction.
- **Shrink the agent: a tighter prompt or a smaller model.** Rejected. It would lower the token count, but it keeps model latency, keeps the wording variance that caused Run 1's Evidence score of 3/4, and keeps the governance overhead: a policy entry, a `run-agent.sh` branch, retrieval allow-list entries, harness grant maps and Bash in a read-write container. A structural check needs none of these.
- **Raise the REG-01 cost budget.** Rejected. It turns the `cost` check green without changing what the step costs, and it leaves the governance overhead in place.
- **Fold the check into the tester.** Rejected. The tester runs only inside the team loop after an implementer, so a standalone "Check the demos." would need a whole team run. It would also leave an agent in charge of a decision two scripts already make. The routing map deferred this option for the same reason.
- **Convert to deterministic code.** Preferred, pending integration. The after-conversion entry (`cd08730a`) shows `scripts/verify_demos_deterministic.py` averaged 7.2 s at $0 token cost across three runs on the same input, gave the same `decision` object on all three (checked with `diff`: only the `timed` lines' realtics differ, which are timing noise), and gave the same verdict as the agent, PASS. Every check the agent's output passed on this input also passed: the verdict, the PASS lines quoted exactly, and a tree left as it was found. The Evidence and Judgment rubric dimensions score written prose and do not apply to the structured output, so they are marked not applicable. This ADR stays Proposed until the script is integrated into the running workflow and the end-to-end regression check passes.

## Consequences
Measured benefits so far (Calibration Log Entry 2): cycle time fell from 29.9 s to 7.2 s, token cost fell from $0.1147 per run to zero, the verdict and decision fields no longer vary between runs, and review time fell from 73 s to 48 s. Integration will also retire one governed role with Bash in a read-write container.

Known trade-offs:
- The script cannot explain beyond its rules. Run 2's agent read `src/heretic/g_game.c:2190` to explain exit 255. The script states the fixed meaning from decision-006 and nothing more.
- The agent's "Anything unexpected" line could notice things nobody wrote a rule for. The script reports only what its rules check, plus every output line verbatim. Output it does not recognize gives BLOCKED with the lines quoted, never a guess.
- If `demo-suite.sh` or `demo1-check.sh` change their output lines, the script's parser must change in the same commit.

To watch: if a BLOCKED for unrecognized output appears in normal use, the scripts' output changed, and the fix is the parser, in code, before considering a return to the agent.

Acceptance condition: keep this ADR at Proposed until the conversion is wired into the running workflow in one commit that also retires the agent's governance artifacts, and the end-to-end regression check passes with no new failures. Rollback: the integration will be a single commit, so one `git revert` restores the agent version if the script gives a wrong result in the running workflow.

## Evidence
Expected at Proposed, now measured (Calibration Log Entry 2, before `f454c21c` and after `cd08730a`):

| Measurement | Expected at Proposed | Measured: agent | Measured: script |
|---|---|---|---|
| Latency | roughly the demo replay time | 29.9 s | 7.2 s |
| Cost | 0 tokens | $0.1147, 9,168 tokens | $0, 0 tokens |
| Predictability | the same decision on three runs | verdict same: yes; text same: no | decision same: yes |
| Audit clarity | one readable script and a JSON result | definition, policy entry and transcript | one script, 277 lines, and named JSON fields |
| Quality | every check the agent passed still passes | verdict PASS, quoted exactly 3/3 | verdict PASS, quoted exactly 3/3 |

Implementation and tests: `8bd4e24c` (`scripts/verify_demos_deterministic.py`, `eval/test_deterministic_step.py`: 19 passed in 0.16s, covering the three edge cases).

Logged before this ADR:
- `docs/agents/demo-verifier-iteration-log.md`: Run 1 (15/16, $0.0782, 1:00) and Run 2 (16/16, $0.0814, 1:04).
- `docs/iteration-log.md`, "Feature 1 Task 8": the v0.2.0 verification run, PASS.
- `docs/calibration-log.md`: REG-01-r1 at `4d53dc40` and REG-01-r2 at `432e6797`, demos PASS at 4227 gametics, `cost` FAIL on both.
- `docs/step-classification.md`: the four-signal assessment and the three edge cases.
