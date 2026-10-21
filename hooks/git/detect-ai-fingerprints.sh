#!/bin/bash
# Hook: detect-ai-fingerprints (commit-body scan)
# Enforces: skills/detect-ai-fingerprints/SKILL.md at push/pr-create/pr-merge time.
# Trigger: PreToolUse on Bash(git push *), Bash(gh pr create *), Bash(gh pr merge *)
#
# Calls scan.sh --commit-message-file <temp> against the latest commit message. Blocks
# the push when the scanner finds any AI-fingerprint violation: em-dashes,
# en-dashes, banned adverbs, structured Why:/How to apply: blocks in commit
# bodies, header/bullet shapes in commit bodies, history references in code
# comments (when the body itself contains them), countable claims missing
# Verified-by trailer, etc.
#
# Scope (v1): commit-message body only. The scanner's --staged / --working /
# --pr modes scan code diffs and would surface a large backlog of historical
# violations; gating push on those needs a separate phasing decision and is
# out of scope for v1.
#
# Closes the gap operator named at claude-configs-public#120: the scanner
# existed and worked; no hook called it; the discipline was incidental to
# the agent reaching for the right skill, not enforced.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
# Fast skip (#1083): exit before starting python3 when the tool payload's
# command cannot match this hook's trigger. Only taken when tool_input's first
# key is a non-empty "command" (an empty or missing command keeps the git-push
# fallback) and the command uses no JSON escape other than \n \t \r \" \\ \/
# (\u, \f, \b could hide letters or whitespace). \n \t \r become spaces, so an
# escaped newline before the trigger still counts as a boundary. Git-hook
# invocations (refs on stdin, no JSON) take the full path.
_FAST_CMDS=$(printf '%s' "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"(\\.|[^"\\])*"' 2>/dev/null || true)
# A long command takes the full path (#1098): bash substitutions slow down
# superlinearly under a UTF-8 locale, and past the hook timeout a skip check
# would let the command through. 16 KiB keeps the check in milliseconds.
_FAST_FULL=0; (( ${#_FAST_CMDS} > 16384 )) && { _FAST_FULL=1; _FAST_CMDS=""; }
_FAST_ESC="${_FAST_CMDS//'\\'/}"; _FAST_ESC="${_FAST_ESC//'\"'/}"; _FAST_ESC="${_FAST_ESC//'\/'/}"
_FAST_ESC="${_FAST_ESC//'\n'/}"; _FAST_ESC="${_FAST_ESC//'\t'/}"; _FAST_ESC="${_FAST_ESC//'\r'/}"
_FAST_CMDS="${_FAST_CMDS//'\n'/ }"; _FAST_CMDS="${_FAST_CMDS//'\t'/ }"; _FAST_CMDS="${_FAST_CMDS//'\r'/ }"
# The shell rebuilds words from quotes and backslashes (#1098): `git "add"`,
# `g\it add` and `git  add` all run git add. Match the trigger against the text
# as written and against a copy with quote and backslash characters dropped and
# blanks squeezed; skip only if neither matches. A command containing ANSI-C
# $'...' (which can spell any byte) takes the full path.
[[ "$_FAST_CMDS" == *"\$'"* ]] && _FAST_FULL=1
# A quote or backslash between two letters or digits (`pr"x"`, `x\git`) joins
# words; only the full path's quote handling decides what that runs. In the
# JSON text a shell `"` or `\` is itself escaped, hence the leading backslash.
[[ "$_FAST_CMDS" == *[[:alnum:]]\\[\"\\][[:alnum:]]* || "$_FAST_CMDS" == *[[:alnum:]]\'[[:alnum:]]* ]] && _FAST_FULL=1
_FAST_BUILT="${_FAST_CMDS//[\"\'\\]/}"
while [[ "$_FAST_BUILT" == *"  "* ]]; do _FAST_BUILT="${_FAST_BUILT//  / }"; done
_FAST_FIRST='"tool_input"[[:space:]]*:[[:space:]]*[{][[:space:]]*"command"[[:space:]]*:[[:space:]]*"[^"]'
_FAST_RE='(^|[^[:alnum:]])(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+(create|merge))([^[:alnum:]]|$)'
if [[ $_FAST_FULL == 0 && "$INPUT" =~ $_FAST_FIRST && "$_FAST_ESC" != *'\'* ]] && ! [[ "$_FAST_CMDS" =~ $_FAST_RE || "$_FAST_BUILT" =~ $_FAST_RE ]]; then exit 0; fi
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Mirror self-review.sh's trigger pattern (BSD-portable boundary per issue #106).
TRIGGERS='(^|[^[:alnum:]])(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+(create|merge))([^[:alnum:]]|$)'
if ! echo "$COMMAND" | grep -qE "$TRIGGERS"; then
    exit 0
fi

# Multi-statement-with-cd yield (mirrors self-review.sh + branch-guard.sh).
CD_COUNT=$(echo "$COMMAND" | { grep -oE '(^|[^[:alnum:]])cd[[:space:]]' 2>/dev/null || true; } | wc -l | tr -d ' ')
if [[ "$CD_COUNT" -gt 0 ]]; then
    if [[ "$CD_COUNT" -gt 1 ]] || echo "$COMMAND" | grep -qE $'\n|;|\\|\\|'; then
        exit 0
    fi
fi

# Resolve effective repo dir (leading-cd pattern from branch-guard).
EFFECTIVE_CWD="$CWD"
if [[ "$COMMAND" =~ ^[[:space:]]*cd[[:space:]]+([^[:space:];&]+) ]]; then
    CD_TARGET="${BASH_REMATCH[1]}"
    CD_TARGET="${CD_TARGET%\"}"; CD_TARGET="${CD_TARGET#\"}"
    CD_TARGET="${CD_TARGET%\'}"; CD_TARGET="${CD_TARGET#\'}"
    case "$CD_TARGET" in
        /*) ;;
        *) CD_TARGET="$CWD/$CD_TARGET" ;;
    esac
    if [[ -d "$CD_TARGET" ]]; then
        EFFECTIVE_CWD="$CD_TARGET"
    fi
fi

if [[ -z "$EFFECTIVE_CWD" ]] || ! git -C "$EFFECTIVE_CWD" rev-parse --git-dir >/dev/null 2>&1; then
    exit 0
fi

# Locate scan.sh. Walk up from this hook file's directory to find the repo
# root that contains skills/detect-ai-fingerprints/scan.sh.
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCAN_SH=""
search="$SCRIPT_DIR"
while [[ "$search" != "/" && -n "$search" ]]; do
    candidate="$search/skills/detect-ai-fingerprints/scan.sh"
    if [[ -x "$candidate" ]]; then
        SCAN_SH="$candidate"
        break
    fi
    search=$(dirname "$search")
done

if [[ -z "$SCAN_SH" ]]; then
    # Scanner not found in this checkout; silently allow rather than block
    # on missing tooling. The hook is opt-in by way of file existence.
    exit 0
fi

# Zero-commit push carries nothing to review (#714). Compute ahead-of-upstream
# count when an upstream is set; if it returns 0, this push transfers no
# commits and the hook has nothing to prevent. When no upstream is set (fresh
# branch, `git push -u origin branch`), the push carries the whole branch and
# the scan proceeds against HEAD.
UPSTREAM=$(git -C "$EFFECTIVE_CWD" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)
if [[ -n "$UPSTREAM" ]]; then
    AHEAD=$(git -C "$EFFECTIVE_CWD" rev-list --count "@{u}..HEAD" 2>/dev/null || echo "0")
    if [[ "$AHEAD" -eq 0 ]]; then
        exit 0
    fi
fi

COMMIT_MSG=$(git -C "$EFFECTIVE_CWD" log -1 --pretty=%B 2>/dev/null || true)
if [[ -z "$COMMIT_MSG" ]]; then
    exit 0
fi

# Write to a temp file (scan.sh --commit-message-file expects a path it can read).
# Ensure trailing newline: scan.sh's line-reading loop drops the final line
# if the file is not newline-terminated (separate ticket filed against the
# scanner). Printf with %s\n guarantees terminator regardless of whether
# COMMIT_MSG already ended with one.
TMP_MSG=$(mktemp)
trap 'rm -f "$TMP_MSG"' EXIT
printf '%s\n' "$COMMIT_MSG" > "$TMP_MSG"

SCAN_OUT=$(bash "$SCAN_SH" --commit-message-file "$TMP_MSG" 2>&1)
SCAN_EXIT=$?

if [[ "$SCAN_EXIT" -eq 0 ]]; then
    exit 0
fi

# Non-zero exit: violations found (or scanner errored).
cat >&2 <<HOOKEOF
BLOCKED: detect-ai-fingerprints scan of the latest commit body found
violations. Fix the commit message and amend, then retry:

  git commit --amend

Scanner output:
$SCAN_OUT

See skills/detect-ai-fingerprints/SKILL.md for the rule catalogue
and the rationale for each. Common offenders:
  - em-dashes (U+2014) and en-dashes (U+2013): use ASCII -- or rewrite.
  - Banned adverbs (deliberately, intentionally, explicitly,
    fundamentally, essentially, crucially, notably): rewrite.
  - Structured Why: / How to apply: blocks in commit bodies: drop them.
  - ## headers and bullet lists in commit bodies: use prose paragraphs.

If you genuinely cannot fix the body and the scanner's reading is wrong,
file an issue on the scanner. Do not bypass.
HOOKEOF
exit 2
