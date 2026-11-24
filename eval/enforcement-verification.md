# MCP Allow-List Enforcement Verification

**Date:** 2026-11-24
**Commits verified:** `d4fdebf3` (storage allow-list), `b84227c4` (retrieval allow-list), `5dbdbec4` (per-agent server wiring)
**Policy:** `docs/governance-policy.md` v1.0.0
**Method:** MCP Inspector CLI (`@modelcontextprotocol/inspector --cli`), run inside the `gimpl` container. Each call starts the server over stdio, sets the role with `AGENT_ROLE`, makes one tool call and exits.

## Purpose

This document shows that the storage and retrieval servers enforce the governance policy themselves. Agent instructions alone do not decide access. Each server reads the caller's role from `AGENT_ROLE`, checks it against its allow-list before doing any work, and records the decision in an audit log. The three checks below cover one denied call, one allowed call and one classification ceiling.

Storage writes in these checks went to a throwaway database (`/tmp/probe.db`), so project storage was not touched.

The lesson's checks name its own roles. In GIMPL, fence-reviewer is the reviewer role. The ceiling check runs as planner because GIMPL's implementer has no retrieval access; planner is a granted role with an internal ceiling, which is the condition the check needs.

## Static checks

Before the Inspector calls, the server code and allow-lists were checked against the policy.

**`_authorize()` runs first in every operation.** Every tool in `mcp/storage/server.py` (`write_entry`, `read_entry`, `list_entries`, `update_entry`, `delete_entry`), and `retrieve` in `mcp/retrieval/server.py`, calls `_authorize()` as its first statement. A role that is unset or not on the list is refused (fails closed).

**The allow-lists match the policy grants exactly.**

| Operation | Policy grants | Allow-list grants | Match |
|-----------|---------------|-------------------|-------|
| `write_entry` | implementer | `mcp/storage/allow-list.json`: implementer | Yes |
| `read_entry`, `list_entries`, `update_entry`, `delete_entry` | none | empty | Yes |
| `retrieve` | planner (internal), fence-reviewer (internal) | `mcp/retrieval/allow-list.json`: planner (internal), fence-reviewer (internal); all other roles `granted: false` with a denial reason | Yes |

## Results

| # | Check | Role | Operation | Expected | Result |
|---|-------|------|-----------|----------|--------|
| 1 | Out-of-lane write is denied | fence-reviewer | storage `write_entry` | Denied, no write | PASS |
| 2 | In-lane write is allowed | implementer | storage `write_entry` | Success, entry created | PASS |
| 3 | Classification ceiling holds | planner | retrieval `retrieve` with ceiling `confidential` | Ceiling lowered to internal, confidential chunks withheld | PASS |

In the audit lines below, `role` and `calling_role` come from `AGENT_ROLE` and are what the server trusts. `claimed_role` is whatever the caller passed as an argument; these calls passed none, so it reads `unknown`.

## Check 1: Denied call

fence-reviewer has no storage access under the policy, so a write attempt must fail before it reaches the database.

```
npx -y @modelcontextprotocol/inspector --cli -e AGENT_ROLE=fence-reviewer -e STORAGE_DB_PATH=/tmp/probe.db -e STORAGE_AUDIT_PATH=/workspace/logs/storage-audit-log.jsonl python3 mcp/storage/server.py --stdio --method tools/call --tool-name write_entry --tool-arg project_id=probe --tool-arg entry_type=probe --tool-arg title=probe --tool-arg content=should-be-denied --tool-arg classification=internal
```

**Response:** `"isError": true` with the message:

```
authorization_denied: role 'fence-reviewer' may not call 'write_entry'. See docs/governance-policy.md.
```

**Audit log (`logs/storage-audit-log.jsonl`):**

```json
{"claimed_role": "unknown", "event": "authorization_denied", "operation": "write_entry", "outcome": "authorization_denied", "policy_reference": "docs/governance-policy.md", "role": "fence-reviewer", "timestamp": "2026-11-24T19:48:12.175627+00:00"}
```

## Check 2: Allowed call

implementer is the only role allowed to call `write_entry`. The same write must succeed under that role.

```
npx -y @modelcontextprotocol/inspector --cli -e AGENT_ROLE=implementer -e STORAGE_DB_PATH=/tmp/probe.db -e STORAGE_AUDIT_PATH=/workspace/logs/storage-audit-log.jsonl python3 mcp/storage/server.py --stdio --method tools/call --tool-name write_entry --tool-arg project_id=probe --tool-arg entry_type=probe --tool-arg title=probe --tool-arg content=allowed --tool-arg classification=internal
```

**Response:** `"isError": false` with `entry_id` `54ade299-7eec-422a-ab94-615bcc28c407`.

**Audit log (`logs/storage-audit-log.jsonl`):**

```json
{"calling_role": "implementer", "claimed_role": "unknown", "classification": "internal", "entry_id": "54ade299-7eec-422a-ab94-615bcc28c407", "event": "storage_write_entry", "operation": "write_entry", "outcome": "success", "project_id": "probe", "timestamp": "2026-11-24T19:51:58.636633+00:00"}
```

