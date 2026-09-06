#!/usr/bin/env bash
# scripts/probe/_test_probe_common.sh
#
# Bats-style test for the python3 substitution in _probe_file_infra_ticket
# (fix #676 for noble-pulsar P0-1 on PR #668).
#
# Verifies:
#   AC1: no sed-based substitution remains in _probe_file_infra_ticket.
#   AC2: playwright's `&&`-bearing install_cmd renders cleanly.
#   AC3: k6's `|`-bearing install_cmd does not abort the probe.
#   AC4: metacharacter-free input renders byte-identically to sed output.
#
# Does not require gh; stubs it. Does not require the templates; writes an
# inline template into a sandbox so the test is self-contained.

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"

PASS=0
FAIL=0
pass() { PASS=$((PASS+1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }

TMPL_LITERAL='## Tool install request: {tool}

**Blocking:** {blocking_tickets}
**Layer:** {layer}
**Repo:** {repo}
**Requested version:** {version_requested}
**Requester session:** {requester_session}

### Suggested install commands

```bash
{install_commands}
```
'

# ---------------------------------------------------------------------------
# AC1: no sed substitution inside _probe_file_infra_ticket
# ---------------------------------------------------------------------------
test_ac1_no_sed_in_body_render() {
    echo "test_ac1_no_sed_in_body_render:"
    local body_render
    body_render=$(awk '/^_probe_file_infra_ticket/,/^}/' "$HERE/_common.sh" | grep -c '^[[:space:]]*sed ' || true)
    if [[ "$body_render" -eq 0 ]]; then
        pass "AC1: no sed-based substitution inside _probe_file_infra_ticket"
    else
        fail "AC1: sed-based substitution still present ($body_render lines)"
    fi
}

# Helper: run _probe_file_infra_ticket in a sandbox with a stubbed gh.
_run_probe_ticket() {
    local sandbox="$1" tool="$2" layer="$3" install_cmd="$4" blocking="$5"
    # Sandbox layout: templates/infra-ticket-tool-install.md, bin/gh stub on PATH.
    mkdir -p "$sandbox/templates" "$sandbox/bin"
    printf '%s' "$TMPL_LITERAL" > "$sandbox/templates/infra-ticket-tool-install.md"
    # Stub gh: dispatch on subcommand. `issue create` captures --body and
    # echoes a predictable URL. `issue list` returns empty (no existing
    # ticket) so dedupe (#680) doesn't fire. `issue view` is unused here
    # but stubbed for symmetry.
    cat > "$sandbox/bin/gh" <<'GH'
#!/usr/bin/env bash
if [[ "$1" == "issue" && "$2" == "list" ]]; then
    # No existing ticket found; probe proceeds to create
    exit 0
fi
if [[ "$1" == "issue" && "$2" == "view" ]]; then
    # Called with reused ticket; test controls this path via GH_EXISTING_URL
    if [[ -n "${GH_EXISTING_URL:-}" ]]; then
        echo "$GH_EXISTING_URL"
    fi
    exit 0
fi
if [[ "$1" == "issue" && "$2" == "create" ]]; then
    shift 2
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --body) printf '%s' "$2" > "$GH_STUB_BODY_OUT"; shift 2 ;;
            --title) shift 2 ;;
            --label) shift 2 ;;
            *) shift ;;
        esac
    done
    echo "https://github.com/fake/repo/issues/999"
    exit 0
fi
exit 0
GH
    chmod +x "$sandbox/bin/gh"
    # Fake git repo root at sandbox
    (cd "$sandbox" && git init -q 2>/dev/null || true)
    # Source the probe helper in a subshell so its `exit` doesn't kill the test.
    (
        cd "$sandbox"
        export PATH="$sandbox/bin:$PATH"
        export GH_STUB_BODY_OUT="$sandbox/gh_body.txt"
        source "$HERE/_common.sh"
        _probe_file_infra_ticket "$tool" "$layer" "$install_cmd" "$blocking"
    ) > "$sandbox/probe_stdout.txt" 2>"$sandbox/probe_stderr.txt" ; local rc=$?
    echo "$rc"
}

