#!/usr/bin/env python3
"""Combine one CI run's evidence into ci-audit-trail-<sha>.json (job audit-trail).

The audit-trail job runs with if: always(), downloads every artifact the run
uploaded into one directory (actions/download-artifact@v4, merge-multiple),
and calls this script with each job's result from the needs context:

    python3 scripts/build-audit-trail.py --artifacts ci-artifacts \\
        --sha <sha> --event pull_request --pr 12 --run-id <id> --run-url <url> \\
        --changed-files "a b c" --requires-eval true --touches-policy false \\
        --result change-type-check=success --result policy-gate=success \\
        --result eval-gate=success --result agent-review=success

Every job ends in exactly one of these states, so an auditor can tell a
job that failed from one that had nothing to do:

- passed         the job ran its checks and they passed
- failed         the job ran and failed (or timed out)
- not_triggered  the job ran but had nothing to check: the classifier found
                 no agent-affecting change, or the job runs on pull requests
                 only and this was a push
- skipped        the job did not run because a job it needs failed, or it
                 ran and recorded a skip (the advisory reviewer with no key)
- cancelled      the run was cancelled before the job finished
- missing        no result was passed for the job

The script reads only the files in --artifacts and its own arguments. It
never reads the environment, so no secret can reach the trail, and it masks
anything shaped like an API key as a backstop. It always exits 0: the trail
records failures, it does not cause them. It also writes
ci-audit-trail-summary.md for the job summary and the pull request comment.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Job key -> report file that job uploads. Add a job here when it is added
# to ci.yml, and list it in GATING if it can block a merge.
REPORTS = {
    "change-type-check": "change-classification.json",
    "policy-gate": "policy-report.json",
    "eval-gate": "eval-report.json",
    "agent-review": "review-audit.json",
}
GATING = {"policy-gate", "eval-gate"}
ORDER = list(REPORTS)

# Backstop only: nothing should ever put a key in an artifact.
KEY_PATTERN = re.compile(
    r"(sk-or-v1-[A-Za-z0-9]{16,}|sk-ant-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9]{32,}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def flag(value: str):
    return {"true": True, "false": False}.get((value or "").strip().lower())


def job_state(job: str, result: str, report, event: str) -> tuple[str, str]:
    """One state and a short reason, from the needs result and the job's report."""
    result = (result or "").strip().lower()
    if not result:
        return "missing", "no result was passed for this job"
    if result == "cancelled":
        return "cancelled", "the run was cancelled before the job finished"
    if result == "failure":
        return "failed", "the job failed; see its report and log"
    if result == "skipped":
        if job == "agent-review" and event != "pull_request":
            return "not_triggered", "runs on pull requests only"
        return "skipped", "did not run because a job it needs did not succeed"
    if result != "success":
        return "missing", f"unrecognized result {result!r}"
    if job == "agent-review" and not isinstance(report, dict):
        return "failed", "the advisory review uploaded no review-audit.json"
    status = report.get("status") if isinstance(report, dict) else None
    if status == "not_triggered":
        return "not_triggered", report.get("reason", "nothing to check")
    if status == "skipped":
        return "skipped", report.get("reason", "recorded a skip")
    if status in ("error", "failed"):
        return "failed", report.get("reason", "the job's report records a failure")
    return "passed", "ran and passed"


def pytest_summary(report) -> dict | None:
    if not isinstance(report, dict) or "summary" not in report:
        return None
    failed = [t.get("nodeid") for t in report.get("tests", []) if t.get("outcome") in ("failed", "error")]
    return {
        "exitcode": report.get("exitcode"),
        "summary": report.get("summary"),
        "failed_tests": failed,
        "duration_seconds": report.get("duration"),
    }


