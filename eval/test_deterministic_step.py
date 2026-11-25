"""Unit tests for scripts/verify_demos_deterministic.py (ADR-001).

Run from the repository root:  python3 -m pytest eval/test_deterministic_step.py -v

The script replaces the demo-verifier agent. These tests pin its contract
(named input and output files, the same report content, exit 0/1/2, no
language model) and the three edge cases the agent handled by judgment
(docs/step-classification.md): engine exit 255 is normal, a newer binary for
another game is not a reason to rebuild, and a tree that was dirty before the
check is reported, not blamed. Script output below is copied from the logged
runs: docs/agents/demo-verifier-iteration-log.md Runs 1 and 2, the Task 8
verification run in docs/iteration-log.md, and the Task 7 failure-path runs.
"""

import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verify_demos_deterministic.py"
sys.path.insert(0, str(SCRIPT.parent))
import verify_demos_deterministic as vd  # noqa: E402

WAD_LINE = "IWAD OK: wads/blasphem.wad (e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63)"
TRACE_LINE = ("trace OK: tests/demos/heretic/golden/demo1.tics "
              "(537e8a1fd73967c0099d1ee55c0586e353d5240d27dd3a41dfa15ac3757d2f30)")
MANIFEST_TEXT = (ROOT / vd.MANIFEST).read_text(encoding="utf-8")


def timed(realtics=132, fps="1120.795410"):
    return f"timed 4227 gametics in {realtics} realtics ({fps} fps)"


def suite_pass(realtics=132):
    return "\n".join([WAD_LINE, TRACE_LINE, timed(realtics), "engine exit code: 255",
                      "PASS: demo1 4227 gametics, trace matches", "PASS: 1 demo(s)"]) + "\n"


def cross_pass(realtics=116):
    return "\n".join([WAD_LINE, timed(realtics, "1275.387939"), "engine exit code: 255",
                      "PASS: 4227 gametics == expected 4227"]) + "\n"


SUITE_TRACE_FAIL = "\n".join([   # Task 7: edited trace in a temp copy
    WAD_LINE, TRACE_LINE, timed(), "engine exit code: 255",
    "gametic 100: p0.armor expected 50 got 0",
    "FAIL: demo1 trace differs from tests/demos/heretic/golden/demo1.tics",
    "FAIL: 1 of 1 demo(s) failed"]) + "\n"
SUITE_SETUP_ERROR = (WAD_LINE + "\nERROR: tests/demos/heretic/golden/demo1.tics sha256 mismatch: "
                     "expected 537e8a1f, got 00000000\n")
CROSS_FAIL = "\n".join([WAD_LINE, "timed 4226 gametics in 116 realtics (1275.387939 fps)",
                        "engine exit code: 255", "FAIL: 4226 gametics != expected 4227"]) + "\n"


class FakeRunner:
    """Stands in for run_command: canned (exit, output) per command, and a
    queue of `git status --short` outputs (before the run, after the run)."""

    def __init__(self, suite=(0, None), cross=(0, None), status=("", ""), build=(0, "")):
        self.answers = {"suite": (suite[0], suite_pass() if suite[1] is None else suite[1]),
                        "cross": (cross[0], cross_pass() if cross[1] is None else cross[1]),
                        "build": build}
        self.status = list(status)
        self.calls = []

    def __call__(self, argv, cwd):
        self.calls.append(argv)
        if argv == vd.GIT_STATUS:
            return 0, self.status.pop(0)
        key = {tuple(vd.SUITE): "suite", tuple(vd.CROSS_CHECK): "cross", tuple(vd.BUILD): "build"}[tuple(argv)]
        return self.answers[key]


@pytest.fixture
def repo(tmp_path):
    """A repository tree with the real manifest and a binary newer than every source."""
    (tmp_path / "tests/demos/heretic").mkdir(parents=True)
    (tmp_path / vd.MANIFEST).write_text(MANIFEST_TEXT, encoding="utf-8")
    (tmp_path / "src/heretic").mkdir(parents=True)
    for rel, mtime in (("src/heretic/g_game.c", 1000), ("src/i_main.c", 1000), ("src/doomtype.h", 1000),
                       ("src/chocolate-heretic", 2000)):
        (tmp_path / rel).write_text("x", encoding="utf-8")
        os.utime(tmp_path / rel, (mtime, mtime))
    return tmp_path


