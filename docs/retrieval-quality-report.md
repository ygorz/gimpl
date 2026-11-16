# Retrieval quality report: proj-lessons corpus

- Ground truth: `docs/retrieval-ground-truth.md` (6 queries, committed in 6e7bf29c before any run; expected answers never edited)
- Corpus: `.memory/reference/lessons/`, 7 docs, 21 chunks (paragraph chunking), no untagged-document warnings
- Server: `mcp/retrieval/server.py`, model `all-MiniLM-L6-v2` (baked into the image), threshold 0.65, `top_k = 3`, `RETRIEVAL_MAX_CEILING = internal`
- Runner: `mcp/retrieval/run_ground_truth.py`
- Runs: 2026-11-16 (America/Denver), both in a `--network none` container. Raw output saved as `docs/retrieval-validation-run-1.txt` and `docs/retrieval-validation-run-2.txt` (committed in 95fbff56).
- **Result: 5 of 6 passed (83%) in both runs, identical documents, chunks and scores. Bar is 80% with a stable rerun: met.**

## Pass rules (Lesson 3.2)

- precision and near-miss: expected doc in the top 3 with similarity score >= 0.65
- keyword: expected doc returned at all (keyword fallback allowed, labelled)
- ceiling: forbidden doc absent (empty result passes)

All queries used `project_id = proj-lessons`, `classification_ceiling = internal`, no metadata filters.

## Results per query

Citations are `source_document#chunk_index`. Score is the cosine similarity for vector hits; keyword hits have no score.

| Q | Kind | Expected | Returned (citation, method, score) | Result | Why |
|---|---|---|---|---|---|
| Q1 | precision (direct) | `lesson-container-clock-utc.md` | `lesson-container-clock-utc.md#1` vector 0.694; `lesson-container-clock-utc.md#2` vector 0.678 | PASS | Expected doc first, above 0.65 |
| Q2 | near-miss | `lesson-exit-255-normal.md` (decoy `lesson-missing-mobj-ierror.md`) | `lesson-exit-255-normal.md#0` vector 0.758 | PASS | Expected doc first; decoy not returned |
| Q3 | keyword | `lesson-missing-mobj-ierror.md` | `lesson-missing-mobj-ierror.md#1` vector 0.661; `lesson-missing-mobj-ierror.md#2` vector 0.66 | PASS | Returned. Matched by vector, so the fallback wasn't needed |
| Q4 | near-miss | `lesson-golden-trace-layout.md` (decoy `lesson-manifest-format.md`) | `lesson-golden-trace-layout.md#2` keyword; `#0` keyword; `#1` keyword | FAIL | No vector hit cleared 0.65, so the server fell back to keyword. See diagnosis |
| Q5 | ceiling | forbidden `lesson-container-api-credentials.md` | `lesson-container-clock-utc.md#1` keyword; `lesson-manifest-format.md#2` keyword; `lesson-container-clock-utc.md#2` keyword | PASS | Confidential doc absent |
| Q6 | precision (planner) | `lesson-evidence-gap-substitute-check.md` | `lesson-evidence-gap-substitute-check.md#2` vector 0.73 | PASS | Expected doc first, above 0.65 |

## Diagnosis

**Q4 (FAIL, documented as a known gap).** The expected doc is the best vector match at 0.573, ahead of the decoy at 0.499, but below 0.65. So the decoy isn't winning, and the doc isn't missing or untagged. The chunks are mostly repo paths (`tests/demos/heretic/golden/<demo>.tics`), which embed weakly against a plain-English "where should it be saved" question. The keyword fallback then returned only the correct doc, which would satisfy a keyword rule but not the precision rule. I'm not lowering the threshold or rewording the query. The expectation is realistic: a planner would ask exactly this. Proposed fix, one change and a full rerun: add a plain-English sentence to `lesson-golden-trace-layout.md` that says what the path means.

**Q5 (PASS).** In a diagnostic check of raw vector scores without the ceiling filter, the confidential doc scores 0.792 for this question, the strongest match in the corpus. At the internal ceiling it is filtered out, nothing else clears 0.65, and the keyword fallback returns unrelated chunks. The pass comes from the ceiling, not from a weak match.

**Keyword fallback noise.** The fallback ORs every token in the query, stopwords included (`fts_query` in `server.py`). Q5's fallback hits are about the clock and the manifest, not credentials. Proposed server fix: drop stopwords and require a minimum match before returning keyword hits.

## Raw output

Run 1 (`docs/retrieval-validation-run-1.txt`):

```
Q1: PASS [lesson-container-clock-utc.md#1(vector,0.694), lesson-container-clock-utc.md#2(vector,0.678)]
Q2: PASS [lesson-exit-255-normal.md#0(vector,0.758)]
Q3: PASS [lesson-missing-mobj-ierror.md#1(vector,0.661), lesson-missing-mobj-ierror.md#2(vector,0.66)]
Q4: FAIL [lesson-golden-trace-layout.md#2(keyword,None), lesson-golden-trace-layout.md#0(keyword,None), lesson-golden-trace-layout.md#1(keyword,None)]
Q5: PASS [lesson-container-clock-utc.md#1(keyword,None), lesson-manifest-format.md#2(keyword,None), lesson-container-clock-utc.md#2(keyword,None)]
Q6: PASS [lesson-evidence-gap-substitute-check.md#2(vector,0.73)]

5/6 passed
```

Run 2 (`docs/retrieval-validation-run-2.txt`): identical to run 1, line for line.

## Clamp check (after ba4ce8d1)

Same Q5 question, sent with `classification_ceiling: confidential`. Returned `lesson-container-clock-utc.md#1` (public, keyword), `lesson-manifest-format.md#2` (internal, keyword), `lesson-container-clock-utc.md#2` (public, keyword). The credentials doc was absent. Server log:

```
CLAMP: requested ceiling 'confidential' lowered to 'internal' (RETRIEVAL_MAX_CEILING)
```

## Role-level ceiling check (live session)

The planner subagent itself called `retrieve` with the Q5 question, `classification_ceiling: confidential` and `top_k: 5`. It got five keyword chunks with null scores: `lesson-container-clock-utc.md#1` and `#2` (public), `lesson-manifest-format.md#2` and `#0` (internal), and `lesson-exit-255-normal.md#2` (public). The credentials doc was absent, and the server log showed the same `CLAMP:` line. The boundary binds the role, not just the test client.
