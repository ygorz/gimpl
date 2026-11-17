#!/usr/bin/env bash
# Finish one eval run: copy the session transcript (main + subagents), the
# audit-log slice, the "after" snapshot, new run summaries and metrics into
# the run dir. Run inside the same container, after exiting Claude Code.
#   eval/finish_run.sh .eval-artifacts/runs/<dev|holdout>/<RUN-ID>
# The "after" snapshot also hashes every file the "before" snapshot hashed.
# Optional env: CLAUDE_PROJECTS_DIR (default: ${CLAUDE_CONFIG_DIR:-~/.claude}/projects/-workspace)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
DIR=${1:?usage: eval/finish_run.sh <run-dir>}
DIR=${DIR%/}
[ -f "$DIR/run.json" ] || { echo "ERROR: $DIR/run.json not found" >&2; exit 1; }

SESSION_ID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["session_id"])' "$DIR/run.json")
PROJECTS=${CLAUDE_PROJECTS_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/-workspace}
SRC="$PROJECTS/$SESSION_ID.jsonl"
if [ ! -f "$SRC" ]; then
  echo "ERROR: no transcript at $SRC. Was claude started with --session-id $SESSION_ID from /workspace?" >&2
  exit 1
fi
cp "$SRC" "$DIR/session.jsonl"
mkdir -p "$DIR/subagents"
if [ -d "$PROJECTS/$SESSION_ID/subagents" ]; then
  cp -r "$PROJECTS/$SESSION_ID/subagents/." "$DIR/subagents/"
fi
echo "transcript: session.jsonl + $(find "$DIR/subagents" -name 'agent-*.jsonl' | wc -l) subagent file(s)"

OFFSET=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["audit_offset_before"])' "$DIR/run.json")
if [ -f .memory/storage-audit.log ]; then
  tail -n +"$((OFFSET + 1))" .memory/storage-audit.log > "$DIR/audit.jsonl"
else
  : > "$DIR/audit.jsonl"
fi
echo "audit: $(wc -l < "$DIR/audit.jsonl") new line(s)"

python3 eval/snapshot.py "$DIR/git-after.json" "$DIR/git-before.json"
[ -f /tmp/retrieval.log ] && cp /tmp/retrieval.log "$DIR/retrieval-tmp.log"

DIR="$DIR" python3 - <<'EOF'
import json, os, shutil
from datetime import datetime, timezone
d = os.environ["DIR"]
meta = json.load(open(f"{d}/run.json"))
meta["end_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
json.dump(meta, open(f"{d}/run.json", "w"), indent=2)
before = set(json.load(open(f"{d}/git-before.json"))["porcelain"])
os.makedirs(f"{d}/run-summary", exist_ok=True)
for line in json.load(open(f"{d}/git-after.json"))["porcelain"]:
    path = line[3:].split(" -> ")[-1].strip('"')
    if line not in before and path.startswith("docs/runs/") and path.endswith(".md"):
        shutil.copy(path, f"{d}/run-summary/")
        print("run summary:", path)
EOF

if python3 eval/test_deterministic.py --metrics "$DIR" > /dev/null 2>&1; then
  echo "metrics: $DIR/metrics.json"
else
  echo "metrics: not computed (artifacts malformed; the deterministic suite will say why)"
fi
echo "Next: python3 eval/test_deterministic.py $DIR"
