#!/usr/bin/env bash
# Repeatable DEMO1 timedemo check for chocolate-heretic against blasphem.wad.
#
# Usage: scripts/demo1-check.sh
#   EXPECTED_TICS=N  expected gametic count (default 4227)
#
# Exits 0 on PASS, 1 on FAIL, 2 on setup/precondition errors.

set -u

# Always run headless: no window or sound device, same as the container
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy

EXPECTED_TICS="${EXPECTED_TICS:-4227}"
WAD_SHA256="e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

WAD="wads/blasphem.wad"
BIN="src/chocolate-heretic"

die() {
    echo "ERROR: $*" >&2
    exit 2
}

if ! [[ "$EXPECTED_TICS" =~ ^[0-9]+$ ]]; then
    die "EXPECTED_TICS must be a non-negative integer (got '$EXPECTED_TICS')"
fi

# 1. Verify the IWAD.
[ -f "$WAD" ] || die "$WAD is missing"
actual_sha="$(sha256sum "$WAD" | cut -d' ' -f1)"
if [ "$actual_sha" != "$WAD_SHA256" ]; then
    die "$WAD sha256 mismatch: expected $WAD_SHA256, got $actual_sha"
fi
echo "IWAD OK: $WAD ($actual_sha)"

# Build if the binary is missing.
if [ ! -x "$BIN" ]; then
    echo "$BIN not found; building..."
    { ./autogen.sh && make -j"$(nproc)"; } || die "build failed"
    [ -x "$BIN" ] || die "build finished but $BIN is still missing"
fi

# 2. Run the timedemo. chocolate-heretic exits 255 after a timedemo (I_Error).
output="$("$BIN" -iwad "$WAD" -timedemo demo1 -nodraw -nosound 2>&1)"
rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 255 ]; then
    echo "$output" >&2
    die "chocolate-heretic exited with unexpected code $rc"
fi

# 3. Extract "timed N gametics".
timed_line="$(printf '%s\n' "$output" | grep -m1 -E 'timed [0-9]+ gametics')"
if [ -z "$timed_line" ]; then
    echo "$output" >&2
    die "no 'timed N gametics' line in output (exit code $rc)"
fi
tics="$(printf '%s\n' "$timed_line" | sed -E 's/.*timed ([0-9]+) gametics.*/\1/')"

echo "$timed_line"
echo "engine exit code: $rc"

# 4. Compare.
if [ "$tics" -eq "$EXPECTED_TICS" ]; then
    echo "PASS: $tics gametics == expected $EXPECTED_TICS"
    exit 0
else
    echo "FAIL: $tics gametics != expected $EXPECTED_TICS"
    exit 1
fi
