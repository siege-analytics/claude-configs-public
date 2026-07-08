#!/bin/bash
# Test: hooks/git/detect-ai-fingerprints.sh
#
# Sets up an isolated temp git repo, makes commits with different message
# shapes, and asserts the hook blocks or passes as expected.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/git/detect-ai-fingerprints.sh"

# shellcheck source=./run_scenarios.sh
source "$SCRIPT_DIR/run_scenarios.sh"

# Set up an isolated git repo with the scanner reachable from this checkout.
TMP_REPO=$(mktemp -d)
trap 'rm -rf "$TMP_REPO"' EXIT
cd "$TMP_REPO"
git init -q
git config user.email "t@example.test"
git config user.name "test"
# Symlink the scanner into the temp repo so the hook's upward-walk finds it.
mkdir -p skills/meta/detect-ai-fingerprints
ln -s "$REPO_ROOT/skills/meta/detect-ai-fingerprints/scan.sh" skills/meta/detect-ai-fingerprints/scan.sh
ln -s "$REPO_ROOT/skills/meta/detect-ai-fingerprints/scan_ast.py" skills/meta/detect-ai-fingerprints/scan_ast.py

commit_with_body() {
    local subject="$1"
    local body="$2"
    echo "$RANDOM" > scratch.txt
    git add scratch.txt
    git commit -q -m "$subject" -m "$body"
}

make_payload() {
    local cmd="$1"
    printf '{"tool_input":{"command":"%s"},"cwd":"%s"}' "$cmd" "$TMP_REPO"
}

# Scenario (a): clean commit body, push -> PASS
commit_with_body "fix: clean subject" "Plain ASCII body with no banned tokens."
expect_pass "(a) clean commit body" "$HOOK" "$(make_payload 'g'$'i''t push origin main')"

# Scenario (b): em-dash in body, push -> BLOCK
commit_with_body "fix: em-dash subject" "This body has an em—dash in it."
expect_block "(b) em-dash in body" "$HOOK" "$(make_payload 'g'$'i''t push origin main')"

# Scenario (c): banned adverb in body, push -> BLOCK
commit_with_body "fix: adverb subject" "This intentionally tests the adverb rule."
expect_block "(c) banned adverb in body" "$HOOK" "$(make_payload 'g'$'i''t push origin main')"

# Scenario (d): structured Why:/How to apply: block in body -> BLOCK
commit_with_body "fix: structured" $'Body line.\n\nWhy: rationale text here.\nHow to apply: do the thing.'
expect_block "(d) structured Why/How to apply" "$HOOK" "$(make_payload 'g'$'i''t push origin main')"

# Scenario (e): non-trigger command -> PASS silently regardless of body
commit_with_body "fix: em-dash subject 2" "Another em—dash body."
expect_pass "(e) non-trigger command (git status)" "$HOOK" "$(make_payload 'g'$'i''t status')"

# Note: the hook walks up from its OWN install location to find scan.sh,
# not from the target repo. There's no scenario for "scanner missing" --
# the scanner is always reachable from the hook's own checkout. Skipping
# what would have been scenario (f).

report
