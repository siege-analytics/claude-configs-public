#!/bin/bash
# Hook: bash/destructive-guard (v2, all tiers enforced)
# Enforces: discipline against destructive Bash commands at PreToolUse time.
# Trigger: PreToolUse on Bash
#
# Closes claude-configs-public#127 v1 (prod-destructive tier) and #582 v2
# (shared-resource, general-mutation tiers promoted to mechanical).
#
# Logic:
#   - For each (tier, pattern, reason) in DENY_PATTERNS, regex-match command.
#   - If match AND no escape -> BLOCK (exit 2).
#   - Otherwise -> exit 0.
#
# Escape hatches (all tiers):
#   1. Evidence-chain override in command text:
#      [destructive-ok: Reason: <why>; Evidence: <obs>; Falsification: <disproof>]
#   2. Latest commit on HEAD has an `Authorized: <reason>` trailer.
#      One-shot; expires on the next commit.
#   3. Pattern is in the allow-list file (project-scoped
#      <repo>/.claude/destructive-bash-allowlist.txt, falls back to
#      ~/.claude/destructive-bash-allowlist.txt). One regex per line.
#   4. Env var CLAUDE_DESTRUCTIVE_BASH=allow set for the subprocess.
#      Discouraged.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

# Block-event logging (#602): record every block for classification.
source "$HOOK_DIR/../lib/log-block.sh" 2>/dev/null || true

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

    # shared-resource tier: commands that affect shared state (GitHub issues, releases).
    # Promoted from v2-deferred to mechanical in #582.
    "shared-resource|gh[[:space:]]+issue[[:space:]]+(create|comment|edit|close|delete|reopen|label)|github issue write"
    "shared-resource|gh[[:space:]]+pr[[:space:]]+(create|merge|close|edit|comment|review)|github pull request write"
    "shared-resource|gh[[:space:]]+release[[:space:]]+create|github release create"
    # general-mutation tier: network mutations via curl.
    # Promoted from v2-deferred to mechanical in #582.
    "general-mutation|curl[[:space:]]+.*-X[[:space:]]+(POST|PUT|PATCH|DELETE)|network mutation via curl"
)

# Governance issue reporting is a reporting surface, not an implementation
# mutation. Allow only inspectable `gh issue create` / `gh issue comment`
# commands with non-empty title/body evidence. Issue edit/close/delete/etc.
# remain guarded shared-resource mutations.
is_governance_issue_reporting_command() {
    python3 - "$COMMAND" "$CWD" <<'PYCODE'
import os, shlex, sys

command = sys.argv[1]
cwd = sys.argv[2] or os.getcwd()
if any(ch in command for ch in "\n\r;&|<>`$"):
    sys.exit(1)
try:
    args = shlex.split(command)
except ValueError:
    sys.exit(1)
if len(args) >= 3 and args[0] == "cd":
    if len(args) < 5 or args[2] != "&&":
        sys.exit(1)
    cwd = args[1]
    args = args[3:]
if len(args) < 3 or args[0] != "gh" or args[1] != "issue":
    sys.exit(1)
sub = args[2]
if sub not in {"create", "comment"}:
    sys.exit(1)

def parse_flags(positional_count, required_flags):
    positional = []
    flags = {}
    i = 3
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            if "=" in arg:
                flag, value = arg.split("=", 1)
            else:
                flag = arg
                i += 1
                if i >= len(args):
                    sys.exit(1)
                value = args[i]
            if flag not in required_flags:
                sys.exit(1)
            if flag in flags:
                sys.exit(1)
            flags[flag] = value
        else:
            positional.append(arg)
        i += 1
    if len(positional) != positional_count:
        sys.exit(1)
    return positional, flags

def nonempty_body(flags):
    has_body = "--body" in flags
    has_body_file = "--body-file" in flags
    if has_body == has_body_file:
        return False
    if has_body:
        return bool(flags["--body"].strip())
    body_file = flags["--body-file"]
    if body_file == "-" or body_file.startswith(("/dev/fd/", "/proc/self/fd/")):
        return False
    path = body_file if os.path.isabs(body_file) else os.path.join(cwd, body_file)
    try:
        return os.path.isfile(path) and os.path.getsize(path) > 0 and bool(open(path, encoding="utf-8").read().strip())
    except Exception:
        return False

if sub == "create":
    _positional, flags = parse_flags(0, {"--repo", "--title", "--body", "--body-file"})
    title = flags.get("--title", "")
    if not title.strip():
        sys.exit(1)
    if not nonempty_body(flags):
        sys.exit(1)
    sys.exit(0)

positional, flags = parse_flags(1, {"--repo", "--body", "--body-file"})
if positional[0].startswith("-"):
    sys.exit(1)
if not nonempty_body(flags):
    sys.exit(1)
sys.exit(0)
PYCODE
}

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

# Evidence-chain override (escape 1). Ref: #582.
if echo "$COMMAND" | grep -qE '\[destructive-ok:[[:space:]]+Reason:[^]]+;[[:space:]]*Evidence:[^]]+;[[:space:]]*Falsification:[^]]+\]'; then
    exit 0
fi

if is_governance_issue_reporting_command; then
    exit 0
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
        if [[ "$HAS_AUTHORIZED_TRAILER" -eq 1 ]]; then
            continue
        fi
        MATCHED_BLOCKS+=("$tier|$reason|$pattern")
    fi
done

[[ ${#MATCHED_BLOCKS[@]} -eq 0 ]] && exit 0

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
    echo "  1. Include an evidence-chain override in the command:"
    echo "     [destructive-ok: Reason: <why>; Evidence: <obs>; Falsification: <disproof>]"
    echo "  2. Add an Authorized: <reason> trailer to the latest commit"
    echo "     (one-shot; expires on next commit)."
    echo "  3. Add the exact regex to your allow-list:"
    echo "       <repo>/.claude/destructive-bash-allowlist.txt   (project)"
    echo "       ~/.claude/destructive-bash-allowlist.txt        (global)"
    echo "  4. CLAUDE_DESTRUCTIVE_BASH=allow as a process env var"
    echo "     (discouraged; bypasses ALL patterns)."
    echo ""
    echo "If the pattern is firing as a false positive on legitimate work,"
    echo "use the allow-list. If the command is genuinely destructive and"
    echo "deliberate, use the evidence-chain override with a reason."
} >&2
MATCHED_REASON="${MATCHED_BLOCKS[0]#*|}"
MATCHED_REASON="${MATCHED_REASON%%|*}"
log_block_event "destructive-guard" "$MATCHED_REASON" "$COMMAND"
exit 2
