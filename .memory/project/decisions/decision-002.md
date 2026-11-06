# Decision 002 - .memory/ lives in the repo, alongside the feature it describes

**Date:** 2026-11-05
**Review by:** 2027-02-03
**Status:** Active

**Decision:** .memory/ is committed in the repo. Memory changes are made on the same feature branch as the work they describe and merge to master with it.

**Alternatives rejected:** Keeping .memory/ on a separate dedicated branch; keeping .memory/ outside git.

**Rationale:** Memory should travel with the code it explains, so the why of a feature merges with it and stays in git history; a separate branch or outside-git notes would drift out of sync.

