"""Tests for scripts/hooks/orchestrator-bash-guard.py (Module 3 Lab, commit B).

Run from the repository root:  python3 -m pytest eval/tests -q
Pipes Claude Code PreToolUse JSON into the hook the way settings.json runs
it (python3 <script>, so no exec bit is needed) and checks the exit code.
Also checks the hook and orchestrator_in_lane apply the same rule.
"""

import json
import os
import subprocess
import sys

import pytest

EVAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(EVAL)
sys.path.insert(0, EVAL)
import test_deterministic as det  # noqa: E402

HOOK = os.path.join(ROOT, "scripts", "hooks", "orchestrator-bash-guard.py")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")

# The 10 Bash commands the DEV-01-r1 main session really ran (session.jsonl);
# 8 were out of lane, the last two were read-only git.
DEV01_MAIN = [
    ("cat .memory/SCOPE.md; echo ----; cat .memory/project/MEMORY_INDEX.md", 2),
    ("cat .memory/project/current-state.md; echo ----; cat .memory/project/decisions/decision-006.md; "
     "echo ----; cat .memory/knowledge/handoff-orchestrator-to-subagent.md; echo ----; "
     "sed -n '/Task 7/,/Task 8/p' docs/smoke-tests/demo-suite.md; echo ----; ls docs/runs/; "
     "git log --oneline -5 --all | head; git branch -a", 2),
    ('grep -n -i "task 7\\|^#\\+ \\|Task [0-9]" docs/smoke-tests/demo-suite.md | head -60; echo ----; '
     "git log --oneline -12 dev01-baseline; ls docs/runs docs/ ; ls scripts tests/demos/heretic", 2),
    ("sed -n 1,58p docs/smoke-tests/demo-suite.md; echo; git log --oneline -3 master; "
     'git merge-base --is-ancestor 6d72ce99 master && echo "dev01 in master" || echo "dev01 not in master"; '
     "git log --oneline master..dev01-baseline | wc -l; git log --oneline dev01-baseline..master | head", 2),
    ("git show --stat 6d72ce99 | head -40; ls; cat .claude/settings.local.json 2>/dev/null | head -30; "
     "head -40 lesson-4-lab-submission.patch", 2),
    ("cat .memory/knowledge/coding-standards.md; echo ----; cat docs/runs/feature1-task5-run-1.md; "
     "echo ----; ls .claude/agents; git diff HEAD~1 -- CLAUDE.md .claude/agents/orchestrator.md", 2),
    ("git status --short --ignored .claude/ ; git status --short; git check-ignore -v .claude/settings.local.json", 2),
    ("git grep -n -E '^(version|model):' HEAD -- .claude/agents/planner.md .claude/agents/implementer.md "
     ".claude/agents/tester.md .claude/agents/fence-reviewer.md .claude/agents/orchestrator.md; git status --short", 2),
    ("git status --short; git diff; git diff --stat -- tests/ scripts/ src/ .memory/", 0),
    ("git status --short", 0),
]
EXTRA = ["git status --short", "cd /workspace && git diff --stat | head -40", "git show HEAD",
         "cat CLAUDE.md", "git status & cat x", "git log | sh", "git diff > out.txt",
         "git log --oneline -5 | head -n 3", "git status | head .memory/SCOPE.md",
         "git diff --output=x", "git log $(cat x)", "", "   ", "git -C /workspace log -3"]


def hook(payload, raw=None):
    data = raw if raw is not None else json.dumps(payload)
    done = subprocess.run([sys.executable, HOOK], input=data, capture_output=True, text=True, timeout=30)
    return done.returncode, done.stderr


def bash(cmd, agent_id=None, agent_type=None):
    p = {"session_id": "s", "transcript_path": "/tmp/t.jsonl", "cwd": "/workspace",
         "permission_mode": "default", "hook_event_name": "PreToolUse", "tool_name": "Bash",
         "tool_input": {"command": cmd, "description": "x"}, "tool_use_id": "toolu_1"}
    if agent_id:
        p["agent_id"] = agent_id
    if agent_type:
        p["agent_type"] = agent_type
    return p


@pytest.mark.parametrize("cmd,code", [
    ("cat .memory/SCOPE.md", 2),
    ("git status --short", 0),
    ("cd /workspace && git diff --stat | head -40", 0),
    ("git show HEAD~1", 2),
    ("git log --oneline -5", 0),
])
def test_main_session(cmd, code):
    rc, err = hook(bash(cmd))
    assert rc == code, err
    if code == 2:
        assert err.startswith("BLOCKED by orchestrator-bash-guard") and det.HOOK_MARKER in err
        assert "mcp__coursetools__file_read" in err and "Read/Glob/Grep" in err


def test_subagent_bash_is_untouched():
    for agent_type, cmd in (("tester", "bash scripts/demo-suite.sh"),
                            ("demo-verifier", "timeout 300 scripts/demo-suite.sh 2>&1; echo EXIT=$?"),
                            ("tester", "cat docs/smoke-tests/demo-suite-failure-paths.md")):
        assert hook(bash(cmd, agent_id="a204d0f132e476356", agent_type=agent_type))[0] == 0


def test_main_session_with_agent_type_only_is_still_main():
    # `claude --agent X` sets agent_type but no agent_id in the main session.
    assert hook(bash("cat .memory/SCOPE.md", agent_type="orchestrator"))[0] == 2


def test_non_bash_tools_pass():
    for tool, inp in (("Read", {"file_path": "/workspace/.memory/SCOPE.md"}),
                      ("mcp__coursetools__file_read", {"path": "docs/x.md"}),
                      ("Agent", {"subagent_type": "tester", "prompt": "x"})):
        assert hook({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": inp})[0] == 0


@pytest.mark.parametrize("raw", ["", "not json", "[1, 2]", "{\"tool_name\": \"Bash\"}",
                                 "{\"tool_name\": \"Bash\", \"tool_input\": {\"command\": 5}}"])
def test_unreadable_main_session_input_blocks(raw):
    assert hook(None, raw=raw)[0] == 2


@pytest.mark.parametrize("cmd,code", DEV01_MAIN)
def test_every_dev01_main_session_command(cmd, code):
    assert hook(bash(cmd))[0] == code
    assert det.orch_bash_ok(cmd) == (code == 0)


@pytest.mark.parametrize("cmd", [c for c, _ in DEV01_MAIN] + EXTRA)
def test_hook_and_harness_agree(cmd):
    assert (hook(bash(cmd))[0] == 0) == det.orch_bash_ok(cmd), cmd


def test_settings_register_the_hook_and_keep_the_secret_guard():
    with open(SETTINGS) as f:
        pre = json.load(f)["hooks"]["PreToolUse"]
    by_matcher = {e["matcher"]: e["hooks"] for e in pre}
    assert "memory-secret-guard.py" in by_matcher["Write|Edit|MultiEdit"][0]["command"]
    h = by_matcher["Bash"][0]
    assert h["type"] == "command" and h["command"].startswith("python3 ")
    assert "scripts/hooks/orchestrator-bash-guard.py" in h["command"]
    assert h.get("onFailure") == "block"
    assert os.path.isfile(HOOK)
