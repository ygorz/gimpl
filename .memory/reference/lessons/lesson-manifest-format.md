---
classification: internal
project: proj-lessons
doc_type: lesson
---

## Lesson: The demo manifest is the source of truth for trace hashes

**What happened.** In Feature 1 Task 4 (2026-11-14) the planner stopped with open questions about the manifest: what format its lines should use, and whether to record a short or full commit SHA. George chose four space-separated fields with `#` comment lines, and the full 40-character source commit SHA. The manifest was written to `tests/demos/heretic/manifest` with decision-006's DEMO1 values: 4227 gametics, the trace sha256 and source commit 01044d09.

**What we learned.** Each data line is `<demo> <gametics> <trace_sha256> <source_commit>`. There is one manifest per game, so it needs no game column. Once the manifest exists, it is the repo's source of truth for each trace's sha256 and source commit; decision-006 only records the approval and why. Hardcoding a hash in a script would create a second copy that can drift, so `scripts/demo-suite.sh` reads every manifest line and contains no trace sha256 at all.

**How to apply it.** To add a demo to the suite, add one line to that game's manifest, with George's approval under coding standard 4, and never hardcode tic counts, hashes or commits in a script. If a trace's sha256 does not match its manifest line, the runner exits 2 as a setup error. Check the manifest, not memory or an old decision entry, when you need a current hash.
