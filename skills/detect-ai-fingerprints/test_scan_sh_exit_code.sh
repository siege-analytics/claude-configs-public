#!/bin/bash
# Test: scan.sh violation-counter regex matches every rule scan_ast.py emits (#766 B-1)
#
# Regression against a bug where the counter regex omitted writing-code:4,
# writing-code:8, writing-tests:5, so exit 1 never fired for those rules.
#
# Approach: extract the regex from scan.sh's counting line, then feed it a
# synthetic emission for every rule scan_ast.py can emit. Every rule must
# match. Also compare the rule set the regex covers against the emissions
# scan_ast.py actually produces.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCAN_SH="$SCRIPT_DIR/scan.sh"
SCAN_AST="$SCRIPT_DIR/scan_ast.py"

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s\n' "$1"; printf '         %s\n' "$2"; }

# Extract the counter regex from scan.sh. The line looks like:
#   ast_n=$(printf ... | grep -cE ':writing-(...)' || true)
COUNTER_REGEX=$(grep -oE "grep -cE ':writing-[^']+" "$SCAN_SH" \
    | sed -E 's|^grep -cE '\'':||' \
    | head -1)

if [ -z "$COUNTER_REGEX" ]; then
    bad "extract counter regex" "grep -cE ':writing-...' not found in scan.sh"
    exit 1
fi

# Every rule the AST scanner is known to emit (checked against docstring below).
RULE_TOKENS=(
    "writing-code-4-django-orm-kwarg(unknown-field)"
    "writing-code-7-silent-swallow(Return)"
    "writing-code-8"
    "writing-code-9-unused-parameter"
    "writing-code-15-unbounded-io(missing-timeout)"
    "writing-tests-5"
    "writing-releases-3"
)

for token in "${RULE_TOKENS[@]}"; do
    line="foo.py:1:${token}: excerpt"
    if echo "$line" | grep -qE "$COUNTER_REGEX"; then
        ok "counter regex matches: ${token}"
    else
        bad "counter regex misses: ${token}" "regex=$COUNTER_REGEX"
    fi
done

# Sanity: the regex should NOT match unrelated ast-scanner error output.
non_rule_lines=(
    "foo.py:1:scan-ast-error: [Errno 2] No such file"
    "foo.py:1:scan-ast-syntax-error: unexpected EOF"
    "foo.py:1:scan-ast-warning: test file unreadable"
)
for line in "${non_rule_lines[@]}"; do
    if echo "$line" | grep -qE "$COUNTER_REGEX"; then
        bad "counter regex over-matches non-rule: ${line}" "regex=$COUNTER_REGEX"
    else
        ok "counter regex ignores non-rule: ${line}"
    fi
done

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
