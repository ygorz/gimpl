# Iteration Log: Build-Warnings Report Agent (Module 1 Lab, Task 2)

**Pass threshold (set before Run T2-001):** at least 15 of 20, with Accuracy of Counts and Scope Discipline both scoring 3 or higher.

**How each field is measured:**
- Cycle time is the `real` time reported by `time claude "<prompt>"`.
- Review latency is the time from the agent finishing (after `/exit`) to scoring being complete.
- Cost and tokens come from `/cost` at the end of the session.
- Isolation was verified before the run: `ls /workspace/ISOLATION-*` showed only `ISOLATION-T2` in this container (and only `ISOLATION-T1` in the Task 1 container); `ls /workspace/..` and `ls / | grep -i gimpl` showed no sibling worktree; `docker inspect gimpl-t2` showed only `gimpl-lab-t2 -> /workspace` and the `claude-auth` volume.
- Scope is checked by running `git status` on the host in the `gimpl-lab-t2` worktree after the run.

| Run ID | Date | Agent/tool | Prompt or command | Cycle time | Rubric scores (notes) | Pass/fail | Review latency | Cost / tokens | Observations |
|---|---|---|---|---|---|---|---|---|---|
| T2-001 | 2026-10-25 | Claude Code (Opus) in the gimpl container, worktree `gimpl-lab-t2` | Prompt v1 (below), run as `time claude "$(cat /tmp/prompt-t2.txt)"` | 2m 8.5s | Build Result: 4/4 (exit 0, binary checked, explained `PIPESTATUS` vs `tee`) · Counts: 4/4 (0 Heretic warnings, matches host awk check; `-Wall` confirmed on; rerunnable commands included) · Evidence: 3/4 (full log saved and referenced, CFLAGS noted, no compiler version) · Scope: 4/4 (no source edits, no git; files listed match host `git status`: only the two new docs files) · Clarity: 3/4 (clear summary and tables; nothing to flag for porting with zero warnings) · Total: 18/20 | Pass (18 ≥ 15; Counts and Scope ≥ 3) | 3m 28.76s | $0.29 total. Opus: 518 input, 4.4k output, 265.8k cache read, 17.9k cache write. Haiku: 1.8k input, 21 output. | Zero Heretic warnings is a real result, not a counting failure; the prompt's rules didn't anticipate build output outside `docs/build-warnings/`. Full notes in Run notes below. |

## Run notes

### T2-001 observations
- **Zero warnings is a real result, and it was verified.** Heretic compiles with no warnings under `-Wall -Wdeclaration-after-statement -Wredundant-decls`. An empty count could also mean the counting method was broken (the original path-prefix approach would have read 0 too, because make prints bare filenames). The agent ruled that out by confirming `-Wall` is in the Heretic Makefile and that the Heretic section of the log (lines 279 to 327) holds only compile and link lines. Anyone repeating this task should keep that check, because a zero without it means nothing.
- **What this means for the port:** the C side is a clean baseline. Any warning that appears in a later build is a new, real signal, not old noise, which makes this a cheap regression check to rerun after each port.
- **The other 5 warnings are not from the compiler.** Three come from autotools (an obsolete `AC_PROG_CC_C99` macro, a note about `win_opendir.c` in a subdirectory, and a forward-compatibility notice). Two are make "clock skew detected" warnings, caused by the Mac and the container (which runs on UTC) disagreeing about file timestamps. It didn't affect this clean build, but it could confuse incremental rebuilds in a shared worktree.
- **The prompt's scope rule was ambiguous in practice.** "Only create files under `docs/build-warnings/`" conflicts with running the build, which has to create `configure`, Makefiles, `*.o` files, and binaries across the tree. The agent handled it sensibly by listing those as build output, and `.gitignore` keeps them out of `git status`, but the next prompt should say "build output ignored by git is expected" instead of relying on the agent to work that out.
- **Reproducibility gap:** the agent wrote its counting script to a scratch file, `hw.awk`, outside the repo. The report shows the script's contents, so it can still be rerun, but the next prompt should ask for one-line commands inline and the compiler version (`cc --version`), which was the one point lost on Evidence.

## Run prompts

### Prompt v1 (T2-001)

The prompt was saved to `/tmp/prompt-t2.txt` inside the container (outside the repo) so the `$` and quote characters reach Claude unchanged, then run with `time claude "$(cat /tmp/prompt-t2.txt)"`.

```
You are in the gimpl repo root at /workspace (a fork of Chocolate Doom; only Chocolate Heretic in src/heretic is in scope).

Task: run the documented build and report on compiler warnings. Do not fix anything.

1. Confirm there is no existing build output for Heretic (no src/chocolate-heretic, no src/heretic/*.o).
2. Run: mkdir -p docs/build-warnings && (./autogen.sh && make) 2>&1 | tee docs/build-warnings/build-T2-001.log ; echo "build exit: ${PIPESTATUS[0]}"
3. Check that src/chocolate-heretic exists and is executable.
4. From build-T2-001.log, count the warning lines produced while make is building src/heretic/, grouped by the warning flag in brackets (like [-Wunused-variable]); count warnings with no bracketed flag as "(no flag)". Make builds each folder from inside it, so warning lines show bare filenames like p_enemy.c:123:5: warning: ... A warning is a Heretic warning when it appears between make's "Entering directory '.../src/heretic'" and "Leaving directory '.../src/heretic'" lines. Also find the src/heretic/ file with the most warnings, and count all other warnings as one number.
5. Write docs/build-warnings/report-T2-001.md with: build result and real exit code, the binary check, total Heretic warnings, a table of Heretic warnings by flag, the top file, the non-Heretic total, the exact grep/awk commands you used, and a list of every file you created. Do not run git; it will not work in this container.

Use the run ID T2-001 in both output filenames. If either file already exists, stop and tell me instead of overwriting it.

Rules: only create files under docs/build-warnings/. Do not edit any source file, do not try to silence or fix warnings, do not install packages, do not use the network, and do not git commit or push. If the build fails, stop after step 2, quote the first error line, and still write the report.
```

## Final state after merge

Output of `git log --oneline --graph -15` on `master` after both lab branches were merged:

```
(added after both merges)
```
