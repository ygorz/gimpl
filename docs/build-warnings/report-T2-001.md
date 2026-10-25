# Build warnings report — run T2-001

Scope: Chocolate Heretic (`src/heretic/`). Nothing was fixed or changed in the source.

## Build result

- Command: `mkdir -p docs/build-warnings && (./autogen.sh && make) 2>&1 | tee docs/build-warnings/build-T2-001.log ; echo "build exit: ${PIPESTATUS[0]}"`
- Exit code (`${PIPESTATUS[0]}`, which is the build's own code, not `tee`'s): **0**. The build **succeeded**.
- Before the build there was no `src/chocolate-heretic` and no `src/heretic/*.o`.
- Full log: `docs/build-warnings/build-T2-001.log`

## Binary check

`src/chocolate-heretic` exists and is executable (`-rwxr-xr-x`, 3441112 bytes; `test -x` passed).

## Heretic warnings

**Total: 0.** The Heretic section of the log runs from line 279 (`make[3]: Entering directory '/workspace/src/heretic'`) to line 327 (`Leaving directory`). It has only `CC`/`CCLD` lines and no `warning:` lines. The Heretic Makefile compiles with `CFLAGS = -O2 -g -Wall -Wdeclaration-after-statement -Wredundant-decls`, so warnings were turned on. The zero is real, not caused by warnings being turned off.

| Warning flag | Count |
|---|---|
| (none) | 0 |

**Top file:** none, because no `src/heretic/` file produced a warning.

## Non-Heretic warnings

**Total: 5.** None of these are C compiler warnings. They come from autotools and make:

| Log line | Warning |
|---|---|
| 1 | `configure.ac:42: warning: The macro 'AC_PROG_CC_C99' is obsolete.` |
| 12 | `src/Makefile.am:59: warning: source file '$(top_builddir)/win32/win_opendir.c' is in a subdirectory,` |
| 14 | `automake: warning: possible forward-incompatibility.` |
| 73 | `make: warning:  Clock skew detected.  Your build may be incomplete.` |
| 75 | `make: warning:  Clock skew detected.  Your build may be incomplete.` |

Note: the clock-skew warning means some file timestamps in the container are in the future. Make says the build "may be incomplete". The build started from a clean tree and the Heretic section compiled every object, so this probably did not matter here. It is worth knowing about for later incremental builds.

## Commands used

The awk script below follows make's Entering/Leaving lines as a stack of directories. It tags each `: warning: ` line `H` if the current directory is `src/heretic`, otherwise `O`. The script was saved to a scratch file, `hw.awk`:

```awk
/Entering directory '/ { d=$0; sub(/.*Entering directory '/,"",d); sub(/'.*/,"",d); st[++n]=d; next }
/Leaving directory '/  { if(n>0) n--; next }
/: warning: / { cur=(n>0?st[n]:""); h=(cur ~ /\/src\/heretic$/); print (h?"H":"O") "\t" $0 }
```

```sh
L=build-T2-001.log
grep -c ': warning: ' $L                                   # all warning lines -> 5
awk -f hw.awk $L | cut -f1 | sort | uniq -c                # H vs O -> 0 H, 5 O
# by flag (Heretic only)
awk -f hw.awk $L | awk -F'\t' '$1=="H"{ if (match($2,/\[-W[^]]*\]$/)) f=substr($2,RSTART,RLENGTH); else f="(no flag)"; c[f]++ } END{for(f in c) print c[f], f}' | sort -rn
# by file (Heretic only)
awk -f hw.awk $L | awk -F'\t' '$1=="H"{split($2,a,":"); c[a[1]]++} END{for(f in c) print c[f], f}' | sort -rn | head
# cross-check
grep -n ': warning: ' $L
grep -n "directory '/workspace/src/heretic'" $L            # -> lines 279 and 327
sed -n '279,327p' $L | grep -ci warning                    # -> 0
grep -n 'Wall' /workspace/src/heretic/Makefile             # confirms -Wall in CFLAGS
```

## Files created

- `docs/build-warnings/build-T2-001.log` (build log)
- `docs/build-warnings/report-T2-001.md` (this report)
- `hw.awk`, a scratch helper in the session scratchpad. It is outside the repo.
- Build products from `autogen.sh`/`make` across the tree: `configure`, Makefiles, `config.h`, `*.o`, `src/chocolate-*` binaries and so on. The task asked for this build, but these files are outside `docs/build-warnings/`.
