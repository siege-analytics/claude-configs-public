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

# --- Codex hostile-review F2-F5 lock-in fixtures (issue #760) ---

# (g) F2: use INSIDE `if not FLAG:` body -- that IS the unavailable branch, must fire
cat > "$TMP/g.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    if not SHAPELY_AVAILABLE:
        return shapely.geometry.Polygon(coords)
    return None
EOF
OUT=$(python3 "$SCAN" "$TMP/g.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(g) F2 use inside 'if not FLAG:' body: writing-code-8 fires"
else
    bad "(g) F2 use inside 'if not FLAG:' body" "out=$OUT"
fi

# (h) F3: `if FLAG: return` followed by use -- fallthrough means FLAG false, must fire
cat > "$TMP/h.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    if SHAPELY_AVAILABLE:
        return None
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/h.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(h) F3 positive-early-return doesn't establish truthy: writing-code-8 fires"
else
    bad "(h) F3 positive early return" "out=$OUT"
fi

# (i) F4: compound `if FLAG and other: return` doesn't prove FLAG, must fire
cat > "$TMP/i.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords, other):
    if SHAPELY_AVAILABLE and other:
        return None
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/i.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(i) F4 compound test doesn't establish truthy: writing-code-8 fires"
else
    bad "(i) F4 compound establish" "out=$OUT"
fi

# (j) F5: private helper docstring mentions flag but no caller-contract phrase, must fire
cat > "$TMP/j.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def _make_polygon_impl(coords):
    """SHAPELY_AVAILABLE is a module-level flag."""
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/j.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(j) F5 private helper bare flag mention: writing-code-8 fires"
else
    bad "(j) F5 bare docstring mention" "out=$OUT"
fi

# (k) F5 counterpart: docstring names flag AND has caller-contract phrase, silent
cat > "$TMP/k.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def _make_polygon_impl(coords):
    """Caller must check SHAPELY_AVAILABLE before invoking."""
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/k.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(k) F5 private helper w/ caller-contract phrase: writing-code-8 silent"
else
    bad "(k) F5 with caller contract" "out=$OUT"
fi

# (l) F2 counterpart: else-branch of `if not FLAG:` IS guarded (flag truthy there)
cat > "$TMP/l.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    if not SHAPELY_AVAILABLE:
        return None
    else:
        return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/l.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(l) F2 counterpart else-branch of 'if not FLAG:': writing-code-8 silent"
else
    bad "(l) F2 counterpart else-branch" "out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
