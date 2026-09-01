#!/bin/bash
# Test: hooks/write/ticket-propagation-guard.sh
#
# Regression coverage for #688: the guard chose its frontmatter branch with
# `echo "$CONTENT" | head -1` under `set -o pipefail`. Above the pipe buffer
# `echo` takes SIGPIPE, pipefail propagates 141, and the branch is skipped, so
# valid `ticket_refs:` frontmatter was ignored on large artifacts only.
#
# The size pairs below are the point of this file. Asserting exit 0 on a large
# compliant artifact alone would also pass if the guard were disabled, so every
# compliant case is paired with a non-compliant one of the same size.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/write/ticket-propagation-guard.sh"

# shellcheck source=./run_scenarios.sh
source "$SCRIPT_DIR/run_scenarios.sh"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/plans"

FRONTMATTER='---
ticket_refs:
  - siege-analytics/claude-configs-public#688: comment pending
---
'
BODY_REF='See siege-analytics/claude-configs-public#251 for the failure evidence.'

# $1 = target file, $2 = "with-fm"|"no-fm", $3 = filler bytes
make_artifact() {
    local path="$1" fm="$2" bytes="$3"
    : > "$path"
    [[ "$fm" == "with-fm" ]] && printf '%s' "$FRONTMATTER" >> "$path"
    printf '# Artifact\n\n%s\n\n' "$BODY_REF" >> "$path"
    # Filler includes `---` horizontal rules, which every real plans artifact has.
    python3 -c "import sys; n=int(sys.argv[1]); sys.stdout.write(('---\n\nfiller paragraph text\n\n')*(n//30))" "$bytes" >> "$path"
}

payload() {
    printf '{"tool_name":"Edit","tool_input":{"file_path":"%s","old_string":"a","new_string":"b"}}' "$1"
}

# --- Large artifacts: the #688 regression. 200KB clears any platform pipe buffer.

make_artifact "$TMP/plans/large-compliant.md" with-fm 200000
make_artifact "$TMP/plans/large-noncompliant.md" no-fm 200000

expect_pass "(a) 200KB artifact WITH ticket_refs frontmatter is allowed" "$HOOK" \
    "$(payload "$TMP/plans/large-compliant.md")"
expect_block "(b) 200KB artifact WITHOUT frontmatter is still blocked" "$HOOK" \
    "$(payload "$TMP/plans/large-noncompliant.md")"

# --- Small artifacts: the behaviour that already worked, pinned against regression.

make_artifact "$TMP/plans/small-compliant.md" with-fm 1000
make_artifact "$TMP/plans/small-noncompliant.md" no-fm 1000

expect_pass "(c) 1KB artifact WITH ticket_refs frontmatter is allowed" "$HOOK" \
    "$(payload "$TMP/plans/small-compliant.md")"
expect_block "(d) 1KB artifact WITHOUT frontmatter is still blocked" "$HOOK" \
    "$(payload "$TMP/plans/small-noncompliant.md")"

# --- AC3: refs declared in frontmatter must not be reported as unpropagated.
# Exit-code assertions cannot see this symptom, so it is checked on the message.
# The fixture declares `ticket_refs:` whose entries are commented out, so the
# metadata check correctly fails and the guard still prints its ref list -- but
# #688 appears only in the frontmatter, so a correct body scan must not report it.

cat > "$TMP/plans/ref-leak.md" <<EOF
---
ticket_refs:
# siege-analytics/claude-configs-public#688: commented out
---

# Artifact

Body cites siege-analytics/claude-configs-public#251 only.
EOF
python3 -c "import sys; sys.stdout.write(('---\n\nfiller paragraph text\n\n')*7000)" >> "$TMP/plans/ref-leak.md"

leak_out=$(printf '%s' "$(payload "$TMP/plans/ref-leak.md")" | bash "$HOOK" 2>&1)
leak_exit=$?

if [[ "$leak_exit" -ne 2 ]]; then
    printf '  [FAIL] (e) ref-leak fixture should block (expected exit 2, got %d)\n' "$leak_exit"
    _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
    _HARNESS_FAILED_NAMES+=("(e) ref-leak fixture blocks")
elif echo "$leak_out" | grep -q '#688'; then
    printf '  [FAIL] (e) refs declared in frontmatter leaked into the reported ref list\n'
    _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
    _HARNESS_FAILED_NAMES+=("(e) frontmatter refs absent from message")
else
    printf '  [PASS] (e) refs declared in frontmatter are absent from the reported ref list\n'
    _HARNESS_PASS=$((_HARNESS_PASS + 1))
fi

# --- Bypass regression: `propagation-deferred:` in the BODY must not satisfy
# the guard. The old `sed -n '/^---$/,/^---$/p'` frontmatter range restarted at
# every `---` rule, so an unindented line inside a fenced block between two
# rules landed in FRONTMATTER. Quoting the guard's own error message into a
# document disabled the guard for that document.

printf '%s\n' \
    '# Doc with no frontmatter at all' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251 and is unpropagated.' \
    '' \
    '---' \
    '' \
    'Quoting the guard error message in a fenced block:' \
    '' \
    '```' \
    'propagation-deferred: workspace-only draft, will propagate after review' \
    '```' \
    '' \
    '---' \
    '' \
    'More body.' > "$TMP/plans/deferred-in-body.md"

expect_block "(f) body-level propagation-deferred between --- rules does not satisfy the guard" "$HOOK" \
    "$(payload "$TMP/plans/deferred-in-body.md")"

report
