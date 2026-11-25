#!/usr/bin/env python3
"""Deterministic replacement for the demo-verifier agent (ADR-001).

Answers "does chocolate-heretic still replay every pinned demo tic for tic?"
the way .claude/agents/demo-verifier.md v0.2.1 did, with no language model:

  1. Rebuild src/chocolate-heretic (./autogen.sh && make) only if it is
     missing or older than a .c or .h file in src/ or src/heretic/. A newer
     binary for another game, such as src/chocolate-hexen, is not a source
     file and never triggers a rebuild.
  2. Record `git status --short`.
  3. Run scripts/demo-suite.sh, then the scripts/demo1-check.sh cross-check,
     with the dummy SDL drivers.
  4. Record `git status --short` again.
  5. Decide the verdict from the scripts' output:
       PASS     suite exit 0, a "PASS: <demo> <N> gametics, trace matches"
                line for every demo in tests/demos/heretic/manifest, the
                "PASS: <count> demo(s)" line, and a cross-check
                "PASS: <N> gametics == expected <N>" with exit 0, where N is
                the manifest's demo1 gametics.
       FAIL     suite exit 1 (quotes the FAIL: line and the first gametic
                line), the suite and the cross-check disagree, or the check
                changed the working tree.
       BLOCKED  suite exit 2 (quotes the ERROR: line), any other exit code,
                a failed rebuild, or output this script does not recognize.
     Engine exit 255 after -timedemo is normal (decision-006); both scripts
     accept it, and the report says so.

Usage (from the repository root, inside the gimpl container):
    python3 scripts/verify_demos_deterministic.py \
        --input eval/demo-verify/check-the-demos.json --output /tmp/demo-verify.json

Input and output move only through the two named files. The script reads no
environment variable for its own settings, prints only the verdict line, and
writes the full report, every command line quoted verbatim, to --output.
Exit code: 0 PASS, 1 FAIL, 2 BLOCKED.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = "tests/demos/heretic/manifest"
BINARY = "src/chocolate-heretic"
SOURCE_DIRS = ("src", "src/heretic")       # what chocolate-heretic is built from
SOURCE_SUFFIXES = (".c", ".h")
SUITE = ["./scripts/demo-suite.sh"]
CROSS_CHECK = ["./scripts/demo1-check.sh"]
BUILD = ["bash", "-c", "./autogen.sh && make"]
GIT_STATUS = ["git", "status", "--short"]
HEADLESS = {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
ENGINE_EXIT_MEANING = ("chocolate-heretic exits 255 after -timedemo; that is the "
                       "engine's normal end of a demo, never a failure by itself (decision-006)")
EXIT = {"PASS": 0, "FAIL": 1, "BLOCKED": 2}

DEMO_PASS = re.compile(r"^PASS: (\w+) (\d+) gametics, trace matches$")
SUITE_TOTAL = re.compile(r"^PASS: (\d+) demo\(s\)$")
CROSS_PASS = re.compile(r"^PASS: (\d+) gametics == expected (\d+)$")
FIRST_DIFF = re.compile(r"^gametic \d+: ")

# A runner takes (argv, cwd) and returns (exit code, combined output text).
Runner = Callable[[list, Path], "tuple[int, str]"]


def run_command(argv: list, cwd: Path) -> "tuple[int, str]":
    """Run one command with the dummy SDL drivers; stdout and stderr together."""
    env = dict(os.environ, **HEADLESS)
    proc = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True)
    return proc.returncode, proc.stdout


def read_manifest(root: Path) -> "list[tuple[str, int]]":
    """(demo, gametics) for each demo line, skipping # comments and blanks."""
    demos = []
    for line in (root / MANIFEST).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        demos.append((fields[0], int(fields[1])))
    return demos


def rebuild_reason(root: Path) -> "str | None":
    """Why a rebuild is needed, or None. Only .c/.h files in SOURCE_DIRS count."""
    binary = root / BINARY
    if not binary.exists():
        return f"{BINARY} is missing"
    built = binary.stat().st_mtime
    for d in SOURCE_DIRS:
        folder = root / d
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.suffix in SOURCE_SUFFIXES and f.stat().st_mtime > built:
                return f"{f.relative_to(root)} is newer than {BINARY}"
    return None


