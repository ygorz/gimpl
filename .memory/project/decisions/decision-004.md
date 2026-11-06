# Decision 004 - -tichash error handling and fixed trace run flags

**Date:** 2026-11-06
**Review by:** 2027-02-04
**Status:** Active
**Scope:** Project (applies to every reference trace and every comparison run, beyond feature/per-tic-demo-suite)
**Classification:** Internal (no Confidential or Secret content)
**Approved by:** Human (project owner), in session on 2026-11-06
**Branch / commit:** feature/per-tic-demo-suite, on top of ab266f63
**Related:** decision-003 (trace format v1); decision-001 (per-tic reference traces); coding standards 4 and 5
**Supersedes:** none

**Decision:**
1. Missing mobj stops the run. If a player in game has no mobj on a level tic, the -tichash hook calls I_Error (`G_TicHashWrite: player N has no mobj at gametic T`) instead of skipping that player's block or writing placeholder values.
2. Fixed run flags. Reference traces are generated, and comparison traces are produced, with exactly the same invocation: `src/chocolate-heretic -iwad wads/blasphem.wad -timedemo <demo> -nodraw -nosound -tichash <file>`, with SDL_VIDEODRIVER=dummy and SDL_AUDIODRIVER=dummy. A trace made with any other flags cannot be committed as a reference and cannot be compared against one.

**Rationale:**
- Format v1 cannot represent an absent mobj. Skipping the block would quietly change the column layout and hide a broken trace, while stopping makes the problem visible at the exact tic. The check only runs when -tichash is set, so normal play is unchanged (coding standard 5).
- `rndindex` belongs to M_Random, which code outside the game simulation also calls (menus, status bar, possibly sound). Running with different flags could change `rndindex` without any real desync. Fixing the flags means a difference in the trace always points to a change in game behaviour.
- The headless flags match scripts/demo1-check.sh. Two runs with these flags on 2026-11-06 produced byte-identical traces.

**Alternatives rejected:**
- Skip the player block, or write a placeholder such as `p0 -`: rejected because it hides the fault and breaks the fixed columns.
- Leave `rndindex` out of the trace to avoid flag sensitivity: rejected because the fingerprint keeps both RNG indices (demo-suite.md decisions).
- Allowing the flags to vary and accepting differences in `rndindex`: rejected because it makes the comparison weaker.

**Constraint:** Changing the run flags means regenerating every reference trace, which needs human approval (coding standard 4). The runner (task 5) must use these flags and nothing else.
