# Demo suite failure-path runs: Feature 1 Task 7

Date: 2026-11-16 (America/Denver). Feature 1 Task 7: failure-path runs of `scripts/demo-suite.sh`, modeled on `docs/smoke-tests/demo1-failure-paths-run003.md`.

Forced failures used temp copies in a `mktemp -d` tree outside the repo. The real golden trace (`tests/demos/heretic/golden/demo1.tics`) and the real manifest (`tests/demos/heretic/manifest`) were never edited. The runner resolves `ROOT` from its own location (`ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`), so a copy at `$T/scripts/demo-suite.sh` runs against `$T`. The engine binary and the wad were symlinked into `$T`; the manifest and the trace were fresh copies restored into `$T` before each case.

Engine exit code 255 after `-timedemo` is normal (decision-006); the `timed N gametics` line decides the result. Runner exit codes: 0 PASS, 1 FAIL, 2 setup error.

No build was done. `src/chocolate-heretic` is dated 2026-11-07 21:23:48 UTC and no `.c`, `.h` or `.am` file under `src/` is newer.

## Results (required cases)

| Case | Condition | Expected exit | Actual exit | Key output line | Match |
|---|---|---|---|---|---|
| A | Real PASS, in the repo, real golden and manifest | 0 | 0 | `PASS: demo1 4227 gametics, trace matches` | yes |
| B | Temp trace edited at gametic 100 (p0 armor 0 -> 50), temp manifest sha256 updated to the edited trace | 1 | 1 | `gametic 100: p0.armor expected 50 got 0` | yes |
| C | Temp manifest sha256 set to 64 `a` characters, trace intact | 2 | 2 | `ERROR: tests/demos/heretic/golden/demo1.tics sha256 mismatch: expected aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, got 537e8a1fd73967c0099d1ee55c0586e353d5240d27dd3a41dfa15ac3757d2f30` | yes |

Notes on the table:

- Case C is a setup error (exit 2) by the runner's design, not exit 1. The sha256 check runs before the demo, so no `timed` line is printed.
- In Case B, "expected 50" is the edited value because the temp trace is the reference; "got 0" is what the engine produced. The manifest sha256 had to be updated to the edited trace's sha256, or the runner exits 2 at the sha256 check (this is O1 below).

## Results (OPTIONAL cases O1 to O5)

These are optional extras, not required by Task 7. All behaved as expected.

| Case | Condition | Expected exit | Actual exit | Key output line | Match |
|---|---|---|---|---|---|
| O1 OPTIONAL | Trace edited (momy edit), manifest sha256 not updated | 2 | 2 | `ERROR: tests/demos/heretic/golden/demo1.tics sha256 mismatch: expected 537e8a1fd73967c0099d1ee55c0586e353d5240d27dd3a41dfa15ac3757d2f30, got b23a7ac74f38c1acdf8ddd913899dc772cdc3d71a5a1ef66d05e0603511db823` | yes |
| O2 OPTIONAL | Manifest sha256 is `abc123` | 2 | 2 | `ERROR: tests/demos/heretic/manifest: sha256 must be 64 hex characters for demo1 (got 'abc123')` | yes |
| O3 OPTIONAL | Manifest gametics set to 4226 | 1 | 1 | `FAIL: demo1 4227 gametics != expected 4226` | yes |
| O4 OPTIONAL | `$T/src/chocolate-heretic` symlink removed | 2 | 2 | `ERROR: src/chocolate-heretic is missing or not executable (build it first)` | yes |
| O5 OPTIONAL | Temp trace header `v1` -> `v2`, manifest sha256 updated | 2 | 2 | `ERROR: demo1: trace header mismatch` | yes |

**Overall verdict: PASS.** Required cases A=0, B=1, C=2 and optional cases O1=2, O2=2, O3=1, O4=2, O5=2 all matched.

## Case output (verbatim from the Tester)

Case A, in the repo:

```
IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)
trace OK: tests/demos/heretic/golden/demo1.tics (537e8a1fd73967c0099d1ee55c0586e353d5240d27dd3a41dfa15ac3757d2f30)
timed 4227 gametics in 117 realtics (1264.487183 fps)
engine exit code: 255
PASS: demo1 4227 gametics, trace matches
PASS: 1 demo(s)
EXIT=0
```

`scripts/demo1-check.sh` in the repo, run alongside:

```
IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)
timed 4227 gametics in 117 realtics (1264.487183 fps)
engine exit code: 255
PASS: 4227 gametics == expected 4227
EXIT=0
```

Case B (corrected run, field 12 = p0 armor):

```
before: 100 28 84 p0 ef801143 ffa00e9c ffc80000 00000000 00000000 00000000 100 0 1 0 0
after:  100 28 84 p0 ef801143 ffa00e9c ffc80000 00000000 00000000 00000000 100 50 1 0 0
edited sha256: 4181f063d06af081fead309219ef3b059bfb7a7a9db2beae1df322aa0c8cd68f
temp manifest: demo1 4227 4181f063d06af081fead309219ef3b059bfb7a7a9db2beae1df322aa0c8cd68f 01044d09d232bcd7684fce42661f6b5310b57200
IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)
trace OK: tests/demos/heretic/golden/demo1.tics (4181f063d06af081fead309219ef3b059bfb7a7a9db2beae1df322aa0c8cd68f)
timed 4227 gametics in 118 realtics (1253.771240 fps)
engine exit code: 255
gametic 100: p0.armor expected 50 got 0
FAIL: demo1 trace differs from tests/demos/heretic/golden/demo1.tics
FAIL: 1 of 1 demo(s) failed
EXIT=1
```

Case C:

