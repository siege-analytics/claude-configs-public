#!/usr/bin/env bash
# Shared helper for tool-availability probes.
#
# Consumers: scripts/probe/<tool>.sh source this file and call:
#
#   probe_run TOOL_NAME BIN_NAME INSTALL_CMD [MODULE_NAME]
#
# Behavior per the tool-availability-probe SKILL.md:
#   1. Check if BIN_NAME resolves on PATH; if MODULE_NAME set, also try
#      python3 -c "import MODULE_NAME".
#   2. If present: emit {"status": "installed", "tool": "...", "version": "..."} and exit 0.
#   3. If absent, resolve tool_install_policy from PROJECT.md at the target
#      repo root (env TOOL_INSTALL_POLICY overrides). Values: allow|prompt|block.
#      Default: block.
#   4. If allow (or prompt with TOOL_INSTALL_YES=1): run INSTALL_CMD. On success,
#      re-probe; emit {"status": "installed-just-now", ...} and exit 0.
#   5. If block or install failed: render infra ticket body from
#      templates/infra-ticket-tool-install.md (or hard-coded fallback if
#      that template is absent), file via gh, emit {"status":
#      "blocked-on-infra", "ticket": "#N"} and exit 78.
#
# Exit codes:
#   0  = installed | installed-just-now
#   2  = probe prerequisite missing (e.g. no gh CLI, no python3 for module check)
#   78 = blocked-on-infra
#
# All output is single-line JSON on stdout; human-readable messages on stderr.

set -euo pipefail

_probe_emit_json() {
    # $1 = compact JSON payload
    printf '%s\n' "$1"
}

_probe_resolve_policy() {
    # env override wins
    if [[ -n "${TOOL_INSTALL_POLICY:-}" ]]; then
        printf '%s' "$TOOL_INSTALL_POLICY"
        return
    fi
    # PROJECT.md at repo root
    local repo_root
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
    local project_md="$repo_root/PROJECT.md"
    if [[ -f "$project_md" ]]; then
        local policy
        policy=$(grep -E '^tool_install_policy:' "$project_md" 2>/dev/null | head -1 | sed -E 's/^tool_install_policy:[[:space:]]*//' || true)
        if [[ -n "$policy" ]]; then
            printf '%s' "$policy"
            return
        fi
    fi
    printf 'block'
}

