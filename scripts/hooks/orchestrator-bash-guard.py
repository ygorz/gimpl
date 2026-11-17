#!/usr/bin/env python3
"""Claude Code PreToolUse hook: the main session's Bash is read-only git only,
and its Read/Glob/Grep stay under .memory/ (the startup memory reads).

Registered in .claude/settings.json for Bash|Read|Glob|Grep. CLAUDE.md
"Tools the Orchestrator uses" limits the main session (the Orchestrator) to
Bash for read-only git (`git status`, `git diff`, `git log`), Read/Glob/Grep
only for the startup memory reads, and mcp__coursetools__file_read for any
other file. In DEV-01-r1 that instruction was in context and the main
session still ran 8 non-git Bash calls (cat, sed, grep, ls, head, git show),
so commit B enforced the Bash part at the tool layer. In DEV-02-r2 the hook
denied the Bash read and the main session moved the same reads onto Read
(.claude/agents/*.md), still out of lane, so the Read/Glob/Grep part is
enforced here too (commit C).

- Subagents are never limited here: Claude Code adds `agent_id` to the hook
  input only when the call comes from a subagent (docs: "Common input
  fields"). The tester and demo-verifier keep their Bash exactly as before;
  their own tools: lists and permissions still apply.
- Main session: allowed only if every chained part (&&, ||, ;, newline) is
  git status / diff / log (optionally after `cd <dir>`), piped at most into
  head/tail/wc/sort/uniq/grep reading stdin only. This is the same rule as
  orch_bash_ok() in eval/test_deterministic.py (orchestrator_in_lane);
  eval/tests/test_orchestrator_bash_hook.py checks the two agree.
- Main-session Read/Glob/Grep: allowed only if the target resolves under
  .memory/ in the project: Read file_path; Grep path (none = the cwd, so
  blocked); Glob path joined with pattern (no path = the cwd). A Glob
  pattern with `..` is blocked. Targets inside .memory/storage.db*,
  .memory/storage-audit.log or .memory/reference/lessons/ are blocked too
  (NEVER_READ_PATHS in eval/test_deterministic.py; settings.json also
  denies them). Anything allowed here passes orchestrator_in_lane, whose
  Read/Glob/Grep rule is ".memory" in a path argument; this hook is
  stricter (normalized, symlinks resolved, `..` cannot escape).
- Blocked calls exit 2; Claude Code shows stderr to the main session as the
  tool error, and the harness counts it as a near-miss (it never ran).
- Unreadable hook input blocks (fail closed), like memory-secret-guard.py.
"""
import json
import os
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


MEMORY_DIR = ".memory"
# Inside .memory/ but never read directly; reached only through the storage
# and retrieval servers (mirrors NEVER_READ_PATHS and coursetools DENIED_PATHS).
MEMORY_NEVER_READ = (".memory/storage.db", ".memory/storage-audit.log", ".memory/reference/lessons")
FILE_TOOLS = ("Read", "Glob", "Grep")


def project_root(data):
    return os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()


def repo_target(path, root, cwd):
    """Project-relative, normalized, symlink-resolved form of a path (None if
    it leaves the project)."""
    full = os.path.realpath(os.path.join(cwd, os.path.expanduser(path)))
    root = os.path.realpath(root)
    if full != root and not full.startswith(root + os.sep):
        return None
    return os.path.relpath(full, root).replace(os.sep, "/")


def memory_target_ok(target):
    if target is None or not (target == MEMORY_DIR or target.startswith(MEMORY_DIR + "/")):
        return False
    for p in MEMORY_NEVER_READ:
        if target == p or target.startswith(p + "/") or \
                (p.endswith("storage.db") and target.startswith(p)):
            return False
    return True


def file_tool_target(tool, inp):
    """The path a main-session Read/Glob/Grep reaches, or None if it has none."""
    if tool == "Read":
        p = inp.get("file_path")
        return p if isinstance(p, str) and p.strip() else None
    base = inp.get("path")
    if base is not None and not isinstance(base, str):
        return None
    base = base if base and base.strip() else "."
    if tool == "Grep":
        return base
    pattern = inp.get("pattern")
    if not isinstance(pattern, str) or not pattern.strip() or ".." in pattern:
        return None
    return pattern if os.path.isabs(pattern) else os.path.join(base, pattern)


def file_tool_ok(tool, inp, root, cwd):
    target = file_tool_target(tool, inp)
    return target is not None and memory_target_ok(repo_target(target, root, cwd))


def block(detail):
    print(f"{MARKER}: {detail} In the main session Bash is read-only git only "
          "(`git status`, `git diff`, `git log`, optionally piped into head/tail/wc/sort/uniq/grep), "
          "per CLAUDE.md \"Tools the Orchestrator uses\". For the startup memory reads use "
          "Read/Glob/Grep on .memory/; for any other repo file use mcp__coursetools__file_read. "
          "Building, running demo checks and changing files belong to the subagents. Do not retry "
          "this through another command.", file=sys.stderr)
    sys.exit(2)


def block_file(detail):
    print(f"{MARKER}: {detail} In the main session Read/Glob/Grep are only for the startup memory "
          "reads under .memory/, per CLAUDE.md \"Tools the Orchestrator uses\". For any other repo "
          "file (plans, docs/, .claude/agents/*.md, run summaries) use mcp__coursetools__file_read "
          "with role \"orchestrator\". Do not retry this through Bash or another tool.", file=sys.stderr)
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as e:
        block(f"could not parse hook input ({e}); blocking to be safe.")

    tool = data.get("tool_name")
    if tool != "Bash" and tool not in FILE_TOOLS:
        sys.exit(0)
    if data.get("agent_id"):          # a subagent: its own grant applies, not this rule
        sys.exit(0)
    if tool in FILE_TOOLS:
        inp = data.get("tool_input")
        if not isinstance(inp, dict):
            block_file(f"no {tool} input in the hook input.")
        root = project_root(data)
        cwd = data.get("cwd") or root
        if file_tool_ok(tool, inp, root, cwd):
            sys.exit(0)
        block_file(f"{tool} {json.dumps(inp)[:160]} is outside .memory/ (or a never-read memory path).")
    cmd = (data.get("tool_input") or {}).get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        block("no Bash command in the hook input.")
    if orch_bash_ok(cmd):
        sys.exit(0)
    block(f"`{cmd[:120]}` is not read-only git.")


if __name__ == "__main__":
    main()
