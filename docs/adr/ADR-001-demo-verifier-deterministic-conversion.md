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
- **Keep the agentic step.** Rejected. Iteration Log Runs 1 and 2 cost $0.0782 and $0.0814 with cycle times of 1:00 and 1:04, and REG-01 failed the cost budget on both runs (57,861 and 57,626 tokens against 51,200). The verdict on every logged run came from script output the agent copied. The one quality problem it had, Run 1 paraphrasing the sha256 line and `git status`, was a copying problem, which code removes by construction.
- **Shrink the agent: a tighter prompt or a smaller model.** Rejected. It would lower the token count, but it keeps model latency, keeps the wording variance that caused Run 1's Evidence score of 3/4, and keeps the governance overhead: a policy entry, a `run-agent.sh` branch, retrieval allow-list entries, harness grant maps and Bash in a read-write container. A structural check needs none of these.
- **Raise the REG-01 cost budget.** Rejected. It turns the `cost` check green without changing what the step costs, and it leaves the governance overhead in place.
- **Fold the check into the tester.** Rejected. The tester runs only inside the team loop after an implementer, so a standalone "Check the demos." would need a whole team run. It would also leave an agent in charge of a decision two scripts already make. The routing map deferred this option for the same reason.
- **Convert to deterministic code.** Preferred. The script is expected to take only as long as the demo replay itself, cost zero tokens, give the same decision on every run, and be readable in one file. Before it replaces the agent, it must pass every deterministic check the agent passed, and it must have unit tests for the three edge cases above.

## Consequences
Expected benefits: zero token cost, cycle time close to the demo replay time, the same decision on every run, an output a reviewer can check field by field, and one less governed agent role with Bash.

Known trade-offs:
- The script cannot explain beyond its rules. Run 2's agent read `src/heretic/g_game.c:2190` to explain exit 255. The script states the fixed meaning from decision-006 and nothing more.
- The agent's "Anything unexpected" line could notice things nobody wrote a rule for. The script reports only what its rules check, plus every output line verbatim. Output it does not recognize gives BLOCKED with the lines quoted, never a guess.
- If `demo-suite.sh` or `demo1-check.sh` change their output lines, the script's parser must change in the same commit.

To watch before integration: the measured latency, cost and decision repeatability match these expectations, and every deterministic check the agent passed still passes. To accept: the conversion is integrated as one commit that also retires the agent's governance artifacts, and the end-to-end regression check passes with no new failures.

Rollback: the integration will be a single commit, so one `git revert` restores the agent version if the script gives a wrong result in the running workflow.

## Evidence
Expected, not yet measured (the script does not exist yet):
- Latency: roughly the demo replay time, against the agent's 1:00 and 1:04.
- Cost: 0 tokens.
- Predictability: the same decision fields on three runs of one input.
- Audit clarity: one readable script and a JSON result, against a transcript.
- Quality: every deterministic check the agent passed still passes.

Evidenced so far (logged before this ADR):
- `docs/agents/demo-verifier-iteration-log.md`: Run 1 (15/16, $0.0782, 1:00) and Run 2 (16/16, $0.0814, 1:04).
- `docs/iteration-log.md`, "Feature 1 Task 8": the v0.2.0 verification run, PASS.
- `docs/calibration-log.md`: REG-01-r1 at `4d53dc40` and REG-01-r2 at `432e6797`, demos PASS at 4227 gametics, `cost` FAIL on both.
- `docs/step-classification.md`: the four-signal assessment and the three edge cases.

The measured comparison is added after the before-and-after measurement.
