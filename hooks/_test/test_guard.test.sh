#!/bin/bash
# Test: hooks/git/test-guard.sh
#
# Exercises test evidence enforcement at PreToolUse on git push.
# Projects with testing: in PROJECT.md demand test evidence;
# projects without are unaffected.
#
# Ref: claude-configs-public#386

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/git/test-guard.sh"

# shellcheck source=./run_scenarios.sh
source "$SCRIPT_DIR/run_scenarios.sh"

# --- Setup: create a temporary git repo with PROJECT.md ---
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Repo WITH testing: section — set up with a bare remote so
# origin/develop exists for merge-base resolution.
mkdir -p "$TMPDIR/with-testing-bare"
git init -q --bare "$TMPDIR/with-testing-bare"

mkdir -p "$TMPDIR/with-testing"
cd "$TMPDIR/with-testing"
git init -q
# Without a repo-local identity the commits below fail on any machine that has
# no global git config, the pushes fail with "src refspec develop does not
# match any", origin/develop never exists, and the hook yields on an
# unresolvable merge base instead of reaching the rule under test.
git config user.email "t@example.test"
git config user.name "test"
git checkout -q -b develop
cat > PROJECT.md <<'PROJEOF'
name: test-project
testing:
  layers:
    - name: backend
      framework: pytest
      test_dir: tests/
      pattern: "test_{stem}.py"
PROJEOF
mkdir -p src tests
echo 'def hello(): return 1' > src/app.py
echo 'def test_hello(): assert True' > tests/test_app.py
git add -A
git commit -q -m "initial [no-ticket]"
git remote add origin "$TMPDIR/with-testing-bare"
git push -q origin develop

# Every scenario below needs origin/develop to resolve a merge base. When it is
# absent the hook yields with exit 0, which reads as a pass on the expect_pass
# scenarios and hides the failure. Fail loudly here instead.
if ! git rev-parse --verify -q origin/develop >/dev/null; then
    echo "SETUP FAILED: origin/develop does not exist after push." >&2
    echo "Scenarios would yield exit 0 on an unresolvable merge base." >&2
    exit 1
fi

# Repo WITHOUT testing: section
mkdir -p "$TMPDIR/no-testing"
cd "$TMPDIR/no-testing"
git init -q
git config user.email "t@example.test"
git config user.name "test"
git checkout -q -b develop
cat > PROJECT.md <<'PROJEOF'
name: no-test-project
description: A project without testing section
PROJEOF
echo 'print("hello")' > app.py
git add -A
git commit -q -m "initial [no-ticket]"

make_payload() {
    local cmd="$1"
    local cwd="$2"
    python3 -c "
import json, sys
print(json.dumps({'tool_input': {'command': sys.argv[1]}, 'cwd': sys.argv[2]}))
" "$cmd" "$cwd"
}

# --- PASS: not a push command ---
expect_pass "(a) non-push command is ignored" "$HOOK" \
    "$(make_payload 'git status' "$TMPDIR/with-testing")"

# --- PASS: project without testing: section ---
expect_pass "(b) project without testing: section is unaffected" "$HOOK" \
    "$(make_payload 'git push origin develop' "$TMPDIR/no-testing")"

# --- BLOCK: project with testing: but no signal file ---
# The setup above pushed develop, so HEAD matches origin/develop and the
# merge-base diff is empty. The hook exits 0 on an empty touched-file set,
# which is correct: a push carrying no source change demands no evidence.
# Leave an unpushed source change so the scenario reaches the rule it names.
cd "$TMPDIR/with-testing"
echo 'def added(): return 2' >> src/app.py
git add src/app.py
git commit -q -m "touch source #386"

expect_block_because "(c) project with testing: but no test-gate.json" "$HOOK" \
    "$(make_payload 'git push origin develop' "$TMPDIR/with-testing")" \
    'no test-gate.json was found'

# --- PASS: project with testing: and valid signal file ---
cat > "$TMPDIR/with-testing/test-gate.json" <<'SIGEOF'
{
  "ticket": "#386",
  "lastUpdated": "2026-06-09T14:30:00Z",
  "evidence": [
    {"source": "src/app.py", "test": "tests/test_app.py", "result": "pass", "framework": "pytest", "timestamp": "2026-06-09T14:28:00Z"}
  ]
}
SIGEOF

expect_pass "(d) project with testing: and valid evidence" "$HOOK" \
    "$(make_payload 'git push origin develop' "$TMPDIR/with-testing")"

# --- PASS: structured [run-skip] override ---
# The bare [run-skip: reason] form this scenario used was blocked on purpose by
# #579, which requires the Reason/Evidence/Falsification chain. The scenario
# still pins down that a valid override opens the gate; only the accepted shape
# of the override changed.
rm "$TMPDIR/with-testing/test-gate.json"
cd "$TMPDIR/with-testing"
echo 'def goodbye(): return 0' >> src/app.py
git add -A
git commit -q -m "add goodbye #386 [run-skip: Reason: test infra under repair; Evidence: pytest exits 4 on collection; Falsification: a passing collection run]"

expect_pass "(e) structured [run-skip] override allows push" "$HOOK" \
    "$(make_payload 'git push origin develop' "$TMPDIR/with-testing")"

# The bare form is now blocked rather than allowed. Asserted so that a
# regression re-opening it fails here rather than passing by omission.
cd "$TMPDIR/with-testing"
echo 'def farewell(): return 3' >> src/app.py
git add -A
git commit -q -m "add farewell #386 [run-skip: test infra under repair]"

expect_block_because "(e2) bare [run-skip: reason] is blocked" "$HOOK" \
    "$(make_payload 'git push origin develop' "$TMPDIR/with-testing")" \
    "'\[run-skip\]' override now requires evidence chain"

# --- BLOCK: evidence exists but doesn't cover a touched file ---
cd "$TMPDIR/with-testing"
mkdir -p src/utils
echo 'def helper(): return 42' > src/utils/helpers.py
git add -A
git commit -q -m "add helpers #386"
cat > "$TMPDIR/with-testing/test-gate.json" <<'SIGEOF'
{
  "ticket": "#386",
  "lastUpdated": "2026-06-09T14:30:00Z",
  "evidence": [
    {"source": "src/app.py", "test": "tests/test_app.py", "result": "pass", "framework": "pytest", "timestamp": "2026-06-09T14:28:00Z"}
  ]
}
SIGEOF

expect_block "(f) evidence exists but missing for new file" "$HOOK" \
    "$(make_payload 'git push origin develop' "$TMPDIR/with-testing")"

# --- PASS: gh pr create also triggers ---
expect_block "(g) gh pr create also triggers check" "$HOOK" \
    "$(make_payload 'gh pr create --title test --body test' "$TMPDIR/with-testing")"

# --- Report ---
report
