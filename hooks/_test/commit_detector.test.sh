#!/usr/bin/env bash
# The shared commit detector must tell doing from talking about.
#
# Two directions, and they are not equally costly:
#
#   MUST CATCH   - a miss is an unguarded commit. A first attempt at this fix
#                  stripped every quoted span, which silently disabled the guards
#                  for `bash -c` and `eval`. Those cases are pinned here.
#   MUST NOT CATCH - a hit is the #55 false positive: a read-only command, or a
#                  heredoc documenting commit shapes, blocked as a ticketless
#                  commit. Observed live, including while writing this fix.
#
# Ref: #55, #106.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB="$SCRIPT_DIR/../lib/command-text.py"
GUARDS="$SCRIPT_DIR/../git"

pass=0
fail=0

detects() {
    printf '%s' "$1" | python3 "$LIB" --is-commit >/dev/null
}

check_catch() {
    local desc="$1" cmd="$2"
    if detects "$cmd"; then
        printf '  PASS: catches %s\n' "$desc"; pass=$((pass + 1))
    else
        printf '  FAIL: MISSED %s -- an unguarded commit\n' "$desc"; fail=$((fail + 1))
    fi
}

check_ignore() {
    local desc="$1" cmd="$2"
    if detects "$cmd"; then
        printf '  FAIL: blocks %s -- the #55 false positive\n' "$desc"; fail=$((fail + 1))
    else
        printf '  PASS: ignores %s\n' "$desc"; pass=$((pass + 1))
    fi
}

echo "=== commit detector ==="
echo
echo "  -- must catch (a miss here fails open) --"
check_catch "a plain invocation"            'git commit -m "x"'
check_catch "cd && (the #106 bypass)"       'cd /tmp/foo && git commit -m x'
check_catch "bash -c"                       'bash -c "git commit -m x"'
check_catch "bash -c with cd inside"        "bash -c 'cd /x && git commit -m y'"
check_catch "eval"                          'eval "git commit -m x"'
check_catch "sh -c"                         'sh -c "git commit"'
check_catch "zsh -c"                        'zsh -c "git commit -m x"'
check_catch "nested bash -c"                'bash -c "bash -c '"'"'git commit -m z'"'"'"'
check_catch "an unbalanced apostrophe"      "echo don't && git commit -m x"
check_catch "a left-shift, not a heredoc"   'x=$((1 << 2)); git commit -m y'
check_catch "--amend"                       'git commit --amend --no-edit'
check_catch "a message mentioning itself"   'git commit -m "explains git commit"'
check_catch "semicolon separator"           'echo hi; git commit -m x'
# #1109: the shell runs these as the verb; quotes and backslashes go away.
check_catch "a double-quoted verb"           'git "commit" -m x'
check_catch "a single-quoted verb"           "git 'commit' -m x"
check_catch "a backslash in git"             'g\it commit -m x'
check_catch "empty quotes inside git"        "g''it commit -m x"
check_ignore "an escaped space is one word"   'grep -rn git\ commit hooks/'
check_catch "a heredoc opener"              'git commit -F - <<MSG
body
MSG'

echo
echo "  -- must not catch (a hit here is the bug) --"
check_ignore "a grep for the string"        'grep -rn "git commit" .'
check_ignore "an echo about it"             'echo "remember to git commit later"'
check_ignore "python -c (not a shell)"      'python3 -c "print('"'"'git commit'"'"')"'
check_ignore "a heredoc body documenting it" 'gh issue create --body "$(cat <<EOF
run git commit here
EOF
)"'
check_ignore "ripgrep over the codebase"    'rg --files-with-matches "git commit"'

echo
echo "  -- through the real guards --"
# ticket-required blocked this exact shape live: a heredoc body mentioning the
# verb, in a command that commits nothing.
payload='{"tool_name":"Bash","tool_input":{"command":"gh issue create --body \"see git commit docs\""}}'
if out=$(printf '%s' "$payload" | bash "$GUARDS/ticket-required.sh" 2>&1); then
    printf '  PASS: ticket-required allows a gh issue create that merely mentions it\n'; pass=$((pass + 1))
else
    printf '  FAIL: ticket-required blocked a non-commit: %s\n' "$(printf '%s' "$out" | head -1)"; fail=$((fail + 1))
fi

# and still blocks a real ticketless commit
payload='{"tool_name":"Bash","tool_input":{"command":"git commit -m \"no ticket here\""}}'
if printf '%s' "$payload" | bash "$GUARDS/ticket-required.sh" >/dev/null 2>&1; then
    printf '  FAIL: ticket-required ALLOWED a ticketless commit\n'; fail=$((fail + 1))
else
    printf '  PASS: ticket-required still blocks a ticketless commit\n'; pass=$((pass + 1))
fi

# and still blocks one hidden behind bash -c
payload='{"tool_name":"Bash","tool_input":{"command":"bash -c \"git commit -m no-ticket\""}}'
if printf '%s' "$payload" | bash "$GUARDS/ticket-required.sh" >/dev/null 2>&1; then
    printf '  FAIL: ticket-required ALLOWED a commit hidden in bash -c\n'; fail=$((fail + 1))
else
    printf '  PASS: ticket-required blocks a commit hidden in bash -c\n'; pass=$((pass + 1))
fi

echo
echo "  -- no-attribution sees the message, which lives in quotes --"
# Regression: routing the message area through the code-only text stripped the
# quoted span the message lives in, so attribution in a normal -m "..." was never
# seen. The #55 false positive is handled by the detector rejecting non-commits,
# not by stripping the message.
attr_payload() {
    python3 -c "
import json, sys
print(json.dumps({'session_id':'p','hook_event_name':'PreToolUse','tool_name':'Bash',
                  'tool_input':{'command': sys.argv[1]}}))" "$1"
}
if attr_payload 'git commit -m "fix: x

Co-Authored-By: Claude <noreply@anthropic.com>"' | bash "$GUARDS/no-attribution.sh" >/dev/null 2>&1; then
    printf '  FAIL: no-attribution ALLOWED a commit carrying attribution\n'; fail=$((fail + 1))
else
    printf '  PASS: no-attribution catches attribution in a quoted message\n'; pass=$((pass + 1))
fi

if attr_payload 'gh issue create --body "docs about git commit and Claude Code"' | bash "$GUARDS/no-attribution.sh" >/dev/null 2>&1; then
    printf '  PASS: no-attribution ignores a non-commit that mentions both\n'; pass=$((pass + 1))
else
    printf '  FAIL: no-attribution blocked a non-commit (the #55 shape)\n'; fail=$((fail + 1))
fi

echo
echo "  -- a crashing helper falls back to over-matching (#1109) --"
for broken in 'def (' 'import os; os._exit(1)' 'raise SystemExit(3)'; do
    BR="$(mktemp -d)"; printf '%s\n' "$broken" > "$BR/command-text.py"
    for verb in 'git commit -m x' 'git \"commit\" -m x' "g\\\\it commit -m x"; do
        if bash -c "source '$SCRIPT_DIR/../lib/command-text.sh'; _CT_PY='$BR/command-text.py'; ct_is_git_commit \"$verb\""; then
            printf '  PASS: catches [%s] when the helper is: %s\n' "$verb" "$broken"; pass=$((pass + 1))
        else
            printf '  FAIL: misses [%s] when the helper is: %s -- fails open\n' "$verb" "$broken"; fail=$((fail + 1))
        fi
    done
    rm -rf "$BR"
done
echo
echo "Results: $pass passed, $fail failed"
[[ $fail -gt 0 ]] && exit 1
exit 0
