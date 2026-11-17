# Decision 005 - Per-game layout for demo test data

**Date:** 2026-11-06
**Review by:** 2027-02-04
**Status:** Active
**Scope:** Project (every demo test file, for every game, beyond feature/per-tic-demo-suite)
**Classification:** Internal (no Confidential or Secret content)
**Approved by:** Human (project owner), in session on 2026-11-06
**Branch / commit:** feature/per-tic-demo-suite, on top of 066ea6ac
**Related:** decision-001 (amended 2026-11-06 for this path); decision-003 (trace format v1); coding standard 4
**Supersedes:** the tests/demos/golden/demo1.tics trace path in decision-001, and the tests/demos/golden/<demo>.tics and tests/demos/manifest paths in docs/smoke-tests/demo-suite.md

**Decision:** Demo test data is grouped by game under tests/demos/<game>/:
- Reference traces: tests/demos/<game>/golden/<demo>.tics. DEMO1 for Heretic is tests/demos/heretic/golden/demo1.tics.
- Manifest: tests/demos/<game>/manifest, one per game, listing that game's demos (demo name, expected gametics, trace sha256, source commit).
- <game> is the lowercase game name (heretic for Chocolate Heretic).

**Rationale:** The repo has several games. A per-game directory stops demo names such as demo1 from colliding between games and keeps each game's traces, sha256s and source commits together. A per-game manifest needs no game column.

**Alternatives rejected:**
- A flat tests/demos/golden/ directory: demo names collide across games.
- One shared tests/demos/manifest with a game column: every row would need a game field, and one game's changes would touch a file shared with the others.

**Constraint:** Moving or renaming a reference trace or manifest counts as editing it and needs human approval (coding standard 4).