REQUEST = {"request": "Check the demos.", "build_if_stale": True}


# --- Normal: the logged PASS runs ------------------------------------------

def test_logged_pass_run_is_pass(repo):
    """Input: suite and cross-check output from Iteration Log Run 2 / Task 8.
    Expected: PASS, exit 0, every line quoted. Protects against a converted
    check that rejects a build the agent correctly passed."""
    report = vd.verify(repo, REQUEST, FakeRunner())
    d, e = report["decision"], report["evidence"]
    assert d["verdict"] == "PASS" and vd.EXIT[d["verdict"]] == 0
    assert d["demo_results"] == ["PASS: demo1 4227 gametics, trace matches", "PASS: 1 demo(s)"]
    assert d["cross_check_result"] == ["PASS: 4227 gametics == expected 4227"]
    assert e["iwad_sha256"] == [WAD_LINE] and e["trace_sha256"] == [TRACE_LINE]
    assert e["git_status_after"] == ["(empty)"] and report["unexpected"] == ["none"]


def test_decision_is_identical_across_three_runs_despite_timing_noise(repo):
    """Input: three PASS runs whose timed lines differ only in realtics (116,
    130, 132, as logged). Expected: byte-identical decision objects. Protects
    the predictability claim in ADR-001: timing noise must never change a
    verdict, and the verbatim timed line must still be kept."""
    runs = [vd.verify(repo, REQUEST, FakeRunner(suite=(0, suite_pass(rt)))) for rt in (116, 130, 132)]
    decisions = [json.dumps(r["decision"], sort_keys=True) for r in runs]
    assert decisions[0] == decisions[1] == decisions[2]
    assert [r["evidence"]["timed"][0] for r in runs] == [timed(116), timed(130), timed(132)]


# --- Failure: mismatch, disagreement, setup error ---------------------------

def test_trace_mismatch_is_fail_with_first_difference(repo):
    """Input: Task 7 failure-path output (edited trace), suite exit 1.
    Expected: FAIL, exit 1, the FAIL: line and the first differing gametic
    quoted. Protects against a desync being reported as anything but FAIL,
    and against losing the tic and field a fix needs."""
    d = vd.verify(repo, REQUEST, FakeRunner(suite=(1, SUITE_TRACE_FAIL), cross=(0, None)))["decision"]
    assert d["verdict"] == "FAIL"
    assert "gametic 100: p0.armor expected 50 got 0" in d["reason"]
    assert "FAIL: demo1 trace differs" in d["reason"] and "disagree" in d["reason"]


def test_cross_check_disagreeing_with_a_passing_suite_is_fail(repo):
    """Input: suite PASS, cross-check 4226 != 4227 (exit 1). Expected: FAIL
    saying the two disagree. Protects the agent's rule that the two scripts
    must agree, so one broken script cannot pass a bad build."""
    d = vd.verify(repo, REQUEST, FakeRunner(cross=(1, CROSS_FAIL)))["decision"]
    assert d["verdict"] == "FAIL" and "disagree" in d["reason"]
    assert d["cross_check_result"] == ["FAIL: 4226 gametics != expected 4227"]


def test_suite_setup_error_is_blocked_not_fail(repo):
    """Input: Task 7 bad-sha256 output, suite exit 2. Expected: BLOCKED,
    exit 2, the ERROR: line quoted. Protects against a broken setup being
    blamed on the code under test (the agent's BLOCKED rule)."""
    d = vd.verify(repo, REQUEST, FakeRunner(suite=(2, SUITE_SETUP_ERROR)))["decision"]
    assert d["verdict"] == "BLOCKED" and vd.EXIT["BLOCKED"] == 2
    assert "ERROR: tests/demos/heretic/golden/demo1.tics sha256 mismatch" in d["reason"]


# --- Named edge cases the agent handled by judgment --------------------------

def test_engine_exit_255_is_normal(repo):
    """Edge case 1 (decision-006; Runs 1 and 2, Judgment 4/4). Input: PASS
    output that includes 'engine exit code: 255'. Expected: PASS, with the
    fixed meaning in the report. Protects against every run failing because
    the engine's normal demo-end exit looks like an error."""
    report = vd.verify(repo, REQUEST, FakeRunner())
    assert report["decision"]["verdict"] == "PASS"
    assert report["evidence"]["engine_exit"] == ["engine exit code: 255"]
    assert "normal" in report["evidence"]["engine_exit_meaning"]


