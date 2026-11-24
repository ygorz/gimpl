"""Tests for scripts/hooks/decision-write-guard.py (Module 4, closes HO-05).

Run from the repository root:  python3 -m pytest eval/tests -q
Pipes Claude Code PreToolUse JSON into the hook the way settings.json runs
it (python3 <script>) with CLAUDE_PROJECT_DIR set to a temporary project,
and checks the exit code and the audit line. Only the orchestrator (the
main session) may write under .memory/project/decisions/.
"""

import json
import os
import subprocess
import sys

import pytest

EVAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(EVAL)
HOOK = os.path.join(ROOT, "scripts", "hooks", "decision-write-guard.py")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")
MARKER = "BLOCKED by decision-write-guard"
DECISION = ".memory/project/decisions/decision-007.md"
SUBAGENTS = ["implementer", "planner", "tester", "fence-reviewer", "demo-verifier", "port-planner"]


@pytest.fixture
def project(tmp_path):
    (tmp_path / ".memory" / "project" / "decisions").mkdir(parents=True)
    (tmp_path / "docs" / "runs").mkdir(parents=True)
    return tmp_path


def run_hook(project, payload=None, raw=None):
    data = raw if raw is not None else json.dumps(payload)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
    return subprocess.run([sys.executable, HOOK], input=data, capture_output=True,
                          text=True, env=env, cwd=str(project))


def call(project, tool, path, agent_type=None, agent_id=None, **extra):
    field = {"NotebookEdit": "notebook_path", "mcp__coursetools__file_write": "path"}.get(tool, "file_path")
    payload = {"tool_name": tool, "tool_input": {field: path, **extra}, "cwd": str(project)}
    if agent_type is not None:
        payload["agent_type"] = agent_type
    if agent_id is not None:
        payload["agent_id"] = agent_id
    return run_hook(project, payload)


def audit_lines(project):
    log = project / "logs" / "decision-guard-audit-log.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_registered_for_every_write_tool_and_fails_closed():
    hooks = json.load(open(SETTINGS))["hooks"]["PreToolUse"]
    entries = [h for e in hooks for h in e["hooks"] if "decision-write-guard.py" in h["command"]]
    assert len(entries) == 1
    matcher = next(e["matcher"] for e in hooks if any(h in entries for h in e["hooks"]))
    assert set(matcher.split("|")) == {"Write", "Edit", "MultiEdit", "NotebookEdit",
                                       "mcp__coursetools__file_write"}
    assert entries[0].get("onFailure") == "block"


def test_red_team_prompt_8_implementer_file_write_is_blocked_and_logged(project):
    r = call(project, "mcp__coursetools__file_write", DECISION, "implementer", "a1",
             role="implementer", content="supersedes decision-006")
    assert r.returncode == 2 and MARKER in r.stderr
    [line] = audit_lines(project)
    assert line["event"] == "authorization_denied"
    assert line["operation"] == "mcp__coursetools__file_write"
    assert line["agent_type"] == "implementer"
    assert line["target"] == DECISION
    assert line["policy_reference"] == "docs/governance-policy.md"


@pytest.mark.parametrize("agent", SUBAGENTS)
@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit", "NotebookEdit",
                                  "mcp__coursetools__file_write"])
def test_every_subagent_is_blocked_on_every_write_tool(project, agent, tool):
    r = call(project, tool, DECISION, agent, "a1")
    assert r.returncode == 2 and MARKER in r.stderr
    assert len(audit_lines(project)) == 1


def test_claimed_coursetools_role_is_ignored(project):
    r = call(project, "mcp__coursetools__file_write", DECISION, "implementer", "a1", role="orchestrator")
    assert r.returncode == 2


@pytest.mark.parametrize("tool", ["Write", "Edit", "mcp__coursetools__file_write"])
def test_orchestrator_main_session_may_write_decisions(project, tool):
    assert call(project, tool, DECISION).returncode == 0
    assert call(project, tool, DECISION, agent_type="orchestrator").returncode == 0
    assert audit_lines(project) == []


def test_session_started_as_another_agent_is_blocked(project):
    # claude --agent implementer: agent_type set, no agent_id
    assert call(project, "Write", DECISION, agent_type="implementer").returncode == 2


def test_orchestrator_invoked_as_a_subagent_is_blocked(project):
    assert call(project, "Write", DECISION, "orchestrator", "a1").returncode == 2


@pytest.mark.parametrize("path", [
    "docs/../.memory/project/decisions/decision-007.md",
    "./.memory/project/decisions/x.md",
    ".memory/project/decisions",
    ".memory/project/decisions/sub/x.md",
    "ABSOLUTE",
])
def test_other_spellings_of_the_folder_are_blocked(project, path):
    if path == "ABSOLUTE":
        path = str(project / DECISION)
    assert call(project, "Write", path, "implementer", "a1").returncode == 2


def test_symlink_into_the_folder_is_blocked(project):
    os.symlink(project / ".memory" / "project" / "decisions", project / "docs" / "notes")
    r = call(project, "mcp__coursetools__file_write", "docs/notes/decision-007.md", "implementer", "a1")
    assert r.returncode == 2


@pytest.mark.parametrize("path", [
    ".memory/project/current-state.md",
    ".memory/project/decisions-archive/x.md",
    "docs/runs/handoff.md",
    "tests/demos/heretic/manifest",
])
def test_subagent_writes_elsewhere_are_not_this_hooks_business(project, path):
    assert call(project, "mcp__coursetools__file_write", path, "implementer", "a1").returncode == 0
    assert audit_lines(project) == []


def test_other_tools_pass_through(project):
    r = run_hook(project, {"tool_name": "Read", "tool_input": {"file_path": DECISION},
                           "agent_type": "implementer", "agent_id": "a1"})
    assert r.returncode == 0


@pytest.mark.parametrize("raw", ["", "not json", "[]"])
def test_unreadable_input_blocks(project, raw):
    r = run_hook(project, raw=raw)
    assert r.returncode == 2 and MARKER in r.stderr


def test_write_with_no_path_blocks(project):
    r = run_hook(project, {"tool_name": "Write", "tool_input": {}, "agent_type": "implementer",
                           "agent_id": "a1"})
    assert r.returncode == 2


def test_failed_audit_write_still_blocks(project):
    (project / "logs").write_text("not a directory")
    assert call(project, "Write", DECISION, "implementer", "a1").returncode == 2
