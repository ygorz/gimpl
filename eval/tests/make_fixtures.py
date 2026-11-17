"""Writes the hand-made gate fixtures under eval/tests/fixtures/.

Run from the repository root:  python3 eval/tests/make_fixtures.py
The fixtures are committed; this script only shows how they were made.
They imitate a DEV-01 run (Task 7 replayed) in Claude Code's JSONL format.
Field names follow Claude Code transcripts as of 2026; check them against
the real DEV-01 run before trusting the fixture.

valid/            passes every deterministic check
malformed/        session.jsonl cut off mid-line
missing-tester/   the tester transcripts are gone
golden-changed/   demo1.tics sha256 differs after the run
"""

import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures")
SESSION = "11111111-2222-4333-8444-555555555555"
DEMO1 = "537e8a1fd73967c0099d1ee55c0586e353d5240d27dd3a41dfa15ac3757d2f30"
MANIFEST_SHA = "0f2c4d0b5b7f3e7e1a9d6c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a39"
LESSON_ID = "00000000-0000-4000-8000-0000000000aa"
NEW_DOC = "docs/smoke-tests/demo-suite-failure-paths.md"
SUMMARY = "docs/runs/dev01-run-1.md"


class Clock:
    def __init__(self):
        self.s = 0

    def __call__(self, step=4):
        self.s += step
        return f"2026-11-17T17:{self.s // 60:02d}:{self.s % 60:02d}.000Z"


def lines(rows):
    return "".join(json.dumps(r) + "\n" for r in rows)


def text_msg(kind, text, ts, msg_id=None, usage=None):
    msg = {"role": kind, "content": text if kind == "user" else [{"type": "text", "text": text}]}
    if msg_id:
        msg["id"], msg["usage"] = msg_id, usage
    return {"type": kind, "timestamp": ts, "sessionId": SESSION, "message": msg}


def use(tool_id, name, inp, ts, msg_id, side=False):
    return {"type": "assistant", "timestamp": ts, "sessionId": SESSION, "isSidechain": side,
            "message": {"role": "assistant", "id": msg_id,
                        "usage": {"input_tokens": 200, "output_tokens": 300,
                                  "cache_creation_input_tokens": 1500, "cache_read_input_tokens": 9000},
                        "content": [{"type": "tool_use", "id": tool_id, "name": name, "input": inp}]}}


def res(tool_id, content, ts, side=False, extra=None):
    row = {"type": "user", "timestamp": ts, "sessionId": SESSION, "isSidechain": side,
           "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id,
                                                     "content": content}]}}
    row.update(extra or {})
    return row


def mcp_text(obj):
    return [{"type": "text", "text": json.dumps(obj)}]


LESSON = {"source_document": "lesson-demo-suite-exit-codes.md", "chunk_index": 0,
          "excerpt": "demo-suite.sh exits 1 on a trace mismatch and 2 on setup errors.",
          "classification": "internal", "similarity_score": 0.71, "retrieval_method": "vector"}

REPORTS = {
    "planner": f"""## Plan
1. Tester runs the suite before any change (baseline).
2. Implementer writes {NEW_DOC} with the two required failure paths.
3. Tester reruns the suite and both failure paths, then restores.
4. Fence-reviewer checks scope.

## Files
- {NEW_DOC}

## Done criteria
- demo-suite.sh prints `PASS: demo1 4227 gametics, trace matches`, exit 0, before and after.

## Open questions
- None.

## Citations
- lesson-demo-suite-exit-codes.md#0 (vector, score 0.71)
""",
    "tester": """## Verdict
PASS

## Evidence
- `./scripts/demo-suite.sh; echo "suite exit: $?"`
- `timed 4227 gametics`
- `PASS: demo1 4227 gametics, trace matches`
- `PASS: 1 demo(s)`

## git status
Clean apart from the planned file.
""",
    "implementer": f"""## Files changed
- {NEW_DOC}

## Notes
Two required failure paths, optional O1-O5 marked optional.

## Not done
- Nothing.

## Lesson stored
- entry_id {LESSON_ID} (proj-lessons, internal)
""",
    "fence-reviewer": f"""## Verdict
APPROVE

## Findings
- Only {NEW_DOC} and the run summary changed; nothing under tests/demos/heretic/golden/.

## Lessons checked
- lesson-demo-suite-exit-codes.md#0 (vector, score 0.71): followed.
""",
}

