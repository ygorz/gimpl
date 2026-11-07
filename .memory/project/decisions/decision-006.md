# Decision 006 - DEMO1 reference trace generated and approved

**Date:** 2026-11-07
**Review by:** 2027-02-05
**Status:** Active
**Status note (2026-11-07):** committed in f66cb067. The "not yet committed" wording below is kept as history; git is the source of truth for commit status (CLAUDE.md v0.1.4).
**Scope:** Project (the approved reference trace outlives feature/per-tic-demo-suite; every future DEMO1 comparison depends on it)
**Classification:** Internal (commit ids, file hashes and a command line; no Confidential or Secret content)
**Approved by:** Human (project owner), in session on 2026-11-07, under coding standard 4
**Branch / commit:** feature/per-tic-demo-suite, source commit 01044d09 (trace not yet committed at time of writing)
**Related:** decision-001 (per-tic reference traces); decision-003 (trace format v1); decision-004 (fixed run flags); decision-005 (trace path); coding standard 4
**Supersedes:** none

**Decision:** tests/demos/heretic/golden/demo1.tics, generated as recorded below, is the approved DEMO1 reference trace (Task 3 in docs/smoke-tests/demo-suite.md).

**Provenance:**
- Source commit: 01044d09d232bcd7684fce42661f6b5310b57200, working tree clean before and after the build. src/ is unchanged from the -tichash hook commit 066ea6ac.
- Build: `make clean`, then a full `make`, both exit 0, using the existing configure output (configure was not re-run).
- Binary: src/chocolate-heretic, 3443168 bytes, sha256 363af95782323ce2aa3e2882195c9293b51f8ea615fd4f7630b667a8a2feefac.
- WAD: wads/blasphem.wad sha256 e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63, matching the value pinned in scripts/demo1-check.sh.
- Invocation (decision-004, exactly):
  `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy src/chocolate-heretic -iwad wads/blasphem.wad -timedemo demo1 -nodraw -nosound -tichash tests/demos/heretic/golden/demo1.tics`
- Trace: sha256 537e8a1fd73967c0099d1ee55c0586e353d5240d27dd3a41dfa15ac3757d2f30, 340359 bytes, 4228 lines (the v1 header plus gametics 0-4226, so DEMO1 has no non-level tics). LF endings, no trailing spaces, ends with a newline.

**Determinism check:** The same invocation was run twice, the second run writing to a scratch file. Both runs printed `timed 4227 gametics`, and `cmp` found the two traces byte-identical (same sha256, size and line count). The scratch copy was not kept in the repo.

**Exit code:** Both runs exited 255. That is normal for chocolate-heretic after -timedemo and is not a failure. The `timed N gametics` line decides the result, not the exit code. The runner (Task 5) must not treat 255 as a FAIL.

**Rationale:** This is the reference that decision-001 calls for. The clean rebuild means the binary is tied to a known commit, so the trace's source commit can be recorded honestly. The previous binary predated the hook commit and could not be tied to one. The two-run check confirms that the fixed flags give a reproducible trace before it becomes the reference.

**Why this layer:** This is a decision entry, not knowledge or current-state, because it records a human approval with its reasons and provenance. That has to stay findable after the branch merges, and any regeneration would supersede it. It is not knowledge because it is not a standing rule; coding standard 4 is the rule, and this entry records one approval under it. It is not current-state because current-state is workflow-scoped and is archived when the branch merges, while the trace's provenance stays relevant.

**Constraint:** Regenerating, editing, moving or renaming this trace needs human approval (coding standard 4) and a new decision entry that supersedes this one. Once Task 4 adds tests/demos/heretic/manifest, the manifest is the repo's source of truth for the trace sha256 and source commit; this entry records the approval and why.
