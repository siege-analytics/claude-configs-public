#!/bin/bash
# Test: writing-code:15 detector — unbounded blocking I/O
#
# Covers M-2 (#766): subprocess.Popen(...).communicate() and
# `Popen(...).wait()` chained forms must fire. Also locks in the canonical
# fire/silent shapes for the other UNBOUNDED_IO_SURFACES entries.

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

fires_wc15() {
    echo "$1" | grep -q "writing-code-15"
}

# (a) subprocess.run without timeout — fires
cat > "$TMP/a.py" <<'EOF'
import subprocess
subprocess.run(["ls"])
EOF
OUT=$(python3 "$SCAN" "$TMP/a.py" 2>&1)
if fires_wc15 "$OUT"; then
    ok "(a) subprocess.run() no timeout — fires"
else
    bad "(a) subprocess.run() no timeout" "out=$OUT"
fi

# (b) subprocess.run WITH timeout — silent
cat > "$TMP/b.py" <<'EOF'
import subprocess
subprocess.run(["ls"], timeout=5)
EOF
OUT=$(python3 "$SCAN" "$TMP/b.py" 2>&1)
if ! fires_wc15 "$OUT"; then
    ok "(b) subprocess.run(timeout=5) — silent"
else
    bad "(b) subprocess.run with timeout" "out=$OUT"
fi

# (c) M-2: subprocess.Popen(...).communicate() — fires
cat > "$TMP/c.py" <<'EOF'
import subprocess
def go():
    return subprocess.Popen(["x"]).communicate()
EOF
OUT=$(python3 "$SCAN" "$TMP/c.py" 2>&1)
if fires_wc15 "$OUT"; then
    ok "(c) M-2: subprocess.Popen(...).communicate() — fires"
else
    bad "(c) M-2 subprocess.Popen chain" "out=$OUT"
fi

# (d) M-2: bare Popen(...).wait() chained — fires
cat > "$TMP/d.py" <<'EOF'
from subprocess import Popen
def go():
    return Popen(["x"]).wait()
EOF
OUT=$(python3 "$SCAN" "$TMP/d.py" 2>&1)
if fires_wc15 "$OUT"; then
    ok "(d) M-2: Popen(...).wait() bare-form — fires"
else
    bad "(d) M-2 bare Popen wait" "out=$OUT"
fi

# (e) requests.get without timeout — fires
cat > "$TMP/e.py" <<'EOF'
import requests
requests.get("http://x")
EOF
OUT=$(python3 "$SCAN" "$TMP/e.py" 2>&1)
if fires_wc15 "$OUT"; then
    ok "(e) requests.get() no timeout — fires"
else
    bad "(e) requests.get() no timeout" "out=$OUT"
fi

# (f) requests.get with timeout — silent
cat > "$TMP/f.py" <<'EOF'
import requests
requests.get("http://x", timeout=10)
EOF
OUT=$(python3 "$SCAN" "$TMP/f.py" 2>&1)
if ! fires_wc15 "$OUT"; then
    ok "(f) requests.get(timeout=10) — silent"
else
    bad "(f) requests.get with timeout" "out=$OUT"
fi

# (g) urllib.request.urlopen without timeout — fires
cat > "$TMP/g.py" <<'EOF'
import urllib.request
urllib.request.urlopen("http://x")
EOF
OUT=$(python3 "$SCAN" "$TMP/g.py" 2>&1)
if fires_wc15 "$OUT"; then
    ok "(g) urllib.request.urlopen() no timeout — fires"
else
    bad "(g) urlopen no timeout" "out=$OUT"
fi

# (h) timeout=None WITHOUT audit comment — fires (secondary shape)
cat > "$TMP/h.py" <<'EOF'
import subprocess
subprocess.run(["ls"], timeout=None)
EOF
OUT=$(python3 "$SCAN" "$TMP/h.py" 2>&1)
if fires_wc15 "$OUT"; then
    ok "(h) timeout=None no audit comment — fires"
else
    bad "(h) timeout=None no audit" "out=$OUT"
fi

# (i) timeout=None WITH audit comment — silent
cat > "$TMP/i.py" <<'EOF'
import subprocess
# Deadline enforced upstream by run_with_deadline caller helper
subprocess.run(["ls"], timeout=None)
EOF
OUT=$(python3 "$SCAN" "$TMP/i.py" 2>&1)
if ! fires_wc15 "$OUT"; then
    ok "(i) timeout=None WITH audit comment — silent"
else
    bad "(i) timeout=None with audit comment" "out=$OUT"
fi

# (j) m-5: timeout=0 (int zero) — fires (functionally unbounded)
cat > "$TMP/j.py" <<'EOF'
import subprocess
subprocess.run(["ls"], timeout=0)
EOF
OUT=$(python3 "$SCAN" "$TMP/j.py" 2>&1)
if fires_wc15 "$OUT"; then
    ok "(j) m-5: timeout=0 — fires"
else
    bad "(j) m-5 timeout=0" "out=$OUT"
fi

# (k) m-5: timeout=0.0 (float zero) — fires
cat > "$TMP/k.py" <<'EOF'
import requests
requests.get("http://x", timeout=0.0)
EOF
OUT=$(python3 "$SCAN" "$TMP/k.py" 2>&1)
if fires_wc15 "$OUT"; then
    ok "(k) m-5: timeout=0.0 on requests.get — fires"
else
    bad "(k) m-5 timeout=0.0" "out=$OUT"
fi

# (l) m-5 counterpart: fractional-but-positive timeout=0.001 — silent (bounded)
cat > "$TMP/l.py" <<'EOF'
import subprocess
subprocess.run(["ls"], timeout=0.001)
EOF
OUT=$(python3 "$SCAN" "$TMP/l.py" 2>&1)
if ! fires_wc15 "$OUT"; then
    ok "(l) m-5 counterpart: timeout=0.001 (positive) — silent"
else
    bad "(l) m-5 counterpart" "out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
