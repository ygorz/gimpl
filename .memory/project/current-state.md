# Current State - Feature 1 (per-tic demo suite)

**Scope:** Workflow (archive when feature/per-tic-demo-suite merges to master)
**Branch:** feature/per-tic-demo-suite
**Last updated:** 2026-11-07 (commit status of anything below: check git, which wins over this file; CLAUDE.md v0.1.4)

## Where things stand
- `scripts/demo-suite.sh` is a stub: it prints planned steps and exits 0; no demo runs yet.
- Trace format v1 is pinned in `docs/smoke-tests/demo-suite.md` ("Trace format (v1)"): positional, space-separated, hex for `fixed_t`/`angle_t`, decimal for the rest, `#tichash v1` header, per-player `pN` blocks, no line on non-level tics, runner compares by gametic. Recorded in decision-003.
- The `-tichash` C hook is in (task 1, commit 066ea6ac): `G_TicHashWrite()` in `src/heretic/g_game.c` plus a `prndindex` extern in `src/heretic/m_random.h`. A missing player mobj stops the run with `I_Error` (decision-004).
- The hook-off check passed (task 6): `scripts/demo1-check.sh` reports 4227 gametics with the hook built in and the flag not set.
- Task 3 is done: the DEMO1 reference trace `tests/demos/heretic/golden/demo1.tics` exists, approved under coding standard 4, from a clean rebuild at 01044d09. Two runs were byte-identical (4227 gametics, 4228 lines). Provenance, hashes and the exact invocation are in decision-006. The trace was committed in f66cb067 (2026-11-07); git is the source of truth for its current status.
- `docs/smoke-tests/demo-suite.md` now marks Task 3 done, with the trace sha256 and a pointer to decision-006.
- Demo test data is laid out per game (decision-005): traces in `tests/demos/<game>/golden/<demo>.tics`, manifest at `tests/demos/<game>/manifest`. `tests/demos/heretic/manifest` does not exist yet.
- Fixed run flags for generating and comparing traces: `-iwad wads/blasphem.wad -timedemo <demo> -nodraw -nosound -tichash <file>` with the dummy SDL drivers (decision-004). The engine exits 255 after -timedemo; that is normal, and the `timed N gametics` line decides the result.
- `scripts/demo1-check.sh` remains the working DEMO1 check (wad sha256, 4227 gametics) and stays unchanged.
- Approach is fixed by decision-001 (committed per-tic reference traces plus a bash runner).
- The 2.3 memory system (.memory/, docs/memory-architecture.md, CLAUDE.md v0.1.4) is being finished on this branch. v0.1.2 added data classification and date rules to the write policy; v0.1.3 says a credential is recorded only as its env var name and that a blocked write means stop and tell George; v0.1.4 says memory does not record git status as a lasting fact and git wins when they disagree.
- Credentials are kept out of .memory/ by two hooks with the same patterns: the Claude Code PreToolUse hook `scripts/hooks/memory-secret-guard.py` (registered in `.claude/settings.json`, blocks Write/Edit/MultiEdit) and the versioned git hook `scripts/hooks/pre-commit` (install per clone, see its first line). Details and known gaps in docs/memory-architecture.md, Enforcement.

## Next action
Task 4: add `tests/demos/heretic/manifest` with demo name (demo1), expected gametics (4227), trace sha256 and source commit (01044d09), all from decision-006. The manifest is covered by coding standard 4, so it needs explicit human approval before it is written; do not start it without that. The full ordered task list is in `docs/smoke-tests/demo-suite.md`.

## Deferred (do not reopen without a human decision)
- Pinned C reference build (Approach 2): deferred in decision-001.
- DEMO2 and DEMO3: out until DEMO1 works end to end.

## Open questions
- DEMO3 is still deferred (2582 gametics, not yet pinned). Open: when to pin it once DEMO1 works end to end.
- Rebuild before trace: decision-006's trace was made from a clean rebuild at a recorded commit, because the earlier binary could not be tied to a commit. Open: whether to make "clean rebuild at a recorded commit before generating any reference trace" a standing rule (for example an amendment to decision-004, or a check in the runner). It is not a rule yet; needs a human decision.
