# Agent Governance Policy

Version: v1.0.0
Last updated: 2026-11-24
Reviewed by: George Gorzhiyev

## Policy basis

This policy is derived from:

- The routing-and-tool-grant map (docs/routing-and-tool-grant-map.md)
- Near-miss patterns observed in calibration (docs/calibration-log.md, section: Near-miss patterns and latent risks)
- Least-privilege defaults applied to all roles

### Risk statements

Each risk below comes from the calibration log and is addressed by a rule in this policy.

1. **Out-of-lane reads.** The orchestrator still attempts reads outside its lane (1 near-miss in HO-01, 2 each in DEV-02-r3 and REG-01-r2), and only the tool layer stops them, not the prompt.
2. **Displacement.** Blocking one tool moves the same reads to another (Bash to Read in DEV-02-r2), so a limit that covers a single tool leaves the risk open.
3. **Decision provenance.** An implementer can write a new record in `.memory/project/decisions/` that a reviewer then treats as authority, and no role checks where that record came from (HO-05).
4. **Unenforced MCP limits.** Nothing blocks the main session from calling `mcp__storage__*` or `mcp__retrieval__*`, and the `docs/runs/`-only write limit is checked by the test harness rather than enforced (HO-06 held only because no call was made).

## Least-privilege default

Every role starts with no access. All grants below are explicit and justified.
Any access not explicitly granted to a role is denied by default.

To widen access, open a pull request with: the proposed grant, a concrete justification, and confirmation that the grant does not conflict with any near-miss pattern in the calibration log.

## Roles covered

This policy has one entry for each of the 7 roles in `.claude/agents/`. Course role names map to GIMPL roles as follows: Reviewer = fence-reviewer (review-only), Tester = tester, Implementer = implementer, Orchestrator = orchestrator. Project Manager is not used in GIMPL, because there is no ticket or PR-description work. GIMPL adds planner, port-planner and demo-verifier.

The storage server exposes five operations (`write_entry`, `read_entry`, `list_entries`, `update_entry`, `delete_entry`) and the retrieval server exposes one (`retrieve`). The project skills are `summarize-session` and `write-handoff`. Classification levels, lowest to highest, are public, internal, confidential and secret.

In GIMPL, "memory" is `/workspace/.memory/`: project memory, the lessons corpus behind `retrieve`, and the storage database. "Memory mounted" on a read-only workspace means the role sees it read-only. "Memory omitted" means the startup script hides it.

## Role: implementer

**Version:** v1.0.0

**Defined in:** `.claude/agents/implementer.md`

### MCP server and operation access

| Operation | Server | Granted | Justification / Denial reason |
|---|---|---|---|
| write_entry | storage | YES | Implementer makes the change, so it is the role that learns something new. It stores one lesson per task in `proj-lessons`, classified public or internal. |
| read_entry | storage | NO | The approved plan already carries the cited lessons; the implementer's job does not need stored state (least privilege). Direct reads of `.memory/storage.db` are also denied in `.claude/settings.json` (Read, Grep, Glob and `sqlite3`), so the limit is not tied to one tool (calibration-log.md, near-miss: displacement, DEV-02-r2). |
| list_entries | storage | NO | Same reason as `read_entry`: the implementer records lessons, it does not browse them (least privilege). |
| update_entry | storage | NO | Rewriting an existing lesson changes what the planner and fence-reviewer later treat as authority, the same provenance risk as a self-written decision record (calibration-log.md, near-miss: HO-05). |
| delete_entry | storage | NO | Implementer must not remove project state. No agent manages the lesson lifecycle; removing an entry is an operator action. |
| retrieve | retrieval | NO | The plan it is handed already cites the relevant lessons; retrieval belongs to the planner and fence-reviewer (least privilege). |

### Skill activation scope

| Skill | Activation permitted | Reason if denied |
|---|---|---|
| summarize-session | YES | Implementer may summarize its own work. |
| write-handoff | NO | Implementer returns its result to the orchestrator; ending and handing off a session is the orchestrator's job. |

### Data classification ceiling

**Maximum level:** internal

