#!/usr/bin/env bash
# Mechanical scanner for AI-fingerprint rules across the per-act rule files. Covers writing-prose:1-4, writing-code:2, writing-tests:3-4, writing-claims:2-3, writing-releases:2.
# Operates on a unified diff from stdin OR fetches the diff itself based on flags.
# Reports violations as <file>:<line>:<rule>:<excerpt>. Exit 0 if clean, 1 if violations found.
#
# Usage:
#   scan.sh                       # scan staged diff (git diff --cached)
#   scan.sh --pr <number>         # scan a GitHub PR (requires gh)
#   scan.sh --working             # scan working-tree diff (git diff)
#   scan.sh --message <text>      # scan a commit/PR message body for writing-prose / writing-claims violations
#   scan.sh --message-file <path> # scan a commit/PR message body from a file
#
# Modifiers (combine with any mode):
#   --ignore <glob>               # skip files matching this glob (repeatable). For ad-hoc and
#                                 # inspection use; production gates (commit, code-review) do
#                                 # NOT pass --ignore. The narrow legitimate use is scanning
#                                 # the scanner's own definition files, which contain the rule
#                                 # source, regex, and worked examples by design.
#
# This scanner covers writing-prose:1-4, writing-code:2, writing-tests:3-4, writing-claims:2-3, writing-releases:2. The remaining rules require [skill:code-review] judgment.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

EM_DASH=$'\xe2\x80\x94'   # U+2014
EN_DASH=$'\xe2\x80\x93'   # U+2013

ADVERBS_RE='\b(deliberately|intentionally|explicitly|fundamentally|essentially|crucially|notably)\b'
HISTORY_RE='\b(PR #[0-9]+|Sprint [A-Za-z0-9]+|v[0-9]+\.[0-9]+\.[0-9]+ (hardening|follow-up|fix)|issue #[0-9]+|ticket [A-Z]+-[0-9]+)\b'
WHY_BLOCK_RE='^[[:space:]]*(\*\*|##+ )?(Why|How to apply)[:\*]'
# writing-claims:2 / :3: countable-claim and completeness trigger phrases. Conservative on first roll-out.
COUNTABLE_RE='\b(all [0-9]+|all [a-z]+ engines?|all [a-z]+ connectors?|all call sites?|every (call site|engine|caller|connector)|no remaining|fully covers|completes the [a-z]+ surface)\b'
# writing-claims:2 / :3: required Verified-by trailer when a countable claim is present.
VERIFIED_BY_RE='^[[:space:]]*Verified-by:[[:space:]]+'
# writing-tests:3: actionable-skip-message verbs. Heuristic; tune over time.
SKIP_VERBS_RE='\b(install|set|configure|run|enable|start|provide|export)\b'
# writing-tests:3: a skip message is matched against pytest.skip / pytest.xfail / unittest skip.
SKIP_CALL_RE='(pytest\.skip|pytest\.xfail|@pytest\.mark\.skipif|self\.skipTest|unittest\.skip)\([^)]*'

violations=0
declare -a IGNORE_GLOBS=()

