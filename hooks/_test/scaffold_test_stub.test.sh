#!/usr/bin/env bash
# hooks/_test/scaffold_test_stub.test.sh
#
# Fixture-driven test for hooks/create-ticket/scaffold-test-stub.sh (#661).
# Exits 0 iff every fixture passes.
#
# Round-1 hostile review (from PR #672) added seven fixtures beyond the
# initial three, corresponding to the six findings + integration coverage.

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
HOOK="$REPO_ROOT/hooks/create-ticket/scaffold-test-stub.sh"

if [[ ! -x "$HOOK" ]]; then
    echo "FAIL: hook not executable: $HOOK"
    exit 1
fi

PASS=0
FAIL=0

pass() { PASS=$((PASS+1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }

# Common: write a minimal pytest-unit template into a sandbox templates/tests/.
_write_pytest_tmpl() {
    local dir="$1"
    mkdir -p "$dir/templates/tests"
    cat > "$dir/templates/tests/pytest-unit.py.tmpl" <<'TMPL'
# Stub for ticket #{ticket_id}, AC{ac_id}: {feature}
def test_ac{ac_id}_{feature}():
    assert False, "AC{ac_id} for ticket #{ticket_id} ({feature}) is not implemented."
TMPL
}

_write_playwright_tmpl() {
    local dir="$1"
    mkdir -p "$dir/templates/tests"
    cat > "$dir/templates/tests/playwright-e2e.spec.ts.tmpl" <<'TMPL'
// Stub for ticket #{ticket_id}, AC{ac_id}: {feature}
import { test } from '@playwright/test';
test('AC{ac_id}: {feature}', async () => {
    throw new Error(`AC{ac_id} for ticket #{ticket_id} ({feature}) is not implemented`);
});
TMPL
}

# ---------------------------------------------------------------------------
# fixture 1 -- no-op (body has no Automation block)
# ---------------------------------------------------------------------------
test_noop() {
    echo "test_noop:"
    local body='## Context\nSome ticket body\n\n## AC\n- [ ] AC1'
    local out
    out=$(printf '%s' "$body" | "$HOOK" --stdin --repo-root "$REPO_ROOT" 2>/dev/null)
    if [[ "$out" == *"Generated stubs"* ]]; then
        fail "test_noop: expected body unchanged, got Generated-stubs footer"
    else
        pass "test_noop: body passed through unchanged"
    fi
}

# ---------------------------------------------------------------------------
# fixture 2 -- happy path with explicit Probe: installed
# ---------------------------------------------------------------------------
test_happy_path() {
    echo "test_happy_path:"
    local sandbox
    sandbox=$(mktemp -d)
    _write_pytest_tmpl "$sandbox"
    local body
    body=$(cat <<'BODYEOF'
Automation:
Tool: pytest
Stub: tests/test_paginated_search.py
Probe: installed
Ticket-id: 656
AC-id: 1
Feature: paginated_search
BODYEOF
)
    local out
    out=$(printf '%s' "$body" | "$HOOK" --stdin --repo-root "$sandbox" 2>/dev/null)
    if [[ ! -f "$sandbox/tests/test_paginated_search.py" ]]; then
        fail "test_happy_path: expected stub file"
    elif ! grep -q 'AC1' "$sandbox/tests/test_paginated_search.py"; then
        fail "test_happy_path: stub missing AC marker"
    elif [[ "$out" != *"Generated stubs"* ]]; then
        fail "test_happy_path: output body missing footer"
    else
        pass "test_happy_path: stub rendered + footer"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# fixture 3 -- Probe: blocked-on-infra:URL (legacy hand-shaped)
# ---------------------------------------------------------------------------
test_blocked_path_legacy_form() {
    echo "test_blocked_path_legacy_form:"
    local sandbox
    sandbox=$(mktemp -d)
    _write_playwright_tmpl "$sandbox"
    local body
    body=$(cat <<'BODYEOF'
Automation:
Tool: playwright
Stub: tests/e2e/reset_flow.spec.ts
Probe: blocked-on-infra:https://github.com/org/repo/issues/999
Ticket-id: 700
AC-id: 1
Feature: reset_flow
BODYEOF
)
    local out
    out=$(printf '%s' "$body" | "$HOOK" --stdin --repo-root "$sandbox" 2>/dev/null)
    if [[ ! -f "$sandbox/tests/e2e/reset_flow.spec.ts" ]]; then
        fail "test_blocked_path_legacy_form: expected stub at tests/e2e/reset_flow.spec.ts"
    elif [[ "$out" != *"issues/999"* ]]; then
        fail "test_blocked_path_legacy_form: Blocked-by missing infra URL"
    else
        pass "test_blocked_path_legacy_form: stub + Blocked-by"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# fixture 4 -- Round-1 finding 1-1: no Probe: line, hook must auto-invoke.
#   Uses a fake probe script that emits {"status":"installed",...}.
# ---------------------------------------------------------------------------
test_auto_probe_installed() {
    echo "test_auto_probe_installed:"
    local sandbox
    sandbox=$(mktemp -d)
    _write_pytest_tmpl "$sandbox"
    mkdir -p "$sandbox/scripts/probe"
    cat > "$sandbox/scripts/probe/pytest.sh" <<'PROBE'
#!/usr/bin/env bash
echo '{"status":"installed","tool":"pytest","version":"8.0.0"}'
exit 0
PROBE
    chmod +x "$sandbox/scripts/probe/pytest.sh"
    local body
    body=$(cat <<'BODYEOF'
Automation:
Tool: pytest
Stub: tests/test_auto.py
Ticket-id: 720
AC-id: 1
Feature: auto_probe
BODYEOF
)
    local out
    out=$(printf '%s' "$body" | "$HOOK" --stdin --repo-root "$sandbox" 2>/dev/null)
    if [[ ! -f "$sandbox/tests/test_auto.py" ]]; then
        fail "test_auto_probe_installed: expected stub (auto-probe branch broken; finding 1-1)"
    elif [[ "$out" != *"Generated stubs"* ]]; then
        fail "test_auto_probe_installed: footer missing"
    else
        pass "test_auto_probe_installed: auto-probe path rendered stub"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# fixture 5 -- Round-1 finding 1-2: real probe JSON blocked-on-infra with
#   .ticket field. Hook must extract .ticket, not just .status.
# ---------------------------------------------------------------------------
test_auto_probe_blocked_real_json() {
    echo "test_auto_probe_blocked_real_json:"
    local sandbox
    sandbox=$(mktemp -d)
    _write_playwright_tmpl "$sandbox"
    mkdir -p "$sandbox/scripts/probe"
    cat > "$sandbox/scripts/probe/playwright.sh" <<'PROBE'
#!/usr/bin/env bash
echo '{"status":"blocked-on-infra","tool":"playwright","ticket":"https://github.com/org/repo/issues/1234"}'
exit 78
PROBE
    chmod +x "$sandbox/scripts/probe/playwright.sh"
    local body
    body=$(cat <<'BODYEOF'
Automation:
Tool: playwright
Stub: tests/e2e/onboarding.spec.ts
Ticket-id: 730
AC-id: 2
Feature: onboarding
BODYEOF
)
    local out
    out=$(printf '%s' "$body" | "$HOOK" --stdin --repo-root "$sandbox" 2>/dev/null)
    if [[ ! -f "$sandbox/tests/e2e/onboarding.spec.ts" ]]; then
        fail "test_auto_probe_blocked_real_json: stub should render even when blocked"
    elif [[ "$out" != *"issues/1234"* ]]; then
        fail "test_auto_probe_blocked_real_json: Blocked-by missing .ticket URL (finding 1-2)"
    else
        pass "test_auto_probe_blocked_real_json: real-JSON blocked path emits Blocked-by"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# fixture 6 -- Round-1 finding 1-3: Stub path itself contains placeholders.
# ---------------------------------------------------------------------------
test_stub_path_placeholders() {
    echo "test_stub_path_placeholders:"
    local sandbox
    sandbox=$(mktemp -d)
    _write_pytest_tmpl "$sandbox"
    local body
    body=$(cat <<'BODYEOF'
Automation:
Tool: pytest
Stub: tests/test_ac{ac_id}_{feature}.py
Probe: installed
Ticket-id: 750
AC-id: 3
Feature: cursor_paging
BODYEOF
)
    local out
    out=$(printf '%s' "$body" | "$HOOK" --stdin --repo-root "$sandbox" 2>/dev/null)
    if [[ -f "$sandbox/tests/test_ac{ac_id}_{feature}.py" ]]; then
        fail "test_stub_path_placeholders: literal-brace filename created (finding 1-3 regression)"
    elif [[ ! -f "$sandbox/tests/test_ac3_cursor_paging.py" ]]; then
        fail "test_stub_path_placeholders: expected substituted filename"
    else
        pass "test_stub_path_placeholders: Stub path placeholders substituted"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# fixture 7 -- Round-1 finding 1-4: Automation inside a fenced code block
#   must be ignored.
# ---------------------------------------------------------------------------
test_fenced_ignored() {
    echo "test_fenced_ignored:"
    local sandbox
    sandbox=$(mktemp -d)
    _write_pytest_tmpl "$sandbox"
    local body
    body=$(cat <<'BODYEOF'
Here is an example Automation block used only for documentation:

```
Automation:
Tool: pytest
Stub: tests/test_should_not_render.py
Probe: installed
Ticket-id: 999
AC-id: 9
Feature: example_only
```

The real ticket has no Automation block above the fence.
BODYEOF
)
    local out
    out=$(printf '%s' "$body" | "$HOOK" --stdin --repo-root "$sandbox" 2>/dev/null)
    if [[ -f "$sandbox/tests/test_should_not_render.py" ]]; then
        fail "test_fenced_ignored: fenced example rendered (finding 1-4 regression)"
    elif [[ "$out" == *"Generated stubs"* ]]; then
        fail "test_fenced_ignored: footer appeared for fenced example"
    else
        pass "test_fenced_ignored: fenced Automation ignored"
    fi
    rm -rf "$sandbox"
}

# ---------------------------------------------------------------------------
# fixture 8 -- Round-1 finding 2-1: Stub path with ../ must be rejected.
# ---------------------------------------------------------------------------
test_path_traversal_rejected() {
    echo "test_path_traversal_rejected:"
    local sandbox
    sandbox=$(mktemp -d)
    _write_pytest_tmpl "$sandbox"
    # Create a sibling temp dir OUTSIDE the sandbox to prove containment.
    local sibling
    sibling=$(mktemp -d)
    local body
    body=$(cat <<BODYEOF
Automation:
Tool: pytest
Stub: ../$(basename "$sibling")/escaped.py
Probe: installed
Ticket-id: 760
AC-id: 1
Feature: traversal
BODYEOF
)
    local out
    out=$(printf '%s' "$body" | "$HOOK" --stdin --repo-root "$sandbox" 2>/dev/null)
    if [[ -f "$sibling/escaped.py" ]]; then
        fail "test_path_traversal_rejected: wrote outside repo root (finding 2-1 regression)"
    else
        pass "test_path_traversal_rejected: escape attempt refused"
    fi
    rm -rf "$sandbox" "$sibling"
}

# ---------------------------------------------------------------------------
# fixture 9 -- Round-1 finding 2-2: values with sed metacharacters must
#   either be rejected OR pass through cleanly (no sed error, no corruption).
# ---------------------------------------------------------------------------
test_sed_metachars_rejected() {
    echo "test_sed_metachars_rejected:"
    local sandbox
    sandbox=$(mktemp -d)
    _write_pytest_tmpl "$sandbox"
    local body
    body=$(cat <<'BODYEOF'
Automation:
Tool: pytest
Stub: tests/test_meta.py
Probe: installed
Ticket-id: 770
AC-id: 1
Feature: a|b
BODYEOF
)
    local out err rc
    { out=$(printf '%s' "$body" | "$HOOK" --stdin --repo-root "$sandbox" 2>/tmp/scaffold_err_$$); rc=$?; } || true
    err=$(cat /tmp/scaffold_err_$$)
    rm -f /tmp/scaffold_err_$$
    # Either: value rejected + block skipped (no file rendered).
    # Or: value accepted safely (file rendered with literal 'a|b').
    if [[ -f "$sandbox/tests/test_meta.py" ]]; then
        if grep -q 'a|b' "$sandbox/tests/test_meta.py"; then
            pass "test_sed_metachars_rejected: value passed through literally (safe)"
        else
            fail "test_sed_metachars_rejected: value corrupted in output"
        fi
    else
        # Rejected. Look for a stderr warning naming the value.
        if [[ "$err" == *"unsafe"* || "$err" == *"skipping"* ]]; then
            pass "test_sed_metachars_rejected: unsafe value rejected (block skipped)"
        else
            fail "test_sed_metachars_rejected: block silently dropped without diagnostic"
        fi
    fi
    rm -rf "$sandbox"
}

test_noop
test_happy_path
test_blocked_path_legacy_form
test_auto_probe_installed
test_auto_probe_blocked_real_json
test_stub_path_placeholders
test_fenced_ignored
test_path_traversal_rejected
test_sed_metachars_rejected

echo ""
echo "Summary: $PASS passed, $FAIL failed"
if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