SUITE_OUT = ("IWAD OK: /workspace/wads/blasphem.wad\ntrace OK: tests/demos/heretic/golden/demo1.tics\n"
             "timed 4227 gametics\nengine exit code: 0\nPASS: demo1 4227 gametics, trace matches\n"
             "PASS: 1 demo(s)\nsuite exit: 0")


def subagent(agent_id, role, prompt, clock):
    """One subagent transcript: its prompt, its tool calls, its report."""
    rows = [text_msg("user", prompt, clock())]
    rows[0]["isSidechain"] = True
    n = 0

    def call(name, inp, out):
        nonlocal n
        n += 1
        tid = f"toolu_{agent_id}_{n}"
        rows.append(use(tid, name, inp, clock(), f"msg_{agent_id}_{n}", side=True))
        rows.append(res(tid, out, clock(), side=True))

    if role in ("planner", "fence-reviewer"):
        call("mcp__retrieval__retrieve", {"query": "demo-suite failure paths exit codes",
                                          "project_id": "proj-lessons",
                                          "classification_ceiling": "internal"}, mcp_text([LESSON]))
        call("mcp__coursetools__file_read", {"path": "scripts/demo-suite.sh", "role": role},
             mcp_text({"content": "#!/bin/sh\n..."}))
    elif role == "tester":
        call("Bash", {"command": './scripts/demo-suite.sh; echo "suite exit: $?"'}, SUITE_OUT)
        call("Bash", {"command": "git status --porcelain"}, "")
    elif role == "implementer":
        call("mcp__coursetools__file_write", {"path": NEW_DOC, "content": "# Demo-suite failure paths\n",
                                              "role": "implementer"}, mcp_text({"ok": True}))
        call("mcp__storage__write_entry", {"project_id": "proj-lessons", "classification": "internal",
                                           "calling_role": "implementer",
                                           "content": "Force a failure with a copied trace, never the golden."},
             mcp_text({"entry_id": LESSON_ID}))
    final = text_msg("assistant", REPORTS[role], clock(), f"msg_{agent_id}_final",
                     {"input_tokens": 300, "output_tokens": 600, "cache_creation_input_tokens": 1000,
                      "cache_read_input_tokens": 9000})
    final["isSidechain"] = True
    rows.append(final)
    return rows


