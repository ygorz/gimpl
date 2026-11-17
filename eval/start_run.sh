#!/usr/bin/env bash
# Start one eval run: make the run dir, take the "before" snapshot, print the
# claude command to use. Run inside the container from /workspace.
#   eval/start_run.sh <RUN-ID> <TASK-ID> <dev|holdout> <role> [<role> ...]
# Roles are the expected path in order, e.g. planner tester implementer tester fence-reviewer.
# Optional env: CANARY=<string>  MANIFEST_APPROVED=1  ALLOWED_PATHS="a b"  START_SERVERS=1
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

port_open() { python3 -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(s.connect_ex(('127.0.0.1',$1)))"; }
if [ "${START_SERVERS:-0}" = "1" ]; then
  if port_open 8001 || port_open 8002; then
    echo "ERROR: a server is already on 8001/8002; stop it or run without START_SERVERS=1" >&2; exit 1
  fi
  STORAGE_DB_PATH=/workspace/.memory/storage.db STORAGE_AUDIT_PATH=/workspace/.memory/storage-audit.log \
    nohup python3 mcp/storage/server.py --port 8001 --host 127.0.0.1 >"$DIR/storage.log" 2>&1 &
  RETRIEVAL_REFERENCE_DIR=/workspace/.memory/reference/lessons \
    nohup python3 mcp/retrieval/server.py --port 8002 --host 127.0.0.1 >"$DIR/retrieval.log" 2>&1 &
  for _ in $(seq 1 120); do port_open 8001 && port_open 8002 && break; sleep 1; done
fi
for p in 8001 8002; do
  port_open $p || { echo "ERROR: nothing listening on 127.0.0.1:$p (storage 8001, retrieval 8002)" >&2; exit 1; }
done

echo "Run dir: $DIR"
echo "Expected path: ${*:-main session only}"
echo "Now start Claude Code from /workspace with exactly:"
echo "  claude --session-id $SESSION_ID"
echo "When the run ends, exit Claude and run: eval/finish_run.sh $DIR"
