#!/bin/bash
# Test: writing-tests:5 detector in scan_ast.py (#56)

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

# Set up a git-repo-shaped tree so _test_files_for_source finds .git
mkdir -p "$TMP/repo/pkg" "$TMP/repo/tests"
git init -q "$TMP/repo"

# Isolate writing-tests-5 by grepping specifically for that rule token
# (other rules like writing-code-7 may also fire on these fixtures; those
# are covered by their own test suites).

fires_wt5() {
    echo "$1" | grep -q "writing-tests-5"
}

# (a) except with no matching test file: writing-tests-5 fires
cat > "$TMP/repo/pkg/thing.py" <<'EOF'
def fetch():
    try:
        return do_it()
    except ConnectionError:
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg/thing.py" 2>&1)
if fires_wt5 "$OUT"; then
    ok "(a) except with no test file: writing-tests-5 fires"
else
    bad "(a) no test file" "out=$OUT"
fi

# (b) except with matching pytest.raises in test file: writing-tests-5 silent
cat > "$TMP/repo/tests/test_thing.py" <<'EOF'
import pytest
def test_connection_error():
    with pytest.raises(ConnectionError):
        fetch()
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg/thing.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(b) matching pytest.raises in test file: writing-tests-5 silent"
else
    bad "(b) matching pytest.raises" "out=$OUT"
fi

# (c) except with dotted class + short-name test match
cat > "$TMP/repo/pkg/thing2.py" <<'EOF'
import requests.exceptions
def fetch():
    try:
        return do_it()
    except requests.exceptions.RequestException:
        raise
EOF
cat > "$TMP/repo/tests/test_thing2.py" <<'EOF'
import pytest
def test_request_error():
    with pytest.raises(RequestException):
        fetch()
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg/thing2.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(c) dotted class matched by short-name in test: writing-tests-5 silent"
else
    bad "(c) dotted-class match" "out=$OUT"
fi

# (d) except with noqa carve-out: writing-tests-5 silent (writing-code-7 may still fire on Pass)
cat > "$TMP/repo/pkg/thing3.py" <<'EOF'
def cleanup():
    try:
        stop_it()
    except OSError:  # noqa: writing-tests-5 (finally-cleanup, best-effort)
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg/thing3.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(d) noqa: writing-tests-5 carve-out: silent"
else
    bad "(d) noqa carve-out" "out=$OUT"
fi

# (e) test files are exempt from the rule
cat > "$TMP/repo/tests/test_selfref.py" <<'EOF'
import pytest
def test_something():
    try:
        pass
    except OSError:
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/tests/test_selfref.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(e) test file exempt from writing-tests:5"
else
    bad "(e) test file exempt" "out=$OUT"
fi

# (f) bare except: no class name, skipped (no fire regardless of test file)
cat > "$TMP/repo/pkg/thing4.py" <<'EOF'
def loose():
    try:
        risky()
    except:
        pass
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg/thing4.py" 2>&1); RC=$?
# writing-code:7 will also fire on bare-except-pass; we care that writing-tests-5 is silent
if ! echo "$OUT" | grep -q "writing-tests-5"; then
    ok "(f) bare except: writing-tests-5 silent (writing-code:7 handles bare)"
else
    bad "(f) bare except tests-5 fired unexpectedly" "out=$OUT"
fi

# --- Codex hostile-review F6-F8 lock-in fixtures (issue #760) ---

# (g) F6: namespaced test layout tests/pkg/sub/test_thing.py must be discovered
mkdir -p "$TMP/repo/pkg2/sub" "$TMP/repo/tests/pkg2/sub"
cat > "$TMP/repo/pkg2/sub/thing.py" <<'EOF'
def fetch():
    try:
        return do_it()
    except ConnectionError:
        raise
EOF
cat > "$TMP/repo/tests/pkg2/sub/test_thing.py" <<'EOF'
import pytest
def test_connection_error():
    with pytest.raises(ConnectionError):
        fetch()
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg2/sub/thing.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(g) F6 namespaced test layout tests/pkg2/sub/test_thing.py discovered: silent"
else
    bad "(g) F6 namespaced test layout" "out=$OUT"
