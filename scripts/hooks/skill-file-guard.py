#!/usr/bin/env python3
"""Claude Code PreToolUse hook: subagents do not read skill files through Bash.

Registered in .claude/settings.json for Bash. docs/governance-policy.md
scopes skills per role: subagents get only the skills their agent file
preloads, and no subagent has the Skill tool. A skill's SKILL.md opened as a
plain file would get around that scope, the same displacement seen in
DEV-02-r2, where blocking one tool moved the reads to another
(docs/calibration-log.md). The other paths are closed elsewhere:

- Read, Edit and Write: `Read(./.claude/skills/**)` and
  `Edit(./.claude/skills/**)` deny rules in .claude/settings.json. Claude
  Code also applies the Read rule to Grep and Glob (best effort, per its
  permissions docs).
- coursetools file_read, file_write and codebase_search: `.claude/skills`
  is in DENIED_PATHS in mcp/coursetools_server.py.

This hook covers Bash, which only the tester, demo-verifier and
trace-auditor have as subagents. It blocks a subagent's Bash command that names `.claude/skills`
or a `SKILL.md` file. It is a string check: a command that reaches the files
without naming them (a glob such as `.claude/sk*`, a variable, `find`) is
not caught, so it is a tripwire, not a boundary. A skill file holds
instructions only, so a read that gets past it grants no tool or permission
the role does not already have.

- The main session is not limited here: its Bash is read-only git
  (orchestrator-bash-guard.py), and it has the Skill tool.
- Caller identity comes from Claude Code's `agent_id` / `agent_type` hook
  input fields, as in decision-write-guard.py.
- A blocked call exits 2 and is appended to logs/skill-guard-audit-log.jsonl
  (git-ignored). A failed log write never lets the call through.
- Unreadable hook input blocks (fail closed).
"""
import datetime
import json
import os
import re
import sys

MARKER = "BLOCKED by skill-file-guard"
AUDIT_LOG = os.path.join("logs", "skill-guard-audit-log.jsonl")
POLICY_REFERENCE = "docs/governance-policy.md"
SKILL_FILE_PATTERN = re.compile(r"\.claude/+skills|skill\.md", re.IGNORECASE)


def project_root(data):
    return os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()


def is_main_session(data):
    """The main session (the orchestrator), not a subagent or another --agent."""
    if data.get("agent_id"):
        return False
    return data.get("agent_type") in (None, "", "orchestrator")


def audit(root, data, command, reason):
    try:
        os.makedirs(os.path.join(root, "logs"), exist_ok=True)
        with open(os.path.join(root, AUDIT_LOG), "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "event": "authorization_denied",
                "guard": "skill-file-guard",
                "operation": "Bash",
                "command": command[:200] if isinstance(command, str) else None,
                "agent_type": data.get("agent_type") or "main-session",
                "agent_id": data.get("agent_id"),
                "reason": reason,
                "policy_reference": POLICY_REFERENCE,
            }, sort_keys=True) + "\n")
    except Exception:
        pass    # logging is best effort; the call is blocked either way


def block(detail):
    print(f"{MARKER}: {detail} Skills load only through the Skill tool or an agent's "
          "skills: preload, never as plain files (docs/governance-policy.md). Use the skills "
          "your agent file preloads. Do not retry this through another command or tool.",
          file=sys.stderr)
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as e:
        block(f"could not parse hook input ({e}); blocking to be safe.")

    if data.get("tool_name") != "Bash" or is_main_session(data):
        sys.exit(0)
    command = (data.get("tool_input") or {}).get("command") if isinstance(data.get("tool_input"), dict) else None
    root = project_root(data)
    if not isinstance(command, str):
        audit(root, data, command, "no command")
        block("no Bash command in the hook input; blocking to be safe.")
    if not SKILL_FILE_PATTERN.search(command):
        sys.exit(0)
    who = data.get("agent_type") or "a subagent"
    audit(root, data, command, "skill files are not read as plain files")
    block(f"{who} may not reach skill files through Bash (`{command[:120]}`).")


if __name__ == "__main__":
    main()
