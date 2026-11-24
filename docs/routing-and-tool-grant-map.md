# GIMPL Routing and Tool-Grant Map

Companion to `docs/orchestration-diagram.md`. It says which role gets which tool, why each withheld tool is withheld, how work is routed, and where George must approve. The agent definitions in `.claude/agents/` must match this map exactly. If one changes, the other changes in the same commit.

Course MCP servers, all registered in `.mcp.json`: `coursetools` (`mcp/coursetools_server.py`), `storage` (HTTP on 127.0.0.1:8001) and `retrieval` (HTTP on 127.0.0.1:8002). Tool ids are `mcp__<server>__<tool>`, for example `mcp__coursetools__file_read` or `mcp__retrieval__retrieve`. Native Claude Code tools are named plainly (`Bash`, `Write`, `Edit`).

## Grant lines

| Role | Granted | Withheld, and the risk |
|---|---|---|
| orchestrator (main session) | Agent (invoke subagents), `mcp__coursetools__file_read`, `Read`/`Glob`/`Grep` for the startup memory reads only, `mcp__coursetools__file_write` for run summaries under `docs/runs/` only, `Bash` for read-only git only (`git status`, `git diff`, `git log`) so it can gate the implementer and hand the diff to the fence-reviewer | Code edits (`Write`, `Edit`), `Bash` for builds, tests or file changes, `codebase_search`, `task_tracker`, `web_search`. An orchestrator that does the work itself skips every check below it. Every storage and retrieval tool. These limits are held by instruction in `CLAUDE.md`, since Claude Code doesn't restrict the main session's tools from a definition file. |
| planner | `mcp__coursetools__file_read`, `mcp__coursetools__codebase_search`, `mcp__retrieval__retrieve` | `file_write`, `Write`, `Edit`, `Bash`, `shell`. A planner that edits has already started implementing without a reviewed plan. Every storage tool (see the Module 3.2 section). |
| implementer | `mcp__coursetools__file_read`, `mcp__coursetools__file_write`, `mcp__coursetools__codebase_search`, `mcp__storage__write_entry` | `task_tracker` (it would mark its own work done). The other storage tools and `retrieve` (see the Module 3.2 section). `test_runner` and `Bash` (it would grade its own work). Native `Write`/`Edit`, so every write goes through one tool. Never writes under `tests/demos/heretic/golden/` (an agent re-baselining DEMO1 would make a real desync "pass"). |
| tester | `Bash` (build, `scripts/demo-suite.sh`, `scripts/demo1-check.sh`, `git status`), `mcp__coursetools__file_read` | `file_write`, `Write`, `Edit` (a tester that can edit could "fix" a failing trace). `mcp__coursetools__test_runner` is withheld on purpose: it is a dummy that always returns PASS, and a fake PASS must never count as evidence. Every storage and retrieval tool. |
| fence-reviewer | `mcp__coursetools__file_read`, `mcp__coursetools__codebase_search`, `mcp__retrieval__retrieve` | Every write tool, every storage tool and `Bash`. It judges the diff it is handed and can't change what it judges. |

No role holds `mcp__coursetools__task_tracker`, `mcp__coursetools__shell` or `mcp__coursetools__web_search`. GIMPL work is fully local, and George updates status himself.

### Tally check (a tool on more than two roles gets reviewed)

- `file_read` is on all five roles. It's flagged, then accepted: it's a read-only primitive every role needs, and it can't change anything.
- `codebase_search` is on three roles (planner, implementer, fence-reviewer). It's flagged, then accepted for the same reason.
- `file_write` is on two roles: the implementer for code, and the orchestrator for orchestration documents only. No flag.
- `mcp__retrieval__retrieve` is on two roles (planner, fence-reviewer), and `mcp__storage__write_entry` is on one (implementer). No flag.
- `Bash` is on two roles: the tester, and the orchestrator for read-only git only. It's the broadest grant, so the tester's instructions limit it to building, running the two scripts and inspecting output, and `git status` must show no changes from it. A planned hardening step is a PreToolUse hook that blocks writes under `tests/demos/heretic/golden/` for every agent.

## Enforcement layers

