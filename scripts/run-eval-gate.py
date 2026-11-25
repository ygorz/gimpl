#!/usr/bin/env python3
"""Evaluation Harness gate for CI (job eval-gate in .github/workflows/ci.yml).

Runs GIMPL's Module 3 evaluation harness and writes one report,
eval-report.json, in the reports directory. Exits 1 if any part fails, so
the job blocks the merge.

    python3 scripts/run-eval-gate.py --reports /reports
    python3 scripts/run-eval-gate.py --reports ci-artifacts --not-triggered

What runs (inside the gimpl image, repository mounted read-only):
1. pytest eval/tests: unit tests for the deterministic checks, the rubric
   suite's gate and the PreToolUse guard hooks. The full pytest report is
   saved as eval-tests-report.json.
2. eval/test_deterministic.py on each committed fixture run in
   eval/tests/fixtures/. The valid run must pass (exit 0); each broken run
   must fail (exit 1). A broken run that passes means a check stopped
   catching the fault it guards.

What does not run: eval/test_rubric_suite.py. The rubric judge is Claude
Code on the operator's interactive login, and CI holds no Claude
credential. The report records it as "not_run" with that reason instead of
counting it as a pass.

--not-triggered writes the report for a run where the change classifier
found no agent-affecting change: status "not_triggered", nothing executed.
That mode uses only the standard library, so it runs on the CI runner
without building the image.

The script reads no environment variables and writes only into the
reports directory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = "eval/tests/fixtures"

# Fixture run -> the exit code eval/test_deterministic.py must return.
EXPECTED_EXIT = {
    "valid": 0,
    "malformed": 1,
    "golden-changed": 1,
    "missing-tester": 1,
}

RUBRIC_NOT_RUN = {
    "status": "not_run",
    "reason": ("eval/test_rubric_suite.py runs Claude Code on the operator's "
               "interactive login; CI holds no Claude credential"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def last_line(text: str) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else ""


def run_pytest(reports: Path) -> dict:
    report_file = reports / "eval-tests-report.json"
    cmd = [sys.executable, "-m", "pytest", "eval/tests", "-q",
           "-p", "no:cacheprovider",
           "--json-report", f"--json-report-file={report_file}"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    summary = {}
    try:
        summary = json.loads(report_file.read_text(encoding="utf-8")).get("summary", {})
    except (OSError, ValueError):
        pass
    return {
        "command": "python3 -m pytest eval/tests -q -p no:cacheprovider",
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "summary": summary,
        "report": report_file.name,
    }


def run_fixture(name: str, expected: int) -> dict:
    run_dir = f"{FIXTURES}/{name}"
    proc = subprocess.run([sys.executable, "eval/test_deterministic.py", run_dir],
                          cwd=ROOT, capture_output=True, text=True)
    ok = proc.returncode == expected
    print(f"[{'OK' if ok else 'FAIL'}] {run_dir}: exit {proc.returncode}, expected {expected}")
    return {
        "fixture": run_dir,
        "expected_exit": expected,
        "exit_code": proc.returncode,
        "passed": ok,
        "summary": last_line(proc.stdout),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reports", required=True, help="writable directory for the reports")
    parser.add_argument("--not-triggered", action="store_true",
                        help="record that the classifier found no agent-affecting change")
    args = parser.parse_args()

    reports = Path(args.reports)
    reports.mkdir(parents=True, exist_ok=True)
    report = {"job": "eval-gate", "timestamp": now()}

    if args.not_triggered:
        report.update({
            "status": "not_triggered",
            "reason": "change-type-check set requires-eval=false: no agent-affecting file changed",
            "pytest": None,
            "deterministic_fixtures": [],
            "rubric_judge": dict(RUBRIC_NOT_RUN),
        })
        code = 0
    else:
        tests = run_pytest(reports)
        fixtures = [run_fixture(name, expected) for name, expected in EXPECTED_EXIT.items()]
        passed = tests["passed"] and all(f["passed"] for f in fixtures)
        report.update({
            "status": "passed" if passed else "failed",
            "pytest": tests,
            "deterministic_fixtures": fixtures,
            "rubric_judge": dict(RUBRIC_NOT_RUN),
        })
        code = 0 if passed else 1

    out = reports / "eval-report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"eval-gate: {report['status']} (wrote {out})")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
