#!/bin/bash
# Test: writing-releases:3 detector — deprecation message must anchor removal (#771 m-1)
#
# Message must contain BOTH a version-or-date anchor AND a removal keyword
# (remove/removed/dropped/slated for/target/EOL).

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

fires_wr3() {
    echo "$1" | grep -q "writing-releases-3"
}

# (a) DeprecationWarning with version + keyword — silent
cat > "$TMP/a.py" <<'EOF'
raise DeprecationWarning("X deprecated since v3.15.0; will be removed in v3.17.0")
EOF
OUT=$(python3 "$SCAN" "$TMP/a.py" 2>&1)
if ! fires_wr3 "$OUT"; then
    ok "(a) version + 'removed' — silent"
else
    bad "(a) both anchors" "out=$OUT"
fi

# (b) bare "will be removed in a future release" (no version) — fires
cat > "$TMP/b.py" <<'EOF'
raise DeprecationWarning("foo, will be removed in a future release")
EOF
OUT=$(python3 "$SCAN" "$TMP/b.py" 2>&1)
if fires_wr3 "$OUT"; then
    ok "(b) no version anchor — fires"
else
    bad "(b) no version" "out=$OUT"
fi

# (c) version present but no removal keyword — fires
cat > "$TMP/c.py" <<'EOF'
raise DeprecationWarning("deprecated since v1.0.0; use bar instead")
EOF
OUT=$(python3 "$SCAN" "$TMP/c.py" 2>&1)
if fires_wr3 "$OUT"; then
    ok "(c) no removal keyword — fires"
else
    bad "(c) missing removal-kw" "out=$OUT"
fi

# (d) date anchor + 'EOL' — silent
cat > "$TMP/d.py" <<'EOF'
raise DeprecationWarning("EOL by 2026-09-01; use Y instead")
EOF
OUT=$(python3 "$SCAN" "$TMP/d.py" 2>&1)
if ! fires_wr3 "$OUT"; then
    ok "(d) date + EOL — silent"
else
    bad "(d) date + EOL" "out=$OUT"
fi

# (e) warnings.warn(msg, DeprecationWarning) with both anchors — silent
cat > "$TMP/e.py" <<'EOF'
import warnings
warnings.warn("foo dropped in v4.0.0", DeprecationWarning)
EOF
OUT=$(python3 "$SCAN" "$TMP/e.py" 2>&1)
if ! fires_wr3 "$OUT"; then
    ok "(e) warnings.warn positional — silent"
else
    bad "(e) warn positional" "out=$OUT"
fi

# (f) warnings.warn with category= kwarg — fires (no anchors)
cat > "$TMP/f.py" <<'EOF'
import warnings
warnings.warn("please update", category=DeprecationWarning)
EOF
OUT=$(python3 "$SCAN" "$TMP/f.py" 2>&1)
if fires_wr3 "$OUT"; then
    ok "(f) warn(category=Deprecation) no anchors — fires"
else
    bad "(f) warn kwarg" "out=$OUT"
fi

# (g) non-deprecation warning (UserWarning) — silent (rule doesn't apply)
cat > "$TMP/g.py" <<'EOF'
raise UserWarning("this is not a deprecation")
EOF
OUT=$(python3 "$SCAN" "$TMP/g.py" 2>&1)
if ! fires_wr3 "$OUT"; then
    ok "(g) UserWarning — silent (out of scope)"
else
    bad "(g) UserWarning false-fire" "out=$OUT"
fi

# (h) implicit string concat spanning two literals — flattens correctly
cat > "$TMP/h.py" <<'EOF'
raise DeprecationWarning("foo, deprecated since v3.15.0. "
                          "Will be removed in v3.17.0.")
EOF
OUT=$(python3 "$SCAN" "$TMP/h.py" 2>&1)
if ! fires_wr3 "$OUT"; then
    ok "(h) implicit concat across literals — silent"
else
    bad "(h) concat flatten" "out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