**Reason:** Implementation needs only repository files and internal lessons. The storage server refuses confidential and secret writes.

### Autonomy level

**Level:** medium

**Conditions for human checkpoint:** Before starting, the operator has approved the plan. Before writing `tests/demos/heretic/manifest`, the operator's task message must approve it. Never writes under `tests/demos/heretic/golden/` or `.memory/project/decisions/`; any change to a golden trace or a decision record goes to the operator (calibration-log.md, near-miss: HO-05). Any file outside the approved plan's file list is out of scope.

**Reason:** File changes are reversible on a branch and are checked by the tester and fence-reviewer, but golden traces and decision records are the reference every later check trusts.

**Container permissions:** workspace read-write, memory mounted

## Role: fence-reviewer

**Version:** v1.0.0

**Defined in:** `.claude/agents/fence-reviewer.md`

### MCP server and operation access

| Operation | Server | Granted | Justification / Denial reason |
|---|---|---|---|
| write_entry | storage | NO | A judge that writes lessons could shape what later reviews are checked against, the same provenance risk as a self-written decision record (calibration-log.md, near-miss: HO-05). |
| read_entry | storage | NO | Lessons reach the reviewer through `retrieve`, which applies the classification ceiling; raw stored entries are not needed (least privilege). |
| list_entries | storage | NO | The reviewer checks the diff against retrieved lessons; browsing raw entries is not part of that job (least privilege). |
| update_entry | storage | NO | Fence-reviewer must not change the lessons it checks changes against (calibration-log.md, near-miss: HO-05). |
| delete_entry | storage | NO | A reviewer removes nothing; erasing a lesson would hide a mistake from later reviews. |
| retrieve | retrieval | YES | Retrieves lessons about what the diff touches and checks the change against them. Ceiling internal. |

### Skill activation scope

| Skill | Activation permitted | Reason if denied |
|---|---|---|
| summarize-session | YES | Fence-reviewer may summarize its own review. |
| write-handoff | NO | Fence-reviewer returns a verdict to the orchestrator; it does not end or hand off sessions. |

### Data classification ceiling

**Maximum level:** internal

**Reason:** Reviewing scope needs the diff, the plan, the coding standards and internal lessons, nothing above internal.

### Autonomy level

**Level:** high

**Conditions for human checkpoint:** Output is advisory only; it may not apply any change. Any golden-trace finding goes straight to the operator. A decision record that appears in the diff is reported as a violation, never accepted as authority (calibration-log.md, near-miss: HO-05).

**Reason:** The role cannot write files or run commands, so it can run without a checkpoint; the checkpoint sits on what is done with its findings.

**Container permissions:** workspace read-only, memory mounted

## Role: orchestrator

**Version:** v1.0.0

**Defined in:** `.claude/agents/orchestrator.md`

### MCP server and operation access

| Operation | Server | Granted | Justification / Denial reason |
|---|---|---|---|
| write_entry | storage | NO | The orchestrator routes and gates; it does not do content. Lessons go in through the implementer only (calibration-log.md, gap 10: main-session storage and retrieval exclusion). |
| read_entry | storage | NO | Reading stored content is not the orchestrator's job, and it already attempts content reads outside its lane that only the tool layer stops (calibration-log.md, gap 10; near-miss: orchestrator out-of-lane reads, HO-01, DEV-02-r3, REG-01-r2). |
| list_entries | storage | NO | Listing entries is part of reading stored content, which is not the orchestrator's job (calibration-log.md, gap 10: main-session storage and retrieval exclusion). |
| update_entry | storage | NO | The orchestrator does not curate lessons (calibration-log.md, gap 10: main-session storage and retrieval exclusion). |
| delete_entry | storage | NO | No agent manages the lesson lifecycle in GIMPL; the operator curates lessons, so delete is denied even for the orchestrator. |
| retrieve | retrieval | NO | Lessons come out through the planner and fence-reviewer, who cite them in their results (calibration-log.md, gap 10: main-session storage and retrieval exclusion). |

