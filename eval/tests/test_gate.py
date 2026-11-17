"""Gate tests: the judge is never called on a broken run.

Run from the repository root:  python3 -m pytest eval/tests -q
The judge is replaced here, and only here, by a stub. The real path in
eval/test_rubric_suite.py always calls `claude -p`.
"""

import json
import os
import sys

import pytest

EVAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, EVAL)
import test_deterministic as det  # noqa: E402
import test_rubric_suite as trs  # noqa: E402

FIX = os.path.join(EVAL, "tests", "fixtures")
RUBRIC = trs.load_rubric(os.path.join(EVAL, "rubric.json"))
BROKEN = {"malformed": "run_artifacts_valid",
          "missing-tester": "run_artifacts_valid",
          "golden-changed": "golden_unchanged"}


@pytest.fixture
def judge_forbidden(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(trs, "call_judge", lambda prompt: calls.append(prompt) or "{}")
    monkeypatch.setattr(trs, "results_dir", lambda run_dir, fixture: str(tmp_path))
    monkeypatch.setattr(trs, "load_rubric", lambda path=None: RUBRIC)
    return calls


def stub_reply(score):
    def judge(prompt):
        name = prompt.split("DIMENSION: ", 1)[1].split("\n", 1)[0]
        return json.dumps({"dimension": name, "score": score, "justification": "stub: `PASS: 1 demo(s)`"})
    return judge


@pytest.mark.parametrize("name,failing_check", BROKEN.items())
def test_deterministic_names_the_failure(name, failing_check):
    results = det.collect_results(os.path.join(FIX, name))
    failed = [r["check"] for r in results if r["status"] == det.FAIL]
    assert failed == [failing_check]


@pytest.mark.parametrize("name", BROKEN)
def test_gate_blocks_broken_runs(name, judge_forbidden):
    assert trs.run_rubric_suite(os.path.join(FIX, name), fixture=True) == 1
    with pytest.raises(trs.GateClosed):  # the inner gate holds even if a caller skips the outer one
        trs.collect_rubric_results(os.path.join(FIX, name), RUBRIC)
    assert judge_forbidden == [], "the judge was called on a broken run"


def test_valid_fixture_reaches_judge(monkeypatch, tmp_path):
    monkeypatch.setattr(trs, "call_judge", stub_reply(3))
    monkeypatch.setattr(trs, "results_dir", lambda run_dir, fixture: str(tmp_path))
    monkeypatch.setattr(trs, "load_rubric", lambda path=None: RUBRIC)
    assert trs.run_rubric_suite(os.path.join(FIX, "valid"), fixture=True) == 0
    saved = json.load(open(tmp_path / "rubric-results.json"))
    names = [r["check"] for r in saved["results"]]
    assert names == [f"rubric:{d['name']}" for d in RUBRIC["dimensions"]] + ["rubric:aggregate"]
    assert all(r["score"] == 3 and r["justification"] for r in saved["results"][:-1])
    assert saved["results"][-1]["score"] == 15 and saved["fixture"] is True


@pytest.mark.parametrize("reply", ['{"score": 7}', "Looks good to me.", '{"score": "3"}', '{"score": true}'])
def test_bad_judge_reply_is_a_fail_not_a_crash(monkeypatch, reply):
    monkeypatch.setattr(trs, "call_judge", lambda prompt: reply)
    results = trs.collect_rubric_results(os.path.join(FIX, "valid"), RUBRIC)
    assert all(r["status"] == "FAIL" for r in results)
    assert all(r["score"] is None for r in results[:-1])


def test_judge_command_uses_stdin_and_default_model(monkeypatch):
    seen = {}

    class Done:
        returncode, stderr = 0, ""
        stdout = json.dumps({"result": "{}", "is_error": False})

    def fake_run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return Done()

    monkeypatch.setattr(trs.subprocess, "run", fake_run)
    trs.call_judge("x" * 200000)
    assert seen["input"] == "x" * 200000 and "x" * 10 not in " ".join(seen["cmd"])
    assert "--model" not in seen["cmd"] and "--bare" not in seen["cmd"]
    assert seen["cwd"] == trs.JUDGE_CWD