def test_newer_binary_for_another_game_does_not_rebuild(repo):
    """Edge case 2 (Run 1, Unexpected). Input: src/chocolate-hexen newer than
    src/chocolate-heretic. Expected: no rebuild. Protects against a slow,
    tree-touching rebuild on every run just because another game was built."""
    hexen = repo / "src/chocolate-hexen"
    hexen.write_text("x", encoding="utf-8")
    os.utime(hexen, (3000, 3000))
    runner = FakeRunner()
    report = vd.verify(repo, REQUEST, runner)
    assert vd.rebuild_reason(repo) is None and vd.BUILD not in runner.calls
    assert report["decision"]["rebuilt"] is False


def test_newer_heretic_source_does_rebuild(repo):
    """Counterpart to edge case 2. Input: src/heretic/p_inter.c newer than the
    binary. Expected: one rebuild before the suite, reported as unexpected.
    Protects against verifying a stale binary after a source change."""
    src = repo / "src/heretic/p_inter.c"
    src.write_text("x", encoding="utf-8")
    os.utime(src, (3000, 3000))
    runner = FakeRunner()
    report = vd.verify(repo, REQUEST, runner)
    assert runner.calls.index(vd.BUILD) < runner.calls.index(vd.SUITE)
    assert report["decision"]["rebuilt"] is True and report["decision"]["verdict"] == "PASS"
    assert "src/heretic/p_inter.c is newer" in report["unexpected"][0]


def test_tree_dirty_before_the_check_is_reported_not_blamed(repo):
    """Edge case 3 (Run 2: the uncommitted log edit). Input: the same
    ' M docs/agents/demo-verifier-iteration-log.md' before and after.
    Expected: PASS, listed as pre-existing. Protects against failing every
    check run on a working branch with uncommitted edits."""
    line = " M docs/agents/demo-verifier-iteration-log.md"
    report = vd.verify(repo, REQUEST, FakeRunner(status=(line + "\n", line + "\n")))
    d = report["decision"]
    assert d["verdict"] == "PASS"
    assert d["git_status_pre_existing"] == [line] and d["git_status_changed_by_check"] == []
    assert "not caused by it" in report["unexpected"][0]


def test_git_warnings_are_not_tree_changes(repo):
    """Input: a git warning line after the run (as on a read-only mount).
    Expected: PASS. Protects against a false FAIL from text that is not a
    status entry."""
    runner = FakeRunner(status=("", "warning: unable to refresh index: Read-only file system\n"))
    assert vd.verify(repo, REQUEST, runner)["decision"]["verdict"] == "PASS"


def test_change_made_during_the_check_is_fail(repo):
    """Input: the tree is clean before and the manifest is modified after.
    Expected: FAIL naming the path. Protects the scope rule: a verifier that
    changes what it verifies can no longer be trusted (coding standard 4)."""
    d = vd.verify(repo, REQUEST, FakeRunner(status=("", " M tests/demos/heretic/manifest\n")))["decision"]
    assert d["verdict"] == "FAIL" and "tests/demos/heretic/manifest" in d["reason"]


# --- Known limitation: output the rules do not cover -------------------------

@pytest.mark.parametrize("suite", [
    (0, WAD_LINE + "\n" + timed() + "\nengine exit code: 255\n"),     # exit 0, no PASS lines
    (124, "timeout: the monitored command dumped core\n"),            # an exit the suite never uses
])
def test_unrecognized_suite_output_is_blocked_not_guessed(repo, suite):
    """Known limitation: the agent could reason about output nobody wrote a
    rule for; the script cannot. Expected: BLOCKED with the lines quoted and
    'cause not guessed'. Protects against a silent PASS (or an invented cause)
    on an input class the rules do not cover."""
    report = vd.verify(repo, REQUEST, FakeRunner(suite=suite))
    assert report["decision"]["verdict"] == "BLOCKED"
    assert "cause not guessed" in report["decision"]["reason"]
    assert report["commands"]["suite"]["lines"] == suite[1].splitlines()


