#!/usr/bin/env bash
# Scenario tests for hooks/git/test-tracking-guard.sh
# Each scenario builds a hermetic temp git repo (core.excludesFile=/dev/null
# so only the local .gitignore matters) and feeds the hook a PreToolUse
# payload carrying tool_input.command + cwd.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
HOOK="$ROOT/hooks/git/test-tracking-guard.sh"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# payload <command> <cwd>
payload() {
  python3 - "$1" "$2" <<'PY'
import json, sys
print(json.dumps({"tool_input": {"command": sys.argv[1]}, "cwd": sys.argv[2]}))
PY
}

# mkrepo <name> -> prints repo path; hermetic (local .gitignore only)
mkrepo() {
  local d="$WORK/$1"
  mkdir -p "$d"
  git -C "$d" init -q
  git -C "$d" config user.email t@t
  git -C "$d" config user.name t
  git -C "$d" config core.excludesFile /dev/null
  printf 'seed\n' > "$d/README.md"
  git -C "$d" add README.md
  git -C "$d" commit -q -m seed
  echo "$d"
}

# --- AC1: ignored + untracked test file under tests/ -> BLOCK ---
R1=$(mkrepo ac1)
mkdir -p "$R1/tests"
printf 'def test_a():\n assert 1\n' > "$R1/tests/test_a.py"
printf 'test_*.py\n' > "$R1/.gitignore"
git -C "$R1" add .gitignore && git -C "$R1" commit -q -m gi
expect_block_because \
  "AC1 ignored+untracked tests/test_a.py blocks" \
  "$HOOK" "$(payload "git push" "$R1")" \
  "silently git-ignored"

# --- AC2: tracked test file matching the pattern -> PASS (silent) ---
R2=$(mkrepo ac2)
mkdir -p "$R2/tests"
printf 'def test_a():\n assert 1\n' > "$R2/tests/test_a.py"
printf 'test_*.py\n' > "$R2/.gitignore"
git -C "$R2" add -f tests/test_a.py .gitignore && git -C "$R2" commit -q -m addtest
expect_pass \
  "AC2 tracked tests/test_a.py passes" \
  "$HOOK" "$(payload "git push" "$R2")"

# AC2b: assert the pass is genuinely silent (no stderr output)
OUT2=$(printf '%s' "$(payload "git push" "$R2")" | bash "$HOOK" 2>&1)
if [[ -z "$OUT2" ]]; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1)); printf '  [PASS] AC2b tracked-repo pass is silent (no output)\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1)); _HARNESS_FAILED_NAMES+=("AC2b silent pass")
  printf '  [FAIL] AC2b expected empty output, got: %s\n' "${OUT2:0:200}"
fi

# --- AC3: deliberately-ignored scratch file OUTSIDE tests/ -> PASS ---
R3=$(mkrepo ac3)
printf 'def test_scratch():\n assert 1\n' > "$R3/test_scratch.py"   # repo root, no tests/ component
printf 'test_*.py\n' > "$R3/.gitignore"
git -C "$R3" add .gitignore && git -C "$R3" commit -q -m gi
expect_pass \
  "AC3 ignored scratch test_scratch.py outside tests/ passes" \
  "$HOOK" "$(payload "git push" "$R3")"

# --- AC4a: offender present + structured override in latest commit -> PASS ---
R4=$(mkrepo ac4a)
mkdir -p "$R4/tests"
printf 'def test_a():\n assert 1\n' > "$R4/tests/test_a.py"
printf 'test_*.py\n' > "$R4/.gitignore"
git -C "$R4" add .gitignore
git -C "$R4" commit -q -m "wire gitignore

[test-track-skip: Reason: fixture is intentionally local-only; Evidence: generated at runtime by conftest; Falsification: it appears in the committed tree]"
expect_pass \
  "AC4a structured override passes" \
  "$HOOK" "$(payload "git push" "$R4")"

# --- AC4b: offender present + BARE override -> BLOCK (evidence chain required) ---
R5=$(mkrepo ac4b)
mkdir -p "$R5/tests"
printf 'def test_a():\n assert 1\n' > "$R5/tests/test_a.py"
printf 'test_*.py\n' > "$R5/.gitignore"
git -C "$R5" add .gitignore
git -C "$R5" commit -q -m "wire gitignore

[test-track-skip: trust me]"
expect_block_because \
  "AC4b bare override blocks" \
  "$HOOK" "$(payload "git push" "$R5")" \
  "evidence chain"

# --- AC5: non-push command (git status) -> PASS even with offender present ---
expect_pass \
  "AC5 non-trigger command (git status) passes" \
  "$HOOK" "$(payload "git status" "$R1")"

# --- AC6: nested tests/ dir (pkg/tests/) offender -> BLOCK ---
R6=$(mkrepo ac6)
mkdir -p "$R6/pkg/tests"
printf 'def test_n():\n assert 1\n' > "$R6/pkg/tests/test_n.py"
printf 'test_*.py\n' > "$R6/.gitignore"
git -C "$R6" add .gitignore && git -C "$R6" commit -q -m gi
expect_block_because \
  "AC6 nested pkg/tests/ offender blocks" \
  "$HOOK" "$(payload "git push" "$R6")" \
  "silently git-ignored"

report
