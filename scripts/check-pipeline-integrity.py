#!/usr/bin/env python3
"""Pipeline Integrity Check (job pipeline-integrity in .github/workflows/ci.yml).

Reads the workflow file itself, not the code change, and fails if the
pipeline's own guardrails have been weakened. Each check runs as its own
workflow step, so a failure names the guardrail it came from:

    python3 scripts/check-pipeline-integrity.py --check gates
    python3 scripts/check-pipeline-integrity.py --check audit
    python3 scripts/check-pipeline-integrity.py --check classifier
    python3 scripts/check-pipeline-integrity.py --check self
    python3 scripts/check-pipeline-integrity.py --report ci-artifacts/pipeline-integrity-report.json \\
        --step-outcome gates=success --step-outcome audit=success ...

The checks:

gates       policy-gate and eval-gate exist and cannot be demoted: no
            continue-on-error (job or any step) and no job-level if:. A
            job-level continue-on-error turns the gate's result into
            "success" for every job that needs it; a step-level one makes
            the check itself green; a job-level if: lets the gate report
            "skipped", which satisfies a required status check.
audit       audit-trail exists, runs with exactly if: always(), and needs
            every other job, so a failing run is still recorded and no
            job's result is left off the record.
classifier  change-type-check exists, cannot be skipped (no job-level if:,
            no continue-on-error), still publishes requires-eval, and
            eval-gate still needs it and reads that output. Without the
            classifier, eval-gate's steps read an empty value and record
            "not_triggered" on every change.
self        pipeline-integrity itself has no needs:, no job-level if: and
            no continue-on-error, so it runs and reports on every change
            whatever the other jobs do. (Beyond the three required checks.)

--report runs every check again, without stopping at the first failure,
and writes pipeline-integrity-report.json in the same shape as the other
jobs' reports (job, status, timestamp, reason). A check that could not be
evaluated (the workflow is missing or does not parse, or PyYAML is not
installed) is recorded as "not_run" and the report's status is "failed": a
check that did not run never counts as a pass. The report itself always
exits 0; the check steps are what fail the job.

The script reads only the workflow file. It holds no credential and never
reads the environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

GATES = ("policy-gate", "eval-gate")
AUDIT = "audit-trail"
CLASSIFIER = "change-type-check"
SELF = "pipeline-integrity"

CHECKS = {
    "gates": "policy-gate and eval-gate have no continue-on-error and no job-level if:",
    "audit": "audit-trail runs with if: always() and needs every other job",
    "classifier": "change-type-check exists, cannot be skipped and still drives eval-gate",
    "self": "pipeline-integrity has no needs:, no job-level if: and no continue-on-error",
}
STEP_NAMES = {
    "gates": "Check 1: gates have no continue-on-error",
    "audit": "Check 2: audit-trail keeps if: always()",
    "classifier": "Check 3: change-type-check classifier exists",
    "self": "Check 4: pipeline-integrity stays independent",
}


class NotEvaluated(Exception):
    """The workflow could not be read, so no check can be evaluated."""


def load_workflow(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise NotEvaluated("PyYAML is not installed (pinned in requirements-ci.txt)") from exc
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise NotEvaluated(f"cannot read {path}: {exc.strerror}") from exc
    try:
        workflow = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise NotEvaluated(f"{path.name} does not parse as YAML: {exc}") from exc
    if not isinstance(workflow, dict) or not isinstance(workflow.get("jobs"), dict):
        raise NotEvaluated(f"{path.name} defines no jobs")
    return workflow


def needs_of(job: dict) -> set:
    needs = job.get("needs", [])
    if isinstance(needs, str):
        return {needs}
    return set(needs) if isinstance(needs, list) else {str(needs)}


def is_set(value) -> bool:
    """continue-on-error counts as set unless it is absent or literally false.
    An expression such as ${{ true }} can evaluate to true, so it counts."""
    return value is not None and value is not False


def bare_condition(value) -> str:
    text = str(value).strip()
    match = re.fullmatch(r"\$\{\{(.*)\}\}", text, flags=re.S)
    if match:
        text = match.group(1)
    return re.sub(r"\s+", "", text)


def step_label(step: dict, index: int) -> str:
    return repr(step.get("name") or step.get("uses") or f"step {index + 1}")


def demotions(key: str, job: dict) -> list[str]:
    """Ways a job's result can stop meaning what it says."""
    found = []
    if is_set(job.get("continue-on-error")):
        found.append(f"{key}: job-level continue-on-error: {job.get('continue-on-error')!r} "
                     "(dependent jobs and the audit trail would see 'success' when it fails)")
    for i, step in enumerate(job.get("steps") or []):
        if isinstance(step, dict) and is_set(step.get("continue-on-error")):
            found.append(f"{key}: step {step_label(step, i)} has continue-on-error: "
                         f"{step.get('continue-on-error')!r} (the check turns green when that step fails)")
    if "if" in job:
        found.append(f"{key}: job-level if: {job['if']!r} (a skipped job satisfies a required status check)")
    return found