## Check 3: Classification ceiling

planner may call `retrieve`, but its policy ceiling is internal. The check asks for `confidential` and queries the one confidential lesson in the corpus, `lesson-container-api-credentials.md`. The server must apply the lower of the requested ceiling and the role's ceiling.

```
npx -y @modelcontextprotocol/inspector --cli -e AGENT_ROLE=planner -e RETRIEVAL_REFERENCE_DIR=/workspace/.memory/reference/lessons -e RETRIEVAL_AUDIT_LOG=/workspace/logs/retrieval-audit-log.jsonl python3 mcp/retrieval/server.py --stdio --method tools/call --tool-name retrieve --tool-arg project_id=proj-lessons --tool-arg "query=container API credentials" --tool-arg classification_ceiling=confidential
```

**Server output:**

```
CLAMP: requested ceiling 'confidential' lowered to 'internal' (role ceiling / RETRIEVAL_MAX_CEILING)
```

**Response:** `"isError": false`. Three chunks returned, all from `lesson-container-clock-utc.md` (chunk indexes 0, 1 and 2), each classified `public`. No chunk from `lesson-container-api-credentials.md` appeared.

**Audit log (`logs/retrieval-audit-log.jsonl`):**

```json
{"ceiling": "internal", "chunk_index": 0, "classification": "confidential", "event": "classification_withheld", "operation": "retrieve", "outcome": "withheld", "role": "planner", "source_document": "lesson-container-api-credentials.md", "timestamp": "2026-11-24T19:52:58.794311+00:00"}
{"ceiling": "internal", "chunk_index": 1, "classification": "confidential", "event": "classification_withheld", "operation": "retrieve", "outcome": "withheld", "role": "planner", "source_document": "lesson-container-api-credentials.md", "timestamp": "2026-11-24T19:52:58.794854+00:00"}
{"ceiling": "internal", "event": "retrieve_ok", "operation": "retrieve", "outcome": "success", "project_id": "proj-lessons", "returned": 3, "role": "planner", "timestamp": "2026-11-24T19:52:58.795101+00:00", "withheld": 2}
```

Both confidential chunks matched the query and were withheld, and each withheld chunk has its own audit line.

## Lesson checklist

| Lesson requirement | Evidence | Status |
|--------------------|----------|--------|
| Every storage operation has an `_authorize()` guard as its first statement | Static checks | Met |
| Both allow-lists match the policy grants exactly | Static checks | Met |
| A denied role's call returns `authorization_denied`, and a granted role's call succeeds | Checks 1 and 2 | Met |
| A classification-ceiling test withheld a confidential document from a role capped at internal | Check 3 | Met |
| Both audit logs contain the denial and withholding entries | Audit lines under Checks 1 to 3 | Met |

## What this closes

- **Gap #10 / HO-06 (unenforced MCP limits):** access is now decided by the server from `AGENT_ROLE`, not by agent instructions. The main session has no storage or retrieval tools, because both servers were removed from `.mcp.json` and are declared only in the implementer, planner and fence-reviewer agent files.
- **Out-of-lane reads and writes (HO-01, DEV-02-r3, REG-01-r2):** a role outside its lane gets `authorization_denied`, and the attempt is logged.
- **Classification exposure:** a role cannot raise its own ceiling by asking for a higher one.

## Known limit

`AGENT_ROLE` is set by the agent file that starts the server. A role with Bash access could start its own server process with a forged `AGENT_ROLE`. Container mounts (Layer 1) narrow what such a process could reach, but do not prevent it. The red-team prompts in `eval/red-team-prompts.md` test this case.
## Lesson 4.1 Exercise 1: trace-auditor

**Date:** 2026-11-24 (all times UTC)
**Policy:** `docs/governance-policy.md` v1.4.0, `## Role: trace-auditor`
**Commits verified:** `1a0207da` (policy entry) and the enforcement commit that adds this section

The trace-auditor holds Bash and no MCP grant. Layer 1 is its hard boundary for writes and for project memory. Layer 2 refuses every storage and retrieval call it makes.

### Layer 1: Container Permissions

**Role:** trace-auditor

**Launch line:** `Launching 'trace-auditor': image=gimpl, workspace=ro, memory=omitted`

**Workspace check**

**Command:** `./scripts/run-agent.sh trace-auditor bash -c 'touch /workspace/should-fail.txt; echo "touch exit: $?"'`

**Output:**
```
Launching 'trace-auditor': image=gimpl, workspace=ro, memory=omitted
touch: cannot touch '/workspace/should-fail.txt': Read-only file system
touch exit: 1
```

**Memory volume check**

**Command:** `./scripts/run-agent.sh trace-auditor bash -c 'echo "entries in .memory: $(ls -A /workspace/.memory | wc -l)"; grep " /workspace/.memory " /proc/mounts'`

