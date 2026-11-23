#!/usr/bin/env bash
# universal-mutation-gate must fail CLOSED when it cannot read its own input
# (#1097). An empty command used to mean "nothing to check" however it came
# about, so a missing extractor, a missing python3 or an unparseable payload
# allowed every command. Ported from electinfo/electinfo_claude_skills#335.
#
# Each case runs the gate from a copied hook tree, so a case that removes the
# extractor or python3 affects nothing outside $T.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
REAL_PY="$(command -v python3)"
mkdir -p "$T/ws/sessions/s1" "$T/repo" "$T/home" "$T/nopy"
cp -R "$ROOT/hooks" "$T/ws/hooks"
cp -R "$ROOT/bin" "$T/ws/bin"; cp -R "$ROOT/catalog" "$T/ws/catalog"
( cd "$T/repo" && git init -q && git -c user.name=t -c user.email=t@t commit -q --allow-empty -m init )
# PATH without python3: the system tools the hook needs, linked one by one.
for tool in bash cat dirname basename git grep sed tr head printf env mkdir date wc cut; do
    p="$(command -v "$tool" 2>/dev/null)" && ln -s "$p" "$T/nopy/$tool"
done

PASS=0; FAIL=0; FAILED=()
gate() {  # gate <stdin> [PATH] [hook tree] -> exit code; stderr to $T/err
    local path="${2:-/usr/local/bin:/usr/bin:/bin}" tree="${3:-$T/ws/hooks}"
    printf '%s' "$1" | (cd "$T/repo" && env -i PATH="$path" HOME="$T/home" \
        CRAFT_AGENT_WORKSPACE="$T/ws" CRAFT_SESSION_DIR="$T/ws/sessions/s1" \
        bash "$tree/bash/universal-mutation-gate.sh" >/dev/null 2>"$T/err")
}
expect() {  # expect <want-rc> <name> <stdin> [PATH] [tree]
    local want="$1" name="$2"; shift 2
    gate "$@"; local rc=$?
    if [[ "$rc" == "$want" ]]; then PASS=$((PASS + 1)); printf '  [PASS] %s (exit %s)\n' "$name" "$rc"
    else FAIL=$((FAIL + 1)); FAILED+=("$name"); printf '  [FAIL] %s (exit %s, wanted %s)\n' "$name" "$rc" "$want"; fi
}
says() {  # says <name> <text>: the last block message names its cause
    if grep -qF "$2" "$T/err"; then PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"
    else FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s (stderr: %s)\n' "$1" "$(head -c 200 "$T/err")"; fi
}
payload() { "$REAL_PY" -c 'import json,sys;print(json.dumps({"tool_name":"Bash","hook_event_name":"PreToolUse","session_id":"s1","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}))' "$1" "$T/repo"; }
MUT="$(payload 'touch x')"

echo "--- control ---"
expect 2 "mutation blocks with no gate" "$MUT"

echo "--- broken input must fail CLOSED ---"
cp -R "$T/ws/hooks" "$T/noextract"; rm "$T/noextract/lib/extract-json.py"
expect 2 "missing lib/extract-json.py" "$MUT" "" "$T/noextract"
says "message names the missing extractor" "extract-json.py"
cp -R "$T/ws/hooks" "$T/unreadable"; chmod 000 "$T/unreadable/lib/extract-json.py"
if [[ ! -r "$T/unreadable/lib/extract-json.py" ]]; then
    expect 2 "unreadable lib/extract-json.py" "$MUT" "" "$T/unreadable"
fi
chmod 644 "$T/unreadable/lib/extract-json.py"
expect 2 "python3 not on PATH" "$MUT" "$T/nopy"
says "message names python3" "python3 is not on PATH"
mkdir -p "$T/fakepy"; for f in "$T"/nopy/*; do ln -s "$(readlink "$f")" "$T/fakepy/$(basename "$f")"; done
ln -s "$(command -v true)" "$T/fakepy/python3"
expect 2 "python3 that does nothing" "$MUT" "$T/fakepy"
expect 2 "non-JSON payload" 'touch x'
says "message names an unparseable payload" "not a JSON hook payload"
expect 2 "truncated JSON" "${MUT:0:40}"
expect 2 "JSON array, not an object" '["touch x"]'
# The extractor exists but cannot extract from a payload that does parse.
for kind in syntax empty dir; do
    cp -R "$T/ws/hooks" "$T/x-$kind"; X="$T/x-$kind/lib/extract-json.py"
    case $kind in syntax) printf 'def (\n' > "$X";; empty) : > "$X";; dir) rm "$X"; mkdir "$X";; esac
    expect 2 "extractor broken ($kind)" "$MUT" "" "$T/x-$kind"
done
expect 2 "command the extractor cannot print (lone surrogate)" '{"tool_name":"Bash","hook_event_name":"PreToolUse","tool_input":{"command":"rm -rf build # \ud800"}}'
says "message names the unreadable command" "cannot be read as text"
expect 2 "command over 64 KiB" "$(payload "rm -rf build #$(head -c 70000 /dev/zero | tr '\0' a)")"
says "message names the size" "over 64 KiB"
# Bytes, not characters (#1106 review): 30k four-byte characters is 120 KB of
# UTF-8 and 360 KB once JSON-escaped, though only 30k characters long.
expect 2 "command of multi-byte characters over the byte limit" "$(payload "touch x # $("$REAL_PY" -c 'print("\U0001F600"*30000)')")"
says "message names the size" "too large to check"

echo "--- legitimate input still reaches the normal decision path ---"
expect 0 "parsed payload with no command field" '{"tool_name":"Read","hook_event_name":"PreToolUse","tool_input":{"file_path":"/etc/hostname"}}'
expect 0 "empty stdin" ''
expect 0 "empty object (parsed, nothing to check)" '{}'
expect 0 "read-only git status" "$(payload 'git status')"
expect 0 "read-only git log" "$(payload 'git log --oneline -3')"
expect 2 "destructive rm with no gate" "$(payload 'rm -rf build')"
# A large Write must still reach the decision path: the exported copy of the
# payload drops long strings, so it stays under the 128 KiB per-string limit.
wpay() { "$REAL_PY" -c 'import json,sys;print(json.dumps({"tool_name":"Write","hook_event_name":"PreToolUse","session_id":"s1","cwd":sys.argv[2],"tool_input":{"file_path":sys.argv[1],"content":"a"*int(sys.argv[3])}}))' "$T/ws/sessions/s1/data/notes.md" "$T/repo" "$1"; }
gate "$(wpay 10)"; SMALL=$?
expect "$SMALL" "140 KiB Write decides like a small one" "$(wpay 143360)"
wrepo() { "$REAL_PY" -c 'import json,sys;print(json.dumps({"tool_name":"Write","hook_event_name":"PreToolUse","session_id":"s1","cwd":sys.argv[2],"tool_input":{"file_path":sys.argv[1],"content":"a"*int(sys.argv[3])}}))' "$T/repo/x.py" "$T/repo" "$1"; }
expect 2 "ungated Write into the repo blocks" "$(wrepo 10)"
expect 2 "the same Write padded past 128 KiB still blocks" "$(wrepo 143360)"

printf '\nResults: %d passed, %d failed\n' "$PASS" "$FAIL"
(( FAIL == 0 )) || { printf 'Failed: %s\n' "${FAILED[@]}"; exit 1; }
