"""Rubric-scored checks for GIMPL orchestration runs (AE 3.3).

Run from the repository root (/workspace in the container):
    python3 eval/test_rubric_suite.py .eval-artifacts/runs/<dev|holdout>/<RUN-ID>
    python3 eval/test_rubric_suite.py --fixture eval/tests/fixtures/valid

The judge is Claude Code in print mode on the container's existing login
(no API key), with the session's default model (George, 2026-11-16).

Gate: the judge is called only if every deterministic check is PASS or
NOT EXERCISED and the run's artifacts load. This is enforced in
collect_rubric_results() itself, so no caller can reach the judge past a
failed floor.

--fixture scores a hand-made run dir (for the demo when no real run is
available). Results go to .eval-artifacts/fixture-scores/<name>/ so the
committed fixture is never changed, and they are marked "fixture": true.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_deterministic import (FAIL, block_text, changed_paths, collect_results,  # noqa: E402
                                load_run, run_all_checks)

RUBRIC_PATH = os.environ.get("GIMPL_RUBRIC", "eval/rubric.json")
JUDGE_CWD = "/tmp/gimpl-judge"     # outside the repo: no CLAUDE.md, hooks or .mcp.json
JUDGE_TIMEOUT = 300
VIEW_CAP = 60000                   # characters of run evidence shown to the judge
JUDGE_CMD = ["claude", "-p", "--output-format", "json",
             "--tools", "",                   # no built-in tools
             "--disallowedTools", "mcp__*",   # no MCP tools
             "--strict-mcp-config",           # ignore every .mcp.json
             "--setting-sources", "user",     # skip project settings and hooks
             "--no-session-persistence"]      # keep judge sessions out of projects/
# No --model: the judge uses the session default model (George's decision).
# No --bare: bare mode ignores the OAuth login and needs an API key.


class GateClosed(Exception):
    """The deterministic floor did not pass; the judge must not run."""


class JudgeError(Exception):
    pass


def load_rubric(path=None):
    with open(path or RUBRIC_PATH) as f:
        return json.load(f)


def call_judge(prompt):
    """One judge call. The prompt goes on stdin: a team transcript is far
    larger than Linux's 128 KB limit on one command-line argument."""
    os.makedirs(JUDGE_CWD, exist_ok=True)
    try:
        done = subprocess.run(JUDGE_CMD, input=prompt, capture_output=True, text=True,
                              timeout=JUDGE_TIMEOUT, cwd=JUDGE_CWD)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise JudgeError(f"judge did not run: {e}")
    if done.returncode != 0:
        raise JudgeError(f"judge exit {done.returncode}: {done.stderr.strip()[:300]}")
    try:
        env = json.loads(done.stdout)
    except json.JSONDecodeError:
        raise JudgeError(f"judge envelope is not JSON: {done.stdout[:200]}")
    if env.get("is_error") or "result" not in env:
        raise JudgeError(f"judge reported an error: {str(env)[:300]}")
    return env["result"]


def parse_score(reply):
    """First balanced JSON object in the reply."""
    start = reply.find("{")
    if start == -1:
        raise ValueError("no JSON object in judge reply")
    depth = 0
    for i, ch in enumerate(reply[start:], start):
        depth += ch == "{"
        depth -= ch == "}"
        if depth == 0:
            return json.loads(reply[start:i + 1])
    raise ValueError("unterminated JSON object in judge reply")


def judge_view(run):
    """A short, readable view of the run for the judge, not the raw JSONL."""
    m = run["meta"]
    parts = [f"TASK {m['task_id']} ({m['kind']} run {m['run_id']})",
             f"EXPECTED PATH: {' -> '.join(m['expected_path']) or 'main session only'}"]
    if m.get("task_text"):
        parts.append("TASK TEXT:\n" + m["task_text"])
    first_user = next((block_text(r["message"]["content"]) for r in run["session"]
                       if r.get("type") == "user" and isinstance((r.get("message") or {}).get("content"), str)), "")
    if first_user:
        parts.append("OPERATOR'S FIRST MESSAGE:\n" + first_user[:3000])
    for n, inv in enumerate(run["invocations"], 1):
        parts.append(f"--- STEP {n}: {inv['role']} ---\nHANDOFF (orchestrator -> {inv['role']}):\n"
                     f"{inv['prompt'][:4000]}")
        for c in inv["calls"]:
            if c["tool"] == "Bash":
                parts.append(f"[{inv['role']} ran] {c['input'].get('command', '')[:300]}\n"
                             f"[output] {block_text(c['result'])[-1500:]}")
            elif c["tool"] == "mcp__retrieval__retrieve":
                parts.append(f"[{inv['role']} retrieve] {json.dumps(c['input'])[:400]}\n"
                             f"[results] {block_text(c['result'])[:2000]}")
            elif c["tool"] == "mcp__storage__write_entry":
                parts.append(f"[{inv['role']} write_entry] {json.dumps(c['input'])[:1500]}")
        parts.append(f"REPORT ({inv['role']}):\n{inv['output'][:6000]}")
    for path, text in run["summaries"].items():
        parts.append(f"--- RUN SUMMARY {os.path.basename(path)} ---\n{text[:8000]}")
    parts.append("FILES CHANGED IN THE RUN: " + (", ".join(changed_paths(run)) or "none"))
    view = "\n\n".join(parts)
    if len(view) > VIEW_CAP:
        view = view[:VIEW_CAP] + f"\n[view cut at {VIEW_CAP} characters]"
    return view


