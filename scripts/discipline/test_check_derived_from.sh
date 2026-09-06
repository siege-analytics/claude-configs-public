#!/bin/bash
# Test: scripts/discipline/check-derived-from.py

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCRIPT="$SCRIPT_DIR/check-derived-from.py"

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s\n' "$1"; printf '         %s\n' "$2"; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Fixture repo: one file with 3 commits so we can pin different revs
REPO="$TMP/repo"
git init -q "$REPO"
cd "$REPO"
git config user.email test@test
git config user.name test
mkdir -p upstream
printf 'v1\n' > upstream/fact.md
git add upstream/fact.md
git commit -q -m "v1 upstream"
REV1=$(git rev-parse HEAD)
printf 'v2\n' > upstream/fact.md
git commit -q -am "v2 upstream"
REV2=$(git rev-parse HEAD)
cd - >/dev/null

# ---- (a) current: rev is the tip for the path
cat > "$REPO/current.md" <<EOF
---
derived_from:
  - path: upstream/fact.md
    rev: $REV2
---

body
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$REPO" "$REPO/current.md" 2>&1)
RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -q "1 current"; then
    ok "(a) rev is the tip: current"
else
    bad "(a) rev is the tip: current" "rc=$RC out=$OUT"
fi

# ---- (b) superseded: rev has commits after it that touched the path
cat > "$REPO/superseded.md" <<EOF
---
derived_from:
  - path: upstream/fact.md
    rev: $REV1
---

body
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$REPO" "$REPO/superseded.md" 2>&1)
RC=$?
if [ "$RC" != "0" ] && echo "$OUT" | grep -q "SUPERSEDED"; then
    ok "(b) older rev with newer commits: superseded"
else
    bad "(b) older rev with newer commits: superseded" "rc=$RC out=$OUT"
fi

# ---- (c) unresolved: rev does not exist
cat > "$REPO/unresolved.md" <<'EOF'
---
derived_from:
  - path: upstream/fact.md
    rev: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
---

body
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$REPO" "$REPO/unresolved.md" 2>&1)
RC=$?
if [ "$RC" != "0" ] && echo "$OUT" | grep -q "UNRESOLVED"; then
    ok "(c) rev does not exist: unresolved"
else
    bad "(c) rev does not exist: unresolved" "rc=$RC out=$OUT"
fi

# ---- (d) unresolved: rev exists but doesn't touch the path
mkdir -p "$REPO/other"
cd "$REPO"
printf 'other\n' > other/thing.md
git add other/thing.md
git commit -q -m "other file touched, not fact.md"
UNRELATED_REV=$(git rev-parse HEAD)
cd - >/dev/null

cat > "$REPO/other-rev.md" <<EOF
---
derived_from:
  - path: upstream/fact.md
    rev: $UNRELATED_REV
---

body
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$REPO" "$REPO/other-rev.md" 2>&1)
RC=$?
if [ "$RC" != "0" ] && echo "$OUT" | grep -q "UNRESOLVED"; then
    ok "(d) rev exists but does not touch path: unresolved (not current)"
else
    bad "(d) rev exists but does not touch path" "rc=$RC out=$OUT"
fi

# ---- (e) mixed list: one current, one superseded, one unresolved
cat > "$REPO/mixed.md" <<EOF
---
derived_from:
  - path: upstream/fact.md
    rev: $REV2
  - path: upstream/fact.md
    rev: $REV1
  - path: upstream/fact.md
    rev: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
---

body
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$REPO" "$REPO/mixed.md" 2>&1)
RC=$?
if [ "$RC" != "0" ] && echo "$OUT" | grep -q "1 current, 1 superseded, 1 unresolved"; then
    ok "(e) mixed list: partial-current is still non-zero exit"
else
    bad "(e) mixed list" "rc=$RC out=$OUT"
fi

# ---- (f) artifact with no derived_from block: no entries, exits 0
cat > "$REPO/no-fm.md" <<'EOF'
---
ticket_refs:
  - foo/bar#1
---

body
EOF
OUT=$(python3 "$SCRIPT" --repo-root "$REPO" "$REPO/no-fm.md" 2>&1)
RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -q "0 entries"; then
    ok "(f) no derived_from block: 0 entries, exits 0"
else
    bad "(f) no derived_from block" "rc=$RC out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
