# 1. Quality Rubric: DEMO1 Check Agent

Each dimension below is derived from one acceptance criterion in `docs/prd.md`.

## 1.1 Dimensions

### 1.1.1 Case Coverage (AC1)

Measures whether the agent ran all four cases (A to D) and captured the evidence for each one. A high score requires every case to have its exit code and key output line recorded from an actual run, not assumed.

### 1.1.2 Verdict Accuracy (AC2)

Measures whether the agent's match/mismatch call for each case agrees with the script's actual exit code and the expected result in the PRD (A = 0, B and C = 2, D = 1). A high score requires every verdict to be correct and based on the exit code rather than the PASS/FAIL/ERROR text alone.

### 1.1.3 Restore Hygiene (AC3)

Measures whether the agent returned the repo to the state it found it in. A high score requires the real WAD back in place with the pinned sha256, no dummy or backup files left behind, and `git status` showing only the new results file.

### 1.1.4 Report Clarity (AC4)

Measures whether `docs/smoke-tests/demo1-failure-paths.md` lets a reader understand the outcome without rerunning anything. A high score requires a complete results table with every cell filled and a one-line overall verdict that follows from the table.

## 1.2 Binary Gates (kept as acceptance criteria, not dimensions)

These have no meaningful middle ground, so they are pass/fail gates. Failing either gate fails the run regardless of scores.

- **No tracked-file edits:** the agent did not modify `scripts/`, `src/`, or any other tracked file.
- **No commits:** the agent made no commits. Only I commit, on the host.

## 1.3 Alternatives Considered

- **One dimension per edge case:** ruled out because it would split restore checks across several overlapping dimensions that would always score the same.
- **Making "no edits" a rubric dimension:** ruled out because it is binary. A "partially edited the script" score would hide a run that should simply fail, so it stays a gate.

## Scoring Guide

Levels: 1 = Does not meet, 2 = Partially meets, 3 = Meets, 4 = Exceeds.

### Case Coverage (AC1)

- **1 - Does not meet:** Two or more cases are missing, or results are stated without the script having been run.
  - *Example:* "Case A passes; B and C would fail since the script checks for the WAD." Only Case A was actually run.
- **2 - Partially meets:** One case is missing, or all four are attempted but one is missing its exit code or key output line.
  - *Example:* Case C reads "Failed as expected" with no exit code and no `sha256 mismatch` line.
- **3 - Meets:** All four cases are run, each with its exit code and key output line recorded.
  - *Example:* "Case B: exit 2, `ERROR: wads/blasphem.wad is missing`." The other three cases are in the same form.
- **4 - Exceeds:** All four cases are fully recorded, plus the exact command used for each, so any case can be reproduced in one step.
  - *Example:* "Case D: `EXPECTED_TICS=1 scripts/demo1-check.sh` gave exit 1, `FAIL: 4227 gametics != expected 1`."

### Verdict Accuracy (AC2)

- **1 - Does not meet:** Two or more verdicts are wrong, or a failing case is reported as a match without checking the exit code.
  - *Example:* Case B is marked "match: expected FAIL (exit 1)" when the script actually exited 2, and Case D is marked a mismatch.
- **2 - Partially meets:** One verdict is wrong, or the verdicts are right but based only on PASS/FAIL text.
  - *Example:* "Case C: FAIL, match." The exit code is never mentioned, so the verdict can't be checked against the PRD.
- **3 - Meets:** All four verdicts are correct and based on the actual exit code compared with the PRD's expected one.
  - *Example:* "Case C: expected exit 2, actual exit 2, match."
- **4 - Exceeds:** All verdicts are correct, and the report explains each one in a few words, such as why Case C exits 2 (precondition error) rather than 1 (tic mismatch).
  - *Example:* "Case C: exit 2, match. The sha256 check stops the script before the demo runs, so this is a setup error, not a tic FAIL."

### Restore Hygiene (AC3)

- **1 - Does not meet:** The real WAD is not restored, or its sha256 doesn't match the pinned value.
  - *Example:* The run ends with the dummy file still at `wads/blasphem.wad`, so the next normal run of `demo1-check.sh` fails.
- **2 - Partially meets:** The WAD is restored correctly, but leftovers remain or the restore wasn't verified.
  - *Example:* `wads/blasphem.wad` is back, but `/tmp/blasphem.wad.bak` still exists and no sha256 was recomputed.
- **3 - Meets:** The WAD is restored with a matching sha256, no leftover files remain, and `git status` shows only the new results file.
  - *Example:* "Restored WAD sha256 e9ed3f53… matches the pinned value. `git status --short` shows only `?? docs/smoke-tests/demo1-failure-paths.md`."
- **4 - Exceeds:** Everything in level 3, plus the before and after `git status` and sha256 values are shown side by side in the report.
  - *Example:* A small "Before / After" block lists the same sha256 and the `git status` output on both sides, with the only difference being the results file.

### Report Clarity (AC4)

- **1 - Does not meet:** The results file is missing, or the results exist only in the chat transcript.
  - *Example:* The agent prints a summary in the terminal, but `docs/smoke-tests/demo1-failure-paths.md` was never written.
- **2 - Partially meets:** The file exists, but the table has empty cells or the overall verdict is missing or unclear.
  - *Example:* The table has no "actual exit" column, and the file ends with "Looks mostly fine."
- **3 - Meets:** The file has the full results table with every cell filled, plus a one-line overall verdict that follows from it.
  - *Example:* "Overall: 4/4 cases matched expected exit codes. The failure paths of demo1-check.sh behave as documented."
- **4 - Exceeds:** Everything in level 3, plus a short note on anything unexpected, or a follow-up worth logging, without padding.
  - *Example:* "Note: the missing-WAD message goes to stderr, so tools that only capture stdout would miss it."

### Summary Table

| Dimension | 1: Does Not Meet | 2: Partially Meets | 3: Meets | 4: Exceeds |
|-----------|------------------|--------------------|----------|------------|
| Case Coverage (AC1) | Two or more cases missing, or results assumed without running. | One case missing, or one missing its exit code or key line. | All four run, each with exit code and key line. | Level 3 plus the exact command for each case. |
| Verdict Accuracy (AC2) | Two or more verdicts wrong. | One verdict wrong, or verdicts based on text only. | All verdicts correct and based on exit codes. | Level 3 plus a short reason for each verdict. |
| Restore Hygiene (AC3) | WAD not restored, or wrong sha256. | WAD restored, but leftovers remain or restore unverified. | WAD sha256 matches, no leftovers, `git status` clean except results file. | Level 3 plus before/after evidence side by side. |
| Report Clarity (AC4) | Results file missing. | File exists with empty cells or unclear verdict. | Full table plus a one-line overall verdict. | Level 3 plus a useful note on anything unexpected. |

## Pass Threshold

A run passes if it scores **3 or higher on every dimension** and passes both binary gates.

**Reasoning:** `demo1-check.sh` is the safety check every future port in GIMPL will lean on. A wrong verdict (Verdict Accuracy below 3) would give false confidence that the failure paths work. A sloppy restore (Restore Hygiene below 3) would leave the WAD missing or wrong, so the next normal demo check would fail for a reason that has nothing to do with the code. A well-written report can't make up for either of those, so every dimension needs to reach Meets.

## Notes on Threshold Design

Considered an aggregate minimum of 12/16 instead of a dimension floor. Ruled out because a run could score 4 on Coverage and Report Clarity while scoring 2 on Restore Hygiene, leaving the repo broken but still "passing." The dimension floor prevents that.
