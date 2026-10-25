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
| C | Small dummy text file at `wads/blasphem.wad` | 2 | 2 | `ERROR: wads/blasphem.wad sha256 mismatch: expected e9ed3f53…4cc63, got bdfc8662…3aed64` | yes |
| D | Real wad restored, `EXPECTED_TICS=1` | 1 | 1 | `FAIL: 4227 gametics != expected 1` | yes |

Notes:
- Case A also printed `timed 4227 gametics in 132 realtics` and `engine exit code: 255` (expected for a timedemo).
- Case C exited before the demo ran (no `IWAD OK` or `timed` line). Full dummy sha256: `bdfc866253d0f29819ce485d6bacb0ea25ec2273d49318b4eb31e2bfd13aed64`.
- Case D ran the demo normally (`timed 4227 gametics in 120 realtics`, engine exit 255) and failed only on the tic comparison.
- No case hung or opened a window (runs are headless via `SDL_VIDEODRIVER=dummy`).

## Restore check

- WAD sha256 after restore (step 9): `e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63`, matches step 1 and the pinned value.
- Dummy file deleted; `/tmp/blasphem.wad.bak` no longer exists.
- `git status --short` after Case D (step 11): empty, same as step 2. The only change after this run is this new results file.

## Verdict

PASS: all four cases (A–D) gave the expected exit code and message, and the repo was restored cleanly.