# ---------------------------------------------------------------------------
# AC2: playwright's && renders cleanly
# ---------------------------------------------------------------------------
test_ac2_playwright_ampamp() {
    echo "test_ac2_playwright_ampamp:"
    local sandbox
    sandbox=$(mktemp -d)
    local rc
    rc=$(_run_probe_ticket "$sandbox" "playwright" "e2e" 'npm install -D @playwright/test && npx playwright install --with-deps' "656")
    local body="$sandbox/gh_body.txt"
    if [[ "$rc" != "78" ]]; then
        fail "AC2: expected exit 78, got $rc"
    elif [[ ! -f "$body" ]]; then
        fail "AC2: gh stub captured no body"
    elif ! grep -q 'npm install -D @playwright/test && npx playwright install --with-deps' "$body"; then
        fail "AC2: rendered body missing literal && install command"
    elif grep -q '{install_commands}' "$body"; then
        fail "AC2: leftover {install_commands} placeholder in body"
    else
        pass "AC2: playwright && install command rendered cleanly"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# AC3: k6's | does not abort
# ---------------------------------------------------------------------------
test_ac3_k6_pipe() {
    echo "test_ac3_k6_pipe:"
    local sandbox
    sandbox=$(mktemp -d)
    local rc
    rc=$(_run_probe_ticket "$sandbox" "k6" "performance" 'sudo apt-get update | tee /dev/null && apt-get install -y k6' "656")
    local out="$sandbox/probe_stdout.txt"
    local body="$sandbox/gh_body.txt"
    if [[ "$rc" != "78" ]]; then
        fail "AC3: expected exit 78, got $rc (probe aborted on | ?)"
    elif ! grep -q 'blocked-on-infra' "$out"; then
        fail "AC3: probe stdout missing blocked-on-infra status"
    elif ! grep -q '"ticket":"https' "$out"; then
        fail "AC3: probe stdout missing ticket URL"
    elif ! grep -q 'sudo apt-get update | tee /dev/null && apt-get install -y k6' "$body"; then
        fail "AC3: rendered body missing literal | + && install command"
    else
        pass "AC3: k6 pipe-bearing install command rendered without abort"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# AC4: metacharacter-free input renders identically to legacy sed shape
# ---------------------------------------------------------------------------
test_ac4_plain_input_equivalence() {
    echo "test_ac4_plain_input_equivalence:"
    local sandbox
    sandbox=$(mktemp -d)
    local install_cmd='python3 -m pip install --user pytest'
    local rc
    rc=$(_run_probe_ticket "$sandbox" "pytest" "backend" "$install_cmd" "656")
    local body="$sandbox/gh_body.txt"
    # Reference: apply the same substitution via sed (this is what the
    # legacy code did). Since the input has no metacharacters, this must match.
    local ref
    ref=$(sed \
        -e "s|{tool}|pytest|g" \
        -e "s|{version_requested}|any|g" \
        -e "s|{install_commands}|$install_cmd|g" \
        -e "s|{blocking_tickets}|656|g" \
        -e "s|{layer}|backend|g" \
        -e "s|{repo}|$(basename "$sandbox")|g" \
        -e "s|{requester_session}|${CRAFT_AGENT_SESSION_DIR:-unknown-session}|g" \
        "$sandbox/templates/infra-ticket-tool-install.md")
    if [[ "$rc" != "78" ]]; then
        fail "AC4: expected exit 78, got $rc"
    elif ! diff -q <(printf '%s' "$ref") "$body" >/dev/null 2>&1; then
        fail "AC4: python3 render differs from sed render on plain input"
        diff <(printf '%s' "$ref") "$body" | head -20
    else
        pass "AC4: python3 render byte-identical to legacy sed render on plain input"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# AC5 (#677): gh failure produces escalation-failed status + exit 79, not
# silent kill. Stubs gh to return exit 1; probe must emit valid JSON with
# status=escalation-failed and exit 79, not empty stdout + set-e abort.
# ---------------------------------------------------------------------------
test_ac5_gh_failure_escalation() {
    echo "test_ac5_gh_failure_escalation:"
    local sandbox
    sandbox=$(mktemp -d)
    mkdir -p "$sandbox/templates" "$sandbox/bin"
    printf '%s' "$TMPL_LITERAL" > "$sandbox/templates/infra-ticket-tool-install.md"
    # Stub gh to fail with a real-looking error on stderr
    cat > "$sandbox/bin/gh" <<'GH'
#!/usr/bin/env bash
echo "HTTP 403: label 'task' not found" >&2
exit 1
GH
    chmod +x "$sandbox/bin/gh"
    (cd "$sandbox" && git init -q 2>/dev/null || true)
    local rc probe_stdout
    # Suffix `|| true` on the subshell so its non-zero exit (79 is
    # expected on this scenario) doesn't trip the enclosing `set -e`.
    # Capture rc through the escape-hatch marker.
    rc=0
    (
        cd "$sandbox"
        export PATH="$sandbox/bin:$PATH"
        export GH_STUB_BODY_OUT="$sandbox/gh_body.txt"
        source "$HERE/_common.sh"
        _probe_file_infra_ticket "faketool" "backend" "pip install --user faketool" "677"
    ) > "$sandbox/probe_stdout.txt" 2>"$sandbox/probe_stderr.txt" || rc=$?
    probe_stdout=$(cat "$sandbox/probe_stdout.txt")

    if [[ "$rc" != "79" ]]; then
        fail "AC5: expected exit 79 on gh failure, got $rc"
    elif ! echo "$probe_stdout" | grep -q '"status":"escalation-failed"'; then
        fail "AC5: probe stdout missing status=escalation-failed"
        echo "  stdout: $probe_stdout"
    elif ! echo "$probe_stdout" | grep -q '"reason":'; then
        fail "AC5: probe stdout missing reason field (gh stderr captured)"
    elif ! echo "$probe_stdout" | python3 -c 'import json,sys; json.loads(sys.stdin.read())' 2>/dev/null; then
        fail "AC5: probe stdout is not valid JSON"
        echo "  stdout: $probe_stdout"
    else
        pass "AC5: gh failure produces escalation-failed / exit 79 (not silent kill)"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# AC6/AC7 (#679): tool_install_policy inline comment + CRLF parse cleanly.
# _probe_resolve_policy used to keep the comment in the value, so the case
# statement fell through to block. CRLF had the same effect.
# ---------------------------------------------------------------------------
test_ac6_policy_inline_comment() {
    echo "test_ac6_policy_inline_comment:"
    local sandbox policy
    sandbox=$(mktemp -d)
    (cd "$sandbox" && git init -q)
    printf 'tool_install_policy: allow  # ephemeral CI runner\n' > "$sandbox/PROJECT.md"
    policy=$(
        cd "$sandbox"
        source "$HERE/_common.sh"
        _probe_resolve_policy
    )
    if [[ "$policy" == "allow" ]]; then
        pass "AC6: inline-comment policy parses to allow (was falling through to block)"
    else
        fail "AC6: expected 'allow', got '$policy'"
    fi
    rm -rf "$sandbox"
}

test_ac7_policy_crlf() {
    echo "test_ac7_policy_crlf:"
    local sandbox policy
    sandbox=$(mktemp -d)
    (cd "$sandbox" && git init -q)
    printf 'tool_install_policy: prompt\r\n' > "$sandbox/PROJECT.md"
    policy=$(
        cd "$sandbox"
        source "$HERE/_common.sh"
        _probe_resolve_policy
    )
    if [[ "$policy" == "prompt" ]]; then
        pass "AC7: CRLF line ending does not break parsing"
    else
        fail "AC7: expected 'prompt', got '$(printf '%q' "$policy")'"
    fi
    rm -rf "$sandbox"
}

test_ac8_policy_invalid_value_warns() {
    echo "test_ac8_policy_invalid_value_warns:"
    local sandbox policy stderr_out
    sandbox=$(mktemp -d)
    (cd "$sandbox" && git init -q)
    printf 'tool_install_policy: whatever-typo\n' > "$sandbox/PROJECT.md"
    policy=$(
        cd "$sandbox"
        source "$HERE/_common.sh"
        _probe_resolve_policy 2>"$sandbox/stderr.txt"
    )
    stderr_out=$(cat "$sandbox/stderr.txt")
    if [[ "$policy" == "block" ]] && echo "$stderr_out" | grep -q "not in {allow, prompt, block}"; then
        pass "AC8: invalid policy value treated as block with warning (not silent downgrade)"
    else
        fail "AC8: policy='$policy' stderr='$stderr_out'"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# AC9/AC10 (#680): dedupe existing infra ticket instead of filing a duplicate.
# ---------------------------------------------------------------------------
test_ac9_dedupe_reuses_existing() {
    echo "test_ac9_dedupe_reuses_existing:"
    local sandbox rc probe_stdout
    sandbox=$(mktemp -d)
    mkdir -p "$sandbox/templates" "$sandbox/bin"
    printf '%s' "$TMPL_LITERAL" > "$sandbox/templates/infra-ticket-tool-install.md"
    # Stub gh: issue list returns an existing ticket #42; view returns URL;
    # create should NEVER be called (that's the assertion).
    cat > "$sandbox/bin/gh" <<'GH'
#!/usr/bin/env bash
if [[ "$1" == "issue" && "$2" == "list" ]]; then
    # Match the title (case-sensitive equality per the jq filter in the hook)
    echo '42'
    exit 0
fi
if [[ "$1" == "issue" && "$2" == "view" ]]; then
    echo 'https://github.com/fake/repo/issues/42'
    exit 0
fi
if [[ "$1" == "issue" && "$2" == "create" ]]; then
    # Assertion: dedupe should have prevented create
    echo "AC9 FAIL: gh issue create was called despite existing ticket" >&2
    exit 99
fi
exit 0
GH
    chmod +x "$sandbox/bin/gh"
    (cd "$sandbox" && git init -q 2>/dev/null || true)
    rc=0
    (
        cd "$sandbox"
        export PATH="$sandbox/bin:$PATH"
        export GH_STUB_BODY_OUT="$sandbox/gh_body.txt"
        source "$HERE/_common.sh"
        _probe_file_infra_ticket "pytest" "backend" "pip install --user pytest" "656"
    ) > "$sandbox/probe_stdout.txt" 2>"$sandbox/probe_stderr.txt" || rc=$?
    probe_stdout=$(cat "$sandbox/probe_stdout.txt")

    if [[ "$rc" != "78" ]]; then
        fail "AC9: expected exit 78 (reused), got $rc"
    elif ! echo "$probe_stdout" | grep -q '"reused":true'; then
        fail "AC9: probe stdout missing reused=true"
        echo "  stdout: $probe_stdout"
    elif ! echo "$probe_stdout" | grep -q '"ticket":"https://github.com/fake/repo/issues/42"'; then
        fail "AC9: probe stdout missing the existing ticket URL"
        echo "  stdout: $probe_stdout"
    else
        pass "AC9: dedupe reuses existing infra ticket (no duplicate filed)"
    fi
    rm -rf "$sandbox"
}

test_ac1_no_sed_in_body_render
test_ac2_playwright_ampamp
test_ac3_k6_pipe
test_ac4_plain_input_equivalence
test_ac5_gh_failure_escalation
test_ac6_policy_inline_comment
test_ac7_policy_crlf
test_ac8_policy_invalid_value_warns
test_ac9_dedupe_reuses_existing

echo ""
echo "Summary: $PASS passed, $FAIL failed"
if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
