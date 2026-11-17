# Decision 003 - Per-tic trace format v1

**Date:** 2026-11-06
**Review by:** 2027-02-04
**Status:** Active
**Scope:** Project (outlives feature/per-tic-demo-suite: every committed reference trace depends on it)
**Classification:** Internal (no Confidential or Secret content)
**Approved by:** Human (project owner), in session on 2026-11-06
**Branch / commit:** feature/per-tic-demo-suite, on top of 6673c7ff
**Related:** decision-001 (per-tic reference traces); coding standard 4 (trace approval)
**Supersedes:** none

**Decision:** Per-tic traces use format v1, specified in docs/smoke-tests/demo-suite.md under "Trace format (v1)".
- The first line is the header `#tichash v1 ...`.
- Each tic line is positional and space-separated: `gametic rndindex prndindex`, then one `pN` block per player in game.
- Each player block is x, y, z, angle, momx and momy in 8-digit lowercase hex (cast to uint32), then health (`mo->health`), armorpoints, readyweapon, artifactCount and inventorySlotNum in decimal.
- Non-level tics write no line. The runner matches lines by gametic, not by line number.

**Rationale:**
- Hex shows `fixed_t` values as integer.fraction and angles directly.
- Fixed-width columns line up in a PR diff.
- `%08x` in C and `{:08x}` on `u32` in Rust print the same thing, so the Rust port can match it exactly.
- The header names each column, so the runner can report the drifting field by name, and its version number lets the runner reject an incompatible trace as a setup error instead of a false FAIL.
- `pN` blocks keep columns stable in multiplayer demos (DEMO2/3 later).

**Alternatives rejected:**
- All-decimal positional (Option A): `fixed_t` values are hard to read and columns don't line up.
- key=value tokens (Option C): self-describing, but about 2–3× larger and noisier diffs. The header provides most of that benefit.
- One line per gametic including non-level tics: rejected in favour of matching by gametic and accepting gaps.

**Constraint:** Any change to the format means a new header version, and regenerating every reference trace needs human approval (coding standard 4).
