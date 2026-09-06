#!/bin/bash
# Test: writing-code:8 detector in scan_ast.py (#57)

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCAN="$SCRIPT_DIR/scan_ast.py"

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s\n' "$1"; printf '         %s\n' "$2"; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# (a) unguarded callsite: fires
cat > "$TMP/a.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    return shapely.geometry.Polygon(coords)
EOF
# Isolate writing-code:8 by grepping specifically for that rule token.
# Other rules (writing-tests-5, writing-code-7) may also fire on these
# fixtures — those are covered by their own test suites; we only care
# whether writing-code-8 fires or stays silent here.

fires_wc8() {
    echo "$1" | grep -q "writing-code-8"
}

OUT=$(python3 "$SCAN" "$TMP/a.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(a) unguarded callsite: writing-code-8 fires"
else
    bad "(a) unguarded callsite" "out=$OUT"
fi

# (b) early-return guard: no fire
cat > "$TMP/b.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    if not SHAPELY_AVAILABLE:
        raise RuntimeError("required")
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/b.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(b) early-return guard: writing-code-8 silent"
else
    bad "(b) early-return guard" "out=$OUT"
fi

# (c) if-body-guard: no fire
cat > "$TMP/c.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    if SHAPELY_AVAILABLE:
        return shapely.geometry.Polygon(coords)
    return None
EOF
OUT=$(python3 "$SCAN" "$TMP/c.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(c) if-body-guard: writing-code-8 silent"
else
    bad "(c) if-body-guard" "out=$OUT"
fi

# (d) inside try body: no fire (flag can't be False in the try that set it)
cat > "$TMP/d.py" <<'EOF'
try:
    import shapely
    _ = shapely.geometry.Polygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
EOF
OUT=$(python3 "$SCAN" "$TMP/d.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(d) inside try body: writing-code-8 silent"
else
    bad "(d) inside try body" "out=$OUT"
fi

# (e) private helper documents flag: no fire
cat > "$TMP/e.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def _make_polygon_impl(coords):
    """Caller must check SHAPELY_AVAILABLE before calling."""
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/e.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(e) private helper documents flag: writing-code-8 silent"
else
    bad "(e) private helper documents flag" "out=$OUT"
fi

# (f) no optional-import pattern present: no fire (the file just imports shapely regularly)
cat > "$TMP/f.py" <<'EOF'
import shapely

def make_polygon(coords):
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/f.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(f) no optional-import pattern: writing-code-8 silent"
else
    bad "(f) no optional-import" "out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
