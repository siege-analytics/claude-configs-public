#!/usr/bin/env bash
# Shared helpers for guards that must tell "does this command DO x" from
# "does this command mention x". See command-text.py for the rules.
#
# Fail-closed: if python3 is unavailable the helpers fall back to the original
# inline regex, which over-matches. A guard that over-matches costs a retry; a
# guard that silently stops matching costs an unguarded write.

_CT_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_CT_PY="$_CT_LIB_DIR/command-text.py"
# Assembled rather than written literally: a guard that greps raw command text
# for this pattern blocks any command containing it, including the ones that
# install this file. That is the bug being fixed (#55).
_CT_VERB="git com""mit"
_CT_ADD_VERB="git ""add"
_CT_FALLBACK_RE="(^|[^[:alnum:]])${_CT_VERB}([^[:alnum:]]|\$)"

# ct_is_git_commit <command>  -> 0 when the command invokes the commit verb
ct_is_git_commit() {
    local cmd="$1"
    if [ -f "$_CT_PY" ] && command -v python3 >/dev/null 2>&1; then
        printf '%s' "$cmd" | python3 "$_CT_PY" --is-commit
        return $?
    fi
    printf '%s' "$cmd" | grep -qE "$_CT_FALLBACK_RE"
}

# ct_code_only <command>  -> the command with data regions removed
ct_code_only() {
    local cmd="$1"
    if [ -f "$_CT_PY" ] && command -v python3 >/dev/null 2>&1; then
        printf '%s' "$cmd" | python3 "$_CT_PY"
        return 0
    fi
    printf '%s' "$cmd"
}

# ct_stage_args <command>  -> one path per line that a staging command would add.
#
# Fails CLOSED. Without python3 it falls back to the original crude extraction -
# everything after the verb, flags stripped - which over-reports and so may block
# a command it should not. That is the right direction for this guard: a false
# positive costs a retry, while returning nothing would let a sensitive file be
# staged with nothing looking.
ct_stage_args() {
    local cmd="$1"
    if [ -f "$_CT_PY" ] && command -v python3 >/dev/null 2>&1; then
        printf '%s' "$cmd" | python3 "$_CT_PY" --stage-args
        return 0
    fi
    printf '%s' "$cmd" \
        | sed "s/.*${_CT_ADD_VERB}[[:space:]]*//" \
        | sed 's/[[:space:]]*-[a-zA-Z][a-zA-Z]*[[:space:]]*/ /g' \
        | tr ' ' '\n' \
        | grep -v '^$'
}

# ct_read_payload  -> the hook payload from stdin, capped.
#
# The guards read stdin with an unbounded `cat`. Each hook has its own timeout in
# settings, so a hang is bounded, but a very large payload makes every guard burn
# its whole budget reading bytes it will not use - and with several guards on one
# event that is the difference between a prompt feeling instant and feeling
# broken. A real payload is a few kilobytes; the cap is far above that, so only a
# pathological one is truncated, and one of those was going to time out anyway.
_CT_PAYLOAD_MAX="${CT_PAYLOAD_MAX:-1048576}"
ct_read_payload() {
    local data
    data="$(head -c "$_CT_PAYLOAD_MAX" 2>/dev/null || true)"
    if [ "${#data}" -ge "$_CT_PAYLOAD_MAX" ]; then
        echo "[$(basename "${0:-hook}")] WARN: payload exceeded ${_CT_PAYLOAD_MAX} bytes and was truncated" >&2
    fi
    printf '%s' "$data"
}
