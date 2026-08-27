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

# Repo WITHOUT testing: section
mkdir -p "$TMPDIR/no-testing"
cd "$TMPDIR/no-testing"
git init -q
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
expect_block "(c) project with testing: but no test-gate.json" "$HOOK" \
    "$(make_payload 'git push origin develop' "$TMPDIR/with-testing")"

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

# --- PASS: [run-skip: reason] override ---
rm "$TMPDIR/with-testing/test-gate.json"
cd "$TMPDIR/with-testing"
echo 'def goodbye(): return 0' >> src/app.py
git add -A
git commit -q -m "add goodbye [run-skip: test infra under repair] [no-ticket]"

expect_pass "(e) [run-skip: reason] override allows push" "$HOOK" \
    "$(make_payload 'git push origin develop' "$TMPDIR/with-testing")"

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