def build_judge_prompt(dim, view):
    return (
        "You are scoring one run of a multi-agent software workflow (GIMPL, a C-to-Rust "
        "port verified by demo replays) on ONE quality dimension. Use only the run "
        "evidence below. Pick the level from 1 to 4 whose description and example fit "
        "best. Return only a JSON object with the fields \"dimension\", \"score\" (an "
        "integer from 1 to 4) and \"justification\" (one or two sentences that quote a "
        "short piece of the evidence). Return nothing else.\n\n"
        f"DIMENSION: {dim['name']}\nWHAT IT MEASURES: {dim['description']}\n"
        f"LEVELS:\n{json.dumps(dim['levels'], indent=2)}\n"
        f"EXAMPLES:\n{json.dumps(dim.get('examples', {}), indent=2)}\n\n"
        f"RUN EVIDENCE:\n{view}\n")


def score_dimension(dim, view):
    """A bad or failed judge reply is a FAIL with score null, never a crash."""
    raw = None
    try:
        raw = call_judge(build_judge_prompt(dim, view))
        obj = parse_score(raw)
        score = obj.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 4:
            raise ValueError(f"score {score!r} is not an integer from 1 to 4")
        if obj.get("dimension") not in (None, dim["name"]):
            raise ValueError(f"reply is for dimension {obj.get('dimension')!r}")
        just = str(obj.get("justification", "")).strip()
        passed = score >= dim["pass_threshold"]
        return {"check": f"rubric:{dim['name']}", "failure_mode": "quality (rubric)",
                "status": "PASS" if passed else FAIL, "passed": passed, "score": score,
                "level": dim["levels"][str(score)], "justification": just, "raw_reply": raw,
                "message": f"scored {score}/4 (needs {dim['pass_threshold']}). {just}"}
    except (JudgeError, ValueError, TypeError, json.JSONDecodeError) as e:
        return {"check": f"rubric:{dim['name']}", "failure_mode": "quality (rubric)",
                "status": FAIL, "passed": False, "score": None, "justification": "",
                "raw_reply": raw, "message": f"no valid score: {e}"}


def aggregate(dim_results, threshold):
    scores = [r["score"] for r in dim_results]
    total = sum(s for s in scores if s is not None)
    ok = None not in scores and total >= threshold and all(r["passed"] for r in dim_results)
    why = "" if ok else (" A dimension is unscored." if None in scores else
                         " Below threshold or a dimension under its floor.")
    return {"check": "rubric:aggregate", "failure_mode": "quality (rubric)",
            "status": "PASS" if ok else FAIL, "passed": ok, "score": total,
            "message": f"total {total}/{4 * len(dim_results)} (needs {threshold}).{why}"}


def collect_rubric_results(run_dir, rubric=None):
    """The gate lives here: anything but PASS / NOT EXERCISED in the
    deterministic results (including an unreadable run) closes it."""
    det = collect_results(run_dir)
    failed = [r["check"] for r in det if r["status"] == FAIL]
    if failed or not det or det[0]["check"] != "run_artifacts_valid":
        raise GateClosed(f"deterministic check(s) failed: {', '.join(failed)}")
    run = load_run(run_dir)
    rubric = rubric or load_rubric()
    view = judge_view(run)
    dims = [score_dimension(d, view) for d in rubric["dimensions"]]
    return dims + [aggregate(dims, rubric["overall_pass_threshold"])]


def results_dir(run_dir, fixture):
    if not fixture:
        return run_dir
    out = os.path.join(".eval-artifacts", "fixture-scores", os.path.basename(run_dir.rstrip("/")))
    os.makedirs(out, exist_ok=True)
    return out


def run_rubric_suite(run_dir, fixture=False):
    if not fixture and ".eval-artifacts" + os.sep + "runs" not in os.path.abspath(run_dir):
        print("Not a run dir under .eval-artifacts/runs/. Use --fixture for a fixture.")
        return 2
    if run_all_checks(run_dir) != 0:
        print("\nDeterministic checks failed; rubric not run (no judge call made).")
        return 1
    try:
        results = collect_rubric_results(run_dir)
    except GateClosed as e:
        print(f"\nGate closed: {e}; rubric not run.")
        return 1
    print("\nRubric suite (one judge call per dimension, session default model):\n")
    for r in results:
        print(f"[{r['status']}] {r['check']}: {r['message']}")
    ok = all(r["passed"] for r in results)
    out = os.path.join(results_dir(run_dir, fixture), "rubric-results.json")
    with open(out, "w") as f:
        json.dump({"run_dir": run_dir, "fixture": fixture, "judge": " ".join(JUDGE_CMD),
                   "judge_model": "session default", "view_cap_chars": VIEW_CAP,
                   "scored_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "passed": ok, "results": results}, f, indent=2)
    print(f"\n{sum(r['passed'] for r in results)}/{len(results)} rubric checks passed. Saved {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    fixture = "--fixture" in args
    args = [a for a in args if a != "--fixture"]
    if len(args) != 1:
        print("usage: test_rubric_suite.py <run-dir>  |  --fixture <fixture-dir>")
        sys.exit(2)
    sys.exit(run_rubric_suite(args[0], fixture))