def check_gates(jobs: dict) -> tuple[list[str], dict]:
    findings, inspected = [], {}
    for key in GATES:
        if key not in jobs:
            findings.append(f"{key}: gating job is missing from the workflow")
            inspected[key] = None
            continue
        job = jobs[key] or {}
        inspected[key] = {
            "continue_on_error": job.get("continue-on-error"),
            "steps_with_continue_on_error": [step_label(s, i) for i, s in enumerate(job.get("steps") or [])
                                             if isinstance(s, dict) and is_set(s.get("continue-on-error"))],
            "job_if": job.get("if"),
        }
        findings += demotions(key, job)
    return findings, inspected


def check_audit(jobs: dict) -> tuple[list[str], dict]:
    if AUDIT not in jobs:
        return [f"{AUDIT}: job is missing from the workflow"], {AUDIT: None}
    job = jobs[AUDIT] or {}
    findings = []
    condition = job.get("if")
    if condition is None:
        findings.append(f"{AUDIT}: has no if: always(), so it is skipped whenever any job it needs fails")
    elif bare_condition(condition) != "always()":
        findings.append(f"{AUDIT}: if: {condition!r} is not exactly always()")
    expected = set(jobs) - {AUDIT}
    missing = sorted(expected - needs_of(job))
    if missing:
        findings.append(f"{AUDIT}: needs: does not list {missing}, so their results are left off the record")
    return findings, {AUDIT: {"if": condition, "needs": sorted(needs_of(job)),
                              "jobs_expected_in_needs": sorted(expected)}}


def check_classifier(jobs: dict) -> tuple[list[str], dict]:
    if CLASSIFIER not in jobs:
        return [f"{CLASSIFIER}: classifier job is missing from the workflow"], {CLASSIFIER: None}
    job = jobs[CLASSIFIER] or {}
    findings = demotions(CLASSIFIER, job)
    outputs = job.get("outputs") or {}
    if "requires-eval" not in outputs:
        findings.append(f"{CLASSIFIER}: no requires-eval output")
    eval_job = jobs.get("eval-gate") or {}
    reads = " ".join(str(s.get("if", "")) for s in eval_job.get("steps") or [] if isinstance(s, dict))
    wired = CLASSIFIER in needs_of(eval_job) and f"needs.{CLASSIFIER}.outputs.requires-eval" in reads
    if eval_job and not wired:
        findings.append(f"eval-gate no longer needs {CLASSIFIER} and reads its requires-eval output")
    return findings, {CLASSIFIER: {"job_if": job.get("if"), "continue_on_error": job.get("continue-on-error"),
                                   "outputs": sorted(outputs), "eval_gate_wired": wired}}


