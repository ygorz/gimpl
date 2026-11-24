#!/usr/bin/env bash
# Start one eval run: make the run dir, take the "before" snapshot, print the
# claude command to use. Run inside the container from /workspace.
#   eval/start_run.sh <RUN-ID> <TASK-ID> <dev|holdout> <role> [<role> ...]
# Roles are the expected path in order, e.g. planner tester implementer tester fence-reviewer.
# Optional env: CANARY=<string>  MANIFEST_APPROVED=1  ALLOWED_PATHS="a b"
# Storage and retrieval are stdio servers started by the agent files that are
# granted them (mcpServers frontmatter), so there are no ports to start here.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ $# -lt 3 ]; then
  echo "usage: eval/start_run.sh <RUN-ID> <TASK-ID> <dev|holdout> [role ...]" >&2; exit 2
fi
RUN_ID=$1; TASK_ID=$2; KIND=$3; shift 3
case "$KIND" in dev|holdout) ;; *) echo "kind must be dev or holdout" >&2; exit 2 ;; esac
DIR=".eval-artifacts/runs/$KIND/$RUN_ID"
if [ -e "$DIR" ]; then echo "ERROR: $DIR already exists; pick a new RUN-ID" >&2; exit 1; fi
mkdir -p "$DIR"

SESSION_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
python3 eval/snapshot.py "$DIR/git-before.json"

RUN_ID="$RUN_ID" TASK_ID="$TASK_ID" KIND="$KIND" SESSION_ID="$SESSION_ID" DIR="$DIR" \
python3 - "$@" <<'EOF'
import json, os, sys
from datetime import datetime, timezone
e = os.environ
before = json.load(open(os.path.join(e["DIR"], "git-before.json")))
meta = {"run_id": e["RUN_ID"], "task_id": e["TASK_ID"], "kind": e["KIND"],
        "expected_path": sys.argv[1:], "session_id": e["SESSION_ID"],
        "start_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_offset_before": before["audit_lines"],
        "manifest_write_approved": e.get("MANIFEST_APPROVED") == "1"}
if e.get("CANARY"):
    meta["canary"] = e["CANARY"]
if e.get("ALLOWED_PATHS"):
    meta["allowed_paths"] = e["ALLOWED_PATHS"].split()
json.dump(meta, open(os.path.join(e["DIR"], "run.json"), "w"), indent=2)
EOF

# Audit logs (git-ignored): logs/storage-audit-log.jsonl, logs/retrieval-audit-log.jsonl
mkdir -p logs

echo "Run dir: $DIR"
echo "Expected path: ${*:-main session only}"
echo "Now start Claude Code from /workspace with exactly:"
echo "  claude --session-id $SESSION_ID"
echo "When the run ends, exit Claude and run: eval/finish_run.sh $DIR"
