#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SCRIPT_DIR/release-notes.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/CHANGELOG.md" <<'MD'
# Changelog

## [Unreleased]

### Added

- Meaningful release note.

## [1.0.0] -- 2026-01-01

### Added

- Old note.
MD

python3 "$SCRIPT" --version 1.0.1 --changelog "$TMP/CHANGELOG.md" --out "$TMP/notes.md"
grep -Fq 'Meaningful release note.' "$TMP/notes.md"

cat > "$TMP/empty.md" <<'MD'
# Changelog

## [Unreleased]

## [1.0.0] -- 2026-01-01

MD

if python3 "$SCRIPT" --version 1.0.1 --changelog "$TMP/empty.md" >/tmp/release-notes-empty.out 2>&1; then
  echo 'FAIL: empty changelog generated release notes' >&2
  exit 1
fi

echo 'PASS: release notes generated from non-empty Unreleased and fail on empty notes'
