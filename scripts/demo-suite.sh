#!/usr/bin/env bash
# Per-tic demo test suite for chocolate-heretic against blasphem.wad (Feature 1).
#
# STUB: prints usage and the planned steps, then exits 0. It does not run
# any demo yet. Use scripts/demo1-check.sh for the current DEMO1 check.
# What Feature 1 still needs is listed in docs/smoke-tests/demo-suite.md.
#
# Usage: scripts/demo-suite.sh
#
# Planned exit codes (same as demo1-check.sh): 0 PASS, 1 FAIL (trace or tic
# mismatch), 2 setup/precondition errors.

set -u

cat <<'EOF'
demo-suite.sh: STUB - no demos are run yet.

Usage: scripts/demo-suite.sh

Planned steps (DEMO1 only for now):
  1. Verify wads/blasphem.wad sha256 (same pinned value as demo1-check.sh).
  2. Verify each reference trace in tests/demos/heretic/golden/ against the
     sha256 recorded in tests/demos/heretic/manifest.
  3. Run headless: src/chocolate-heretic -iwad wads/blasphem.wad
       -timedemo demo1 -nodraw -nosound -tichash <tmpfile>
  4. Check the 'timed N gametics' line against the manifest (4227 for DEMO1).
  5. Compare the per-tic trace (gametic, rndindex, prndindex, player fields)
     with tests/demos/heretic/golden/demo1.tics; on FAIL, print the first
     tic that differs and which field changed.

Planned exit codes: 0 PASS, 1 FAIL, 2 setup/precondition error.
EOF

exit 0