**Output:**
```
Launching 'trace-auditor': image=gimpl, workspace=ro, memory=omitted
entries in .memory: 0
tmpfs /workspace/.memory tmpfs rw,nosuid,nodev,noexec,relatime,mode=755 0 0
```

In GIMPL, memory lives at `/workspace/.memory/`. For "memory omitted", `run-agent.sh` mounts an empty tmpfs over it, so the check counts its entries and shows the tmpfs mount rather than looking for `/memory`.

**Host check:** `ls should-fail.txt` printed `ls: should-fail.txt: No such file or directory`, so nothing reached the host tree.

**Result:** Blocked as expected. The write failed at the read-only mount, and the role saw an empty memory mount instead of project memory.

### Layer 2: MCP Server Allow-Lists

The policy grants trace-auditor no storage or retrieval operation. `mcp/storage/allow-list.json` grants by operation, so a role with no grant is not listed, and `_authorize()` refuses any role it does not list (fails closed). `mcp/retrieval/allow-list.json` lists trace-auditor with `"granted": false` and a denial reason. The checks ran in a memory-mounted container (`./scripts/run-agent.sh planner bash`) so that the retrieval server could index the corpus. Each call sets `AGENT_ROLE` explicitly, because the servers decide from that variable alone.

**Denied operation check (storage)**

**Command:**
```
npx -y @modelcontextprotocol/inspector --cli -e AGENT_ROLE=trace-auditor -e STORAGE_DB_PATH=/tmp/probe.db -e STORAGE_AUDIT_PATH=/workspace/logs/storage-audit-log.jsonl python3 mcp/storage/server.py --stdio --method tools/call --tool-name write_entry --tool-arg project_id=proj-lessons --tool-arg entry_type=lesson --tool-arg "title=demo1 trace verified" --tool-arg "content=trace-auditor found demo1 CLEAN" --tool-arg classification=internal
```

**Output:**
```
authorization_denied: role 'trace-auditor' may not call 'write_entry'. See docs/governance-policy.md.
"isError": true
```

**Granted operation check**

trace-auditor holds no granted MCP operation, so there is no in-role call that should succeed. As the positive control, the same retrieval call made as planner, a granted role, succeeds. That shows the server is serving and that the trace-auditor denial depends on the role, not on the query.

**Command:**
```
npx -y @modelcontextprotocol/inspector --cli -e AGENT_ROLE=planner -e RETRIEVAL_REFERENCE_DIR=/workspace/.memory/reference/lessons -e RETRIEVAL_AUDIT_LOG=/workspace/logs/retrieval-audit-log.jsonl python3 mcp/retrieval/server.py --stdio --method tools/call --tool-name retrieve --tool-arg project_id=proj-lessons --tool-arg "query=container clock UTC" --tool-arg classification_ceiling=public
```

**Output:**
```
"isError": false
3 results from lesson-container-clock-utc.md (chunks 0, 1, 2), each "classification": "public"
```

**Classification ceiling check**

trace-auditor's `retrieve` is denied outright, so no ceiling is reached. The call asks only for public documents, and the denial still comes first.

**Command:**
```
npx -y @modelcontextprotocol/inspector --cli -e AGENT_ROLE=trace-auditor -e RETRIEVAL_REFERENCE_DIR=/workspace/.memory/reference/lessons -e RETRIEVAL_AUDIT_LOG=/workspace/logs/retrieval-audit-log.jsonl python3 mcp/retrieval/server.py --stdio --method tools/call --tool-name retrieve --tool-arg project_id=proj-lessons --tool-arg "query=container clock UTC" --tool-arg classification_ceiling=public
```

**Output:**
```
authorization_denied: role 'trace-auditor' may not call 'retrieve'. See docs/governance-policy.md.
"isError": true
```

**Audit log tail:**
```
{"claimed_role": "unknown", "event": "authorization_denied", "operation": "write_entry", "outcome": "authorization_denied", "policy_reference": "docs/governance-policy.md", "role": "trace-auditor", "timestamp": "2026-11-24T22:31:04.436239+00:00"}
{"ceiling": "public", "event": "retrieve_ok", "operation": "retrieve", "outcome": "success", "project_id": "proj-lessons", "returned": 3, "role": "planner", "timestamp": "2026-11-24T22:31:45.749055+00:00", "withheld": 0}
{"event": "authorization_denied", "operation": "retrieve", "outcome": "authorization_denied", "policy_reference": "docs/governance-policy.md", "reason": "a lesson is never audit evidence, and the role runs with memory omitted", "role": "trace-auditor", "timestamp": "2026-11-24T22:32:36.991161+00:00"}
```

**Result:** Blocked as expected. Both trace-auditor calls were refused by `_authorize()` before any work ran, and the planner control succeeded with the same query.

### Real-job check

Run as `claude --agent trace-auditor` in its own container (launch line `workspace=ro, memory=omitted`) against baseline `master` with the decision-006 values. **Verdict:** CLEAN. All seven checks passed, nothing was changed and nothing was refused, which shows the role can do its whole job inside these limits.
