#!/bin/bash
# Test: writing-code:9 detector — silently-dropped parameters (#771 m-1)

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

fires_wc9() {
    echo "$1" | grep -q "writing-code-9"
}

# (a) defaulted param never referenced — fires
cat > "$TMP/a.py" <<'EOF'
def go(x=None, unused_param=42):
    return x
EOF
OUT=$(python3 "$SCAN" "$TMP/a.py" 2>&1)
if fires_wc9 "$OUT"; then
    ok "(a) defaulted unused param — fires"
else
    bad "(a) unused param" "out=$OUT"
fi

# (b) defaulted param referenced — silent
cat > "$TMP/b.py" <<'EOF'
def go(x=None, y=42):
    return x + y
EOF
OUT=$(python3 "$SCAN" "$TMP/b.py" 2>&1)
if ! fires_wc9 "$OUT"; then
    ok "(b) defaulted referenced param — silent"
else
    bad "(b) referenced param" "out=$OUT"
fi

# (c) required param (no default) never referenced — silent (rule doesn't fire)
cat > "$TMP/c.py" <<'EOF'
def go(x, y):
    return x
EOF
OUT=$(python3 "$SCAN" "$TMP/c.py" 2>&1)
if ! fires_wc9 "$OUT"; then
    ok "(c) required unused param — silent (rule scope)"
else
    bad "(c) required unused" "out=$OUT"
fi

# (d) **kwargs spread with forwarding — silent
cat > "$TMP/d.py" <<'EOF'
def wrap(fn, timeout=None, **kwargs):
    return fn(**kwargs, timeout=timeout)
EOF
OUT=$(python3 "$SCAN" "$TMP/d.py" 2>&1)
if ! fires_wc9 "$OUT"; then
    ok "(d) defaulted forwarded via kwargs — silent"
else
    bad "(d) kwargs forward" "out=$OUT"
fi

# (e) unused param documented in docstring — silent (carve-out)
cat > "$TMP/e.py" <<'EOF'
def go(x, deprecated_arg=None):
    """deprecated_arg is a no-op; kept for backwards compatibility."""
    return x
EOF
OUT=$(python3 "$SCAN" "$TMP/e.py" 2>&1)
if ! fires_wc9 "$OUT"; then
    ok "(e) unused param documented in docstring — silent"
else
    bad "(e) doc carve-out" "out=$OUT"
fi

# (f) async function with silently-dropped param — fires
cat > "$TMP/f.py" <<'EOF'
async def go(x=None, unused=42):
    return x
EOF
OUT=$(python3 "$SCAN" "$TMP/f.py" 2>&1)
if fires_wc9 "$OUT"; then
    ok "(f) async fn silently-dropped — fires"
else
    bad "(f) async fn" "out=$OUT"
fi

# (g) decorated with allowlist decorator — silent
# Uses functools.wraps which IS in the default decorator allowlist per scan_ast.py
cat > "$TMP/g.py" <<'EOF'
import functools

def outer(fn):
    @functools.wraps(fn)
    def inner(x, unused=42):
        return fn(x)
    return inner
EOF
OUT=$(python3 "$SCAN" "$TMP/g.py" 2>&1)
if ! fires_wc9 "$OUT"; then
    ok "(g) functools.wraps decorated — silent"
else
    bad "(g) decorator allowlist" "out=$OUT"
fi

# --- R3-F1 (#787) lock-in: scoped visitor + no keyword-name blessing + no bare kwargs-spread ---

# (h) R3-F1a: keyword-argument NAME match must NOT count as use — fires
cat > "$TMP/h.py" <<'EOF'
def wrapper(timeout=30):
    return fn(timeout=10)
EOF
OUT=$(python3 "$SCAN" "$TMP/h.py" 2>&1)
if fires_wc9 "$OUT"; then
    ok "(h) R3-F1a keyword literal name match — fires"
else
    bad "(h) F1a" "out=$OUT"
fi

# (i) R3-F1b: **kwargs spread + named-defaulted param NOT in kwargs — fires
cat > "$TMP/i.py" <<'EOF'
def wrapper(fn, dropped=42, **kwargs):
    return fn(**kwargs)
EOF
OUT=$(python3 "$SCAN" "$TMP/i.py" 2>&1)
if fires_wc9 "$OUT"; then
    ok "(i) R3-F1b named param separate from **kwargs — fires"
else
    bad "(i) F1b" "out=$OUT"
fi

# (j) R3-F1c: nested function shadow — inner's `x` is not outer's — fires
cat > "$TMP/j.py" <<'EOF'
def outer(x=1):
    def inner(x):
        return x
    return inner
EOF
OUT=$(python3 "$SCAN" "$TMP/j.py" 2>&1)
if fires_wc9 "$OUT"; then
    ok "(j) R3-F1c nested shadow — fires"
else
    bad "(j) F1c" "out=$OUT"
fi

# (k) R3-F1 counterpart: legit forward with named + **kwargs — silent
cat > "$TMP/k.py" <<'EOF'
def wrap(fn, timeout=None, **kwargs):
    return fn(timeout=timeout, **kwargs)
EOF
OUT=$(python3 "$SCAN" "$TMP/k.py" 2>&1)
if ! fires_wc9 "$OUT"; then
    ok "(k) R3-F1 counterpart legit forward — silent"
else
    bad "(k) F1 counterpart" "out=$OUT"
fi

# (l) R3-F1 escape hatch: **locals() forwarder — silent
cat > "$TMP/l.py" <<'EOF'
def wrap(fn, arg=42):
    return fn(**locals())
EOF
OUT=$(python3 "$SCAN" "$TMP/l.py" 2>&1)
if ! fires_wc9 "$OUT"; then
    ok "(l) R3-F1 **locals() escape hatch — silent"
else
    bad "(l) locals" "out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
