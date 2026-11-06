# Project Memory Index

Last updated: 2026-11-06

## Active entries

- `decisions/decision-001.md` — Feature 1 (the per-tic demo
 test suite) verifies demos against committed per-tic reference
 traces, checked by scripts/demo-suite.sh. Recorded 2026-11-05;
 trace path amended 2026-11-06 (see decision-005).
 Review by 2027-02-03.

- `decisions/decision-002.md` — .memory/ is committed in the
 repo; memory changes go on the same feature branch as their
 work and merge to master with it (not a separate branch, not
 outside git). Recorded 2026-11-05. Review by 2027-02-03.

- `decisions/decision-003.md` — Per-tic trace format v1:
 `#tichash v1` header, positional space-separated lines, hex for
 fixed_t/angle_t, decimal for the rest, per-player `pN` blocks,
 no line on non-level tics, runner matches by gametic. Spec in
 docs/smoke-tests/demo-suite.md. Recorded 2026-11-06.
 Review by 2027-02-04.

- `decisions/decision-004.md` — The -tichash hook stops with
 I_Error if a player in game has no mobj; reference and
 comparison traces always use the fixed run flags (-nodraw
 -nosound, dummy SDL drivers). Recorded 2026-11-06.
 Review by 2027-02-04.

- `decisions/decision-005.md` — Demo test data is laid out per
 game: traces in tests/demos/<game>/golden/<demo>.tics, one
 manifest per game at tests/demos/<game>/manifest. Recorded
 2026-11-06. Review by 2027-02-04.

- `current-state.md` — Feature 1 status, next action (generate
 the DEMO1 reference trace, needs human approval), and deferred
 work. Workflow-scoped; archive when feature/per-tic-demo-suite
 merges. Updated 2026-11-06.

- `../knowledge/coding-standards.md` — Coding standards
 for this project. Human-maintained, read-only.
 Last reviewed 2026-11-05.

## Archived entries

(none yet)

## Pruning schedule

- Workflow-scoped entries: archived when the branch
 merges to master
- Project-scoped entries: reviewed every 90 days
