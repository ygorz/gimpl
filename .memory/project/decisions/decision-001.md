# Decision 001 - Per-tic golden traces for demos

**Date:** 2026-11-05
**Review by:** 2027-02-03
**Status:** Active
**Amended:** 2026-11-06 - reference trace path changed from tests/demos/golden/demo1.tics to tests/demos/heretic/golden/demo1.tics, because the repo has several games (path rule in decision-005).

**Decision:** For Feature 1 (the per-tic demo test suite), GIMPL verifies demos against committed per-tic reference traces (starting with tests/demos/heretic/golden/demo1.tics), checked by a bash runner, scripts/demo-suite.sh, that sits alongside an unchanged scripts/demo1-check.sh.

**Rationale:** Committed traces fit the existing bash-and-git-review workflow, are quick to build, and can be diffed in a PR. The runner reports the exact tic and field where a demo drifts, so a desync is pinned down to its point of divergence instead of only showing up as a failed demo.

**Alternatives rejected:** Pinning a C reference build and comparing live runs (possibly via cargo test) was deferred, not dropped: it needs a second build, tag handling, and a Rust toolchain if run via cargo test. It becomes worthwhile once Rust ports exist.

**Constraint:** Reference traces require human approval (see coding standard 4 in .memory/knowledge/coding-standards.md).