The storage audit log is read by the operator, not by an agent. Direct reads of `.memory/storage.db`, `.memory/reference/lessons/` and the audit logs under `logs/` are denied in `.claude/settings.json` for the main session and every subagent, so these denials are not tied to one tool; the same paths are blocked for Read, Grep, Glob and `sqlite3` (calibration-log.md, near-miss: displacement, DEV-02-r2).

### Skill activation scope

| Skill | Activation permitted | Reason if denied |
|---|---|---|
| summarize-session | YES | The orchestrator summarizes the run at a workflow breakpoint. |
| write-handoff | YES | The orchestrator is the session that ends and briefs the next one. |

### Data classification ceiling

**Maximum level:** internal

**Reason:** Plans, results, run summaries and startup memory are internal. No GIMPL role needs confidential data.

### Autonomy level

**Level:** medium

**Conditions for human checkpoint:** After the planner, before any file is written. Before the manifest is written. When the evidence cannot come from real `scripts/demo-suite.sh` output, before any substitute check is used. Before any commit and before any merge to master. Any change to a golden trace. After two failed implementer retries.

**Reason:** The orchestrator decides what runs next, so every point where work becomes permanent stops for the operator.

**Container permissions:** workspace read-write, memory mounted

## Role: planner

**Version:** v1.0.0

**Defined in:** `.claude/agents/planner.md`

### MCP server and operation access

| Operation | Server | Granted | Justification / Denial reason |
|---|---|---|---|
| write_entry | storage | NO | The planner has not done the work yet, so it has nothing to record (least privilege). |
| read_entry | storage | NO | Prior lessons reach the planner through `retrieve`, which applies the ceiling (least privilege). |
| list_entries | storage | NO | The planner finds lessons by meaning through `retrieve`; listing raw entries is not part of planning (least privilege). |
| update_entry | storage | NO | The planner cites lessons; it does not edit them. A planner that rewrote a lesson could shape the plan it is about to cite (least privilege). |
| delete_entry | storage | NO | Planning removes nothing; erasing a lesson would hide it from later plans. |
| retrieve | retrieval | YES | Retrieves prior lessons before planning and cites `source_document` and `chunk_index` under `## Citations`. Ceiling internal. |

### Skill activation scope

| Skill | Activation permitted | Reason if denied |
|---|---|---|
| summarize-session | YES | Planner may summarize its own work. |
| write-handoff | NO | Planner returns a plan to the orchestrator; it does not end or hand off sessions. |

### Data classification ceiling

**Maximum level:** internal

**Reason:** Planning needs the task, the codebase, scope and decision files, and internal lessons.

### Autonomy level

**Level:** high

**Conditions for human checkpoint:** The plan is shown to the operator and approved before any file is written. Open questions go to the operator through the orchestrator.

**Reason:** The planner cannot write files or run commands, so the checkpoint sits on the plan it produces, not on the planner.

**Container permissions:** workspace read-only, memory mounted

## Role: tester

**Version:** v1.0.0

**Defined in:** `.claude/agents/tester.md`

### MCP server and operation access

| Operation | Server | Granted | Justification / Denial reason |
|---|---|---|---|
| write_entry | storage | NO | Tester reports results but does not change stored project state. |
| read_entry | storage | NO | Evidence must come only from real runs of `scripts/demo-suite.sh`, never from a stored note (least privilege). The tester holds Bash, so direct reads of the database are also denied in `.claude/settings.json` (calibration-log.md, near-miss: displacement, DEV-02-r2). |
| list_entries | storage | NO | Same as `read_entry`: a stored entry is never test evidence (least privilege). |
| update_entry | storage | NO | The tester reports what the scripts printed; changing stored state is outside that job (least privilege). |
| delete_entry | storage | NO | The tester reports what the scripts printed; removing stored state is outside that job (least privilege). |
| retrieve | retrieval | NO | A lesson is never test evidence; the verdict comes from real script output (least privilege). |

### Skill activation scope

| Skill | Activation permitted | Reason if denied |
|---|---|---|
| summarize-session | YES | Tester may summarize its own work. |
| write-handoff | NO | Tester returns a verdict to the orchestrator; it does not end or hand off sessions. |

