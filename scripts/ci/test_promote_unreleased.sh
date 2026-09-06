#!/bin/bash
# Test: scripts/ci/promote-unreleased.py

set -uo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/promote-unreleased.py"

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s\n' "$1"; printf '         %s\n' "$2"; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# ---- (a) promote non-empty [Unreleased] to [<version>]
cat > "$TMP/a.md" <<'EOF'
# Changelog

## [Unreleased]

### Added

- item A (#1)
- item B (#2)

## [1.0.0] --- 2026-01-01

### Fixed

- earlier bug
EOF
OUT=$(python3 "$SCRIPT" --version 1.1.0 --date 2026-09-05 --changelog "$TMP/a.md" 2>&1)
RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -q "^promoted:" && grep -q "## \[1.1.0\] --- 2026-09-05" "$TMP/a.md" && grep -q "item A" "$TMP/a.md"; then
    ok "(a) non-empty [Unreleased] promoted to [1.1.0]"
else
    bad "(a) promoted to [1.1.0]" "rc=$RC out=$OUT tail=$(tail -20 $TMP/a.md)"
fi

# ---- (b) idempotent when [<version>] already exists
python3 "$SCRIPT" --version 1.1.0 --date 2026-09-05 --changelog "$TMP/a.md" > "$TMP/second.out" 2>&1
RC=$?
if [ "$RC" = "0" ] && grep -q "^already-exists" "$TMP/second.out"; then
    ok "(b) already-exists: second call is no-op"
else
    bad "(b) already-exists: no-op" "rc=$RC out=$(cat $TMP/second.out)"
fi

# ---- (c) empty [Unreleased] is not promoted
cat > "$TMP/c.md" <<'EOF'
# Changelog

## [Unreleased]

<!-- next release entries go here -->

## [1.0.0] --- 2026-01-01

### Fixed

- earlier bug
EOF
OUT=$(python3 "$SCRIPT" --version 1.1.0 --date 2026-09-05 --changelog "$TMP/c.md" 2>&1)
RC=$?
if [ "$RC" = "0" ] && echo "$OUT" | grep -q "empty-unreleased"; then
    ok "(c) empty [Unreleased]: no promotion (creating empty version would poison future promotions)"
else
    bad "(c) empty [Unreleased] no promotion" "rc=$RC out=$OUT"
fi

# ---- (d) missing [Unreleased] header errors out
cat > "$TMP/d.md" <<'EOF'
# Changelog

## [1.0.0] --- 2026-01-01

- released
EOF
OUT=$(python3 "$SCRIPT" --version 1.1.0 --date 2026-09-05 --changelog "$TMP/d.md" 2>&1)
RC=$?
if [ "$RC" = "1" ] && echo "$OUT" | grep -q "no \[Unreleased\] header"; then
    ok "(d) missing [Unreleased] header: exit 1"
else
    bad "(d) missing [Unreleased] header" "rc=$RC out=$OUT"
fi

# ---- (e) --check does not modify the file
cat > "$TMP/e.md" <<'EOF'
# Changelog

## [Unreleased]

### Added

- item

## [1.0.0] --- 2026-01-01

- earlier
EOF
SHA_BEFORE=$(shasum "$TMP/e.md" | awk '{print $1}')
OUT=$(python3 "$SCRIPT" --version 1.1.0 --date 2026-09-05 --changelog "$TMP/e.md" --check 2>&1)
RC=$?
SHA_AFTER=$(shasum "$TMP/e.md" | awk '{print $1}')
if [ "$RC" = "0" ] && [ "$SHA_BEFORE" = "$SHA_AFTER" ] && echo "$OUT" | grep -q "dry-run"; then
    ok "(e) --check does not modify the file"
else
    bad "(e) --check no-modify" "rc=$RC before=$SHA_BEFORE after=$SHA_AFTER"
fi

# ---- (f) version arg accepts v-prefix
cat > "$TMP/f.md" <<'EOF'
# Changelog

## [Unreleased]

### Added

- item
EOF
OUT=$(python3 "$SCRIPT" --version v2.0.0 --date 2026-09-05 --changelog "$TMP/f.md" 2>&1)
RC=$?
if [ "$RC" = "0" ] && grep -q "## \[2.0.0\]" "$TMP/f.md"; then
    ok "(f) v-prefix stripped from version"
else
    bad "(f) v-prefix stripping" "rc=$RC head=$(head -8 $TMP/f.md)"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
