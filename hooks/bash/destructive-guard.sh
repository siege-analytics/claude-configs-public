#!/bin/bash
# Hook: bash/destructive-guard (v1, prod-destructive tier only)
# Enforces: discipline against destructive Bash commands at PreToolUse time.
# Trigger: PreToolUse on Bash
#
# Closes claude-configs-public#127 v1 (per operator decision 2026-05-18:
# "ship C but we should build towards A"). v1 only enforces the
# prod-destructive tier; shared-resource and general-mutation tiers are
# catalogued for v2 and logged as [v2-deferred] without blocking. The
# tier-tagged structure lets v2 layer per-tier gates without reshaping.
#
# Logic:
#   - For each (tier, pattern, reason) in DENY_PATTERNS, regex-match command.
#   - If match AND tier == prod-destructive AND no escape -> BLOCK (exit 2).
#   - If match AND tier in {shared-resource, general-mutation} -> log
#     [v2-deferred:<tier>] to stderr at exit 0 (no block).
#   - Otherwise -> exit 0.
#
# Escape hatches (v1, prod-destructive tier):
#   1. Latest commit on HEAD has an `Authorized: <reason>` trailer.
#      One-shot; expires on the next commit.
#   2. Pattern is in the allow-list file (project-scoped
#      <repo>/.claude/destructive-bash-allowlist.txt, falls back to
#      ~/.claude/destructive-bash-allowlist.txt). One regex per line.
#   3. Env var CLAUDE_DESTRUCTIVE_BASH=allow set for the subprocess.
#      Discouraged.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)

# Fast exit if no command extractable.
[[ -z "$COMMAND" ]] && exit 0

# Env-var override (escape 3) -- check first to avoid scanning.
if [[ "${CLAUDE_DESTRUCTIVE_BASH:-}" == "allow" ]]; then
    exit 0
fi

# Tier-tagged deny-list. Format: "tier|extended-regex|reason"
# v1 prod-destructive: narrow, obvious-destructive shapes only. FP rate
# matters more than FN rate at v1 because operators will disable a noisy
# hook before it provides v2 evidence.
DENY_PATTERNS=(
    # rm -rf at dangerous roots
    "prod-destructive|^[[:space:]]*rm[[:space:]]+(-[a-zA-Z]*[rR][a-zA-Z]*[fF][a-zA-Z]*|-[a-zA-Z]*[fF][a-zA-Z]*[rR][a-zA-Z]*)([[:space:]]+--?[a-zA-Z-]+)*[[:space:]]+(/|\\\$HOME|~|\\.)[[:space:]]*\$|recursive deletion of root tree or home"
    # git push --force / --force-with-lease to protected branches
    "prod-destructive|git[[:space:]]+push[[:space:]]+.*--force(-with-lease)?[[:space:]]+(origin[[:space:]]+)?(main|master|develop|staging)|force-push to protected branch"
    "prod-destructive|git[[:space:]]+push[[:space:]]+.*(main|master|develop|staging).*--force(-with-lease)?|force-push to protected branch"
    # Hook bypass flags
    "prod-destructive|git[[:space:]]+(commit|push|merge|rebase)[[:space:]]+.*--no-verify|hook bypass via --no-verify"
    "prod-destructive|git[[:space:]]+[a-z]+[[:space:]]+.*--no-gpg-sign|sign bypass via --no-gpg-sign"
    "prod-destructive|git[[:space:]]+-c[[:space:]]+commit\\.gpgsign=false|sign bypass via -c commit.gpgsign=false"
    # World-writable recursion
    "prod-destructive|chmod[[:space:]]+-R[[:space:]]+(777|ugo\\+w|a\\+w)|world-writable recursion"
    # psql mutation against non-localhost (negative-lookahead via two patterns)
    # First pattern matches psql with -h <non-local>; second matches connection-string form
    "prod-destructive|psql[[:space:]]+(-h[[:space:]]*|--host[=[:space:]])[^[:space:]l]([^[:space:]]*[^l]|l[^o]|lo[^c])[^[:space:]]*[[:space:]].*-c[[:space:]].*\\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER)\\b|destructive SQL via psql against non-localhost"
    # aws s3 destructive
    "prod-destructive|aws[[:space:]]+s3[[:space:]]+(rm|mv)[[:space:]]+s3://|aws s3 destructive operation"
    # kubectl writes (caller can allow-list dev contexts)
    "prod-destructive|kubectl[[:space:]]+(apply|delete|replace|patch|edit|scale|rollout)[[:space:]]|kubectl mutation"

    # v2-deferred tiers -- logged but not blocked at v1. These exist so the
    # firing log shows what v2 would gate; remove the comment and tighten
    # gates when v2 work begins.
    "shared-resource|gh[[:space:]]+issue[[:space:]]+(create|comment|edit)|github issue write"
    "shared-resource|gh[[:space:]]+release[[:space:]]+create|github release create"
    "general-mutation|curl[[:space:]]+.*-X[[:space:]]+(POST|PUT|PATCH|DELETE)|network mutation via curl"
)

