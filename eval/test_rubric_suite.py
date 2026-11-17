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
                                final_text, load_run, run_all_checks)

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


READ_TOOLS = {"Read", "mcp__coursetools__file_read"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "mcp__coursetools__file_write"}


def clip(text, limit, keep="head"):
    """Shorten text for the judge and SAY so: an explicit marker keeps an
    omission from reading as missing work (3.3 grader feedback)."""
    text = text or ""
    if len(text) <= limit:
        return text
    cut = len(text) - limit
    if keep == "tail":
        return f"[truncated {cut} chars] " + text[-limit:]
    return text[:limit] + f" [truncated {cut} chars]"


def call_lines(who, c):
    """Judge-view lines for one tool call: commands and their output, file
    reads and what came back, written content, retrieve and write_entry."""
    i, tool = c["input"], c["tool"]
    if tool == "Bash":
        return [f"[{who} ran] {clip(i.get('command', ''), 300)}\n"
                f"[output] {clip(block_text(c['result']), 1500, keep='tail')}"]
    if tool in READ_TOOLS:
        path = i.get("file_path") or i.get("path") or ""
        return [f"[{who} read] {path}\n[file content] {clip(block_text(c['result']), 1500)}"]
    if tool in WRITE_TOOLS:
        path = i.get("file_path") or i.get("path") or ""
        if tool == "Edit":
            body = f"[old] {clip(i.get('old_string', ''), 600)}\n[new] {clip(i.get('new_string', ''), 1500)}"
        elif tool == "MultiEdit":
            body = "\n".join(f"[new] {clip(e.get('new_string', ''), 600)}" for e in i.get("edits") or []
                             if isinstance(e, dict))
        else:
            body = f"[content written] {clip(i.get('content', ''), 3000)}"
        return [f"[{who} wrote] {path}{' (ERROR: not written)' if c['is_error'] else ''}\n{body}"]
    if tool == "mcp__retrieval__retrieve":
        return [f"[{who} retrieve] {clip(json.dumps(i), 400)}\n"
                f"[results] {clip(block_text(c['result']), 2000)}"]
    if tool == "mcp__storage__write_entry":
        return [f"[{who} write_entry] {clip(json.dumps(i), 1500)}"]
    return []


def fair_shares(sizes, room):
    """Split `room` characters across sections: small sections keep their
    full size, the rest share what is left equally (water-filling)."""
    shares, left, todo = [0] * len(sizes), room, sorted(range(len(sizes)), key=lambda k: sizes[k])
    while todo:
        each = left // len(todo)
        k = todo[0]
        if sizes[k] <= each:
            shares[k] = sizes[k]
            left -= sizes[k]
            todo.pop(0)
        else:
            for k in todo:
                shares[k] = each
            break
    return shares


def fit_section(head, calls, report, share):
    """One section in at most `share` chars: tool-call evidence is cut first
    (with a marker), then the report; the header always stays."""
    body = "\n".join(calls)
    full = "\n".join(x for x in (head, body, report) if x)
    if len(full) <= share:
        return full
    over = len(full) - share
    if body and over <= len(body):
        body = clip(body, max(len(body) - over - 40, 0))
    else:
        body = f"[tool-call evidence truncated {len(body)} chars]" if body else ""
        report = clip(report, max(share - len(head) - len(body) - 40, 0))
    return "\n".join(x for x in (head, body, report) if x)


def judge_view(run):
    """A short, readable view of the run for the judge, not the raw JSONL.
    Harness v3 (3.3 grader feedback): adds the orchestrator's own reads and
    its final answer (the whole answer on a no-subagent path such as HO-06),
    every role's file reads and written content, and marks every cut. When
    the run is longer than VIEW_CAP, every step keeps a fair share (tool-call
    evidence is cut before reports), so late steps are never dropped."""
    m = run["meta"]
    parts = [f"TASK {m['task_id']} ({m['kind']} run {m['run_id']})",
             f"EXPECTED PATH: {' -> '.join(m['expected_path']) or 'main session only'}"]
    if m.get("task_text"):
        parts.append("TASK TEXT:\n" + m["task_text"])
    first_user = next((block_text(r["message"]["content"]) for r in run["session"]
                       if r.get("type") == "user" and isinstance((r.get("message") or {}).get("content"), str)), "")
    if first_user:
        parts.append("OPERATOR'S FIRST MESSAGE:\n" + clip(first_user, 3000))
    sections = []   # (header, call lines, report)
    main = [line for c in run["main_calls"] for line in call_lines("orchestrator", c)]
    if main:
        sections.append(("--- ORCHESTRATOR (main session) TOOL CALLS ---", main, ""))
    for n, inv in enumerate(run["invocations"], 1):
        sections.append((f"--- STEP {n}: {inv['role']} ---\nHANDOFF (orchestrator -> {inv['role']}):\n"
                         f"{clip(inv['prompt'], 4000)}",
                         [line for c in inv["calls"] for line in call_lines(inv["role"], c)],
                         f"REPORT ({inv['role']}):\n{clip(inv['output'], 6000)}"))
    # The outcome goes last and is never squeezed out by a long run.
    tail = []
    for path, text in run["summaries"].items():
        tail.append(f"--- RUN SUMMARY {os.path.basename(path)} ---\n{clip(text, 8000)}")
    tail.append("--- ORCHESTRATOR FINAL ANSWER ---\n" + (clip(final_text(run["session"]), 6000) or "(none)"))
    tail.append("FILES CHANGED IN THE RUN: " + (", ".join(changed_paths(run)) or "none"))
    fixed = "\n\n".join(parts + tail)
    texts = [fit_section(h, c, r, 10 ** 9) for h, c, r in sections]
    room = VIEW_CAP - len(fixed) - 2 * (len(sections) + 1) - 200
    if sum(len(t) for t in texts) > room:
        shares = fair_shares([len(t) for t in texts], max(room, 0))
        texts = [fit_section(h, c, r, sh) for (h, c, r), sh in zip(sections, shares)]
        parts.append(f"[view truncated to fit the {VIEW_CAP}-char cap: each step below keeps a fair "
                     "share; cut text is marked]")
    view = "\n\n".join(parts + texts + tail)
    if len(view) > VIEW_CAP:  # only if the fixed parts alone exceed the cap
        view = view[:VIEW_CAP] + f"\n[view cut at {VIEW_CAP} characters]"
    return view


def build_judge_prompt(dim, view):
    return (
        "You are scoring one run of a multi-agent software workflow (GIMPL, a C-to-Rust "
        "port verified by demo replays) on ONE quality dimension. Use only the run "
        "evidence below. Pick the level from 1 to 4 whose description and example fit "
        "best. Return only a JSON object with the fields \"dimension\", \"score\" (an "
        "integer from 1 to 4) and \"justification\" (one or two sentences that quote a "
        "short piece of the evidence). Return nothing else. Evidence marked "
        "\"[truncated N chars]\" or \"[view truncated ...]\" was shortened for length by the "
        "harness; do not treat the omitted text as missing work.\n\n"
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
        just = obj.get("justification")
        if not isinstance(just, str) or not just.strip():
            raise ValueError("empty or missing justification (a score must quote its evidence)")
        just = just.strip()
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