fi

# (h) F7: comment/TODO substring must NOT count as coverage
mkdir -p "$TMP/repo/pkg3"
cat > "$TMP/repo/pkg3/thing.py" <<'EOF'
def fetch():
    try:
        return do_it()
    except FileNotFoundError:
        raise
EOF
cat > "$TMP/repo/tests/test_thing.py" <<'EOF'
def test_placeholder():
    # TODO: add with pytest.raises(FileNotFoundError) someday
    assert True
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg3/thing.py" 2>&1)
if fires_wt5 "$OUT"; then
    ok "(h) F7 comment/TODO does not satisfy coverage: fires"
else
    bad "(h) F7 comment satisfies coverage" "out=$OUT"
fi

# (i) F7 counterpart: a real pytest.raises call DOES satisfy coverage
cat > "$TMP/repo/tests/test_thing.py" <<'EOF'
import pytest
def test_placeholder():
    with pytest.raises(FileNotFoundError):
        fetch()
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg3/thing.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(i) F7 counterpart real pytest.raises call: silent"
else
    bad "(i) F7 counterpart real call" "out=$OUT"
fi

# (j) F8: bare noqa (no reason) must NOT count as carve-out
mkdir -p "$TMP/repo/pkg4"
cat > "$TMP/repo/pkg4/thing.py" <<'EOF'
def cleanup():
    try:
        stop_it()
    except OSError:  # noqa: writing-tests-5
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg4/thing.py" 2>&1)
if fires_wt5 "$OUT"; then
    ok "(j) F8 bare noqa without reason: fires"
else
    bad "(j) F8 bare noqa" "out=$OUT"
fi

# (k) F8 counterpart: noqa with reason IS accepted as carve-out
cat > "$TMP/repo/pkg4/thing.py" <<'EOF'
def cleanup():
    try:
        stop_it()
    except OSError:  # noqa: writing-tests-5 (best-effort cleanup, safe to swallow)
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg4/thing.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(k) F8 counterpart noqa with reason: silent"
else
    bad "(k) F8 counterpart with reason" "out=$OUT"
fi

# (l) F7: unittest self.assertRaises(X) satisfies coverage
mkdir -p "$TMP/repo/pkg5"
cat > "$TMP/repo/pkg5/thing.py" <<'EOF'
def fetch():
    try:
        return do_it()
    except KeyError:
        raise
EOF
cat > "$TMP/repo/tests/test_thing.py" <<'EOF'
import unittest
class T(unittest.TestCase):
    def test_key_error(self):
        with self.assertRaises(KeyError):
            fetch()
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg5/thing.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(l) F7 unittest self.assertRaises: silent"
else
    bad "(l) F7 unittest assertRaises" "out=$OUT"
fi

# --- Round 2 M-3 lock-in: bare or fake reason after noqa must not silence ---

# (m) M-3: noqa with 'xxx' (Codex's exact reproduction) — must fire
mkdir -p "$TMP/repo/pkg6"
cat > "$TMP/repo/pkg6/thing.py" <<'EOF'
def cleanup():
    try:
        stop_it()
    except OSError:  # noqa: writing-tests-5 xxx
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg6/thing.py" 2>&1)
if fires_wt5 "$OUT"; then
    ok "(m) M-3 noqa reason 'xxx' rejected: fires"
else
    bad "(m) M-3 noqa reason 'xxx'" "out=$OUT"
fi

# (n) M-3: noqa with 'tbd' — must fire
cat > "$TMP/repo/pkg6/thing.py" <<'EOF'
def cleanup():
    try:
        stop_it()
    except OSError:  # noqa: writing-tests-5 tbd
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg6/thing.py" 2>&1)
if fires_wt5 "$OUT"; then
    ok "(n) M-3 noqa reason 'tbd' rejected: fires"
