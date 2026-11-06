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
- Reference traces are never regenerated or edited silently. A changed
  trace needs human approval and a commit that says why (coding standard 4).
- Approach 2 (a pinned C reference build run side by side) is deferred, not
  rejected; see `.memory/project/decisions/decision-001.md`.
- `scripts/demo1-check.sh` stays unchanged while the suite is built.

## What Feature 1 still needs

1. **C hook.** Add an opt-in `-tichash <file>` flag. After `P_Ticker()` in
   `G_Ticker` (`src/heretic/g_game.c:1259`), write one line per tic with
   the fields listed in "Trace format (v1)" below. It must not change
   behaviour when the flag is absent.
2. **Trace format.** Done: pinned as v1 below (decision-003).
3. **Reference trace.** Generate `tests/demos/golden/demo1.tics` from a
   known-good C build and record that commit.
4. **Manifest.** Add `tests/demos/manifest` with demo name, expected gametics,
   trace sha256 and the source commit for each demo.
5. **Runner.** Replace the stub body of `scripts/demo-suite.sh` with the
   planned steps: wad check, manifest/trace sha256 check, headless run, tic
   count check, per-tic comparison by `gametic` reporting the first tic and
   field that differ, and exit codes 0/1/2.
6. **Hook-off check.** Confirm `scripts/demo1-check.sh` still passes (4227)
   with the hook built in but the flag not set.
7. **Failure-path runs.** Record a PASS run and forced FAIL runs (edited trace,
   bad sha256), as done for `demo1-check.sh`.
8. **Agent.** Update `demo-verifier` to call the suite (rubric and iteration
   log too).
9. **Later.** DEMO3 (2582, not yet pinned) and DEMO2 stay out until DEMO1
   works end to end.

## Trace format (v1)

Pinned 2026-11-06 (`.memory/project/decisions/decision-003.md`). Changing it
means bumping the version in the header and regenerating the reference
traces, which needs human approval (coding standard 4).

### File layout

- ASCII text, `\n` line endings, one file per demo
  (`tests/demos/golden/<demo>.tics`).
- Line 1 is this header, exactly:

  ```
  #tichash v1 gametic rndindex prndindex {pN x y z angle momx momy health armor readyweapon artifactcount invslot}
  ```

  `{...}` marks the per-player group, repeated once per player in game.
- After the header, one line per tic on which the hook runs: after
  `P_Ticker()` in the `GS_LEVEL` case of `G_Ticker`. Non-level tics
  (intermission, finale, demo screen) write no line, so `gametic` values can
  skip. That is expected.
- Fields are separated by one ASCII space. No leading or trailing space.

### Line layout

`gametic rndindex prndindex`, then for each player `i` with
`playeringame[i]`, in ascending `i`: `p<i>` followed by the 11 player fields
in the order below. Each player block starts with `pN`, so a missing player
never shifts another player's columns.

| Column        | Source                            | Encoding |
|---------------|-----------------------------------|----------|
| gametic       | `gametic`                         | decimal  |
| rndindex      | `rndindex`                        | decimal  |
| prndindex     | `prndindex`                       | decimal  |
| pN            | player number `i`                 | `p` + decimal |
| x             | `players[i].mo->x`                | hex      |
| y             | `players[i].mo->y`                | hex      |
| z             | `players[i].mo->z`                | hex      |
| angle         | `players[i].mo->angle`            | hex      |
| momx          | `players[i].mo->momx`             | hex      |
| momy          | `players[i].mo->momy`             | hex      |
| health        | `players[i].mo->health`           | decimal  |
| armor         | `players[i].armorpoints`          | decimal  |
| readyweapon   | `players[i].readyweapon`          | decimal  |
| artifactcount | `players[i].artifactCount`        | decimal  |
| invslot       | `players[i].inventorySlotNum`     | decimal  |

- **hex:** the value cast to 32-bit unsigned, lowercase, zero-padded to 8
  digits. C: `printf("%08x", (unsigned int) v)`. Rust: `format!("{:08x}", v as u32)`.
  A negative `fixed_t` therefore appears in two's complement (`-64.0` is
  `ffc00000`).
- **decimal:** C `%d`, Rust `{}` on the value as `i32`. No padding, `-` for negatives.

Illustrative line (made-up values, not from a real trace):

```
0 0 0 p0 ffc00000 01600000 00000000 40000000 00000000 00000000 100 0 1 0 0
```

### Comparison rules (runner)

- The header must match the reference exactly. A mismatch is a setup error
  (exit 2), not a FAIL.
- Lines are matched by `gametic`, not by line number. A `gametic` present in
  only one of the two traces is a FAIL (missing or extra tic).
- On FAIL, report the first differing `gametic` and the field by its header
  name, e.g. `gametic 1234: p0.momx expected 0001a000 got 0001a001`.