def authorization_denials(artifacts: Path) -> list[dict]:
    """authorization_denied lines from any JSONL audit log uploaded by a job.
    No CI job runs an agent session today, so this is normally empty."""
    denials = []
    for path in sorted(artifacts.rglob("*.jsonl")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and record.get("outcome") == "authorization_denied":
                denials.append({"source": path.name, **record})
    return denials


def mask(text: str) -> tuple[str, int]:
    return KEY_PATTERN.subn("[MASKED]", text)


def summary_markdown(trail: dict) -> str:
    icons = {"passed": "✅", "failed": "❌", "not_triggered": "➖", "skipped": "⏭️",
             "cancelled": "🚫", "missing": "❔"}
    meta = trail["metadata"]
    lines = [
        "## CI Audit Trail",
        "",
        f"Commit `{meta['sha'][:12]}` · {meta['event']}"
        + (f" · PR #{meta['pull_request']}" if meta["pull_request"] else "")
        + f" · overall **{trail['overall']}**",
        "",
        "| Job | Authority | State | Note |",
        "|---|---|---|---|",
    ]
    for job, entry in trail["jobs"].items():
        lines.append(f"| `{job}` | {entry['authority']} | {icons.get(entry['state'], '')} "
                     f"{entry['state']} | {entry['reason'].replace('|', '/')} |")
    cls = trail["change_classification"]
    lines += [
        "",
        f"requires-eval: `{json.dumps(cls['requires_eval'])}` · "
        f"touches-policy: `{json.dumps(cls['touches_policy'])}` · "
        f"changed files: {len(cls['changed_files'])}",
        f"Authorization denials recorded: {len(trail['authorization_denials'])}",
        "",
        f"Full trail: artifact `audit-trail` (`ci-audit-trail-{meta['sha']}.json`).",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the CI audit trail")
    parser.add_argument("--artifacts", default="ci-artifacts")
    parser.add_argument("--out-dir", default=".")
    parser.add_argument("--sha", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--pr", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--run-url", default="")
    parser.add_argument("--changed-files", default="")
    parser.add_argument("--requires-eval", default="")
    parser.add_argument("--touches-policy", default="")
    parser.add_argument("--result", action="append", default=[], metavar="JOB=RESULT",
                        help="a job's needs.<job>.result; repeat once per job")
    args = parser.parse_args()

    artifacts = Path(args.artifacts)
    results = dict(item.split("=", 1) for item in args.result if "=" in item)
    jobs_in_run = ORDER + [j for j in results if j not in REPORTS]

    jobs, reports_present = {}, {}
    for job in jobs_in_run:
        report_name = REPORTS.get(job)
        report = load_json(artifacts / report_name) if report_name else None
        state, reason = job_state(job, results.get(job, ""), report, args.event)
        jobs[job] = {
            "authority": "gating" if job in GATING else
                         "advisory" if job == "agent-review" else "informational",
            "result": results.get(job, ""),
            "state": state,
            "reason": reason,
            "report": report_name if report is not None else None,
        }
        if report_name:
            reports_present[report_name] = report is not None

    gating_states = [jobs[j]["state"] for j in GATING if j in jobs]
    if any(s in ("failed", "cancelled", "missing") for s in gating_states):
        overall = "failed"
    elif any(s == "skipped" for s in gating_states):
        overall = "failed"  # a gate that never ran has not passed
    else:
        overall = "passed"

    policy_report = load_json(artifacts / REPORTS["policy-gate"])
    eval_report = load_json(artifacts / REPORTS["eval-gate"])
    trail = {
        "schema_version": 1,
        "metadata": {
            "sha": args.sha,
            "event": args.event,
            "pull_request": int(args.pr) if args.pr.isdigit() and args.pr != "0" else None,
            "run_id": args.run_id,
            "run_url": args.run_url,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "overall": overall,
        "change_classification": {
            "changed_files": args.changed_files.split(),
            "requires_eval": flag(args.requires_eval),
            "touches_policy": flag(args.touches_policy),
        },
        "jobs": jobs,
        "skipped_states": {j: e["state"] for j, e in jobs.items()
                           if e["state"] in ("not_triggered", "skipped", "cancelled", "missing")},
        "reports_present": reports_present,
        "policy_results": pytest_summary(policy_report),
        "harness_results": eval_report if isinstance(eval_report, dict) else None,
        "harness_tests": pytest_summary(load_json(artifacts / "eval-tests-report.json")),
        "agent_actions": {
            "advisory_review": load_json(artifacts / REPORTS["agent-review"]),
            "note": "No CI job runs an agent session; the advisory reviewer is the only model call.",
        },
        "authorization_denials": authorization_denials(artifacts) if artifacts.is_dir() else [],
    }

    text, masked = mask(json.dumps(trail, indent=2))
    if masked:
        trail = json.loads(text)
        trail["masked_values"] = masked
        text = json.dumps(trail, indent=2)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"ci-audit-trail-{args.sha}.json"
    out.write_text(text + "\n", encoding="utf-8")
    summary, _ = mask(summary_markdown(trail))
    (out_dir / "ci-audit-trail-summary.md").write_text(summary, encoding="utf-8")
    print(f"Wrote {out} (overall: {overall})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