def check_self(jobs: dict) -> tuple[list[str], dict]:
    if SELF not in jobs:
        return [f"{SELF}: job is missing from the workflow"], {SELF: None}
    job = jobs[SELF] or {}
    findings = demotions(SELF, job)
    if needs_of(job):
        findings.append(f"{SELF}: needs: {sorted(needs_of(job))} (it would be skipped, and pass as a "
                        "required check, whenever one of those jobs fails)")
    return findings, {SELF: {"needs": sorted(needs_of(job)), "job_if": job.get("if"),
                             "continue_on_error": job.get("continue-on-error")}}


RUNNERS = {"gates": check_gates, "audit": check_audit, "classifier": check_classifier, "self": check_self}


def run_check(name: str, workflow_path: Path) -> dict:
    entry = {"id": name, "step": STEP_NAMES[name], "looks_for": CHECKS[name]}
    try:
        jobs = load_workflow(workflow_path)["jobs"]
    except NotEvaluated as exc:
        return {**entry, "status": "not_run", "findings": [], "reason": str(exc), "inspected": None}
    findings, inspected = RUNNERS[name](jobs)
    return {**entry, "status": "failed" if findings else "passed", "findings": findings,
            "reason": "; ".join(findings) if findings else "no weakening found", "inspected": inspected}


def print_result(result: dict, annotate: bool) -> None:
    label = {"passed": "PASS", "failed": "FAIL", "not_run": "NOT RUN"}[result["status"]]
    print(f"[{label}] {result['id']}: {result['looks_for']}")
    for finding in result["findings"] or ([result["reason"]] if result["status"] == "not_run" else []):
        print(f"  - {finding}")
        if annotate:
            print(f"::error title=Pipeline Integrity Check ({result['id']})::{finding}")


def sha256(path: Path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def write_report(out: Path, workflow_path: Path, outcomes: dict) -> dict:
    checks = []
    for name in RUNNERS:
        result = run_check(name, workflow_path)
        if name in outcomes:
            result["step_outcome"] = outcomes[name]
        checks.append(result)
    failed = [c["id"] for c in checks if c["status"] == "failed"]
    not_run = [c["id"] for c in checks if c["status"] == "not_run"]
    # A check step that was skipped or cancelled did not prove anything.
    unproven = sorted(n for n, o in outcomes.items() if o not in ("success", "failure"))
    if failed or not_run or unproven:
        status = "failed"
        parts = []
        if failed:
            parts.append(f"weakened: {', '.join(failed)}")
        if not_run:
            parts.append(f"not evaluated: {', '.join(not_run)}")
        if unproven:
            parts.append(f"check steps did not run: {', '.join(unproven)}")
        reason = "; ".join(parts)
    else:
        status, reason = "passed", "all checks passed"
    try:
        shown = str(workflow_path.resolve().relative_to(ROOT))
    except ValueError:
        shown = str(workflow_path)
    report = {
        "job": SELF,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "workflow": shown,
        "workflow_sha256": sha256(workflow_path),
        "checks": checks,
        "failed_checks": failed,
        "not_run_checks": not_run,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"pipeline-integrity: {status} ({reason}); wrote {out}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline Integrity Check")
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", choices=[*RUNNERS, "all"], help="run one check; exit 1 if it fails or cannot run")
    mode.add_argument("--report", type=Path, metavar="PATH", help="run every check and write the JSON report")
    parser.add_argument("--step-outcome", action="append", default=[], metavar="CHECK=OUTCOME",
                        help="steps.<id>.outcome of a check step, recorded in the report")
    parser.add_argument("--annotate", action="store_true", help="also print GitHub ::error annotations")
    args = parser.parse_args()

    if args.report:
        outcomes = dict(item.split("=", 1) for item in args.step_outcome if "=" in item)
        outcomes = {k: v for k, v in outcomes.items() if k in RUNNERS}
        write_report(args.report, args.workflow, outcomes)
        return 0

    names = list(RUNNERS) if args.check == "all" else [args.check]
    results = [run_check(name, args.workflow) for name in names]
    for result in results:
        print_result(result, args.annotate)
    return 0 if all(r["status"] == "passed" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
