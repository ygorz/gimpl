"""Git and golden-hash snapshot for one eval run (used by start_run.sh and
finish_run.sh). Run from the repository root:
    python3 eval/snapshot.py <out.json> [<earlier-snapshot.json>]

file_sha256 holds the content hash of every path `git status` lists (dirty
or untracked) and, when an earlier snapshot is given, of every path that
snapshot hashed. So a file that is dirty both before and after the run but
was edited again during it shows up as changed (3.3 grader feedback);
porcelain status alone cannot see that.
"""
import glob
import hashlib
import json
import os
import subprocess
import sys

GOLDEN = "tests/demos/heretic/golden"
MANIFEST = "tests/demos/heretic/manifest"
AUDIT = "logs/storage-audit-log.jsonl"


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def content_hash(path):
    """sha256 of a file, None if it does not exist, or 'unreadable: ...'."""
    if not os.path.isfile(path):
        return None
    try:
        return sha256(path)
    except OSError as e:
        return f"unreadable: {e.strerror}"


def porcelain_path(line):
    return line[3:].split(" -> ")[-1].strip().strip('"')


def snapshot(earlier=None):
    files = sorted(glob.glob(os.path.join(GOLDEN, "*"))) + [MANIFEST]
    audit_lines = 0
    if os.path.exists(AUDIT):
        with open(AUDIT, "rb") as f:
            audit_lines = sum(1 for _ in f)
    porcelain = [l for l in git("status", "--porcelain=v1", "--untracked-files=all").split("\n") if l]
    hashed = {porcelain_path(l) for l in porcelain if len(l) > 3}
    if earlier:
        hashed |= set((earlier.get("file_sha256") or {}).keys())
    return {"head": git("rev-parse", "HEAD").strip(),
            "branch": git("rev-parse", "--abbrev-ref", "HEAD").strip(),
            "porcelain": porcelain,
            "sha256": {p: sha256(p) if os.path.isfile(p) else None for p in files},
            "file_sha256": {p: content_hash(p) for p in sorted(hashed)},
            "audit_lines": audit_lines}


if __name__ == "__main__":
    earlier = None
    if len(sys.argv) > 2:
        with open(sys.argv[2]) as f:
            earlier = json.load(f)
    snap = snapshot(earlier)
    with open(sys.argv[1], "w") as f:
        json.dump(snap, f, indent=2)
