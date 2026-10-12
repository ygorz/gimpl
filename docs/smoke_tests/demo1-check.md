# DEMO1 check (`scripts/demo1-check.sh`)

The script checks `wads/blasphem.wad` against its sha256 and builds
`src/chocolate-heretic` if it is missing. It then runs
`-timedemo demo1 -nodraw -nosound`, where engine exit code 255 counts as a
normal finish. It compares the `timed N gametics` count with `EXPECTED_TICS`
(default 4227).

Exit codes: `0` PASS, `1` FAIL (tic mismatch), `2` precondition, build or run
error.

## Run 1: default (`scripts/demo1-check.sh`)

`src/chocolate-heretic` was not present, so this run did the build first. The
~645 lines of autogen/configure/make output are left out below.

```
IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)
src/chocolate-heretic not found; building...
[... autogen.sh / configure / make output trimmed ...]
timed 4227 gametics in 163 realtics (907.638062 fps)
engine exit code: 255
PASS: 4227 gametics == expected 4227
```

Exit code: **0**

## Run 2: `EXPECTED_TICS=1 scripts/demo1-check.sh`

```
IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)
timed 4227 gametics in 164 realtics (902.103638 fps)
engine exit code: 255
FAIL: 4227 gametics != expected 1
```

Exit code: **1**
