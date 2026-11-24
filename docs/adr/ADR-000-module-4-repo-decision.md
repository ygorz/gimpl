# ADR-000: GIMPL stays the Module 4 repository

- Status: Accepted
- Date: 2026-11-24 (MT)
- Decider: George Gorzhiyev

## Context
The Module 4 Activation asks learners to fork LaunchCodeAgenticEngineerMod4,
rename it, and copy their Module 1-3 project in without its .git directory.
GIMPL (ygorz/gimpl) already holds the Target Codebase (Chocolate Heretic,
forked from chocolate-doom) and every Module 1-3 harness commit: agents,
skills, memory, MCP servers, eval harness, calibration log.
The Activation is ungraded with no uploads; the capstone asks for "a
repository you can commit to, share, and sanitize" and rewards history that
shows the loop running "across the full course". Course support was asked
which path to take; no reply had arrived by 2026-11-24.

## Decision
GIMPL remains the single repository. Module 4 infrastructure is ported into it
file by file on short branches merged through pull requests. The Mod4 repo is
kept as an unmodified reference: an untouched fork at
github.com/ygorz/LaunchCodeAgenticEngineerMod4, cloned locally next to
GIMPL as mod4-reference at 2c0b27c.

## Path map (Mod4 -> GIMPL)
| Mod4 | GIMPL |
|---|---|
| mcp-servers/storage/, mcp-servers/retrieval/ | mcp/storage/, mcp/retrieval/ |
| .agents/, .skills/ | .claude/agents/, .claude/skills/ |
| default branch main | default branch master |
| image agentic_engineer_4 | image gimpl |
| roles implementer, reviewer, tester, orchestrator, project-manager | orchestrator, planner, port-planner, implementer, tester, fence-reviewer (= Reviewer), demo-verifier; no Project Manager |
| /memory volume | /workspace/.memory (masked with tmpfs for roles whose policy omits memory) |
File names inside those folders follow the lessons exactly
(allow-list.json, logs/storage-audit-log.jsonl, eval/test_policy.py, ...).

## Ported vs reference
- Ported (adapted to GIMPL paths): scripts/run-agent.sh, the _authorize()
  allow-list pattern and both allow-list.json files, docs/governance-policy.md
  template, eval/red-team-*.md format, scripts/check-pipeline-integrity.py,
  scripts/build-audit-trail.py, scripts/run-reviewer.py (OpenRouter),
  scripts/validate_handoff_deterministic.py, schemas/handoff.json,
  eval/test_deterministic_step.py, docs/ci-step-design.md format,
  Dockerfile additions (jq, sqlite3, pytest, pytest-json-report, PyYAML, jsonschema).
- Written fresh for GIMPL: eval/test_policy.py (Mod4's version only checks CI
  basics), .github/workflows/ci.yml (lesson job names, GIMPL paths, master),
  all policy entries, ADR-001/002, docs/step-classification.md.
- Reference only, not copied: Mod4 agents/ and skills/, example-task-app/,
  examples/, docs/calibration-log.md, orchestration-diagram.md,
  routing-and-tool-grant-map.md, ADR-001/ADR-002, eval/test_deterministic.py
  and eval/test_rubric_suite.py (same names as GIMPL's Module 3 harness files),
  docker-entrypoint.sh, CLAUDE.md, README.md.

## Activation checks (recorded 2026-11-24, MT)
1. Image builds: `docker build -t gimpl .` -> `#22 DONE 113.8s` (pinned
   rebuild; first build with the new packages 332.4s). Versions: pytest 9.2.0,
   pytest-json-report 1.5.0, PyYAML 6.0.4, jsonschema 4.26.0, jq 1.7.
2. Files visible in /workspace: `ls /workspace | head -30` lists the repo root
   (AUTHORS, CLAUDE.md, CMakeLists.txt, Dockerfile, ... autogen.sh, config.h).
3. Orchestrator file opens: `sed -n 1,15p .claude/agents/orchestrator.md` ->
   `name: orchestrator`, `model: inherit`, tools Agent,
   mcp__coursetools__file_read, Read, Glob.
4. Orchestrator accepts a task: "Startup check only, change nothing: read your
   startup memory and tell me which subagents you can route a task to and what
   the first step of a port task would be." -> read .memory/SCOPE.md,
   MEMORY_INDEX.md and current-state.md; routes to planner, implementer,
   tester, fence-reviewer; first step of a port task is the planner. The
   orchestrator-bash-guard hook blocked a combined non-read-only git command,
   and retrieval/storage MCP servers were not running (not started for this
   check). current-state.md was found stale; it is refreshed in the 4.1 work.

## Enforcement layer coverage
- A role launched on its own through scripts/run-agent.sh is limited by its
  container (workspace ro/rw, .memory visible or masked) and by the MCP
  allow-lists, which read the role from AGENT_ROLE set by that script.
- Inside one orchestrated Claude Code session, subagents share one MCP server
  process, so per-subagent limits come from each agent's tools: frontmatter,
  .claude/settings.json denies, and the PreToolUse guard hook on the main
  session. This is a stated limit of the design, not a hidden one.

## Consequences
- Lesson commands are translated with the path map; every Module 4 upload
  starts with one line naming the GIMPL path.
- Commit history from Module 1 through the capstone stays in one repository.
- Alternatives considered: (1) literal fork with a copy without .git: loses
  history and duplicates the Doom tree across two repos; (2) fork plus
  re-importing GIMPL history with git subtree/filter-repo: more complex and
  still splits the capstone story.
