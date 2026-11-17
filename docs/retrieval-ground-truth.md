# Retrieval ground truth: GIMPL Lessons Learned corpus (proj-lessons)

Written and committed before the first evaluation run. Expected answers are fixed and must not be edited to match server output; failures are fixed in the corpus or server, or recorded as known gaps.

- Corpus: `.memory/reference/lessons/` (7 docs, `project: proj-lessons`, `doc_type: lesson`)
- Server: course retrieval server, paragraph chunking, threshold 0.65, top_k = 3
- Pass rules (Lesson 3.2):
  - **precision / near-miss:** expected doc appears in the top 3 with similarity score >= 0.65
  - **keyword:** expected doc is returned at all; a keyword-fallback result (no score) is allowed
  - **ceiling:** the forbidden doc is ABSENT from the results (an empty result is a pass)
- Overall bar: at least 80% of queries pass (5 of 6), with a stable rerun.

## Q1 - Direct match: dating entries when the container clock is ahead
- Kind: precision
- Query: "The container clock already shows tomorrow's date. What date should I put on a new memory entry or run summary?"
- Expected top result: lesson-container-clock-utc.md
- Filters: project_id = proj-lessons, classification_ceiling = internal, metadata_filters = none
- Pass: lesson-container-clock-utc.md appears in top 3 with score >= 0.65

## Q2 - Near-miss: exit 255 vs a real I_Error crash
- Kind: near-miss
- Query: "chocolate-heretic exited with code 255 after the DEMO1 timedemo. Does that mean the run failed?"
- Expected top result: lesson-exit-255-normal.md
- Decoy: lesson-missing-mobj-ierror.md (also about engine exits, I_Error and exit codes, but describes a real failure)
- Filters: project_id = proj-lessons, classification_ceiling = internal, metadata_filters = none
- Pass: lesson-exit-255-normal.md appears in top 3 with score >= 0.65

## Q3 - Literal keyword: G_TicHashWrite
- Kind: keyword
- Query: "What does the G_TicHashWrite error mean when a demo run stops early?"
- Expected result: lesson-missing-mobj-ierror.md (the only doc containing the token `G_TicHashWrite`)
- Filters: project_id = proj-lessons, classification_ceiling = internal, metadata_filters = none
- Pass: lesson-missing-mobj-ierror.md is returned (vector or keyword fallback)

## Q4 - Near-miss: where a new reference trace goes vs the manifest
- Kind: near-miss
- Query: "Where in the repo should the reference trace for a new Heretic demo be saved?"
- Expected top result: lesson-golden-trace-layout.md
- Decoy: lesson-manifest-format.md (same demos, same directory tree, hashes and approval rule, but about the manifest file)
- Filters: project_id = proj-lessons, classification_ceiling = internal, metadata_filters = none
- Pass: lesson-golden-trace-layout.md appears in top 3 with score >= 0.65

## Q5 - Classification boundary: credentials and API access
- Kind: ceiling
- Query: "How does the GIMPL container get its Claude API access, and how should credentials be handled?"
- Best semantic match in corpus: lesson-container-api-credentials.md (classification: confidential)
- Filters: project_id = proj-lessons, classification_ceiling = internal, metadata_filters = none
- Pass: lesson-container-api-credentials.md does NOT appear in results; only internal-or-below docs, or an empty result

## Q6 - Planner question: evidence when the runner is a stub
- Kind: precision
- Query: "The demo-suite runner is still a stub, so it can't produce real output. How should I handle this task's acceptance evidence before implementing?"
- Expected top result: lesson-evidence-gap-substitute-check.md
- Filters: project_id = proj-lessons, classification_ceiling = internal, metadata_filters = none
- Pass: lesson-evidence-gap-substitute-check.md appears in top 3 with score >= 0.65
