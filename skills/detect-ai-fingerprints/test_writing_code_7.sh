#!/bin/bash
# Test: writing-code:7 detector in scan_ast.py — silent swallow shapes
#
# Covers M-1 (#766): `return 0` / `return 0.0` / `return 0j` must NOT be
# classified as silent swallow (Python's `0 == False` false-positive).
# Also covers the canonical fire/silent shapes to lock the detector's
# public contract.

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

fires_wc7() {
    echo "$1" | grep -q "writing-code-7"
}

# (a) except Exception: pass — fires
cat > "$TMP/a.py" <<'EOF'
def go():
    try:
        do_it()
    except Exception:
        pass
EOF
OUT=$(python3 "$SCAN" "$TMP/a.py" 2>&1)
if fires_wc7 "$OUT"; then
    ok "(a) except Exception: pass — fires"
else
    bad "(a) pass silent-swallow" "out=$OUT"
fi

# (b) except Exception: return None — fires
cat > "$TMP/b.py" <<'EOF'
def go():
    try:
        return do_it()
    except Exception:
        return None
EOF
OUT=$(python3 "$SCAN" "$TMP/b.py" 2>&1)
if fires_wc7 "$OUT"; then
    ok "(b) except: return None — fires"
else
    bad "(b) return None silent-swallow" "out=$OUT"
fi

# (c) except Exception: return False — fires
cat > "$TMP/c.py" <<'EOF'
def go():
    try:
        return do_it()
    except Exception:
        return False
EOF
OUT=$(python3 "$SCAN" "$TMP/c.py" 2>&1)
if fires_wc7 "$OUT"; then
    ok "(c) except: return False — fires"
else
    bad "(c) return False silent-swallow" "out=$OUT"
fi

# (d) M-1: except ValueError: return 0 — must NOT fire (legit typed sentinel)
cat > "$TMP/d.py" <<'EOF'
def count():
    try:
        return do_it()
    except ValueError:
        return 0
EOF
OUT=$(python3 "$SCAN" "$TMP/d.py" 2>&1)
if ! fires_wc7 "$OUT"; then
    ok "(d) M-1: return 0 is a typed sentinel — silent"
else
    bad "(d) M-1 return 0 misclassified" "out=$OUT"
fi

# (e) M-1: except ValueError: return 0.0 — must NOT fire (0.0 == False in Python)
cat > "$TMP/e.py" <<'EOF'
def score():
    try:
        return do_it()
    except ValueError:
        return 0.0
EOF
OUT=$(python3 "$SCAN" "$TMP/e.py" 2>&1)
if ! fires_wc7 "$OUT"; then
    ok "(e) M-1: return 0.0 is a typed sentinel — silent"
else
    bad "(e) M-1 return 0.0 misclassified" "out=$OUT"
fi

# (f) except Exception: raise — must NOT fire (re-raise is loud)
cat > "$TMP/f.py" <<'EOF'
def go():
    try:
        return do_it()
    except Exception:
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/f.py" 2>&1)
if ! fires_wc7 "$OUT"; then
    ok "(f) re-raise is loud — silent"
else
    bad "(f) raise misclassified" "out=$OUT"
fi

# (g) except Exception: log.error(...); return None — fires (log + terminator)
cat > "$TMP/g.py" <<'EOF'
import logging
log = logging.getLogger(__name__)

def go():
    try:
        return do_it()
    except Exception:
        log.error("failed")
        return None
EOF
OUT=$(python3 "$SCAN" "$TMP/g.py" 2>&1)
if fires_wc7 "$OUT"; then
    ok "(g) log + return None — fires"
else
    bad "(g) log + return None" "out=$OUT"
fi

# (h) # noqa: writing-code-7 carve-out — must NOT fire
cat > "$TMP/h.py" <<'EOF'
def go():
    try:
        do_it()
    except Exception:  # noqa: writing-code-7 (best-effort cleanup)
        pass
EOF
OUT=$(python3 "$SCAN" "$TMP/h.py" 2>&1)
if ! fires_wc7 "$OUT"; then
    ok "(h) noqa carve-out — silent"
else
    bad "(h) noqa didn't silence" "out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