1. **The `tools:` list in each definition (primary).** A tool that isn't listed is unavailable to that role.
2. **`disallowedTools`.** It makes each denial visible in review, and the harness honors it as a second check.
3. **`mcp/roles.allowlist.json` (server side).** coursetools rejects a call whose `role` isn't allowed for that tool. This layer trusts the `role` the agent declares, so it is the weakest of the three.
4. **`.claude/settings.json` `permissions.deny` (harness).** Blocks direct reads and edits of the lessons corpus, the storage database and the audit log for every session and subagent. See the Module 3.2 section.
   These harness rules don't cover MCP tools, so `mcp/coursetools_server.py` refuses the same paths itself: `file_read` and `file_write` reject them and `codebase_search` skips them.
5. **Storage and retrieval server code.** The storage server refuses confidential and secret writes, and the retrieval server clamps every search to `RETRIEVAL_MAX_CEILING`. See the Module 3.2 section.

Boundary-test evidence in `docs/iteration-log.md` records which layer denied the call.

## Routing

| Step | Handoff in | Result out | Orchestrator accepts when | Otherwise |
|---|---|---|---|---|
| 1. Planner | Task text, branch, `.memory/SCOPE.md`, `current-state.md`, the named decisions (004, 006) | `## Plan`, `## Files`, `## Done criteria`, `## Open questions`, `## Citations` | Every step names its files, the done criteria are checkable from output, no golden path is listed, and `## Citations` lists what `retrieve` returned | Re-invoke once with the gap named, then ask George |
| 2. Implementer | Approved plan, allowed file list, `coding-standards.md`, plus failure evidence on a retry | `## Files changed`, `## Notes`, `## Not done`, `## Lesson stored` | Only the planned files changed, `## Not done` is None, and `## Lesson stored` gives an `entry_id` (or says why none was stored) | Retry with the evidence |
| 3. Tester | Changed files, done criteria | `## Verdict`, `## Evidence` (verbatim), `## git status` | DEMO1 at 4227 gametics from real `demo-suite.sh` output (or the substitute check George approved for this task), and a clean `git status` from the tester | Send the evidence to the Implementer (retry) |
| 4. Fence-reviewer | Plan, full `git diff`, Tester result, any approved substitute check | `## Verdict` APPROVE/VIOLATIONS, `## Findings`, `## Lessons checked` | APPROVE, and `## Lessons checked` lists what `retrieve` returned | Send the findings to the Implementer (retry). Any golden-trace finding goes straight to George |

There are at most 2 Implementer retries per task. After that the orchestrator stops and reports to George with all the evidence.

**Evidence gap.** If the task's evidence can't come from real `scripts/demo-suite.sh` output (the runner is a stub, missing or broken), the orchestrator halts before the Implementer, names the gap and proposes a substitute check. It continues only after George approves that check, and the run summary records it as a one-off for that task, never a standing rule. A stub's output is never evidence. The Fence-reviewer flags a substitute check that has no recorded approval.

## Human approval points

- **After the Planner, before any file is written.** The orchestrator shows George the plan and waits for approval.
- **Before the manifest is written (Feature 1 Task 4).** Coding standard 4 covers `tests/demos/heretic/manifest`, so George's task message must say he approves writing it with decision-006's values. Without that the Implementer doesn't start Task 4.
- **Evidence gap.** Before the Implementer starts, George approves any substitute check, as a one-off for that task.
- **Before any commit, and before merging to master.** After the Fence-reviewer approves, the orchestrator presents the diff and evidence and waits. George runs git himself.
- **Any change to a golden trace.** No agent does this. Only George re-records a trace, with a new decision entry.

## MCP storage and retrieval grants (Module 3.2)

All three Module 3.2 duties use project `proj-lessons`. The curated corpus is `.memory/reference/lessons/` (committed, read only through `retrieve`). Lessons found during a run go to the storage server (`.memory/storage.db` and `.memory/storage-audit.log`, git-ignored, written only through `write_entry`).

