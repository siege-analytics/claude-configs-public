#!/usr/bin/env bash
# Content-scope helper for blocking guards (#699).
#
# Guards registered globally with no scope test fire in EVERY workspace on a
# shared Craft server. This helper lets each guard decide whether the current
# command touches a repository the guard actually governs.
#
# The scope decision is based on WHAT THE COMMAND TOUCHES, not on cwd or
# workspace name. Location-based scoping breaks when a session lands in the
# "wrong" workspace; content-scope survives that.
#
# Usage from a guard:
#
#     source "$HOOK_DIR/../lib/scope-check.sh"
#     if ! _scope_in_scope "$COMMAND" "$CWD"; then
#         exit 0
#     fi
#
# The helper returns 0 (in scope) or 1 (out of scope). Guards MUST treat
# out-of-scope as exit 0 (allow), not as a block.
#
# Scope definition: the command touches a repo whose remote origin URL is
# on the SCOPED_OWNERS allowlist. The allowlist defaults to "siege-analytics"
# and can be overridden by exporting CLAUDE_SCOPED_OWNERS as a colon-
# separated list before invoking the hook (e.g. for repos this
# claude-configs-public checkout is used with by other clients).

# Owner allowlist. Colon-separated. Guards that live in this repo scope to
# siege-analytics's namespace by default; other clients override via env.
SCOPED_OWNERS="${CLAUDE_SCOPED_OWNERS:-siege-analytics}"

_scope_extract_owner_from_gh_r() {
    # Parse `gh <verb> ... -R owner/repo` or `--repo owner/repo`.
    # Returns the owner portion on stdout, empty string if not present.
    local command="$1"
    if [[ "$command" =~ (^|[[:space:]])--repo[[:space:]]+([^/[:space:]]+)/ ]]; then
        printf '%s' "${BASH_REMATCH[2]}"
        return
    fi
    if [[ "$command" =~ (^|[[:space:]])--repo=([^/[:space:]]+)/ ]]; then
        printf '%s' "${BASH_REMATCH[2]}"
        return
    fi
    if [[ "$command" =~ (^|[[:space:]])-R[[:space:]]+([^/[:space:]]+)/ ]]; then
        printf '%s' "${BASH_REMATCH[2]}"
        return
    fi
    printf ''
}

_scope_extract_owner_from_origin() {
    # Parse `git config --get remote.origin.url` output for owner.
    # Handles both https and ssh forms:
    #   https://github.com/OWNER/repo.git
    #   git@github.com:OWNER/repo.git
    #   https://gitlab.com/OWNER/repo.git
    local cwd="$1"
    local url
    url=$(git -C "$cwd" config --get remote.origin.url 2>/dev/null || true)
    if [[ -z "$url" ]]; then
        return
    fi
    # ssh form: git@host:OWNER/repo(.git)
    if [[ "$url" =~ ^[a-z]+@[^:]+:([^/]+)/ ]]; then
        printf '%s' "${BASH_REMATCH[1]}"
        return
    fi
    # https form: https://host/OWNER/repo(.git)
    if [[ "$url" =~ ^https?://[^/]+/([^/]+)/ ]]; then
        printf '%s' "${BASH_REMATCH[1]}"
        return
    fi
}

_scope_owner_matches() {
    local owner="$1"
    local IFS=':'
    for a in $SCOPED_OWNERS; do
        if [[ "$owner" == "$a" ]]; then
            return 0
        fi
    done
    return 1
}

# Public entry point. Returns 0 if the guard SHOULD fire for this
# command+cwd; returns 1 if the guard should exit 0 as out-of-scope.
_scope_in_scope() {
    local command="$1"
    local cwd="${2:-$PWD}"

    # 1. Explicit -R / --repo arg wins. If a gh command targets an out-of-
    #    scope owner, the guard doesn't fire even from a scoped cwd.
    local gh_owner
    gh_owner=$(_scope_extract_owner_from_gh_r "$command")
    if [[ -n "$gh_owner" ]]; then
        if _scope_owner_matches "$gh_owner"; then
            return 0
        else
            return 1
        fi
    fi

    # 2. No -R arg: fall back to cwd's git remote origin.
    local origin_owner
    origin_owner=$(_scope_extract_owner_from_origin "$cwd")
    if [[ -z "$origin_owner" ]]; then
        # No git origin resolvable — cannot determine scope. Fall out of
        # scope. Rationale: the whole point of #699 is to STOP over-
        # firing in ambiguous cases. If the command doesn't touch a
        # discoverable repo, there's nothing for a repo-scoped guard to
        # protect. A cross-client session running `git commit` from a
        # non-scoped repo would be able to determine origin; only
        # non-git-repo cwd hits this branch, and those are already outside
        # the guards' remit.
        return 1
    fi
    if _scope_owner_matches "$origin_owner"; then
        return 0
    fi
    return 1
}
