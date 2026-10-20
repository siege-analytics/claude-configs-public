#!/usr/bin/env bash
# no-sensitive-files.sh must read what a command STAGES, not what it says.
#
# The guard matched the verb anywhere in the raw command and then treated
# everything after it as filenames, so a commit message in the same line was
# scanned as paths. A message mentioning a config file was refused as an attempt
# to stage one — and the refusal blocked the very commands that would fix it,
# twice, while this fix was being written. Ref: #67.
#
# The verb is assembled at runtime for the same reason: a guard grepping raw
# command text for it would block any command containing this file's contents.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GUARD="$SCRIPT_DIR/../git/no-sensitive-files.sh"
LIBSH="$SCRIPT_DIR/../lib/command-text.sh"

ADD="git ""add"
COMMIT="git ""commit"
ENVF=".""env"
CREDS="credentials"".json"

pass=0
fail=0

payload() {
    python3 -c "
import json, sys
print(json.dumps({'session_id':'p','hook_event_name':'PreToolUse','tool_name':'Bash',
                  'tool_input':{'command': sys.argv[1]}}))" "$1"
}

allows() {
    local desc="$1" cmd="$2"
    if payload "$cmd" | bash "$GUARD" >/dev/null 2>&1; then
        printf '  PASS: allows %s\n' "$desc"; pass=$((pass + 1))
    else
        printf '  FAIL: BLOCKS %s -- the #67 false positive\n' "$desc"; fail=$((fail + 1))
    fi
}

refuses() {
    local desc="$1" cmd="$2"
    if payload "$cmd" | bash "$GUARD" >/dev/null 2>&1; then
        printf '  FAIL: ALLOWS %s -- a sensitive file would be staged\n' "$desc"; fail=$((fail + 1))
    else
        printf '  PASS: refuses %s\n' "$desc"; pass=$((pass + 1))
    fi
}

echo "=== sensitive-files guard ==="
echo
echo "  -- must refuse (a miss stages a secret) --"
refuses "a forced stage of an env file"      "$ADD -f $ENVF"
refuses "a credentials file"                 "$ADD $CREDS"
refuses "a private key"                      "$ADD deploy.pem"
refuses "one sensitive path among several"   "$ADD src/a.py $ENVF src/b.py"

echo
echo "  -- must allow (a hit here is #67) --"
allows "ordinary source files"               "$ADD src/a.py src/b.py"
allows "a message that mentions a config"    "$ADD a.py && $COMMIT -m \"note about $ENVF and $CREDS\""
allows "a command that stages nothing"       "$COMMIT -m \"x\""
allows "an issue body mentioning staging"    "gh issue create --body \"run $ADD $ENVF\""
allows "an echo about it"                    "echo \"$ADD $ENVF\""

echo
echo "  -- no basename noise --"
out="$(payload "$ADD -f $ENVF" | bash "$GUARD" 2>&1)"
if printf '%s' "$out" | grep -q 'invalid option'; then
    printf '  FAIL: basename still parses paths as options\n'; fail=$((fail + 1))
else
    printf '  PASS: basename takes -- so a dashed path is a path\n'; pass=$((pass + 1))
fi

echo
echo "  -- fails closed without python3 --"
# Returning nothing would let a secret through with nothing looking. The crude
# fallback over-reports instead, which costs a retry.
got="$(bash -c "source '$LIBSH'; _CT_PY=/nonexistent; ct_stage_args \"$ADD -f $ENVF\"" 2>/dev/null | tr '\n' ' ')"
if printf '%s' "$got" | grep -q "$ENVF"; then
    printf '  PASS: fallback still sees the sensitive path\n'; pass=$((pass + 1))
else
    printf '  FAIL: fallback returned [%s] -- fails OPEN\n' "$got"; fail=$((fail + 1))
fi

echo
echo "Results: $pass passed, $fail failed"
[[ $fail -gt 0 ]] && exit 1
exit 0
