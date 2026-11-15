# GIMPL Routing and Tool-Grant Map

Companion to `docs/orchestration-diagram.md`. It says which role gets which tool, why each withheld tool is withheld, how work is routed, and where George must approve. The agent definitions in `.claude/agents/` must match this map exactly. If one changes, the other changes in the same commit.

Course MCP server: `coursetools` (`mcp/coursetools_server.py`, registered in `.mcp.json`). Tool ids are `mcp__coursetools__<tool>`. Native Claude Code tools are named plainly (`Bash`, `Write`, `Edit`).

## Grant lines

| Role | Granted | Withheld, and the risk |
|---|---|---|
| orchestrator (main session) | Agent (invoke subagents), `mcp__coursetools__file_read`, `mcp__coursetools__file_write` for run summaries under `docs/runs/` only, `Bash` for read-only git only (`git status`, `git diff`, `git log`) so it can gate the implementer and hand the diff to the fence-reviewer | Code edits (`Write`, `Edit`), `Bash` for builds, tests or file changes, `codebase_search`, `task_tracker`, `web_search`. An orchestrator that does the work itself skips every check below it. These limits are held by instruction in `CLAUDE.md`, since Claude Code doesn't restrict the main session's tools from a definition file. |
| planner | `mcp__coursetools__file_read`, `mcp__coursetools__codebase_search` | `file_write`, `Write`, `Edit`, `Bash`, `shell`. A planner that edits has already started implementing without a reviewed plan. |
| implementer | `mcp__coursetools__file_read`, `mcp__coursetools__file_write`, `mcp__coursetools__codebase_search` | `task_tracker` (it would mark its own work done). `test_runner` and `Bash` (it would grade its own work). Native `Write`/`Edit`, so every write goes through one tool. Never writes under `tests/demos/heretic/golden/` (an agent re-baselining DEMO1 would make a real desync "pass"). |
| tester | `Bash` (build, `scripts/demo-suite.sh`, `scripts/demo1-check.sh`, `git status`), `mcp__coursetools__file_read` | `file_write`, `Write`, `Edit` (a tester that can edit could "fix" a failing trace). `mcp__coursetools__test_runner` is withheld on purpose: it is a dummy that always returns PASS, and a fake PASS must never count as evidence. |
| fence-reviewer | `mcp__coursetools__file_read`, `mcp__coursetools__codebase_search` | Every write tool and `Bash`. It judges the diff it is handed and can't change what it judges. |

No role holds `mcp__coursetools__task_tracker`, `mcp__coursetools__shell` or `mcp__coursetools__web_search`. GIMPL work is fully local, and George updates status himself.

### Tally check (a tool on more than two roles gets reviewed)

- `file_read` is on all five roles. It's flagged, then accepted: it's a read-only primitive every role needs, and it can't change anything.
- `codebase_search` is on three roles (planner, implementer, fence-reviewer). It's flagged, then accepted for the same reason.
- `file_write` is on two roles: the implementer for code, and the orchestrator for orchestration documents only. No flag.
- `Bash` is on two roles: the tester, and the orchestrator for read-only git only. It's the broadest grant, so the tester's instructions limit it to building, running the two scripts and inspecting output, and `git status` must show no changes from it. A planned hardening step is a PreToolUse hook that blocks writes under `tests/demos/heretic/golden/` for every agent.

## Enforcement layers

1. **The `tools:` list in each definition (primary).** A tool that isn't listed is unavailable to that role.
2. **`disallowedTools`.** It makes each denial visible in review, and the harness honors it as a second check.
3. **`mcp/roles.allowlist.json` (server side).** coursetools rejects a call whose `role` isn't allowed for that tool. This layer trusts the `role` the agent declares, so it is the weakest of the three.

Boundary-test evidence in `docs/iteration-log.md` records which layer denied the call.

## Routing

| Step | Handoff in | Result out | Orchestrator accepts when | Otherwise |
|---|---|---|---|---|
| 1. Planner | Task text, branch, `.memory/SCOPE.md`, `current-state.md`, the named decisions (004, 006) | `## Plan`, `## Files`, `## Done criteria`, `## Open questions` | Every step names its files, the done criteria are checkable from output, and no golden path is listed | Re-invoke once with the gap named, then ask George |
| 2. Implementer | Approved plan, allowed file list, `coding-standards.md`, plus failure evidence on a retry | `## Files changed`, `## Notes`, `## Not done` | Only the planned files changed and `## Not done` is None | Retry with the evidence |
| 3. Tester | Changed files, done criteria | `## Verdict`, `## Evidence` (verbatim), `## git status` | DEMO1 at 4227 gametics from real `demo-suite.sh` output, and a clean `git status` from the tester | Send the evidence to the Implementer (retry) |
| 4. Fence-reviewer | Plan, full `git diff`, Tester result | `## Verdict` APPROVE/VIOLATIONS, `## Findings` | APPROVE | Send the findings to the Implementer (retry). Any golden-trace finding goes straight to George |

There are at most 2 Implementer retries per task. After that the orchestrator stops and reports to George with all the evidence.

## Human approval points

- **Before the manifest is written (Feature 1 Task 4).** Coding standard 4 covers `tests/demos/heretic/manifest`, so George's task message must say he approves writing it with decision-006's values. Without that the Implementer doesn't start Task 4.
- **Before any commit, and before merging to master.** After the Fence-reviewer approves, the orchestrator presents the diff and evidence and waits. George runs git himself.
- **Any change to a golden trace.** No agent does this. Only George re-records a trace, with a new decision entry.

## Alternatives considered

- **Giving the Tester coursetools `test_runner` instead of `Bash`.** Ruled out because it returns PASS without running anything, so a green result would be fake evidence.
- **Folding the Fence-reviewer into the Tester.** Ruled out because the Tester needs `Bash` to run the demo. A scope judge with `Bash` could change files while judging them. Keeping the judge read-only keeps the verdict trustworthy.
- **Reusing `demo-verifier` as the Tester.** Deferred. It still runs `demo1-check.sh` for the Module 2 work, and Feature 1 Task 8 updates it to call the suite once the runner works.
- **A Project Manager role with `task_tracker`.** Ruled out for now. GIMPL has no ticket system, and George tracks status in `.memory/project/current-state.md` himself.
