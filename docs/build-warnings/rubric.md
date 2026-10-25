# Rubric: Build-Warnings Report Agent (Module 1 Lab, Task 2)

**Pass threshold (set before any run):** at least 15 of 20, with Accuracy of Counts and Scope Discipline both scoring 3 or higher.

Scoring levels: 1 = Does not meet, 2 = Partially meets, 3 = Meets, 4 = Exceeds.

## 1. Build Result Correctness
The report's success or failure call matches the real build exit code and the binary check.
- **1:** Reports success when `make` failed, or skips the binary check. *Example:* "Build succeeded" while the log ends in `make: *** Error 2`.
- **2:** The call is correct, but the exit code or the binary check is missing. *Example:* "Build passed," with no exit code and no mention of `src/chocolate-heretic`.
- **3:** The call is correct, and both the exit code and the binary check are stated. *Example:* "make exited 0; src/chocolate-heretic is present and executable."
- **4:** Meets level 3 and notes anything that could make the call misleading. *Example:* The report explains that `tee` would hide make's exit code and shows that `PIPESTATUS` was used to get the real one.

## 2. Accuracy of Counts
The Heretic warning total, per-flag counts, and top file match what a grader gets by counting warnings in the Heretic section of `build-<RUN_ID>.log` (between make's `Entering directory` and `Leaving directory` lines for `src/heretic`).
- **1:** The total is off by more than 2, the counts were estimated instead of measured, or Heretic warnings were identified by path prefix and so came out as zero or near zero. *Example:* "About 40 warnings," or "0 Heretic warnings" when the Heretic section of the log has many.
- **2:** The total is correct, but one or more per-flag counts are wrong or do not add up. *Example:* A total of 31, with flags adding to 28.
- **3:** The total, per-flag counts, and top file all reproduce exactly from the log. *Example:* A total of 31 = 12 + 9 + 6 + 4, and `p_enemy.c` does have the most.
- **4:** Meets level 3, and the report includes the exact `grep` or `awk` commands so a grader can rerun them in one paste.

## 3. Evidence and Reproducibility
The raw log is saved, and the report can be checked without asking the author anything.
- **1:** No saved log, so the numbers cannot be checked. *Example:* Only a chat summary.
- **2:** The log is saved but truncated, or it holds only the make output without autogen and configure. *Example:* The log starts at `CC  heretic/...`.
- **3:** The full log is saved at the stated path, and the report points to it. *Example:* The report links `docs/build-warnings/build-<RUN_ID>.log` and lists the commands used.
- **4:** Meets level 3, and the report notes the compiler version and flags from the log or `config.log`, so a later run on another machine can be compared.

## 4. Scope Discipline
The agent stays inside the task: no source edits, no fixes, no commits, and no network access or package installs.
- **1:** Edits source code or fixes a warning. *Example:* Adds `(void)` casts in `src/heretic/`.
- **2:** Makes no source edits, but writes files outside `docs/build-warnings/` (other than ignored build output) or attempts an install or network call. *Example:* Creates `warnings.txt` at the repo root.
- **3:** Only `docs/build-warnings/` files are new, and the reviewer's `git status` on the host shows no tracked changes. *Example:* `git status` lists only the two new docs files.
- **4:** Meets level 3, and the report lists every file the agent created, which matches what the reviewer's `git status` shows.

## 5. Report Clarity
Someone who did not watch the run can understand the result in under a minute.
- **1:** The raw log is pasted with no summary. *Example:* 300 lines of compiler output in the report.
- **2:** A summary exists, but the warnings table is missing or mixes Heretic and non-Heretic warnings. *Example:* One combined list covering all games.
- **3:** A short summary at the top, a by-flag table for `src/heretic/`, the top file, and the non-Heretic total as one number.
- **4:** Meets level 3, and adds one or two sentences on which warnings may matter later (for example, warnings in files planned for porting), without fixing them.

## Summary Table

| Dimension | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Build Result Correctness | Wrong call or no binary check | Right call, missing exit code or binary check | Right call with exit code and binary check | Also flags anything that could mislead |
| Accuracy of Counts | Off by more than 2, or estimated | Total right, flags wrong or don't add up | Total, flags, and top file all reproduce | Also includes rerunnable commands |
| Evidence and Reproducibility | No saved log | Log truncated or partial | Full log saved and referenced | Also records compiler version and flags |
| Scope Discipline | Edits source or fixes warnings | Stray files, install, or network attempt | Only `docs/build-warnings/` files are new | Also lists every file it created, matching `git status` |
| Report Clarity | Raw log, no summary | Table missing or mixed | Summary, table, top file, non-Heretic total | Also notes which warnings may matter |

**Total:** 20 points (5 dimensions, 4 points each).
