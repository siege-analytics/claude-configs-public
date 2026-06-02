#!/bin/bash
# Hook: detect-ai-fingerprints (commit-body scan)
# Enforces: skills/meta/detect-ai-fingerprints/SKILL.md at push/pr-create/pr-merge time.
# Trigger: PreToolUse on Bash(git push *), Bash(gh pr create *), Bash(gh pr merge *)
#
# Calls scan.sh --message-file <temp> against the latest commit body. Blocks
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
# root that contains skills/meta/detect-ai-fingerprints/scan.sh.
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCAN_SH=""
search="$SCRIPT_DIR"
while [[ "$search" != "/" && -n "$search" ]]; do
    candidate="$search/skills/meta/detect-ai-fingerprints/scan.sh"
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

COMMIT_MSG=$(git -C "$EFFECTIVE_CWD" log -1 --pretty=%B 2>/dev/null || true)
if [[ -z "$COMMIT_MSG" ]]; then
    exit 0
fi

# Write to a temp file (scan.sh --message-file expects a path it can read).
# Ensure trailing newline: scan.sh's line-reading loop drops the final line
# if the file is not newline-terminated (separate ticket filed against the
# scanner). Printf with %s\n guarantees terminator regardless of whether
# COMMIT_MSG already ended with one.
TMP_MSG=$(mktemp)
trap 'rm -f "$TMP_MSG"' EXIT
printf '%s\n' "$COMMIT_MSG" > "$TMP_MSG"

SCAN_OUT=$(bash "$SCAN_SH" --message-file "$TMP_MSG" 2>&1)
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

See skills/meta/detect-ai-fingerprints/SKILL.md for the rule catalogue
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