STATUS_LINE = re.compile(r"^[ MADRCUT?!]{2} \S")


def status_lines(text: str) -> "list[str]":
    """The `git status --short` entries only. Any warning git prints on a
    read-only mount is not a change to the tree."""
    return [line for line in text.splitlines() if STATUS_LINE.match(line)]


def split_status(before: "list[str]", after: "list[str]", ignore: "set[str]") -> "tuple[list[str], list[str]]":
    """(changed by the run, already there before it). A line counts as the
    run's own change if it is new or different after the run. Paths in
    ignore (the --output file, if it sits inside the repository) are not."""
    def path_of(line: str) -> str:
        return line[3:].split(" -> ")[-1].strip()
    changed = [l for l in after if l not in before and path_of(l) not in ignore]
    return changed, before


def lines_matching(lines: "list[str]", prefix: str) -> "list[str]":
    return [l for l in lines if l.startswith(prefix)]


def decide(manifest: "list[tuple[str, int]]", suite_rc: int, suite_out: str,
           check_rc: int, check_out: str, changed_by_run: "list[str]") -> "tuple[str, str]":
    """The verdict and the one-line reason, from the scripts' output only."""
    suite = suite_out.splitlines()
    check = check_out.splitlines()
    if suite_rc == 2:
        err = lines_matching(suite, "ERROR:")
        return "BLOCKED", "suite setup error (exit 2): " + (err[0] if err else "no ERROR: line printed")
    if suite_rc not in (0, 1):
        return "BLOCKED", f"suite exited {suite_rc}, which is not 0, 1 or 2; output quoted, cause not guessed"

    demo1_tics = dict(manifest).get("demo1")
    cross = [CROSS_PASS.match(l) for l in check]
    cross = [m for m in cross if m]
    cross_ok = (check_rc == 0 and len(cross) == 1 and demo1_tics is not None
                and int(cross[0].group(1)) == int(cross[0].group(2)) == demo1_tics)

    if suite_rc == 1:
        fail = lines_matching(suite, "FAIL:")
        diff = [l for l in suite if FIRST_DIFF.match(l)]
        reason = "suite FAIL (exit 1): " + (fail[0] if fail else "no FAIL: line printed")
        if diff:
            reason += "; first difference: " + diff[0]
        if cross_ok:
            reason += "; the cross-check passed, so the two disagree"
        return "FAIL", reason

    # Suite exit 0: every manifest demo must have its PASS line, plus the total.
    passed = {m.group(1): int(m.group(2)) for m in (DEMO_PASS.match(l) for l in suite) if m}
    missing = [d for d, tics in manifest if passed.get(d) != tics]
    total = [SUITE_TOTAL.match(l) for l in suite]
    total = [m for m in total if m]
    if missing or len(total) != 1 or int(total[0].group(1)) != len(manifest):
        what = f"no matching PASS line for {missing}" if missing else "no 'PASS: <count> demo(s)' line for the manifest"
        return "BLOCKED", f"suite exited 0 but {what}; output quoted, cause not guessed"
    if not cross_ok:
        line = (lines_matching(check, "FAIL:") or lines_matching(check, "ERROR:") or ["no PASS line"])[0]
        return "FAIL", f"the suite passed but the cross-check did not (exit {check_rc}: {line}); the two disagree"
    if changed_by_run:
        return "FAIL", "the check changed the working tree: " + "; ".join(changed_by_run)
    return "PASS", f"{len(manifest)} demo(s) replay tic for tic; cross-check {cross[0].group(0)}"


