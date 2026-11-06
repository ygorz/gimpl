# Current State - Feature 1 (per-tic demo suite)

**Scope:** Workflow (archive when feature/per-tic-demo-suite merges to master)
**Branch:** feature/per-tic-demo-suite
**Last updated:** 2026-11-06 (as of commit 6673c7ff, plus the uncommitted trace format v1 changes)

## Where things stand
- `scripts/demo-suite.sh` is a stub: it prints planned steps and exits 0; no demo runs yet.
- Trace format v1 is pinned in `docs/smoke-tests/demo-suite.md` ("Trace format (v1)"): positional, space-separated, hex for `fixed_t`/`angle_t`, decimal for the rest, `#tichash v1` header, per-player `pN` blocks, no line on non-level tics, runner compares by gametic. Recorded in decision-003.
- `scripts/demo1-check.sh` remains the working DEMO1 check (wad sha256, 4227 gametics) and stays unchanged.
- Approach is fixed by decision-001 (committed per-tic reference traces plus a bash runner).
- The 2.3 memory system (.memory/, docs/memory-architecture.md, CLAUDE.md v0.1.1) is being finished on this branch.

## Next action
Add the opt-in `-tichash <file>` C hook (task 1 in `docs/smoke-tests/demo-suite.md`) writing trace format v1. Do not generate a reference trace without human approval (coding standard 4). The full ordered task list is in that doc.

## Deferred (do not reopen without a human decision)
- Pinned C reference build (Approach 2): deferred in decision-001.
- DEMO2 and DEMO3: out until DEMO1 works end to end.

## Open questions
- None.
