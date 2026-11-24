#!/usr/bin/env python3
"""Claude Code PreToolUse hook: only the orchestrator writes decision records.

Registered in .claude/settings.json for
Write|Edit|MultiEdit|NotebookEdit|mcp__coursetools__file_write.
docs/governance-policy.md says no role except the orchestrator (the main
session, acting for the operator) may write under .memory/project/decisions/.
In the HO-05 holdout run an implementer wrote decision-007, which superseded
decision-006, and the fence-reviewer then treated it as authority
(docs/calibration-log.md, near-miss: HO-05). Until this hook, the rule was
held by instruction only.

- Caller identity comes from Claude Code, not from the agent: the hook input
  carries `agent_id` and `agent_type` when the call comes from a subagent
  (or `agent_type` when the session was started with `--agent`). The caller
  is the orchestrator only when there is no `agent_id` and `agent_type` is
  absent or "orchestrator". The `role` argument of a coursetools call is
  claimed by the agent and is ignored here.
- Target: Write/Edit/MultiEdit `file_path`, NotebookEdit `notebook_path`
  (relative to the hook's cwd), and coursetools file_write `path` (relative
  to the project root, as the coursetools server resolves it). Paths are
  normalized and symlinks resolved, so `..` and links cannot reach the
  folder by another name.
- A blocked call exits 2; Claude Code shows stderr to the agent as the tool
  error. Each denial is appended to logs/decision-guard-audit-log.jsonl
  (git-ignored). A failed log write never lets the call through.
- Unreadable hook input or a write with no target path blocks (fail closed).
- Not covered: Bash. Under scripts/run-agent.sh the roles with Bash (tester,
  demo-verifier, trace-auditor) run with memory omitted, and the main session's Bash is
  read-only git (orchestrator-bash-guard.py), so Layer 1 holds that path.
"""
import datetime
import json
import os
import sys

MARKER = "BLOCKED by decision-write-guard"
DECISIONS_DIR = ".memory/project/decisions"
AUDIT_LOG = os.path.join("logs", "decision-guard-audit-log.jsonl")
POLICY_REFERENCE = "docs/governance-policy.md"
PATH_FIELDS = {
    "Write": "file_path",
    "Edit": "file_path",
    "MultiEdit": "file_path",
    "NotebookEdit": "notebook_path",
    "mcp__coursetools__file_write": "path",
}


def project_root(data):
    return os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()


def is_orchestrator(data):
    """The main session with no --agent, or one started as the orchestrator."""
    if data.get("agent_id"):
        return False
    return data.get("agent_type") in (None, "", "orchestrator")


def write_target(tool, inp, root, cwd):
    """Project-relative, normalized, symlink-resolved target of a write, or
    None if the input has no usable path."""
    field = PATH_FIELDS.get(tool)
    path = inp.get(field) if field and isinstance(inp, dict) else None
    if not isinstance(path, str) or not path.strip():
        return None
    base = root if tool.startswith("mcp__") else cwd
    full = os.path.realpath(os.path.join(base, os.path.expanduser(path)))
    root = os.path.realpath(root)
    if full != root and not full.startswith(root + os.sep):
        return full.replace(os.sep, "/")    # outside the project: not a decision record
    return os.path.relpath(full, root).replace(os.sep, "/")


def in_decisions(target):
    return target == DECISIONS_DIR or target.startswith(DECISIONS_DIR + "/")


def audit(root, data, tool, target, reason):
    try:
        os.makedirs(os.path.join(root, "logs"), exist_ok=True)
        with open(os.path.join(root, AUDIT_LOG), "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "event": "authorization_denied",
                "guard": "decision-write-guard",
                "operation": tool,
                "target": target,
                "agent_type": data.get("agent_type") or "main-session",
                "agent_id": data.get("agent_id"),
                "reason": reason,
                "policy_reference": POLICY_REFERENCE,
            }, sort_keys=True) + "\n")
    except Exception:
        pass    # logging is best effort; the call is blocked either way


def block(detail):
    print(f"{MARKER}: {detail} Decision records under {DECISIONS_DIR}/ are written only by "
          "the orchestrator with the operator's approval (docs/governance-policy.md, near-miss "
          "HO-05). Report the proposed decision in your result instead. Do not retry this "
          "through another tool.", file=sys.stderr)
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as e:
        block(f"could not parse hook input ({e}); blocking to be safe.")

    tool = data.get("tool_name")
    if tool not in PATH_FIELDS:
        sys.exit(0)
    root = project_root(data)
    cwd = data.get("cwd") or root
    target = write_target(tool, data.get("tool_input"), root, cwd)
    if target is None:
        audit(root, data, tool, None, "no target path")
        block(f"{tool} has no target path in the hook input; blocking to be safe.")
    if not in_decisions(target) or is_orchestrator(data):
        sys.exit(0)
    who = data.get("agent_type") or "a subagent"
    audit(root, data, tool, target, "decision records are orchestrator-only")
    block(f"{who} may not write {target}.")


if __name__ == "__main__":
    main()