def test_every_manifest_demo_needs_its_pass_line(repo):
    """Input: a manifest with demo1 and demo2, suite output for demo1 only.
    Expected: BLOCKED naming demo2. Protects against a demo added to the
    manifest being counted as verified without ever running."""
    (repo / vd.MANIFEST).write_text(MANIFEST_TEXT + "demo2 1000 " + "a" * 64 + " " + "b" * 40 + "\n",
                                    encoding="utf-8")
    d = vd.verify(repo, REQUEST, FakeRunner())["decision"]
    assert d["verdict"] == "BLOCKED" and "demo2" in d["reason"]


def test_failed_or_disallowed_rebuild_is_blocked(repo):
    """Input: a stale binary, and either a failing build or build_if_stale
    false. Expected: BLOCKED before any demo runs. Protects against testing
    a binary that does not match the source."""
    os.utime(repo / "src/chocolate-heretic", (500, 500))
    runner = FakeRunner(build=(2, "make: *** [all] Error 2\n"))
    assert vd.verify(repo, REQUEST, runner)["decision"]["verdict"] == "BLOCKED"
    assert vd.SUITE not in runner.calls
    runner = FakeRunner()
    d = vd.verify(repo, {"request": "Check the demos.", "build_if_stale": False}, runner)["decision"]
    assert d["verdict"] == "BLOCKED" and vd.BUILD not in runner.calls


# --- Contract: named files, exit codes, no model -----------------------------

def _shell_script(path, body):
    path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    path.chmod(0o755)


@pytest.mark.skipif(shutil.which("git") is None or shutil.which("bash") is None, reason="needs git and bash")
@pytest.mark.parametrize("suite_exit, expected", [(0, 0), (1, 1), (2, 2)])
def test_cli_reads_and_writes_only_the_named_files(repo, tmp_path_factory, suite_exit, expected):
    """End to end through subprocess with stand-in scripts in a real git
    repository. Expected: exit 0/1/2 matching PASS/FAIL/BLOCKED, the report
    only in --output, one verdict line on stdout, and the report file inside
    the repository not counted as a change. Protects the drop-in contract the
    orchestrator and CI rely on."""
    (repo / "scripts").mkdir()
    outputs = {0: suite_pass(), 1: SUITE_TRACE_FAIL, 2: SUITE_SETUP_ERROR}
    _shell_script(repo / "scripts/demo-suite.sh",
                  f"cat <<'OUT'\n{outputs[suite_exit]}OUT\nexit {suite_exit}\n")
    _shell_script(repo / "scripts/demo1-check.sh", f"cat <<'OUT'\n{cross_pass()}OUT\nexit 0\n")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run(git + ["init", "-q"], cwd=repo, check=True)
    subprocess.run(git + ["add", "-A"], cwd=repo, check=True)
    subprocess.run(git + ["commit", "-q", "-m", "fixture"], cwd=repo, check=True)
    request = tmp_path_factory.mktemp("in") / "request.json"
    request.write_text(json.dumps(REQUEST), encoding="utf-8")
    out = repo / "demo-verify.json"
    proc = subprocess.run([sys.executable, str(SCRIPT), "--input", str(request), "--output", str(out),
                           "--repo", str(repo)], capture_output=True, text=True)
    assert proc.returncode == expected, proc.stdout + proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["decision"]["verdict"] == {0: "PASS", 1: "FAIL", 2: "BLOCKED"}[expected]
    assert len(proc.stdout.strip().splitlines()) == 1 and proc.stdout.startswith(report["decision"]["verdict"])
    if expected == 0:
        assert report["decision"]["git_status_changed_by_check"] == []


def test_script_calls_no_language_model():
    """The script imports only the standard library modules below and names
    no model API. Protects the ADR-001 contract: no inference, no API key,
    so the CI step needs no secret."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert imported <= {"__future__", "argparse", "json", "os", "re", "subprocess", "sys", "pathlib", "typing"}
    text = SCRIPT.read_text(encoding="utf-8").lower()
    for word in ("openrouter", "anthropic", "api_key", "claude --", "claude -p", "http://", "https://"):
        assert word not in text, f"{SCRIPT.name} mentions {word!r}"
