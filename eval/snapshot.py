"""Git and golden-hash snapshot for one eval run (used by start_run.sh and
finish_run.sh). Run from the repository root:
    python3 eval/snapshot.py <out.json>
"""
import glob
import hashlib
import json
import os
import subprocess
import sys

GOLDEN = "tests/demos/heretic/golden"
MANIFEST = "tests/demos/heretic/manifest"
AUDIT = ".memory/storage-audit.log"


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def snapshot():
    files = sorted(glob.glob(os.path.join(GOLDEN, "*"))) + [MANIFEST]
    audit_lines = 0
    if os.path.exists(AUDIT):
        with open(AUDIT, "rb") as f:
            audit_lines = sum(1 for _ in f)
    return {"head": git("rev-parse", "HEAD").strip(),
            "branch": git("rev-parse", "--abbrev-ref", "HEAD").strip(),
            "porcelain": [l for l in git("status", "--porcelain=v1", "--untracked-files=all").split("\n") if l],
            "sha256": {p: sha256(p) if os.path.isfile(p) else None for p in files},
            "audit_lines": audit_lines}


if __name__ == "__main__":
    with open(sys.argv[1], "w") as f:
        json.dump(snapshot(), f, indent=2)
