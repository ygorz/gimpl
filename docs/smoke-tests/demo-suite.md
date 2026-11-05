# Per-tic demo suite (`scripts/demo-suite.sh`) - Feature 1 stub

Status: **stub**. The script prints usage and planned steps and exits 0. It
does not run any demo. `scripts/demo1-check.sh` stays the DEMO1 check until
the suite works, and is kept alongside it afterwards.

## Decisions

- Approach 1: per-tic reference traces committed to the repo, run by a bash script.
- `src/` edits are allowed only for the opt-in `-tichash` hook.
- DEMO1 only to start (pinned at 4227 gametics).
- Fingerprint covers RNG (`rndindex`, `prndindex`) and player state only,
  not the thinker list.

## What Feature 1 still needs

1. **C hook.** Add an opt-in `-tichash <file>` flag. After `P_Ticker()` in
   `G_Ticker` (`src/heretic/g_game.c:1259`), write one line per tic with
   `gametic`, `rndindex`, `prndindex` and, for each player in game, the mobj
   x/y/z, angle, momx/momy, health, armor points, ready weapon and inventory
   count. It must not change behaviour when the flag is absent.
2. **Trace format.** Pin the line format (field order, decimal or hex) in this
   doc before generating any trace.
3. **Reference trace.** Generate `tests/demos/golden/demo1.tics` from a
   known-good C build and record that commit.
4. **Manifest.** Add `tests/demos/manifest` with demo name, expected gametics,
   trace sha256 and the source commit for each demo.
5. **Runner.** Replace the stub body of `scripts/demo-suite.sh` with the
   planned steps: wad check, manifest/trace sha256 check, headless run, tic
   count check, per-tic comparison reporting the first tic and field that
   differ, and exit codes 0/1/2.
6. **Hook-off check.** Confirm `scripts/demo1-check.sh` still passes (4227)
   with the hook built in but the flag not set.
7. **Failure-path runs.** Record a PASS run and forced FAIL runs (edited trace,
   bad sha256), as done for `demo1-check.sh`.
8. **Agent.** Update `demo-verifier` to call the suite (rubric and iteration
   log too).
9. **Later.** DEMO3 (2582, not yet pinned) and DEMO2 stay out until DEMO1
   works end to end.