else
    bad "(n) M-3 noqa reason 'tbd'" "out=$OUT"
fi

# (o) M-3: noqa with punctuation-only reason '...' — must fire
cat > "$TMP/repo/pkg6/thing.py" <<'EOF'
def cleanup():
    try:
        stop_it()
    except OSError:  # noqa: writing-tests-5 ...
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg6/thing.py" 2>&1)
if fires_wt5 "$OUT"; then
    ok "(o) M-3 noqa reason '...' rejected: fires"
else
    bad "(o) M-3 noqa reason '...'" "out=$OUT"
fi

# (p) M-3: noqa with 'zzzz' (no vowel) — must fire
cat > "$TMP/repo/pkg6/thing.py" <<'EOF'
def cleanup():
    try:
        stop_it()
    except OSError:  # noqa: writing-tests-5 zzzz
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg6/thing.py" 2>&1)
if fires_wt5 "$OUT"; then
    ok "(p) M-3 noqa reason 'zzzz' (no vowel) rejected: fires"
else
    bad "(p) M-3 noqa reason 'zzzz'" "out=$OUT"
fi

# (q) M-3 counterpart: real word reason 'cleanup' — silent (accepted carve-out)
cat > "$TMP/repo/pkg6/thing.py" <<'EOF'
def cleanup():
    try:
        stop_it()
    except OSError:  # noqa: writing-tests-5 cleanup
        raise
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg6/thing.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(q) M-3 noqa reason 'cleanup' accepted: silent"
else
    bad "(q) M-3 noqa reason 'cleanup'" "out=$OUT"
fi

# --- m-3 (#771) lock-in: arg walker handles Subscript / Starred ---

# (r) m-3: pytest.raises(Optional[ExcClass]) — silent (Subscript unwrapped)
mkdir -p "$TMP/repo/pkg7"
cat > "$TMP/repo/pkg7/thing.py" <<'EOF'
def go():
    try:
        return do_it()
    except FileExistsError:
        raise
EOF
cat > "$TMP/repo/tests/test_thing.py" <<'EOF'
import pytest
from typing import Optional
def test_conn_error():
    with pytest.raises(Optional[FileExistsError]):
        go()
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg7/thing.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(r) m-3 pytest.raises(Optional[Exc]) covers: silent"
else
    bad "(r) m-3 Optional[Exc] not recognized" "out=$OUT"
fi

# (s) m-3: pytest.raises(Union[A, B]) — silent (Subscript+Tuple recursed)
mkdir -p "$TMP/repo/pkg8"
cat > "$TMP/repo/pkg8/thing.py" <<'EOF'
def go():
    try:
        return do_it()
    except LookupError:
        raise
EOF
cat > "$TMP/repo/tests/test_thing.py" <<'EOF'
import pytest
from typing import Union
def test_lookup():
    with pytest.raises(Union[LookupError, ValueError]):
        go()
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg8/thing.py" 2>&1)
if ! fires_wt5 "$OUT"; then
    ok "(s) m-3 pytest.raises(Union[A, B]) covers: silent"
else
    bad "(s) m-3 Union[A, B] not recognized" "out=$OUT"
fi

# (t) m-3: pytest.raises(*exc_tuple) — starred does NOT provide coverage; fires
mkdir -p "$TMP/repo/pkg9"
cat > "$TMP/repo/pkg9/thing.py" <<'EOF'
def go():
    try:
        return do_it()
    except IndexError:
        raise
EOF
cat > "$TMP/repo/tests/test_thing.py" <<'EOF'
import pytest
exc_tuple = (IndexError,)
def test_lookup():
    with pytest.raises(*exc_tuple):
        go()
EOF
OUT=$(python3 "$SCAN" "$TMP/repo/pkg9/thing.py" 2>&1)
if fires_wt5 "$OUT"; then
    ok "(t) m-3 pytest.raises(*starred) not statically resolvable: fires"
else
    bad "(t) m-3 starred false-negative" "out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