_probe_check_bin() {
    # $1 = binary name; $2 = optional python module name
    local bin="$1"
    local module="${2:-}"
    if command -v "$bin" >/dev/null 2>&1; then
        return 0
    fi
    if [[ -n "$module" ]] && command -v python3 >/dev/null 2>&1; then
        if python3 -c "import $module" >/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

_probe_get_version() {
    # $1 = binary name; try --version, then -v; fall back to unknown.
    local bin="$1"
    local v
    v=$("$bin" --version 2>&1 | head -1 || true)
    if [[ -z "$v" ]]; then
        v=$("$bin" -v 2>&1 | head -1 || true)
    fi
    if [[ -z "$v" ]]; then
        v="unknown"
    fi
    printf '%s' "$v"
}

_probe_file_infra_ticket() {
    # $1 = tool name; $2 = layer (optional); $3 = install_cmd; $4 = blocking-ticket
    local tool="$1"
    local layer="${2:-unknown}"
    local install_cmd="$3"
    local blocking="${4:-}"
    if ! command -v gh >/dev/null 2>&1; then
        >&2 echo "probe: gh CLI unavailable; cannot file infra ticket for $tool"
        _probe_emit_json "{\"status\":\"blocked-on-infra\",\"tool\":\"$tool\",\"ticket\":\"unfilable-gh-missing\"}"
        exit 2
    fi
    local repo_root
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
    local template="$repo_root/templates/infra-ticket-tool-install.md"
    local body
    if [[ -f "$template" ]]; then
        # #676 (P0-1): replaced sed-based substitution with python3 str.replace
        # to prevent corruption/abort when install_cmd contains sed metacharacters
        # (& expands to match; | terminates s-command with default delimiter).
        # Playwright's && chain and k6's apt-route | actively triggered this.
        body=$(
            TOOL_NAME="$tool" \
            INSTALL_CMD="$install_cmd" \
            BLOCKING="$blocking" \
            LAYER="$layer" \
            REPO_NAME="$(basename "$repo_root")" \
            REQUESTER="${CRAFT_AGENT_SESSION_DIR:-unknown-session}" \
            VERSION_REQ="any" \
            TEMPLATE_PATH="$template" \
            python3 -c '
import os, sys
tmpl = open(os.environ["TEMPLATE_PATH"]).read()
mapping = {
    "{tool}":               os.environ.get("TOOL_NAME", ""),
    "{version_requested}":  os.environ.get("VERSION_REQ", "any"),
    "{install_commands}":   os.environ.get("INSTALL_CMD", ""),
    "{blocking_tickets}":   os.environ.get("BLOCKING", ""),
    "{layer}":              os.environ.get("LAYER", ""),
    "{repo}":               os.environ.get("REPO_NAME", ""),
    "{requester_session}":  os.environ.get("REQUESTER", ""),
}
for k, v in mapping.items():
    tmpl = tmpl.replace(k, v)
sys.stdout.write(tmpl)
'
        )
    else
        body="Tool install request: $tool
Blocking: $blocking
Layer: $layer
Suggested install: $install_cmd
(Template templates/infra-ticket-tool-install.md not found; using fallback body.)"
    fi
    # #677: capture gh stderr and exit status explicitly. gh can be
    # present and still fail (not authenticated, no network, label
    # missing, rate limited, --body rejected). The previous form
    # redirected stderr to /dev/null and used `local url` on its own
    # line, which made the gh assignment a simple command subject to
    # `set -e`; a non-zero gh aborted the function before
    # _probe_emit_json ran, so the caller saw empty stdout ->
    # probe="unknown" -> nothing appended to BLOCKED_BY -> false-
    # coverage (SKILL.md line 15's stated failure mode).
    #
    # Now: capture stdout+stderr in one buffer, keep the exit code, and
    # emit a distinct status (escalation-failed / exit 79) so consumers
    # treat this case as Skipped-with-reason rather than confusing it
    # with exit 78 (blocked-on-infra means "we filed a real ticket").
    local gh_out gh_rc
    gh_out=$(gh issue create --title "infra: install $tool for $blocking" --label task --body "$body" 2>&1)
    gh_rc=$?
    if [[ $gh_rc -ne 0 ]]; then
        local reason
        reason=$(printf '%s' "$gh_out" | python3 -c 'import sys, json; print(json.dumps(sys.stdin.read()[:500]))')
        _probe_emit_json "{\"status\":\"escalation-failed\",\"tool\":\"$tool\",\"reason\":$reason}"
        exit 79
    fi
    local url
    url=$(printf '%s' "$gh_out" | tail -1)
    _probe_emit_json "{\"status\":\"blocked-on-infra\",\"tool\":\"$tool\",\"ticket\":\"$url\"}"
    exit 78
}

probe_run() {
    # $1 = TOOL_NAME (display); $2 = BIN_NAME; $3 = INSTALL_CMD; $4 = optional MODULE_NAME; $5 = optional LAYER; $6 = optional BLOCKING_TICKET
    local tool_name="$1"
    local bin_name="$2"
    local install_cmd="$3"
    local module_name="${4:-}"
    local layer="${5:-unknown}"
    local blocking="${6:-}"

    if _probe_check_bin "$bin_name" "$module_name"; then
        local ver
        ver=$(_probe_get_version "$bin_name")
        _probe_emit_json "{\"status\":\"installed\",\"tool\":\"$tool_name\",\"version\":\"$ver\"}"
        exit 0
    fi

    local policy
    policy=$(_probe_resolve_policy)
    case "$policy" in
        allow)
            >&2 echo "probe: attempting install for $tool_name via: $install_cmd"
            if eval "$install_cmd" >/dev/null 2>&1; then
                if _probe_check_bin "$bin_name" "$module_name"; then
                    local ver
                    ver=$(_probe_get_version "$bin_name")
                    _probe_emit_json "{\"status\":\"installed-just-now\",\"tool\":\"$tool_name\",\"version\":\"$ver\"}"
                    exit 0
                fi
            fi
            _probe_file_infra_ticket "$tool_name" "$layer" "$install_cmd" "$blocking"
            ;;
        prompt)
            if [[ "${TOOL_INSTALL_YES:-}" == "1" ]]; then
                >&2 echo "probe: TOOL_INSTALL_YES=1 set; attempting install for $tool_name"
                if eval "$install_cmd" >/dev/null 2>&1 && _probe_check_bin "$bin_name" "$module_name"; then
                    local ver
                    ver=$(_probe_get_version "$bin_name")
                    _probe_emit_json "{\"status\":\"installed-just-now\",\"tool\":\"$tool_name\",\"version\":\"$ver\"}"
                    exit 0
                fi
            fi
            _probe_file_infra_ticket "$tool_name" "$layer" "$install_cmd" "$blocking"
            ;;
        block|*)
            _probe_file_infra_ticket "$tool_name" "$layer" "$install_cmd" "$blocking"
            ;;
    esac
}
