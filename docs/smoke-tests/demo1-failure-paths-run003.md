# DEMO1 failure-path smoke test: Run 003

Date: 2026-10-25. Followed `docs/prd.md` ("Ordered actions" 1–12), running from the repo root (`/workspace`) inside the container. The engine was already built (`src/chocolate-heretic`). Each script run was wrapped in `timeout 300` so a hang would show up as exit 124. None hung, and no window opened (the script sets `SDL_VIDEODRIVER=dummy`).

## Results

| Case | Condition | Expected exit | Actual exit | Key output line | Match |
|---|---|---|---|---|---|
| A | Real wad in place, default `EXPECTED_TICS=4227` | 0 | 0 | `PASS: 4227 gametics == expected 4227` | yes |
| B | `wads/blasphem.wad` missing (moved to `/tmp/blasphem.wad.bak`) | 2 | 2 | `ERROR: wads/blasphem.wad is missing` | yes |
| C | Dummy 38-byte text file at `wads/blasphem.wad` | 2 | 2 | `ERROR: wads/blasphem.wad sha256 mismatch: expected e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63, got bdfc866253d0f29819ce485d6bacb0ea25ec2273d49318b4eb31e2bfd13aed64` | yes |
| D | Real wad restored, forced `EXPECTED_TICS=1` | 1 | 1 | `FAIL: 4227 gametics != expected 1` | yes |

**Overall verdict: PASS. All four cases matched their expected exit codes (A=0, B=2, C=2, D=1), and the wad was restored with the pinned sha256.**

Case C exited at the IWAD check before the demo ran: no `IWAD OK` or `timed` line was printed. In Cases A and D the engine printed `timed 4227 gametics in 121 realtics` and exited with code 255, which the script treats as normal after a timedemo.

## Exact commands (each repeatable in one step from the repo root)

Case A:
```sh
timeout 300 scripts/demo1-check.sh; echo "EXIT=$?"
```

Case B (setup + run; restore afterwards with `mv /tmp/blasphem.wad.bak wads/blasphem.wad`):
```sh
mv wads/blasphem.wad /tmp/blasphem.wad.bak && timeout 300 scripts/demo1-check.sh; echo "EXIT=$?"
```

Case C (setup + run, assuming the real wad is already at `/tmp/blasphem.wad.bak` from Case B):
```sh
echo "dummy wad for demo1 failure-path test" > wads/blasphem.wad && timeout 300 scripts/demo1-check.sh; echo "EXIT=$?"
```

Restore (step 8–9):
```sh
rm wads/blasphem.wad && mv /tmp/blasphem.wad.bak wads/blasphem.wad && sha256sum wads/blasphem.wad
```

Case D:
```sh
EXPECTED_TICS=1 timeout 300 scripts/demo1-check.sh; echo "EXIT=$?"
```

## Restore and cleanliness checks

- Step 1 sha256 (before): `e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63`
- Step 9 sha256 (after restore): `e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63`. This matches step 1 and the pinned value.
- `/tmp/blasphem.wad.bak` no longer exists. `/tmp` contains only Claude Code's own `cc-socks` and `claude-0`. `wads/` contains only `blasphem.wad`.
- Step 2 listing of `docs/smoke-tests/`: `agent-summary.md`, `demo1-check.md`, `demo1-failure-paths-run002.md`, `demo1-failure-paths.md`.
- Step 11 listing: the same four files plus this file, `demo1-failure-paths-run003.md`.
- No tracked files were edited, no commits were made, and git was not run. The reviewer checks `git status` on the host.