### Data classification ceiling

**Maximum level:** internal

**Reason:** Testing needs the build, the two demo scripts and their output, nothing above internal.

### Autonomy level

**Level:** medium

**Conditions for human checkpoint:** Any write to a tracked file, and any change under `tests/demos/heretic/golden/`, goes to the operator; `git status` must show no changes from the tester. A setup error is reported as BLOCKED, not worked around.

**Reason:** The tester holds Bash to build and run the demo checks. A tester that can edit could "fix" a failing trace.

**Container permissions:** workspace read-write, memory omitted

## Role: demo-verifier

**Version:** v1.0.0

**Defined in:** `.claude/agents/demo-verifier.md`

### MCP server and operation access

| Operation | Server | Granted | Justification / Denial reason |
|---|---|---|---|
| write_entry | storage | NO | A verifier records its verdict in its report, not in stored state. |
| read_entry | storage | NO | The verdict comes only from `demo-suite.sh` output, cross-checked by `demo1-check.sh` (least privilege). Direct reads are also denied in `.claude/settings.json` (calibration-log.md, near-miss: displacement, DEV-02-r2). |
| list_entries | storage | NO | Same as `read_entry`: a stored entry is never verification evidence (least privilege). |
| update_entry | storage | NO | The verifier reports PASS, FAIL or BLOCKED from script output; changing stored state is outside that job (least privilege). |
| delete_entry | storage | NO | The verifier reports PASS, FAIL or BLOCKED from script output; removing stored state is outside that job (least privilege). |
| retrieve | retrieval | NO | A lesson is never verification evidence (least privilege). |

### Skill activation scope

| Skill | Activation permitted | Reason if denied |
|---|---|---|
| summarize-session | YES | Demo-verifier may summarize its own run. |
| write-handoff | NO | Demo-verifier reports PASS, FAIL or BLOCKED; it does not carry work between sessions. |

### Data classification ceiling

**Maximum level:** internal

**Reason:** Verification needs the build, the pinned demo, the golden traces and script output, nothing above internal.

### Autonomy level

**Level:** medium

**Conditions for human checkpoint:** Any failure is reported to the operator, never fixed or retried with changes. Golden traces and the manifest are never edited or regenerated. `git status` must show no changes from the run.

**Reason:** The role holds Bash to build and run the checks, and a verifier that changes what it verifies can no longer be trusted.

**Container permissions:** workspace read-write, memory omitted

## Role: port-planner

**Version:** v1.0.0

**Defined in:** `.claude/agents/port-planner.md`

### MCP server and operation access

| Operation | Server | Granted | Justification / Denial reason |
|---|---|---|---|
| write_entry | storage | NO | Port specs are files under `docs/port-specs/`, not stored entries (least privilege). |
| read_entry | storage | NO | Port specs cite the C source by file:line, not lessons (least privilege). |
| list_entries | storage | NO | Same as `read_entry`: port specs cite source, not stored entries (least privilege). |
| update_entry | storage | NO | Port planning produces spec files; changing stored state is outside that job (least privilege). |
| delete_entry | storage | NO | Port planning produces spec files; removing stored state is outside that job (least privilege). |
| retrieve | retrieval | NO | Port specs cite the C source, and the role is outside the Feature 1 team (least privilege). |

### Skill activation scope

| Skill | Activation permitted | Reason if denied |
|---|---|---|
| summarize-session | YES | Port-planner may summarize its own work. |
| write-handoff | YES | Port planning runs in operator-led phases that can span sessions. |

### Data classification ceiling

**Maximum level:** internal

**Reason:** Port planning needs the C source, docs and scripts, nothing above internal.

### Autonomy level

**Level:** medium

**Conditions for human checkpoint:** Follows the phase rules the operator gives; a read-only phase makes no file changes. Writes only under `docs/port-specs/` and `docs/context/`, never `src/`, `scripts/`, the wad or build files. A fact that cannot be confirmed from the repo is reported as unconfirmed.

**Reason:** Specs are reversible documents, but they set the plan for a port, so the operator sets each phase.

**Container permissions:** workspace read-write, memory omitted