```
IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)
ERROR: tests/demos/heretic/golden/demo1.tics sha256 mismatch: expected aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, got 537e8a1fd73967c0099d1ee55c0586e353d5240d27dd3a41dfa15ac3757d2f30
EXIT=2
```

O3 (manifest gametics 4226):

```
IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)
trace OK: tests/demos/heretic/golden/demo1.tics (537e8a1fd73967c0099d1ee55c0586e353d5240d27dd3a41dfa15ac3757d2f30)
timed 4227 gametics in 118 realtics (1253.771240 fps)
engine exit code: 255
FAIL: demo1 4227 gametics != expected 4226
FAIL: 1 of 1 demo(s) failed
EXIT=1
```

O5 (header `v1` -> `v2`):

```
manifest: demo1 4227 72d2c2677b6d6ca046c565826b58d23e83888cb644ed254007be1d48aa09a1b6 01044d09d232bcd7684fce42661f6b5310b57200
IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)
trace OK: tests/demos/heretic/golden/demo1.tics (72d2c2677b6d6ca046c565826b58d23e83888cb644ed254007be1d48aa09a1b6)
timed 4227 gametics in 119 realtics (1243.235352 fps)
engine exit code: 255
reference header: #tichash v2 gametic rndindex prndindex {pN x y z angle momx momy health armor readyweapon artifactcount invslot}
run header:       #tichash v1 gametic rndindex prndindex {pN x y z angle momx momy health armor readyweapon artifactcount invslot}
ERROR: demo1: trace header mismatch
EXIT=2
```

## Disclosed note: first Case B attempt used the wrong field

The first Case B attempt edited field 10 (p0 momy) instead of armor (`awk '$1==100{$10="999"}1'`). The runner correctly reported the difference and exited 1; it was not a runner problem, only the wrong field for the intended test. This ran in the first mktemp dir (`/tmp/tmp.qFd8syCGjK`, shared with O1 to O5).

```
before: 100 28 84 p0 ef801143 ffa00e9c ffc80000 00000000 00000000 00000000 100 0 1 0 0
after:  100 28 84 p0 ef801143 ffa00e9c ffc80000 00000000 00000000 999 100 0 1 0 0
new sha b23a7ac74f38c1acdf8ddd913899dc772cdc3d71a5a1ef66d05e0603511db823
timed 4227 gametics in 117 realtics (1264.487183 fps)
engine exit code: 255
gametic 100: p0.momy expected 999 got 00000000
FAIL: demo1 trace differs from tests/demos/heretic/golden/demo1.tics
FAIL: 1 of 1 demo(s) failed
EXIT=1
```

Case B was then rerun with field 12 (armor) in a second mktemp dir (`/tmp/tmp.9kOLqfUPvM`); that is the Case B row above. The momy edit (b23a7ac7...) was also what O1 used, with the manifest sha256 left unchanged.

## Exact commands (repeatable from the repo root, `/workspace`)

Case A (real PASS, in the repo):

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ./scripts/demo-suite.sh; echo "EXIT=$?"
```

Temp-tree setup (run once per temp dir; `T` is a new `mktemp -d`):

```sh
T=$(mktemp -d)
mkdir -p $T/scripts $T/src $T/wads $T/tests/demos/heretic/golden
cp scripts/demo-suite.sh $T/scripts/
ln -s /workspace/src/chocolate-heretic $T/src/chocolate-heretic
ln -s /workspace/wads/blasphem.wad $T/wads/blasphem.wad
```

Restore fresh copies before each forced case (reconstructed from the Orchestrator's brief; the Tester reported restoring fresh copies before each case but did not print its exact restore commands):

```sh
cp tests/demos/heretic/manifest $T/tests/demos/heretic/manifest
cp tests/demos/heretic/golden/demo1.tics $T/tests/demos/heretic/golden/demo1.tics
```

Run command for every forced case:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy $T/scripts/demo-suite.sh; echo "EXIT=$?"
```

Case B edit (field 12 = p0 armor at gametic 100; then update the temp manifest's sha256 field to the new sha256):

```sh
G=$T/tests/demos/heretic/golden/demo1.tics
awk '$1==100{$12="50"}1' $G > $G.new && mv $G.new $G
sha256sum $G
# put that sha256 in the third field of the demo1 line in $T/tests/demos/heretic/manifest
```

Case C edit (bad sha256, trace intact; set the third field of the demo1 line in the temp manifest to 64 `a` characters).

Optional cases, each after restoring fresh copies:

- O1: edit the trace as in Case B (or with `$10="999"`) and leave the temp manifest sha256 unchanged.
- O2: set the temp manifest sha256 field to `abc123`.
- O3: set the temp manifest gametics field to `4226`.
- O4: `rm $T/src/chocolate-heretic`.
- O5: change the trace header `v1` to `v2` in the temp trace and update the temp manifest sha256.

## Restore and cleanliness checks

- `sha256sum tests/demos/heretic/golden/demo1.tics tests/demos/heretic/manifest`, before and after (identical):

  ```
  537e8a1fd73967c0099d1ee55c0586e353d5240d27dd3a41dfa15ac3757d2f30  tests/demos/heretic/golden/demo1.tics
  88b799ac6d23a8a02ae3396bbfc6b7d6d402387db6492ef23287d47b39195ca3  tests/demos/heretic/manifest
  ```

- `git status --short`, before and after (identical):

  ```
  ?? lesson-4-lab-submission.patch
  ```

- Both mktemp dirs were deleted by the Tester after checking each matched `/tmp/tmp.*` (George approved the Tester deleting only its own mktemp dirs for this task). `test -e /tmp/tmp.qFd8syCGjK` exited 1 and `ls -d` reported "No such file or directory"; `test -e /tmp/tmp.9kOLqfUPvM` exited 1.
- No build was done and nothing under `src/` or `tests/demos/heretic/golden/` was touched.
