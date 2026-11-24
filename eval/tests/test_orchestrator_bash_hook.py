"""Tests for scripts/hooks/orchestrator-bash-guard.py (Module 3 Lab, commits B and C).

Run from the repository root:  python3 -m pytest eval/tests -q
Pipes Claude Code PreToolUse JSON into the hook the way settings.json runs
it (python3 <script>, so no exec bit is needed) and checks the exit code.
Also checks the hook and orchestrator_in_lane apply the same rule (Bash:
identical; Read/Glob/Grep: anything the hook allows passes the harness, and
the DEV-02-r2 calls get the same verdict from both).
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


PROJECT = "/workspace"


def hook(payload, raw=None, project=PROJECT):
    data = raw if raw is not None else json.dumps(payload)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=project)
    done = subprocess.run([sys.executable, HOOK], input=data, capture_output=True, text=True,
                          timeout=30, env=env)
    return done.returncode, done.stderr


def tool(name, inp, agent_id=None, agent_type=None, cwd=PROJECT):
    p = {"session_id": "s", "transcript_path": "/tmp/t.jsonl", "cwd": cwd,
         "permission_mode": "default", "hook_event_name": "PreToolUse", "tool_name": name,
         "tool_input": inp, "tool_use_id": "toolu_1"}
    if agent_id:
        p["agent_id"] = agent_id
    if agent_type:
        p["agent_type"] = agent_type
    return p


def harness_ok(name, inp):
    """orchestrator_in_lane's Read/Glob/Grep rule, applied to one call."""
    call = {"tool": name, "input": inp}
    return any(".memory" in a for a in det.tool_path_args(call))


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


def test_session_started_as_another_agent_is_not_limited():
    # `claude --agent trace-auditor` is that role, not the orchestrator: the
    # same main-session test as decision-write-guard.py and skill-file-guard.py.
    for agent_type, cmd in (("trace-auditor", "sha256sum tests/demos/heretic/golden/demo1.tics"),
                            ("trace-auditor", "wc -l tests/demos/heretic/golden/demo1.tics"),
                            ("tester", "bash scripts/demo-suite.sh")):
        assert hook(bash(cmd, agent_type=agent_type))[0] == 0
    assert hook(tool("Read", {"file_path": "/workspace/tests/demos/heretic/manifest"},
                     agent_type="trace-auditor"))[0] == 0
    assert hook(bash("cat .memory/SCOPE.md", agent_type=""))[0] == 2


def test_tools_outside_the_guard_pass():
    for name, inp in (("mcp__coursetools__file_read", {"role": "orchestrator", "path": ".claude/agents/planner.md"}),
                      ("mcp__coursetools__file_read", {"role": "orchestrator", "path": "docs/memory-architecture.md"}),
                      ("Agent", {"subagent_type": "tester", "prompt": "x"}),
                      ("Write", {"file_path": "/workspace/x.md", "content": "x"})):
        assert hook({"hook_event_name": "PreToolUse", "tool_name": name, "tool_input": inp})[0] == 0


# --- commit C: main-session Read/Glob/Grep only under .memory/ -------------

# The main-session file-tool calls of DEV-02-r2 after the Bash denial: the
# startup reads (in lane) and the four agent-file reads orchestrator_in_lane
# failed on, with the verdict both the hook and the harness must give.
DEV02_R2_MAIN = [
    ("Read", {"file_path": "/workspace/.memory/SCOPE.md"}, 0),
    ("Read", {"file_path": "/workspace/.memory/project/MEMORY_INDEX.md"}, 0),
    ("Read", {"file_path": "/workspace/.memory/project/current-state.md"}, 0),
    ("Read", {"file_path": "/workspace/.memory/knowledge/handoff-orchestrator-to-subagent.md"}, 0),
    ("Read", {"file_path": "/workspace/.claude/agents/planner.md"}, 2),
    ("Read", {"file_path": "/workspace/.claude/agents/implementer.md"}, 2),
    ("Read", {"file_path": "/workspace/.claude/agents/tester.md"}, 2),
    ("Read", {"file_path": "/workspace/.claude/agents/fence-reviewer.md"}, 2),
]