| Role | Storage | Retrieval | Ceiling | Why |
|---|---|---|---|---|
| planner | None | `retrieve` | internal | Retrieves prior lessons before it plans, so the plan uses what earlier runs learned. It cites `source_document` and `chunk_index` under `## Citations`. No storage: it hasn't done the work yet, so it has nothing to record. |
| implementer | `write_entry` only | None | internal (write) | It makes the change, so it's the role that learns something new. It stores one lesson per task with `entry_type: lesson` and `calling_role: implementer`. No `read_entry`, `list_entries`, `update_entry` or `delete_entry`: it records lessons, it doesn't curate or erase them. No `retrieve`: the plan it's handed already carries the cited lessons. |
| fence-reviewer | None | `retrieve` | internal | Retrieves lessons about what the diff touches and checks the change against them, listing them under `## Lessons checked`. No storage: a judge that writes lessons could shape what later reviews are checked against. |
| tester | None | None | n/a | Evidence must come only from real runs of `demo-suite.sh`, never from a stored note or a lesson. |
| orchestrator (main session) | None | None | n/a | Routes and gates, it doesn't do content. Held by instruction, since Claude Code doesn't restrict the main session's tools. |
| demo-verifier | None | None | n/a | The verdict comes only from `demo-suite.sh` output, cross-checked by `demo1-check.sh`. Its `tools:` list has no MCP tools. |
| port-planner | None | None | n/a | Port specs cite the C source by file:line, not lessons, and the role is outside the Feature 1 team. Its `tools:` list has no MCP tools. |
| trace-auditor | None | None | n/a | Audits the golden traces and manifest against git and the approved values the operator copies into the task. The operator launches it with `run-agent.sh`; the orchestrator does not route to it. A lesson is never audit evidence, and the role runs with memory omitted. Its `tools:` list has no MCP tools. |

The subagent grants are enforced by each definition's `tools:` list, with the withheld storage and retrieval tools also listed under `disallowedTools`. No role gets a confidential ceiling.

**Server-side enforcement.**
- **Retrieval ceiling clamp.** `retrieve` takes `classification_ceiling` from the caller, so a ceiling written in an agent file is only a request. GIMPL's retrieval server clamps every search to `RETRIEVAL_MAX_CEILING` (default `internal`), set in the container env where no agent can change it. A call asking for `confidential` gets internal results at most, the keyword fallback uses the same clamped value, and the server logs a `CLAMP:` line.
- **Storage write classification.** The storage server refuses `confidential` and `secret` writes, so the implementer can store only public or internal lessons.
- **`calling_role` is self-reported.** The storage server records whatever `calling_role` the caller passes and has no role allow-list. The audit line is trustworthy because only the implementer holds `write_entry`, not because the server checks the role.

**Direct-read deny rules (`.claude/settings.json`).** These apply to the main session and every subagent:
- `Read` and `Edit` of `./.memory/reference/lessons/**`, `./.memory/storage.db*` (including the WAL files) and `./.memory/storage-audit.log`, plus `//memory/**` in case a server falls back to its default `/memory` paths.
- `Bash(sqlite3 *)`.

`Read` deny rules also cover Grep, Glob and the file commands Claude Code recognizes in Bash (`cat`, `head`, `tail` and so on). Bash deny rules are best-effort: a script such as `python -c` that opens the file itself isn't caught. The real guard is that the tester, demo-verifier and trace-auditor are the only Bash subagents (the orchestrator uses Bash only for read-only git, by instruction), and their instructions forbid touching these paths. The audit log is denied to agents too. George reads it himself.

**Network deviation.** The lesson runs agent containers on an `--internal` Docker network (`agent-internal`). That network also blocks the Claude API, so Claude Code can't work there. Agent sessions run on Docker's normal network instead. Both MCP servers bind to 127.0.0.1 inside the container with no published ports (no `-p`), so nothing outside the container can reach them. Builds and demo checks still run on `--network none`.

## Alternatives considered

- **Giving the Tester coursetools `test_runner` instead of `Bash`.** Ruled out because it returns PASS without running anything, so a green result would be fake evidence.
- **Folding the Fence-reviewer into the Tester.** Ruled out because the Tester needs `Bash` to run the demo. A scope judge with `Bash` could change files while judging them. Keeping the judge read-only keeps the verdict trustworthy.
- **Reusing `demo-verifier` as the Tester.** Deferred. Since Feature 1 Task 8 (2026-11-16) it runs `demo-suite.sh` with `demo1-check.sh` as a cross-check, but it stays a standalone check outside the Feature 1 team.
- **Giving the Tester `retrieve` as the reviewing role.** Ruled out. The Tester's evidence must come only from real runs, and it holds `Bash`. The Fence-reviewer is read-only, so it's the safer role to check the work against lessons.
- **Trusting the ceiling in each agent file.** Ruled out. The ceiling is a caller argument, so it's clamped server-side instead.
- **A Project Manager role with `task_tracker`.** Ruled out for now. GIMPL has no ticket system, and George tracks status in `.memory/project/current-state.md` himself.
