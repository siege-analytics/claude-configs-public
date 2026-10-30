#!/usr/bin/env bash
# Test: enforcement-blocks.jsonl separates advisory audit records from blocks,
# and every entry carries a UTC timestamp with an explicit offset (#1119).
# block-classifier-guard must ask only about real, recent blocks, whether the
# log line was written before or after the format change.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

_PASS=0; _FAIL=0
check() {
    local name="$1" cond="$2"
    if [[ "$cond" == "yes" ]]; then
        _PASS=$((_PASS+1)); printf '  [PASS] %s\n' "$name"
    else
        _FAIL=$((_FAIL+1)); printf '  [FAIL] %s\n' "$name"
    fi
}

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
WS="$TMP/ws"
mkdir -p "$WS/hooks/resolver" "$WS/hooks/lib"
cp "$ROOT/hooks/resolver/block-classifier-guard.sh" "$WS/hooks/resolver/"
cp -R "$ROOT/hooks/lib/." "$WS/hooks/lib/"
LOG="$WS/enforcement-blocks.jsonl"

field() {  # field <line-no> <key>
    sed -n "${1}p" "$LOG" | python3 -c 'import json,sys; print(json.load(sys.stdin).get(sys.argv[1]))' "$2"
}

echo "== log_block_event writes UTC and flags advisories"
(
    export CRAFT_AGENT_WORKSPACE="$WS"
    # shellcheck disable=SC1091
    . "$WS/hooks/lib/log-block.sh"
    log_block_event "universal-mutation-gate" "unscoped or ambiguous mutation" "touch x"
    log_block_event "pre-action-guard" "protected branch 'main' (advisory)" "UserPromptSubmit"
)
ts=$(field 1 timestamp)
[[ $ts == *+00:00 ]] && r=yes || r=no; check "timestamp is UTC with an offset ($ts)" "$r"
[[ $(field 1 advisory) == False ]] && r=yes || r=no; check "a real block is not advisory" "$r"
[[ $(field 2 advisory) == True ]] && r=yes || r=no; check "an '(advisory)' invariant is flagged advisory" "$r"

echo "== block-classifier-guard counts only real, recent blocks"
now_local=$(python3 -c 'from datetime import datetime; print(datetime.now().isoformat())')
old_utc=$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=5)).isoformat())')
old_local=$(python3 -c 'from datetime import datetime,timedelta; print((datetime.now()-timedelta(hours=5)).isoformat())')
cat >> "$LOG" <<EOF
{"timestamp": "$now_local", "gate_id": "destructive-guard", "invariant": "legacy naive block", "command": "rm -rf x", "classified": false}
{"timestamp": "$now_local", "gate_id": "branch-state-guard", "invariant": "protected branch 'develop' (advisory)", "command": "UserPromptSubmit", "classified": false}
{"timestamp": "$old_utc", "gate_id": "universal-mutation-gate", "invariant": "old aware block", "command": "touch y", "classified": false}
{"timestamp": "$old_local", "gate_id": "universal-mutation-gate", "invariant": "old naive block", "command": "touch z", "classified": false}
EOF
out=$(cd "$TMP" && env -i PATH="$PATH" HOME="$TMP" CRAFT_AGENT_WORKSPACE="$WS" bash "$WS/hooks/resolver/block-classifier-guard.sh" < /dev/null 2>&1)
n=$(printf '%s\n' "$out" | sed -n 's/^\([0-9]*\) recent enforcement block(s) are UNCLASSIFIED.*/\1/p')
[[ $n == 2 ]] && r=yes || r=no; check "two real recent blocks reported (got '${n:-none}')" "$r"
grep -q 'unscoped or ambiguous mutation' <<<"$out" && r=yes || r=no; check "the new UTC block is reported" "$r"
grep -q 'legacy naive block' <<<"$out" && r=yes || r=no; check "a pre-#1119 naive local block is still reported" "$r"
grep -q 'advisory' <<<"$out" && r=no || r=yes; check "no advisory record is reported, new or legacy" "$r"
grep -q 'old aware block\|old naive block' <<<"$out" && r=no || r=yes; check "blocks older than 4h are not reported" "$r"

echo "== a malformed line does not hide the lines after it"
# Malformed in every time zone: a non-object line, an unparseable timestamp, and
# year 1, which either overflows when localised (east of UTC) or is far older
# than the 4h window. None of them may count, or hide the lines after them.
printf '[]\n{"timestamp": "not-a-time", "gate_id": "x", "invariant": "unparseable", "command": "c"}\n{"timestamp": "0001-01-01T00:00:00", "gate_id": "x", "invariant": "year one", "command": "c"}\n' > "$TMP/bad.jsonl"
cat "$TMP/bad.jsonl" "$LOG" > "$TMP/mixed.jsonl" && mv "$TMP/mixed.jsonl" "$LOG"
out=$(cd "$TMP" && env -i PATH="$PATH" HOME="$TMP" CRAFT_AGENT_WORKSPACE="$WS" bash "$WS/hooks/resolver/block-classifier-guard.sh" < /dev/null 2>&1)
n=$(printf '%s\n' "$out" | sed -n 's/^\([0-9]*\) recent enforcement block(s) are UNCLASSIFIED.*/\1/p')
[[ $n == 2 ]] && r=yes || r=no; check "two real blocks still reported after malformed lines (got '${n:-none}')" "$r"

echo "== a classified block is no longer reported"
bid="universal-mutation-gate:$ts"
printf '{"classifications":[{"block_id":"%s","classification":"normal","class":null,"evidence":""}]}\n' "$bid" > "$WS/block-classification.json"
out=$(cd "$TMP" && env -i PATH="$PATH" HOME="$TMP" CRAFT_AGENT_WORKSPACE="$WS" bash "$WS/hooks/resolver/block-classifier-guard.sh" < /dev/null 2>&1)
n=$(printf '%s\n' "$out" | sed -n 's/^\([0-9]*\) recent enforcement block(s) are UNCLASSIFIED.*/\1/p')
[[ $n == 1 ]] && r=yes || r=no; check "one left after classifying the UTC block (got '${n:-none}')" "$r"

printf 'block_log_advisory_utc: %d passed, %d failed\n' "$_PASS" "$_FAIL"
(( _FAIL == 0 ))