FILE_CASES = [
    ("Read", {"file_path": "/workspace/.memory/SCOPE.md"}, 0),
    ("Read", {"file_path": ".memory/SCOPE.md"}, 0),
    ("Read", {"file_path": "/workspace/.claude/agents/planner.md"}, 2),
    ("Read", {"file_path": "/workspace/docs/memory-architecture.md"}, 2),
    ("Read", {"file_path": "/workspace/CLAUDE.md"}, 2),
    ("Read", {"file_path": "/workspace/.memory/../CLAUDE.md"}, 2),
    ("Read", {"file_path": "/etc/passwd"}, 2),
    ("Read", {"file_path": "/workspace/.memory/storage.db"}, 2),
    ("Read", {"file_path": "/workspace/.memory/storage.db-wal"}, 2),
    ("Read", {"file_path": "/workspace/.memory/storage-audit.log"}, 2),
    ("Read", {"file_path": "/workspace/.memory/reference/lessons/lesson-x.md"}, 2),
    ("Read", {"file_path": "/workspace/.memory/reference/lessons"}, 2),
    ("Read", {"file_path": "/workspace/.memory/reference/README.md"}, 0),
    ("Read", {"file_path": "/workspace/.memory-notes.md"}, 2),
    ("Read", {}, 2),
    ("Grep", {"pattern": "Task 7", "path": ".memory"}, 0),
    ("Grep", {"pattern": "Task 7", "path": "/workspace/.memory/project"}, 0),
    ("Grep", {"pattern": "Task 7"}, 2),                          # no path = whole repo
    ("Grep", {"pattern": "Task 7", "path": "docs"}, 2),
    ("Grep", {"pattern": "x", "path": ".memory/reference/lessons"}, 2),
    ("Glob", {"pattern": "**/*.md"}, 2),                         # no path = whole repo
    ("Glob", {"pattern": "**/*.md", "path": "/workspace"}, 2),
    ("Glob", {"pattern": "**/*.md", "path": ".memory"}, 0),
    ("Glob", {"pattern": ".memory/project/*.md"}, 0),
    ("Glob", {"pattern": "/workspace/.memory/**/*.md"}, 0),
    ("Glob", {"pattern": ".claude/agents/*.md"}, 2),
    ("Glob", {"pattern": "../docs/*.md", "path": ".memory"}, 2),
    ("Glob", {"pattern": "{a,../../docs}/*", "path": ".memory"}, 2),
    ("Glob", {"pattern": "*.md", "path": "/workspace/.memory/reference/lessons"}, 2),
]


@pytest.mark.parametrize("name,inp,code", FILE_CASES)
def test_main_session_file_tools(name, inp, code):
    rc, err = hook(tool(name, inp))
    assert rc == code, err
    if code == 2:
        assert err.startswith("BLOCKED by orchestrator-bash-guard") and det.HOOK_MARKER in err
        assert "mcp__coursetools__file_read" in err and ".memory/" in err


@pytest.mark.parametrize("name,inp,code", DEV02_R2_MAIN)
def test_dev02_r2_main_session_file_calls_hook_and_harness_agree(name, inp, code):
    assert hook(tool(name, inp))[0] == code
    assert harness_ok(name, inp) == (code == 0)


@pytest.mark.parametrize("name,inp,code", FILE_CASES)
def test_hook_never_allows_what_the_harness_fails(name, inp, code):
    # The harness rule (".memory" in a path argument) is looser; the hook may
    # block more, never less.
    if hook(tool(name, inp))[0] == 0:
        assert harness_ok(name, inp), (name, inp)


def test_subagent_file_tools_are_untouched():
    for name, inp in (("Read", {"file_path": "/workspace/.claude/agents/planner.md"}),
                      ("Read", {"file_path": "/workspace/docs/smoke-tests/demo-suite.md"}),
                      ("Grep", {"pattern": "PASS"}),
                      ("Glob", {"pattern": "**/*.md"})):
        assert hook(tool(name, inp, agent_id="a204d0f132e476356", agent_type="demo-verifier"))[0] == 0


