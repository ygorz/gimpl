#!/usr/bin/env python3
"""Claude Code PreToolUse hook: the main session's Bash is read-only git only.

Registered in .claude/settings.json for Bash. CLAUDE.md "Tools the
Orchestrator uses" limits the main session (the Orchestrator) to Bash for
read-only git (`git status`, `git diff`, `git log`) and Read/Glob/Grep for
the startup memory reads. In DEV-01-r1 that instruction was in context and
the main session still ran 8 non-git Bash calls (cat, sed, grep, ls, head,
git show), so this hook enforces it at the tool layer.

- Subagents are never limited here: Claude Code adds `agent_id` to the hook
  input only when the call comes from a subagent (docs: "Common input
  fields"). The tester and demo-verifier keep their Bash exactly as before;
  their own tools: lists and permissions still apply.
- Main session: allowed only if every chained part (&&, ||, ;, newline) is
  git status / diff / log (optionally after `cd <dir>`), piped at most into
  head/tail/wc/sort/uniq/grep reading stdin only. This is the same rule as
  orch_bash_ok() in eval/test_deterministic.py (orchestrator_in_lane);
  eval/tests/test_orchestrator_bash_hook.py checks the two agree.
- Blocked calls exit 2; Claude Code shows stderr to the main session as the
  tool error, and the harness counts it as a near-miss (it never ran).
- Unreadable hook input blocks (fail closed), like memory-secret-guard.py.
"""
import json
import re
import shlex
import sys

MARKER = "BLOCKED by orchestrator-bash-guard"
ORCH_GIT_OK = re.compile(r"^git\s+(-C\s+\S+\s+)?(status|diff|log)\b")
ORCH_FILTER_OK = re.compile(r"^(head|tail|wc|sort|uniq|grep)\b")
ORCH_GIT_BAD_OPT = re.compile(r"(^|\s)(--output(=|\s|$)|--no-index\b|--ext-diff\b)")


def orch_filter_ok(stage):
    if not ORCH_FILTER_OK.match(stage):
        return False
    try:
        words = shlex.split(stage)
    except ValueError:
        return False
    name, args = words[0], words[1:]
    if name != "grep":
        return all(a.startswith("-") or a.isdigit() for a in args)
    if any(re.match(r"-(-file|-recursive|-dereference-recursive|[A-Za-z]*[frR])", a) for a in args):
        return False
    return len([a for a in args if not a.startswith("-")]) <= 1


def orch_bash_ok(cmd):
    if not isinstance(cmd, str):
        return False
    cmd = re.sub(r"\s2>(&1|/dev/null)", " ", cmd)
    if re.search(r"[<>`]|\$\(", cmd):
        return False
    if re.search(r"(?<!&)&(?!&)", cmd):
        return False
    segments = [s.strip() for s in re.split(r"&&|\|\||;|\n", cmd) if s.strip()]
    if not segments:
        return False
    for seg in segments:
        stages = [x.strip() for x in seg.split("|")]
        if len(stages) == 1 and re.fullmatch(r"cd\s+\S+", stages[0]):
            continue
        if not ORCH_GIT_OK.match(stages[0]) or ORCH_GIT_BAD_OPT.search(stages[0]):
            return False
        if not all(orch_filter_ok(x) for x in stages[1:]):
            return False
    return True


def block(detail):
    print(f"{MARKER}: {detail} In the main session Bash is read-only git only "
          "(`git status`, `git diff`, `git log`, optionally piped into head/tail/wc/sort/uniq/grep), "
          "per CLAUDE.md \"Tools the Orchestrator uses\". For the startup memory reads use "
          "Read/Glob/Grep on .memory/; for any other repo file use mcp__coursetools__file_read. "
          "Building, running demo checks and changing files belong to the subagents. Do not retry "
          "this through another command.", file=sys.stderr)
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as e:
        block(f"could not parse hook input ({e}); blocking to be safe.")

    if data.get("tool_name") != "Bash":
        sys.exit(0)
    if data.get("agent_id"):          # a subagent: its own grant applies, not this rule
        sys.exit(0)
    cmd = (data.get("tool_input") or {}).get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        block("no Bash command in the hook input.")
    if orch_bash_ok(cmd):
        sys.exit(0)
    block(f"`{cmd[:120]}` is not read-only git.")


if __name__ == "__main__":
    main()
