# Agent Governance Policy

Version: v1.0.0
Last updated: 2026-11-24
Reviewed by: George Gorzhiyev

## Policy basis

This policy is derived from:

- The routing-and-tool-grant map (docs/routing-and-tool-grant-map.md)
- Near-miss patterns observed in calibration (docs/calibration-log.md, section: Near-miss patterns and latent risks)
- Least-privilege defaults applied to all roles

### Risk statements

Each risk below comes from the calibration log and is addressed by a rule in this policy.

1. **Out-of-lane reads.** The orchestrator still attempts reads outside its lane (1 near-miss in HO-01, 2 each in DEV-02-r3 and REG-01-r2), and only the tool layer stops them, not the prompt.
2. **Displacement.** Blocking one tool moves the same reads to another (Bash to Read in DEV-02-r2), so a limit that covers a single tool leaves the risk open.
3. **Decision provenance.** An implementer can write a new record in `.memory/project/decisions/` that a reviewer then treats as authority, and no role checks where that record came from (HO-05).
4. **Unenforced MCP limits.** Nothing blocks the main session from calling `mcp__storage__*` or `mcp__retrieval__*`, and the `docs/runs/`-only write limit is checked by the test harness rather than enforced (HO-06 held only because no call was made).

## Least-privilege default

Every role starts with no access. All grants below are explicit and justified.
Any access not explicitly granted to a role is denied by default.

To widen access, open a pull request with: the proposed grant, a concrete justification, and confirmation that the grant does not conflict with any near-miss pattern in the calibration log.
