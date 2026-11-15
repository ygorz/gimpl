#!/usr/bin/env bash
# Per-tic demo test suite for chocolate-heretic against blasphem.wad (Feature 1).
#
# Reads tests/demos/heretic/manifest (one line per demo:
# "demo gametics trace_sha256 source_commit"), and for each demo:
#   1. checks the WAD and the reference trace sha256,
#   2. runs the demo headless with the fixed run flags (decision-004),
#   3. checks the 'timed N gametics' line against the manifest,
#   4. compares the per-tic trace with the reference by gametic and reports
#      the first tic and field that differ.
#
# Usage: scripts/demo-suite.sh
#
# Exit codes (same as demo1-check.sh): 0 PASS (every demo), 1 FAIL (tic count
# or trace mismatch), 2 setup/precondition error.
# chocolate-heretic exits 255 after a timedemo; that is normal (decision-006).

set -u

# Always run headless: no window or sound device, same as the container
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy

WAD_SHA256="e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

DIR="tests/demos/heretic"
MANIFEST="$DIR/manifest"
WAD="wads/blasphem.wad"
BIN="src/chocolate-heretic"

die() {
    echo "ERROR: $*" >&2
    exit 2
}

# 1. Read the manifest.
[ -f "$MANIFEST" ] || die "$MANIFEST is missing"

