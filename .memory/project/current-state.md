# Current State - Feature 1 (per-tic demo suite)

**Scope:** Workflow (archive when feature/per-tic-demo-suite merges to master)
**Branch:** feature/per-tic-demo-suite
**Last updated:** 2026-11-06 (as of commit ab266f63, plus the uncommitted -tichash hook and decision-004 changes)

## Where things stand
- `scripts/demo-suite.sh` is a stub: it prints planned steps and exits 0; no demo runs yet.
- Trace format v1 is pinned in `docs/smoke-tests/demo-suite.md` ("Trace format (v1)"): positional, space-separated, hex for `fixed_t`/`angle_t`, decimal for the rest, `#tichash v1` header, per-player `pN` blocks, no line on non-level tics, runner compares by gametic. Recorded in decision-003.
- The `-tichash` C hook is in (task 1, uncommitted): `G_TicHashWrite()` in `src/heretic/g_game.c` plus a `prndindex` extern in `src/heretic/m_random.h`. A missing player mobj stops the run with `I_Error` (decision-004).
- The hook-off check passed (task 6): `scripts/demo1-check.sh` reports 4227 gametics with the hook built in and the flag not set. A test `-tichash` run gave two byte-identical traces (header plus gametic 0-4226) in the session scratchpad only; no reference trace exists yet.
- Fixed run flags for generating and comparing traces: `-iwad wads/blasphem.wad -timedemo <demo> -nodraw -nosound -tichash <file>` with the dummy SDL drivers (decision-004).
- `scripts/demo1-check.sh` remains the working DEMO1 check (wad sha256, 4227 gametics) and stays unchanged.
- Approach is fixed by decision-001 (committed per-tic reference traces plus a bash runner).
- The 2.3 memory system (.memory/, docs/memory-architecture.md, CLAUDE.md v0.1.1) is being finished on this branch.

## Next action
Task 3: generate `tests/demos/golden/demo1.tics` with the fixed run flags and record the source commit. This needs explicit human approval before it runs (coding standard 4); do not start it without that. The full ordered task list is in `docs/smoke-tests/demo-suite.md`.

## Deferred (do not reopen without a human decision)
- Pinned C reference build (Approach 2): deferred in decision-001.
- DEMO2 and DEMO3: out until DEMO1 works end to end.

## Open questions
- None.