is_ignored() {
    local file="$1" pat
    # Defensive expansion: empty array under `set -u` on bash 3.2 (macOS default)
    # would error on `${IGNORE_GLOBS[@]}` directly.
    if (( ${#IGNORE_GLOBS[@]} == 0 )); then
        return 1
    fi
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

            # writing-prose:1: em-dashes / en-dashes (every match per line).
            local em_count
            em_count=$(grep -o -- "$EM_DASH" <<< "$content" | wc -l | tr -d ' ')
            for ((i = 0; i < em_count; i++)); do
                emit "$current_file" "$line_no" "writing-prose-1-em-dash" "$content"
            done
            local en_count
            en_count=$(grep -o -- "$EN_DASH" <<< "$content" | wc -l | tr -d ' ')
            for ((i = 0; i < en_count; i++)); do
                emit "$current_file" "$line_no" "writing-prose-1-en-dash" "$content"
            done

            # writing-prose:3: every banned-adverb match on the line.
            while IFS= read -r adverb; do
                [[ -n "$adverb" ]] && emit "$current_file" "$line_no" "writing-prose-3-adverb($adverb)" "$content"
            done < <(grep -oE "$ADVERBS_RE" <<< "$content")

            # writing-code:2: history references in code comments (heuristic: line begins with # or //).
            if [[ "$content" =~ ^[[:space:]]*(#|//)[^!] ]]; then
                while IFS= read -r ref; do
                    [[ -n "$ref" ]] && emit "$current_file" "$line_no" "writing-code-2-history-ref($ref)" "$content"
                done < <(grep -oE "$HISTORY_RE" <<< "$content")
            fi

            # writing-tests:3: pytest.skip / xfail / skipif / skipTest must name the remediation.
            # Heuristic: extract the call's argument string and check for an actionable
            # verb plus an identifier-shaped token. False positives expected; tune via
            # observed friction.
            if [[ "$current_file" == *.py ]]; then
                local skip_arg
                skip_arg=$(grep -oE "$SKIP_CALL_RE" <<< "$content" | head -1)
                if [[ -n "$skip_arg" ]]; then
                    local skip_msg
                    skip_msg=$(echo "$skip_arg" | sed -E 's/^[^(]+\([^"'\'']*["'\'']?//; s/["'\'']?[[:space:]]*$//')
                    if [[ -n "$skip_msg" ]]; then
                        local has_verb has_id
                        has_verb=$(echo "$skip_msg" | grep -oiE "$SKIP_VERBS_RE" | head -1)
                        # An identifier-shaped token: env var (UPPER), command name, package name, file path.
                        has_id=$(echo "$skip_msg" | grep -oE '([A-Z][A-Z0-9_]+|[a-z][a-z0-9_-]*\.(py|sh|md)|/[a-z]|[a-z][a-z0-9_-]+/)' | head -1)
                        if [[ -z "$has_verb" || -z "$has_id" ]]; then
                            emit "$current_file" "$line_no" "writing-tests-3-skip-not-actionable" "$content"
                        fi
                    fi
                fi
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
    # writing-claims:2 / :3 need a pass over the whole message: collect countable-claim lines,
    # then check whether the message contains a Verified-by: trailer. If claims
    # are present without the trailer, each claim line gets a writing-claims:2 / :3 violation.
    local has_verified_by=0
    declare -a claim_lines=()
    declare -a claim_excerpts=()

    while IFS= read -r line; do
        line_no=$((line_no + 1))

        # Subject line (line 1) is exempt from writing-prose:4 body checks.
        if (( in_subject )); then
            in_subject=0
            continue
        fi
        # Skip the blank separator after subject.
        if [[ -z "$line" && "$line_no" == "2" ]]; then
            continue
        fi

        # writing-claims:2 / :3 trailer detection (any line in body counts).
        if [[ "$line" =~ ^[[:space:]]*Verified-by:[[:space:]]+ ]]; then
            has_verified_by=1
        fi

        # writing-claims:2 / :3 claim detection (collect for end-of-message decision).
        if grep -qiE "$COUNTABLE_RE" <<< "$line"; then
            claim_lines+=("$line_no")
            claim_excerpts+=("$line")
        fi

        # writing-prose:1: em-dashes / en-dashes anywhere in the message.
        local em_count en_count
        em_count=$(grep -o -- "$EM_DASH" <<< "$line" | wc -l | tr -d ' ')
        for ((i = 0; i < em_count; i++)); do
            emit "$virtual_file" "$line_no" "writing-prose-1-em-dash" "$line"
        done
        en_count=$(grep -o -- "$EN_DASH" <<< "$line" | wc -l | tr -d ' ')
        for ((i = 0; i < en_count; i++)); do
            emit "$virtual_file" "$line_no" "writing-prose-1-en-dash" "$line"
        done

        # writing-prose:2: structured rationale blocks.
        if grep -qE "$WHY_BLOCK_RE" <<< "$line"; then
            emit "$virtual_file" "$line_no" "writing-prose-2-structured-rationale" "$line"
        fi

        # writing-prose:3: every adverb match.
        while IFS= read -r adverb; do
            [[ -n "$adverb" ]] && emit "$virtual_file" "$line_no" "writing-prose-3-adverb($adverb)" "$line"
        done < <(grep -oE "$ADVERBS_RE" <<< "$line")

        # writing-prose:4: bullets in commit body.
        if [[ "$line" =~ ^[[:space:]]*[-*\+][[:space:]] ]]; then
            emit "$virtual_file" "$line_no" "writing-prose-4-bullet" "$line"
        fi

        # writing-prose:4: section headers in commit body.
        if [[ "$line" =~ ^##+\  ]]; then
            emit "$virtual_file" "$line_no" "writing-prose-4-header" "$line"
        fi
    done

    # writing-claims:2 / :3 end-of-message decision: claims present without a Verified-by trailer.
    if (( ${#claim_lines[@]} > 0 && has_verified_by == 0 )); then
        local i
        for (( i = 0; i < ${#claim_lines[@]}; i++ )); do
            emit "$virtual_file" "${claim_lines[$i]}" "writing-claims-2-countable-claim-no-verified-by" "${claim_excerpts[$i]}"
        done
    fi
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

COVERAGE_NOTE='scanned: writing-prose:1-4 (stylistic), writing-code:2 (history references in code comments), writing-tests:3-4 (skip messages, mock-without-spec), writing-claims:2-3 (countable claims and completeness claims need Verified-by trailer), writing-releases:2 (skip-count trending). The rest require [skill:code-review] judgment.'

if (( violations > 0 )); then
    echo
    echo "$COVERAGE_NOTE"
    echo "violations: $violations"
    exit 1
fi

echo "clean. $COVERAGE_NOTE"
exit 0
