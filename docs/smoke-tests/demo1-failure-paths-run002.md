# DEMO1 check: failure-path smoke test

Date: 2026-10-25
Script: `scripts/demo1-check.sh` (unchanged)
Procedure: `docs/prd.md`, "Ordered actions" 1–12
Exit code convention (from the script header): 0 = PASS, 1 = FAIL, 2 = setup/precondition error.

## Preconditions

- `src/chocolate-heretic` present and executable.
- WAD sha256 before the run (step 1): `e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63` (matches the pinned value).
- `git status --short` before the run (step 2): empty (clean tree).

## Results

| Case | Condition | Expected exit | Actual exit | Key output line | Match |
|------|-----------|---------------|-------------|-----------------|-------|
| A | Real wad in place, default `EXPECTED_TICS=4227` | 0 | 0 | `PASS: 4227 gametics == expected 4227` | yes |
| B | `wads/blasphem.wad` moved to `/tmp/blasphem.wad.bak` (missing) | 2 | 2 | `ERROR: wads/blasphem.wad is missing` | yes |
| C | Small dummy text file at `wads/blasphem.wad` | 2 | 2 | `ERROR: wads/blasphem.wad sha256 mismatch: expected e9ed3f53…4cc63, got d2aaac54…01d74b` | yes |
| D | Real wad restored, `EXPECTED_TICS=1` | 1 | 1 | `FAIL: 4227 gametics != expected 1` | yes |

Notes:
- Case A also printed `timed 4227 gametics in 121 realtics (1222.685913 fps)` and `engine exit code: 255` (expected for a timedemo).
- Case C exited before the demo ran (no `IWAD OK` or `timed` line). Full dummy sha256: `d2aaac54ca01bf797060888b457b4bd9cb2410888c248812fe071fb79401d74b`.
- Case D ran the demo normally (`timed 4227 gametics in 121 realtics`, engine exit 255) and failed only on the tic comparison.
- No case hung or opened a window (runs are headless via `SDL_VIDEODRIVER=dummy`; each was wrapped in `timeout 300`).

## Commands to repeat each case

Run from the repo root. B and C include their own setup and restore, so each line can be pasted on its own and leaves the WAD in place.

| Case | Command |
|------|---------|
| A | `timeout 300 scripts/demo1-check.sh; echo "exit=$?"` |
| B | `mv wads/blasphem.wad /tmp/blasphem.wad.bak && { timeout 300 scripts/demo1-check.sh; echo "exit=$?"; }; mv /tmp/blasphem.wad.bak wads/blasphem.wad` |
| C | `mv wads/blasphem.wad /tmp/blasphem.wad.bak && echo "dummy wad for failure-path test" > wads/blasphem.wad && { timeout 300 scripts/demo1-check.sh; echo "exit=$?"; }; rm -f wads/blasphem.wad; mv /tmp/blasphem.wad.bak wads/blasphem.wad` |
| D | `EXPECTED_TICS=1 timeout 300 scripts/demo1-check.sh; echo "exit=$?"` |

In this run, B and C were executed back to back (the real wad stayed in `/tmp/blasphem.wad.bak` across both and was restored once after C, per PRD steps 4–8). The per-case lines above are equivalent and self-restoring.

## Restore check

- WAD sha256 after restore (step 9): `e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63`, matches step 1 and the pinned value.
- Dummy file deleted; `/tmp/blasphem.wad.bak` no longer exists.
- `git status --short` after Case D (step 11): empty, same as step 2.

## Verdict

PASS: all four cases (A–D) gave the expected exit code and message, and the repo was restored cleanly.
