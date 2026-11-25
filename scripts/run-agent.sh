#!/usr/bin/env bash
# run-agent.sh: launch one GIMPL agent role in a container with only the
# permissions its entry in docs/governance-policy.md allows.
#
# Usage (from the repo root):
#   ./scripts/run-agent.sh <role> [command...]
#   ./scripts/run-agent.sh fence-reviewer bash
#
# Optional environment:
#   AGENT_IMAGE      image to run (default: gimpl)
#   AGENT_NETWORK    Docker network to attach, e.g. none (default: Docker's
#                    normal network, because Claude Code must reach its API)
#   RUN_AGENT_DRY_RUN=1  print the docker command instead of running it
#
# Works with macOS /bin/bash 3.2 (no associative arrays).
set -euo pipefail

ROLE="${1:?Usage: run-agent.sh <role> [command...]}"
shift

IMAGE="${AGENT_IMAGE:-gimpl}"

# Run from the repo root, so the workspace mount is the whole repository.
if [ ! -f docs/governance-policy.md ] || [ ! -d .claude/agents ]; then
  echo "Run this from the GIMPL repo root (docs/governance-policy.md not found)." >&2
  exit 1
fi

# Deny first: read-only workspace and no memory, then widen only for the
# roles the policy names. A role missing from this list cannot launch.
WORKSPACE_MODE="ro"
MOUNT_MEMORY=0

case "$ROLE" in
  implementer|orchestrator)
    # Policy: workspace read-write, memory mounted
    WORKSPACE_MODE="rw"
    MOUNT_MEMORY=1
    ;;
  planner|fence-reviewer)
    # Policy: workspace read-only, memory mounted (seen read-only)
    WORKSPACE_MODE="ro"
    MOUNT_MEMORY=1
    ;;
  tester|port-planner)
    # Policy: workspace read-write, memory omitted
    WORKSPACE_MODE="rw"
    MOUNT_MEMORY=0
    ;;
  trace-auditor)
    # Policy: workspace read-only, memory omitted. The same as the deny-first
    # default, stated here so the role is governed on purpose, not by omission.
    WORKSPACE_MODE="ro"
    MOUNT_MEMORY=0
    ;;
  *)
    echo "Unknown role: $ROLE" >&2
    echo "This role has no policy entry, so it cannot be launched." >&2
    echo "Roles: orchestrator planner implementer tester fence-reviewer port-planner trace-auditor" >&2
    exit 1
    ;;
esac

ARGS=( run --rm )

# Interactive TTY only when there is one, so scripted runs
# (for example "claude --print ...") also work.
if [ -t 0 ] && [ -t 1 ]; then
  ARGS+=( -it )
else
  ARGS+=( -i )
fi

# Network: not attached to agent-internal, because every role runs Claude
# Code and needs to reach its API. AGENT_NETWORK can narrow it (e.g. none).
if [ -n "${AGENT_NETWORK:-}" ]; then
  ARGS+=( --network "$AGENT_NETWORK" )
fi

# Workspace: the repo, read-only or read-write per policy.
ARGS+=( -v "$(pwd):/workspace:${WORKSPACE_MODE}" )

# Memory: in GIMPL it lives in /workspace/.memory/ (project memory, the
# lessons corpus and the storage database). For "memory omitted", an empty
# tmpfs is mounted over it, so the role cannot see it.
if [ "$MOUNT_MEMORY" -eq 0 ]; then
  ARGS+=( --mount "type=tmpfs,destination=/workspace/.memory" )
fi

# Claude Code login, kept in the claude-auth volume by docker-entrypoint.sh.
ARGS+=( -v claude-auth:/claude-auth )

# Audit logs, written by the MCP servers to /workspace/logs (git-ignored).
# Mounted read-write on its own so read-only roles can still be audited.
ARGS+=( -v "$(pwd)/logs:/workspace/logs:rw" )

# Role identity, read by the MCP servers to decide what this role may call.
ARGS+=( -e "AGENT_ROLE=${ROLE}" )

# Image and optional command (the image default is /bin/bash).
ARGS+=( "$IMAGE" "$@" )

MEMORY_STATE="omitted"
if [ "$MOUNT_MEMORY" -eq 1 ]; then MEMORY_STATE="mounted"; fi
echo "Launching '$ROLE': image=${IMAGE}, workspace=${WORKSPACE_MODE}, memory=${MEMORY_STATE}" >&2

if [ "${RUN_AGENT_DRY_RUN:-0}" = "1" ]; then
  echo "docker ${ARGS[*]}"
  exit 0
fi

mkdir -p logs

exec docker "${ARGS[@]}"
