#!/usr/bin/env bash
# Mechanical scanner for stylistic AI fingerprints (rules 1-6 of [rule:no-ai-fingerprints]).
# Operates on a unified diff from stdin OR fetches the diff itself based on flags.
# Reports violations as <file>:<line>:<rule>:<excerpt>. Exit 0 if clean, 1 if violations found.
#
# Usage:
#   scan.sh                       # scan staged diff (git diff --cached)
#   scan.sh --pr <number>         # scan a GitHub PR (requires gh)
#   scan.sh --working             # scan working-tree diff (git diff)
#   scan.sh --message <text>      # scan a commit/PR message body for rule 2/5/6 violations
#   scan.sh --message-file <path> # scan a commit/PR message body from a file
#
# Modifiers (combine with any mode):
#   --ignore <glob>               # skip files matching this glob (repeatable). For ad-hoc and
#                                 # inspection use; production gates (commit, code-review) do
#                                 # NOT pass --ignore. The narrow legitimate use is scanning
#                                 # the scanner's own definition files, which contain the rule
#                                 # source, regex, and worked examples by design.
#
# This scanner covers rules 1-6 only. Structural rules 7-11 require [skill:code-review] judgment.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

EM_DASH=$'\xe2\x80\x94'   # U+2014
EN_DASH=$'\xe2\x80\x93'   # U+2013

ADVERBS_RE='\b(deliberately|intentionally|explicitly|fundamentally|essentially|crucially|notably)\b'
HISTORY_RE='\b(PR #[0-9]+|Sprint [A-Za-z0-9]+|v[0-9]+\.[0-9]+\.[0-9]+ (hardening|follow-up|fix)|issue #[0-9]+|ticket [A-Z]+-[0-9]+)\b'
WHY_BLOCK_RE='^[[:space:]]*(\*\*|##+ )?(Why|How to apply)[:\*]'

violations=0
declare -a IGNORE_GLOBS=()

is_ignored() {
    local file="$1" pat
    for pat in "${IGNORE_GLOBS[@]}"; do
        # shellcheck disable=SC2053
        if [[ "$file" == $pat ]]; then
            return 0
        fi
    done
    return 1
}

emit() {
    local file="$1" line="$2" rule="$3" excerpt="$4"
    if is_ignored "$file"; then
        return
    fi
    printf '%s:%s:%s: %s\n' "$file" "$line" "$rule" "$excerpt"
    violations=$((violations + 1))
}