# Read allow-list files (project-scoped first, falls back to global).
ALLOW_PATTERNS=()
load_allowlist() {
    local f="$1"
    [[ ! -f "$f" ]] && return
    while IFS= read -r line; do
        # Strip blank lines + comments.
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        ALLOW_PATTERNS+=("$line")
    done < "$f"
}
if [[ -n "$CWD" ]]; then
    proj_allow=""
    if repo_root=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null); then
        proj_allow="$repo_root/.claude/destructive-bash-allowlist.txt"
        load_allowlist "$proj_allow"
    fi
fi
load_allowlist "$HOME/.claude/destructive-bash-allowlist.txt"

# Allow-list check (escape 2). Allow-list patterns are full-regex.
# `${arr[@]:-}` guards against the empty-array-under-set-u bash quirk.
if [[ "${#ALLOW_PATTERNS[@]}" -gt 0 ]]; then
    for allow_re in "${ALLOW_PATTERNS[@]}"; do
        if echo "$COMMAND" | grep -qE "$allow_re"; then
            exit 0
        fi
    done
fi

# Trailer escape (escape 1). Only relevant for git-tracked CWD.
HAS_AUTHORIZED_TRAILER=0
if [[ -n "$CWD" ]] && git -C "$CWD" rev-parse --git-dir >/dev/null 2>&1; then
    commit_msg=$(git -C "$CWD" log -1 --pretty=%B 2>/dev/null || true)
    if [[ -n "$commit_msg" ]]; then
        trailers=$(echo "$commit_msg" | git -C "$CWD" interpret-trailers --parse --no-divider 2>/dev/null || true)
        if echo "$trailers" | grep -qE '^Authorized:[[:space:]]+\S'; then
            HAS_AUTHORIZED_TRAILER=1
        fi
    fi
fi

# Walk deny-list, dispatch per tier.
MATCHED_BLOCKS=()
for entry in "${DENY_PATTERNS[@]}"; do
    tier="${entry%%|*}"; rest="${entry#*|}"
    pattern="${rest%|*}"; reason="${entry##*|}"
    # `entry` has 3 |-separated fields: tier|pattern|reason. The above
    # parses tier and reason; pattern is everything between the first | and
    # the last |. Use awk to be safe.
    pattern=$(printf '%s' "$entry" | awk -F'|' '{for(i=2;i<NF;i++){printf "%s%s",$i,(i<NF-1?"|":"")}}')

    if echo "$COMMAND" | grep -qE -- "$pattern"; then
        case "$tier" in
            prod-destructive)
                # Trailer escape applies only to prod-destructive tier in v1.
                if [[ "$HAS_AUTHORIZED_TRAILER" -eq 1 ]]; then
                    continue
                fi
                MATCHED_BLOCKS+=("$tier|$reason|$pattern")
                ;;
            shared-resource|general-mutation)
                # v2-deferred: log to stderr, do not block.
                echo "[destructive-guard v2-deferred:$tier] $reason (pattern: $pattern)" >&2
                ;;
        esac
    fi
done

[[ "${#MATCHED_BLOCKS[@]:-0}" -eq 0 ]] && exit 0

{
    echo "BLOCKED: command matches one or more destructive-bash patterns."
    echo ""
    for m in "${MATCHED_BLOCKS[@]}"; do
        tier="${m%%|*}"; rest="${m#*|}"
        reason="${rest%%|*}"; pattern="${rest##*|}"
        echo "  - Tier: $tier"
        echo "    Reason: $reason"
        echo "    Pattern: $pattern"
    done
    echo ""
    echo "Escape hatches (in order of preference):"
    echo "  1. Add an Authorized: <reason> trailer to the latest commit"
    echo "     (one-shot; expires on next commit)."
    echo "  2. Add the exact regex to your allow-list:"
    echo "       <repo>/.claude/destructive-bash-allowlist.txt   (project)"
    echo "       ~/.claude/destructive-bash-allowlist.txt        (global)"
    echo "  3. CLAUDE_DESTRUCTIVE_BASH=allow as a process env var"
    echo "     (discouraged; bypasses ALL prod-destructive patterns)."
    echo ""
    echo "If the pattern is firing as a false positive on legitimate work,"
    echo "use the allow-list. If the command is genuinely destructive and"
    echo "deliberate, add the Authorized: trailer with a reason."
} >&2
exit 2
