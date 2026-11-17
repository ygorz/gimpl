---
classification: internal
project: proj-lessons
doc_type: lesson
---

## Lesson: Reference traces live under a per-game golden directory

**What happened.** Decision-001 first put the DEMO1 reference trace at `tests/demos/golden/demo1.tics`. On 2026-11-06 it was amended to `tests/demos/heretic/golden/demo1.tics`, because the repo holds several games and demo names such as demo1 would collide in one flat folder. Decision-005 made the per-game layout the rule for every game.

**What we learned.** Golden traces belong in `tests/demos/<game>/golden/<demo>.tics`, where `<game>` is the lowercase game name, so Heretic traces go in `tests/demos/heretic/golden/`. Grouping by game keeps each game's traces together and stops name collisions. The demo name becomes part of the file path, which is why `scripts/demo-suite.sh` rejects any demo name that does not match `^[A-Za-z0-9_]+$`.

**How to apply it.** A reference trace for a new Heretic demo goes in `tests/demos/heretic/golden/<demo>.tics`, generated with exactly the decision-004 run flags. Agents never create, edit, move, rename or regenerate a golden trace: only George records one, under coding standard 4, and moving or renaming counts as editing. The Fence-reviewer rejects any diff that touches a path under `tests/demos/heretic/golden/`.