# --- Diff scanner: reads unified diff from a process substitution (NOT a pipe).
# Caller MUST invoke as: scan_diff_stdin < <(git diff ...) so the violations
# counter survives. A bare pipeline puts the while loop in a subshell and
# loses the counter.
scan_diff_stdin() {
    local current_file="" line_no=0
    while IFS= read -r line; do
        if [[ "$line" =~ ^\+\+\+\ b/(.+)$ ]]; then
            current_file="${BASH_REMATCH[1]}"
            line_no=0
            continue
        fi
        if [[ "$line" =~ ^@@\ -[0-9,]+\ \+([0-9]+) ]]; then
            line_no="${BASH_REMATCH[1]}"
            continue
        fi
        # Only consider added lines (skip the +++ header handled above).
        if [[ "$line" == +* && "$line" != +++* ]]; then
            local content="${line:1}"

            # Rule 1: em-dashes / en-dashes (every match per line).
            local em_count
            em_count=$(grep -o -- "$EM_DASH" <<< "$content" | wc -l | tr -d ' ')
            for ((i = 0; i < em_count; i++)); do
                emit "$current_file" "$line_no" "rule-1-em-dash" "$content"
            done
            local en_count
            en_count=$(grep -o -- "$EN_DASH" <<< "$content" | wc -l | tr -d ' ')
            for ((i = 0; i < en_count; i++)); do
                emit "$current_file" "$line_no" "rule-1-en-dash" "$content"
            done

            # Rule 4: every banned-adverb match on the line.
            while IFS= read -r adverb; do
                [[ -n "$adverb" ]] && emit "$current_file" "$line_no" "rule-4-adverb($adverb)" "$content"
            done < <(grep -oE "$ADVERBS_RE" <<< "$content")

            # Rule 6: history references in code comments (heuristic: line begins with # or //).
            if [[ "$content" =~ ^[[:space:]]*(#|//)[^!] ]]; then
                while IFS= read -r ref; do
                    [[ -n "$ref" ]] && emit "$current_file" "$line_no" "rule-6-history-ref($ref)" "$content"
                done < <(grep -oE "$HISTORY_RE" <<< "$content")
            fi

            line_no=$((line_no + 1))
            continue
        fi
        # Context lines advance the new-side line counter.
        if [[ "$line" == " "* ]]; then
            line_no=$((line_no + 1))
        fi
    done
}

# --- Message scanner: reads a commit/PR message body from stdin or a file.
# Caller MUST invoke as scan_message_stdin "<file>" < "<file>" (or process sub).
scan_message_stdin() {
    local virtual_file="${1:-<message>}" line_no=0 in_subject=1
    while IFS= read -r line; do
        line_no=$((line_no + 1))

        # Subject line (line 1) is exempt from rule 5 body checks.
        if (( in_subject )); then
            in_subject=0
            continue
        fi
        # Skip the blank separator after subject.
        if [[ -z "$line" && "$line_no" == "2" ]]; then
            continue
        fi

        # Rule 1: em-dashes / en-dashes anywhere in the message.
        local em_count en_count
        em_count=$(grep -o -- "$EM_DASH" <<< "$line" | wc -l | tr -d ' ')
        for ((i = 0; i < em_count; i++)); do
            emit "$virtual_file" "$line_no" "rule-1-em-dash" "$line"
        done
        en_count=$(grep -o -- "$EN_DASH" <<< "$line" | wc -l | tr -d ' ')
        for ((i = 0; i < en_count; i++)); do
            emit "$virtual_file" "$line_no" "rule-1-en-dash" "$line"
        done

        # Rule 2: structured rationale blocks.
        if grep -qE "$WHY_BLOCK_RE" <<< "$line"; then
            emit "$virtual_file" "$line_no" "rule-2-structured-rationale" "$line"
        fi

        # Rule 4: every adverb match.
        while IFS= read -r adverb; do
            [[ -n "$adverb" ]] && emit "$virtual_file" "$line_no" "rule-4-adverb($adverb)" "$line"
        done < <(grep -oE "$ADVERBS_RE" <<< "$line")

        # Rule 5: bullets in commit body.
        if [[ "$line" =~ ^[[:space:]]*[-*\+][[:space:]] ]]; then
            emit "$virtual_file" "$line_no" "rule-5-bullet" "$line"
        fi

        # Rule 5: section headers in commit body.
        if [[ "$line" =~ ^##+\  ]]; then
            emit "$virtual_file" "$line_no" "rule-5-header" "$line"
        fi
    done
}

# --- Argument dispatch.
mode="staged"
arg=""

while (( $# > 0 )); do
    case "$1" in
        --pr)
            mode="pr"
            arg="${2:?--pr requires a PR number}"
            shift 2
            ;;
        --working)
            mode="working"
            shift
            ;;
        --message)
            mode="message-inline"
            arg="${2:?--message requires text}"
            shift 2
            ;;
        --message-file)
            mode="message-file"
            arg="${2:?--message-file requires a path}"
            shift 2
            ;;
        --ignore)
            IGNORE_GLOBS+=("${2:?--ignore requires a glob}")
            shift 2
            ;;
        -h|--help)
            sed -n '2,22p' "$0"
            exit 0
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

case "$mode" in
    staged)
        scan_diff_stdin < <(git diff --cached --unified=3)
        ;;
    working)
        scan_diff_stdin < <(git diff --unified=3)
        ;;
    pr)
        if ! command -v gh >/dev/null 2>&1; then
            echo "gh CLI required for --pr mode" >&2
            exit 2
        fi
        scan_diff_stdin < <(gh pr diff "$arg")
        ;;
    message-inline)
        scan_message_stdin "<inline-message>" < <(printf '%s\n' "$arg")
        ;;
    message-file)
        scan_message_stdin "$arg" < "$arg"
        ;;
esac

if (( violations > 0 )); then
    echo
    echo "scanned with rules 1-6 of [rule:no-ai-fingerprints]; rules 7-11 require [skill:code-review] judgment."
    echo "violations: $violations"
    exit 1
fi

echo "clean (rules 1-6); rules 7-11 still require [skill:code-review] judgment."
exit 0