def build_valid(d):
    clock = Clock()
    os.makedirs(os.path.join(d, "subagents"), exist_ok=True)
    s = [text_msg("user", "Run DEV-01: replay Feature 1 Task 7 (demo-suite failure paths).", clock(0))]
    n = 0

    def main_call(name, inp, out, extra=None):
        nonlocal n
        n += 1
        tid = f"toolu_main_{n}"
        s.append(use(tid, name, inp, clock(), f"msg_main_{n}"))
        s.append(res(tid, out, clock(), extra=extra))

    main_call("Read", {"file_path": "/workspace/.memory/SCOPE.md"}, "GIMPL scope ...")
    main_call("Read", {"file_path": "/workspace/.memory/project/MEMORY_INDEX.md"}, "index ...")
    steps = [("p1", "planner", "Plan Task 7: document demo-suite failure paths. Read docs/smoke-tests/demo-suite.md."),
             ("t1", "tester", "Baseline: run ./scripts/demo-suite.sh and report the result lines and exit code."),
             ("i1", "implementer", f"Write {NEW_DOC} per the approved plan; store one lesson."),
             ("t2", "tester", "Rerun ./scripts/demo-suite.sh after the change; report lines, exit code, git status."),
             ("f1", "fence-reviewer", f"Review the diff: {NEW_DOC} only. Check scope and golden traces.")]
    for agent_id, role, prompt in steps:
        sub = subagent(agent_id, role, prompt, clock)
        with open(os.path.join(d, "subagents", f"agent-{agent_id}.jsonl"), "w") as f:
            f.write(lines(sub))
        main_call("Agent", {"subagent_type": role, "description": role, "prompt": prompt},
                  [{"type": "text", "text": REPORTS[role]}], extra={"toolUseResult": {"agentId": agent_id}})
        if role == "planner":  # George approves the plan; this wait is not agent time
            s.append(text_msg("user", "Approved. Tester before and after, this task only.", clock(120)))
    main_call("Bash", {"command": "git status --porcelain"}, f"?? {NEW_DOC}")
    main_call("mcp__coursetools__file_write", {"path": SUMMARY, "content": "...", "role": "orchestrator"},
              mcp_text({"ok": True}))
    s.append(text_msg("assistant", "Outcome: Accepted, pending George's commit.", clock(), "msg_main_end",
                      {"input_tokens": 100, "output_tokens": 200, "cache_creation_input_tokens": 500,
                       "cache_read_input_tokens": 9000}))
    with open(os.path.join(d, "session.jsonl"), "w") as f:
        f.write(lines(s))

    meta = {"run_id": "FIXTURE-VALID", "task_id": "DEV-01", "kind": "dev",
            "expected_path": ["planner", "tester", "implementer", "tester", "fence-reviewer"],
            "session_id": SESSION, "start_utc": "2026-11-17T17:00:00Z", "end_utc": clock(0)[:19] + "Z",
            "audit_offset_before": 3, "manifest_write_approved": False}
    snap = {"head": "1fcf3926" + "0" * 32, "porcelain": [],
            "sha256": {"tests/demos/heretic/golden/demo1.tics": DEMO1,
                       "tests/demos/heretic/manifest": MANIFEST_SHA}, "audit_lines": 3}
    after = dict(snap, porcelain=[f"?? {NEW_DOC}", f"?? {SUMMARY}"], audit_lines=4)
    audit = {"calling_role": "implementer", "classification": "internal", "entry_id": LESSON_ID,
             "operation": "write_entry", "project_id": "proj-lessons", "timestamp": "2026-11-17T17:01:40Z"}
    for name, obj in (("run.json", meta), ("git-before.json", snap), ("git-after.json", after)):
        with open(os.path.join(d, name), "w") as f:
            json.dump(obj, f, indent=2)
    with open(os.path.join(d, "audit.jsonl"), "w") as f:
        f.write(json.dumps(audit, sort_keys=True) + "\n")
    os.makedirs(os.path.join(d, "run-summary"), exist_ok=True)
    with open(os.path.join(d, "run-summary", "dev01-run-1.md"), "w") as f:
        f.write("# DEV-01 run 1 (fixture)\n\nOutcome: Accepted, pending George's commit.\n")


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    valid = os.path.join(OUT, "valid")
    build_valid(valid)

    bad = os.path.join(OUT, "malformed")
    shutil.copytree(valid, bad)
    with open(os.path.join(bad, "session.jsonl")) as f:
        text = f.read()
    with open(os.path.join(bad, "session.jsonl"), "w") as f:
        f.write(text[: len(text) // 2])          # cut mid-line, like a killed container

    bad = os.path.join(OUT, "missing-tester")
    shutil.copytree(valid, bad)
    for agent_id in ("t1", "t2"):
        os.remove(os.path.join(bad, "subagents", f"agent-{agent_id}.jsonl"))

    bad = os.path.join(OUT, "golden-changed")
    shutil.copytree(valid, bad)
    path = os.path.join(bad, "git-after.json")
    with open(path) as f:
        snap = json.load(f)
    snap["sha256"]["tests/demos/heretic/golden/demo1.tics"] = "f" * 64
    with open(path, "w") as f:
        json.dump(snap, f, indent=2)
    print("wrote", ", ".join(sorted(os.listdir(OUT))), "under", OUT)


if __name__ == "__main__":
    main()
