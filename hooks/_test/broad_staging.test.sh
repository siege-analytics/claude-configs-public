#!/usr/bin/env bash
# no-broad-staging must match the command, not text that mentions the command.
#
# The guard scanned the raw command line, so any command whose DATA contained the
# forbidden form was refused as though it were the form. Writing documentation
# about the rule, or a fixture for this very test, was blocked by the rule it
# describes. Same defect as no-attribution reading the commit message it was meant
# to inspect (landmines.md 10).
#
# Both directions are asserted, because a guard that stops refusing data by
# refusing nothing is worse than the false positive it replaced. The first attempt
# at this fix did exactly that: ct_code_only takes the command as an ARGUMENT and
# it was given the command on stdin, so it returned empty and every blocking case
# silently went green.
#
# Ref: #70.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GUARD="$SCRIPT_DIR/../git/no-broad-staging.sh"
pass=0; fail=0
# Stock macOS has no timeout(1); run unbounded there (#1109).
_tmo() { if command -v timeout >/dev/null 2>&1; then timeout "$@"; else shift; "$@"; fi; }

run() {
    python3 -c "
import json, sys
print(json.dumps({'hook_event_name':'PreToolUse','tool_name':'Bash',
                  'tool_input':{'command': sys.argv[1]}}))" "$1" \
        | _tmo 25 bash "$GUARD" >/dev/null 2>&1
    printf '%s' "$?"
}

blocks() {
    local rc; rc="$(run "$2")"
    if [[ "$rc" == "2" ]]; then printf '  PASS: blocks %s\n' "$1"; pass=$((pass + 1))
    else printf '  FAIL: allowed %s (exit %s) -- the guard is a no-op\n' "$1" "$rc"; fail=$((fail + 1)); fi
}

allows() {
    local rc; rc="$(run "$2")"
    if [[ "$rc" == "0" ]]; then printf '  PASS: allows %s\n' "$1"; pass=$((pass + 1))
    else printf '  FAIL: blocked %s (exit %s) -- false positive on data\n' "$1" "$rc"; fail=$((fail + 1)); fi
}

if [[ ! -f "$GUARD" ]]; then
    printf '  FAIL: guard not found at %s\n\nResults: 0 passed, 1 failed\n' "$GUARD"; exit 1
fi

echo "=== broad staging: code is refused, data is not ==="
echo
echo "  -- the real thing, however it is spelled --"
blocks "the -A form"        'git add -A'
blocks "the bare dot"       'git add .'
blocks "the --all form"     'git add --all'
blocks "chained after cd"   'cd /tmp && git add -A'
blocks "wrapped in bash -c" 'bash -c "git add -A"'
blocks "a single-quoted verb" "git 'add' -A"
blocks "a double-quoted verb" 'git "add" .'
# With the helper failing, the fallback must still see a quoted verb (#1114 review).
BR="$(mktemp -d)"; cp -R "$SCRIPT_DIR/.." "$BR/hooks"; printf 'def (\n' > "$BR/hooks/lib/command-text.py"
GUARD_SAVE="$GUARD"; GUARD="$BR/hooks/git/no-broad-staging.sh"
blocks "a single-quoted verb, helper broken" "git 'add' -A"
blocks "the plain form, helper broken"       'git add -A'
GUARD="$GUARD_SAVE"; rm -rf "$BR"

echo
echo "  -- the same characters as data --"
doc="$(printf 'cat > rules.md <<XEOF\nStage files by name. git add -A is forbidden here.\nXEOF')"
allows "a heredoc documenting the rule" "$doc"
allows "a quoted mention"     "echo 'never use git add -A in this repo'"
allows "staging by name"      'git add src/a.py tests/test_a.py'
allows "an unrelated command" 'git status'

echo
echo "Results: $pass passed, $fail failed"
[[ $fail -gt 0 ]] && exit 1
exit 0
