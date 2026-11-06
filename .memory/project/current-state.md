# Current State - Feature 1 (per-tic demo suite)

**Scope:** Workflow (archive when feature/per-tic-demo-suite merges to master)
**Branch:** feature/per-tic-demo-suite
**Last updated:** 2026-11-05 (as of commit ae75c9ee)

## Where things stand
- `scripts/demo-suite.sh` and `docs/smoke-tests/demo-suite.md` are stubs: the script prints planned steps and exits 0; no demo runs yet.
- `scripts/demo1-check.sh` remains the working DEMO1 check (wad sha256, 4227 gametics) and stays unchanged.
- Approach is fixed by decision-001 (committed per-tic reference traces plus a bash runner).
- The 2.3 memory system (.memory/, docs/memory-architecture.md, CLAUDE.md v0.1.1) is being finished on this branch.

## Next action
Pin the trace line format (field order, decimal or hex) in `docs/smoke-tests/demo-suite.md` before adding the `-tichash` C hook or generating any trace. The full ordered task list is in that doc.

## Deferred (do not reopen without a human decision)
- Pinned C reference build (Approach 2): deferred in decision-001.
- DEMO2 and DEMO3: out until DEMO1 works end to end.

## Open questions
- Exact trace format (see next action).