def verify(root: Path, request: dict, runner: Runner = run_command,
           ignore_paths: "set[str] | None" = None) -> dict:
    """Run the check and return the report. Never edits a tracked file."""
    ignore_paths = ignore_paths or set()
    manifest = read_manifest(root)
    report = {
        "step": "demo-verifier",
        "converted_by": "docs/adr/ADR-001-demo-verifier-deterministic-conversion.md",
        "request": request.get("request", ""),
    }

    build = {"rebuilt": False, "reason": rebuild_reason(root), "exit_code": None, "lines": []}
    before = status_lines(runner(GIT_STATUS, root)[1])
    if build["reason"]:
        if not request.get("build_if_stale", True):
            report.update(_blocked(report, build, before,
                                   f"rebuild needed ({build['reason']}) and build_if_stale is false"))
            return report
        rc, out = runner(BUILD, root)
        build.update(rebuilt=True, exit_code=rc, lines=out.splitlines())
        if rc != 0:
            report.update(_blocked(report, build, before, f"rebuild failed (exit {rc})"))
            return report

    suite_rc, suite_out = runner(SUITE, root)
    check_rc, check_out = runner(CROSS_CHECK, root)
    after = status_lines(runner(GIT_STATUS, root)[1])
    changed, pre_existing = split_status(before, after, ignore_paths)
    verdict, reason = decide(manifest, suite_rc, suite_out, check_rc, check_out, changed)

    suite_lines, check_lines = suite_out.splitlines(), check_out.splitlines()
    unexpected = []
    if build["rebuilt"]:
        unexpected.append(f"rebuilt: {build['reason']}")
    if pre_existing:
        unexpected.append("working tree already had changes before the check; not caused by it")
    report.update({
        "decision": {
            "verdict": verdict,
            "reason": reason,
            "manifest_demos": [f"{d} {t}" for d, t in manifest],
            "rebuilt": build["rebuilt"],
            "suite_exit_code": suite_rc,
            "cross_check_exit_code": check_rc,
            "demo_results": lines_matching(suite_lines, "PASS: ") + lines_matching(suite_lines, "FAIL: "),
            "cross_check_result": (lines_matching(check_lines, "PASS: ") + lines_matching(check_lines, "FAIL: ")
                                   + lines_matching(check_lines, "ERROR: ")),
            "git_status_changed_by_check": changed,
            "git_status_pre_existing": pre_existing,
        },
        "evidence": {
            "iwad_sha256": lines_matching(suite_lines, "IWAD OK:"),
            "trace_sha256": lines_matching(suite_lines, "trace OK:"),
            "timed": lines_matching(suite_lines, "timed "),
            "engine_exit": lines_matching(suite_lines, "engine exit code:"),
            "engine_exit_meaning": ENGINE_EXIT_MEANING,
            "first_difference": [l for l in suite_lines if FIRST_DIFF.match(l)][:1],
            "errors": lines_matching(suite_lines, "ERROR:") + lines_matching(check_lines, "ERROR:"),
            "git_status_after": after or ["(empty)"],
        },
        "commands": {
            "build": build,
            "suite": {"command": " ".join(SUITE), "exit_code": suite_rc, "lines": suite_lines or ["(empty)"]},
            "cross_check": {"command": " ".join(CROSS_CHECK), "exit_code": check_rc,
                            "lines": check_lines or ["(empty)"]},
        },
        "unexpected": unexpected or ["none"],
    })
    return report


def _blocked(report: dict, build: dict, before: "list[str]", reason: str) -> dict:
    return {
        "decision": {"verdict": "BLOCKED", "reason": reason, "rebuilt": build["rebuilt"],
                     "git_status_pre_existing": before},
        "commands": {"build": build},
        "unexpected": ["none"],
    }


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True, help="request file (JSON)")
    parser.add_argument("--output", required=True, help="where to write the report (JSON)")
    parser.add_argument("--repo", default=str(ROOT),
                        help="repository root (default: the repository this script is in)")
    args = parser.parse_args(argv)

    root = Path(args.repo).resolve()
    request = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out = Path(args.output).resolve()
    ignore = set()
    if root in out.parents:
        ignore.add(str(out.relative_to(root)))

    report = verify(root, request, ignore_paths=ignore)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    verdict = report["decision"]["verdict"]
    print(f"{verdict}: {report['decision']['reason']} (report: {args.output})")
    return EXIT[verdict]


if __name__ == "__main__":
    sys.exit(main())
