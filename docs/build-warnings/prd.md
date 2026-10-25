# PRD: Build-Warnings Report Agent (Module 1 Lab, Task 2)

## Workflow summary
A single Claude Code agent, running in the gimpl Docker container, runs the documented build (`./autogen.sh && make`) from a fresh worktree. It saves the full build log and writes a short report on whether the build succeeded and which compiler warnings appear in `src/heretic/`. It does not fix anything.

## Trigger
The operator starts Claude Code inside the gimpl container, with only the Task 2 worktree mounted at `/workspace`, and gives it the Task 2 prompt.

Precondition: the worktree is a fresh checkout of `master` with no prior build output, meaning `src/heretic/*.o` and `src/chocolate-heretic` do not exist.

## Decision events
- If `./autogen.sh` or `configure` fails, the agent stops, saves whatever output exists to the log, and reports the build as failed, quoting the first error line.
- If `make` exits non-zero, the agent reports the build as failed, quotes the first `error:` line, and still counts any warnings that appeared before the failure.
- If `make` exits 0, the agent confirms that `src/chocolate-heretic` exists and is executable before calling the build a success.
- If there are no warnings in `src/heretic/`, the agent says so plainly instead of producing an empty breakdown.
- If any step would require editing files outside `docs/build-warnings/`, installing packages, or using the network, the agent refuses and stops.

## Output files
Each run writes its own files, named with the run ID (for example, `build-T2-001.log` and `report-T2-001.md`), so a rerun never overwrites an earlier run's evidence. If a file with that name already exists, the agent stops instead of overwriting it.

## Ordered actions
1. Confirm the working directory is the repo root and that no Heretic build output exists yet.
2. Run `(./autogen.sh && make) 2>&1 | tee docs/build-warnings/build-<RUN_ID>.log` and record the exit status of the build itself, not of `tee`.
3. Check that `src/chocolate-heretic` exists and is executable.
4. From `build-<RUN_ID>.log`, count the `warning:` lines produced while make is building `src/heretic/`, grouped by the warning flag in brackets (for example, `[-Wunused-variable]`). Because make builds each folder from inside that folder, warning lines show bare filenames such as `p_enemy.c:123:5: warning: ...`. A warning belongs to Heretic when it appears between make's `Entering directory '.../src/heretic'` and `Leaving directory '.../src/heretic'` lines, not because its path starts with `src/heretic/`. Warnings with no bracketed flag are counted under "(no flag)".
5. Identify the `src/heretic/` file with the most warnings, and count the warnings outside `src/heretic/` as a single number.
6. Write `docs/build-warnings/report-<RUN_ID>.md` containing the build result and exit code, the binary check, the total Heretic warning count, a table of warnings by flag, the top file, the non-Heretic total, the exact commands used to produce the counts, and a list of every file the agent created.
7. Leave every file outside `docs/build-warnings/` unchanged, make no commits or pushes, and do not attempt to fix any warning.

## Acceptance criteria
1. `docs/build-warnings/build-<RUN_ID>.log` exists and contains the full autogen, configure, and make output.
2. The report's success or failure call matches the real build exit code and whether `src/chocolate-heretic` is executable.
3. The report's total Heretic warning count exactly equals the result of `awk '/Entering directory .*src\/heretic/{h=1} /Leaving directory .*src\/heretic/{h=0} h && /: warning:/' docs/build-warnings/build-<RUN_ID>.log | wc -l`.
4. Every per-flag count in the table can be reproduced from the same Heretic section of the log, and the per-flag counts, including "(no flag)", add up to the total.
5. The named top file has the highest count when the log's Heretic warnings are grouped by file. Ties are reported as ties.
6. When the reviewer runs `git status` on the host, no tracked files are changed, and the only new untracked files are under `docs/build-warnings/` (build output is ignored by `.gitignore`). Git is checked on the host because a worktree's `.git` pointer file leads to the main repo, which is not mounted in the container.
7. The agent does not push, install packages, or edit source code to silence warnings.

## Why this task
The task is procedural and can be checked from the saved log alone. It is clearly different from Task 1, which runs `scripts/demo1-check.sh` and its failure cases. It also gives useful information about the codebase before the Rust ports begin: how noisy the Heretic C build is, and which warnings an agent should leave alone.