demos=()
exp_tics=()
exp_sha=()
while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^[[:space:]]*(#|$) ]]; then
        continue
    fi
    read -r -a f <<< "$line"
    [ "${#f[@]}" -eq 4 ] || die "$MANIFEST: expected 4 fields (demo gametics sha source_commit), got ${#f[@]}: '$line'"
    [[ "${f[0]}" =~ ^[A-Za-z0-9_]+$ ]] || die "$MANIFEST: bad demo name '${f[0]}'"
    [[ "${f[1]}" =~ ^[0-9]+$ ]] || die "$MANIFEST: gametics must be numeric for ${f[0]} (got '${f[1]}')"
    [[ "${f[2]}" =~ ^[0-9a-fA-F]{64}$ ]] || die "$MANIFEST: sha256 must be 64 hex characters for ${f[0]} (got '${f[2]}')"
    demos+=("${f[0]}")
    exp_tics+=("${f[1]}")
    exp_sha+=("${f[2],,}")
done < "$MANIFEST"

[ "${#demos[@]}" -gt 0 ] || die "$MANIFEST has no demo lines"

# 2. Setup checks: IWAD, binary, reference traces.
[ -f "$WAD" ] || die "$WAD is missing"
actual_sha="$(sha256sum "$WAD" | cut -d' ' -f1)"
if [ "$actual_sha" != "$WAD_SHA256" ]; then
    die "$WAD sha256 mismatch: expected $WAD_SHA256, got $actual_sha"
fi
echo "IWAD OK: $WAD ($actual_sha)"

[ -x "$BIN" ] || die "$BIN is missing or not executable (build it first)"

for i in "${!demos[@]}"; do
    demo="${demos[$i]}"
    ref="$DIR/golden/$demo.tics"
    [ -f "$ref" ] || die "$ref is missing"
    actual_sha="$(sha256sum "$ref" | cut -d' ' -f1)"
    if [ "$actual_sha" != "${exp_sha[$i]}" ]; then
        die "$ref sha256 mismatch: expected ${exp_sha[$i]}, got $actual_sha"
    fi
    echo "trace OK: $ref ($actual_sha)"
done

# 3. Run each demo headless into a temp dir outside the repo.
TMP="$(mktemp -d "${TMPDIR:-/tmp}/demo-suite.XXXXXX")" || die "mktemp failed"
trap 'rm -rf "$TMP"' EXIT

# Compare two traces by gametic. Prints nothing on a match, or one line for
# the first (lowest gametic) difference.
compare_traces() {
    awk -v REFNAME="$1" -v GOTNAME="$2" '
    function note(g, msg) {
        if (!found || (g + 0) < (best + 0)) { best = g; bmsg = msg; found = 1 }
    }
    FNR == 1 {
        filenum++
        if (filenum == 1) {
            n = split($0, h, " ")
            nn = 0
            for (k = 1; k <= n; k++) {
                if (h[k] == "{pN") {
                    for (m = 1; m <= 11 && k + m <= n; m++) {
                        nm = h[k + m]
                        gsub(/[{}]/, "", nm)
                        fname[m] = nm
                        nn++
                    }
                    break
                }
            }
        }
        next
    }
    {
        g = $1
        if (filenum == 1) {
            if (g in ref) note(g, "gametic " g ": duplicate in " REFNAME)
            else ref[g] = $0
        } else {
            if (g in got) note(g, "gametic " g ": duplicate in " GOTNAME)
            else got[g] = $0
        }
    }
    END {
        for (g in ref) {
            if (!(g in got)) { note(g, "gametic " g ": missing in got"); continue }
            if (ref[g] == got[g]) continue
            na = split(ref[g], a, " ")
            nb = split(got[g], b, " ")
            bad = (na != nb)
            if (!bad) {
                for (i = 4; i <= na; i += 12) if (a[i] != b[i]) { bad = 1; break }
            }
            if (bad) { note(g, "gametic " g ": player set/field count differs"); continue }
            for (i = 2; i <= na; i++) {
                if (a[i] != b[i]) {
                    if (i <= 3) name = (i == 2) ? "rndindex" : "prndindex"
                    else {
                        pos = (i - 4) % 12
                        blk = i - pos
                        name = a[blk] "." ((pos >= 1 && pos in fname) ? fname[pos] : "field" pos)
                    }
                    note(g, "gametic " g ": " name " expected " a[i] " got " b[i])
                    break
                }
            }
        }
        for (g in got) if (!(g in ref)) note(g, "gametic " g ": extra in got")
        if (found) print bmsg
    }
    ' "$3" "$4"
}

fails=0
for i in "${!demos[@]}"; do
    demo="${demos[$i]}"
    expected="${exp_tics[$i]}"
    ref="$DIR/golden/$demo.tics"
    run="$TMP/$demo.tics"

    # chocolate-heretic exits 255 after a timedemo (I_Error); that is normal.
    output="$("$BIN" -iwad "$WAD" -timedemo "$demo" -nodraw -nosound -tichash "$run" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ] && [ "$rc" -ne 255 ]; then
        echo "$output" >&2
        die "$demo: chocolate-heretic exited with unexpected code $rc"
    fi

    timed_line="$(printf '%s\n' "$output" | grep -m1 -E 'timed [0-9]+ gametics')"
    if [ -z "$timed_line" ]; then
        echo "$output" >&2
        die "$demo: no 'timed N gametics' line in output (exit code $rc)"
    fi
    tics="$(printf '%s\n' "$timed_line" | sed -E 's/.*timed ([0-9]+) gametics.*/\1/')"

    echo "$timed_line"
    echo "engine exit code: $rc"

    [ -s "$run" ] || die "$demo: run trace $run is missing or empty"

    demo_ok=1
    if [ "$tics" -ne "$expected" ]; then
        echo "FAIL: $demo $tics gametics != expected $expected"
        demo_ok=0
    fi

    # Header must match exactly; otherwise it is a setup error.
    ref_head="$(head -n1 "$ref")"
    run_head="$(head -n1 "$run")"
    if [ "$ref_head" != "$run_head" ]; then
        echo "reference header: $ref_head" >&2
        echo "run header:       $run_head" >&2
        die "$demo: trace header mismatch"
    fi

    diff_line="$(compare_traces "$ref" "$run" "$ref" "$run")"
    if [ -n "$diff_line" ]; then
        echo "$diff_line"
        echo "FAIL: $demo trace differs from $ref"
        demo_ok=0
    fi

    if [ "$demo_ok" -eq 1 ]; then
        echo "PASS: $demo $tics gametics, trace matches"
    else
        fails=$((fails + 1))
    fi
done

if [ "$fails" -eq 0 ]; then
    echo "PASS: ${#demos[@]} demo(s)"
    exit 0
else
    echo "FAIL: $fails of ${#demos[@]} demo(s) failed"
    exit 1
fi