def test_main_session_file_tool_with_agent_type_only_is_still_main():
    assert hook(tool("Read", {"file_path": "/workspace/.claude/agents/planner.md"},
                     agent_type="orchestrator"))[0] == 2


def test_relative_paths_resolve_against_cwd(tmp_path):
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / "docs").mkdir()
    p = str(root)
    assert hook(tool("Grep", {"pattern": "x", "path": "."}, cwd=p + "/.memory"), project=p)[0] == 0
    assert hook(tool("Grep", {"pattern": "x", "path": "../docs"}, cwd=p + "/.memory"), project=p)[0] == 2


def test_symlink_out_of_memory_is_blocked(tmp_path):
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".claude" / "agents").mkdir(parents=True)
    (root / ".claude" / "agents" / "planner.md").write_text("x")
    os.symlink(root / ".claude" / "agents", root / ".memory" / "agents")
    p = str(root)
    assert hook(tool("Read", {"file_path": p + "/.memory/agents/planner.md"}, cwd=p), project=p)[0] == 2


def load_coursetools(monkeypatch):
    """Import mcp/coursetools_server.py with a stand-in FastMCP (the real
    mcp package lives in the container), rooted at this repository."""
    import importlib.util
    import types

    class FastMCP:
        def __init__(self, name):
            pass

        def tool(self):
            return lambda f: f

    fastmcp = types.ModuleType("mcp.server.fastmcp")
    fastmcp.FastMCP = FastMCP
    for name, mod in (("mcp", types.ModuleType("mcp")), ("mcp.server", types.ModuleType("mcp.server")),
                      ("mcp.server.fastmcp", fastmcp)):
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setenv("COURSETOOLS_ROOT", ROOT)
    monkeypatch.setenv("COURSETOOLS_ALLOWLIST", os.path.join(ROOT, "mcp", "roles.allowlist.json"))
    spec = importlib.util.spec_from_file_location("coursetools_under_test",
                                                  os.path.join(ROOT, "mcp", "coursetools_server.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_coursetools_lets_the_orchestrator_read_agent_files_and_docs(monkeypatch):
    """The deny message points at mcp__coursetools__file_read; it must work
    for role orchestrator on the files DEV-02-r2 needed, and still refuse
    the never-read paths."""
    ct = load_coursetools(monkeypatch)
    for path in (".claude/agents/planner.md", ".claude/agents/implementer.md",
                 ".claude/agents/tester.md", ".claude/agents/fence-reviewer.md",
                 "docs/memory-architecture.md", "CLAUDE.md", ".memory/SCOPE.md"):
        assert ct.file_read("orchestrator", path), path
    for path in (".memory/storage-audit.log", ".memory/reference/lessons/x.md", "docs/holdout-task-set.md"):
        with pytest.raises(PermissionError):
            ct.file_read("orchestrator", path)


@pytest.mark.parametrize("raw", ["", "not json", "[1, 2]", "{\"tool_name\": \"Bash\"}",
                                 "{\"tool_name\": \"Bash\", \"tool_input\": {\"command\": 5}}",
                                 "{\"tool_name\": \"Read\"}",
                                 "{\"tool_name\": \"Read\", \"tool_input\": {\"file_path\": 5}}",
                                 "{\"tool_name\": \"Glob\", \"tool_input\": {\"pattern\": \".memory/*\", \"path\": 5}}"])
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
    guarded = [m for m in by_matcher if "orchestrator-bash-guard.py" in by_matcher[m][0]["command"]]
    assert guarded == ["Bash|Read|Glob|Grep"]
    h = by_matcher["Bash|Read|Glob|Grep"][0]
    assert h["type"] == "command" and h["command"].startswith("python3 ")
    assert "scripts/hooks/orchestrator-bash-guard.py" in h["command"]
    assert h.get("onFailure") == "block"
    assert os.path.isfile(HOOK)
