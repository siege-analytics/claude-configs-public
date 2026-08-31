#!/usr/bin/env bash
# hooks/_test/scaffold_test_stub.test.sh
#
# Fixture-driven test for hooks/create-ticket/scaffold-test-stub.sh (#661).
# Exits 0 iff all three fixtures pass.

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

# ----------------------------------------------------------------------------
# fixture 1: no-op (body has no Automation block)
# ----------------------------------------------------------------------------
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

# ----------------------------------------------------------------------------
# fixture 2: happy path — body has an Automation block with Probe=installed;
# hook renders the stub.
# ----------------------------------------------------------------------------
test_happy_path() {
    echo "test_happy_path:"
    local sandbox
    sandbox=$(mktemp -d)
    # Sandbox is self-contained: write minimal templates inline so the test
    # doesn't depend on templates/tests/ landing on the same branch (#660).
    mkdir -p "$sandbox/templates/tests" "$sandbox/tests"
    cat > "$sandbox/templates/tests/pytest-unit.py.tmpl" <<'TMPL'
# Stub for ticket #{ticket_id}, AC{ac_id}: {feature}
def test_ac{ac_id}_{feature}():
    assert False, "AC{ac_id} for ticket #{ticket_id} ({feature}) is not implemented."
TMPL
    local body
    body=$(cat <<'BODYEOF'
## AC
- [ ] AC1: paginated search returns cursor

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
        fail "test_happy_path: expected stub file at tests/test_paginated_search.py"
        rm -rf "$sandbox"
        return
    fi
    if ! grep -q 'AC1' "$sandbox/tests/test_paginated_search.py"; then
        fail "test_happy_path: stub does not contain AC1 marker"
    elif ! grep -q 'paginated_search' "$sandbox/tests/test_paginated_search.py"; then
        fail "test_happy_path: stub does not contain feature name"
    elif [[ "$out" != *"Generated stubs"* ]]; then
        fail "test_happy_path: output body missing Generated-stubs footer"
    else
        pass "test_happy_path: stub rendered + footer appended"
    fi
    rm -rf "$sandbox"
}

# ----------------------------------------------------------------------------
# fixture 3: blocked path — Probe indicates blocked-on-infra; hook renders
# stub AND appends Blocked-by.
# ----------------------------------------------------------------------------
test_blocked_path() {
    echo "test_blocked_path:"
    local sandbox
    sandbox=$(mktemp -d)
    mkdir -p "$sandbox/templates/tests" "$sandbox/tests/e2e"
    cat > "$sandbox/templates/tests/playwright-e2e.spec.ts.tmpl" <<'TMPL'
// Stub for ticket #{ticket_id}, AC{ac_id}: {feature}
import { test } from '@playwright/test';
test('AC{ac_id}: {feature}', async () => {
    throw new Error(`AC{ac_id} for ticket #{ticket_id} ({feature}) is not implemented`);
});
TMPL
    local body
    body=$(cat <<'BODYEOF'
## AC
- [ ] AC1: reset flow completes

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
        fail "test_blocked_path: expected stub at tests/e2e/reset_flow.spec.ts (should render despite blocked probe)"
    elif [[ "$out" != *"Generated stubs"* ]]; then
        fail "test_blocked_path: output body missing Generated-stubs footer"
    elif [[ "$out" != *"Blocked-by"* ]]; then
        fail "test_blocked_path: output body missing Blocked-by line"
    elif [[ "$out" != *"issues/999"* ]]; then
        fail "test_blocked_path: Blocked-by line missing infra ticket URL"
    else
        pass "test_blocked_path: stub rendered + Blocked-by recorded"
    fi
    rm -rf "$sandbox"
}

test_noop
test_happy_path
test_blocked_path

echo ""
echo "Summary: $PASS passed, $FAIL failed"
if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
