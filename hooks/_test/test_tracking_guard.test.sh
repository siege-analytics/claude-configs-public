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

# --- #1162: trigger words inside quoted data are not a push ---
# R1 has an offender, so any scenario that reaches the listing blocks. Before
# the fix these titles and bodies made the hook list every ignored file.
expect_pass \
  "1162a quoted issue title mentioning git push passes" \
  "$HOOK" "$(payload 'gh issue create --title "hooks: git push is slow" --body x' "$R1")"
expect_pass \
  "1162b single-quoted body mentioning gh pr create passes" \
  "$HOOK" "$(payload "gh issue comment 1 --body 'run gh pr create after git push'" "$R1")"
expect_pass \
  "1162c heredoc body mentioning git push passes" \
  "$HOOK" "$(payload "gh issue create --title t --body-file - <<'EOF'
then git push the branch
EOF" "$R1")"

# The shell still runs these, so they still trigger.
expect_block_because \
  "1162d bash -c argument is code, still blocks" \
  "$HOOK" "$(payload 'bash -c "git push origin main"' "$R1")" \
  "silently git-ignored"
expect_block_because \
  "1162e quoted message then a real push still blocks" \
  "$HOOK" "$(payload 'echo "about to push" && git push' "$R1")" \
  "silently git-ignored"
expect_block_because \
  "1162f quoted single-word verb still blocks" \
  "$HOOK" "$(payload 'git "push"' "$R1")" \
  "silently git-ignored"
expect_block_because \
  "1162g unbalanced quote keeps the text and blocks" \
  "$HOOK" "$(payload "echo don't && git push" "$R1")" \
  "silently git-ignored"

# --- #1162: the ignored-file listing is bounded and never fails open ---
REAL_GIT=$(command -v git)
FAKE_SLOW="$WORK/fake-slow-git"
FAKE_FAIL="$WORK/fake-fail-git"
mkdir -p "$FAKE_SLOW" "$FAKE_FAIL"
cat > "$FAKE_SLOW/git" <<EOF
#!/bin/bash
for a in "\$@"; do [[ "\$a" == ls-files ]] && exec sleep 30; done
exec "$REAL_GIT" "\$@"
EOF
cat > "$FAKE_FAIL/git" <<EOF
#!/bin/bash
for a in "\$@"; do [[ "\$a" == ls-files ]] && exit 128; done
exec "$REAL_GIT" "\$@"
EOF
chmod +x "$FAKE_SLOW/git" "$FAKE_FAIL/git"
# R2 is clean (its test is tracked), so only the listing can block it.
_SLOW_START=$SECONDS
PATH="$FAKE_SLOW:$PATH" expect_block_because \
  "1162h listing past its bound blocks with the reason" \
  "$HOOK" "$(payload "git push" "$R2")" \
  "did not finish within its 6s bound"
if (( SECONDS - _SLOW_START < 10 )); then
  _HARNESS_PASS=$((_HARNESS_PASS + 1)); printf '  [PASS] 1162h bounded listing returned inside the 10s hook timeout\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1)); _HARNESS_FAILED_NAMES+=("1162h listing bound")
  printf '  [FAIL] 1162h bounded listing took %ss\n' "$((SECONDS - _SLOW_START))"
fi
PATH="$FAKE_FAIL:$PATH" expect_block_because \
  "1162i failed listing blocks instead of reading as no offenders" \
  "$HOOK" "$(payload "git push" "$R2")" \
  "failed with exit status 128"

# --- #1162: many offenders are listed in one pass and capped ---
R7=$(mkrepo many)
mkdir -p "$R7/tests"
for i in $(seq 1 60); do printf 'def test_x():\n assert 1\n' > "$R7/tests/test_m$i.py"; done
printf 'def test_x():\n assert 1\n' > "$R7/test_root_scratch.py"   # outside tests/: not listed
printf 'test_*.py\n' > "$R7/.gitignore"
git -C "$R7" add .gitignore && git -C "$R7" commit -q -m gi
OUT7=$(printf '%s' "$(payload "git push" "$R7")" | bash "$HOOK" 2>&1); RC7=$?
LISTED7=$(printf '%s\n' "$OUT7" | grep -c '^  - tests/test_m')
if [[ $RC7 -eq 2 && $LISTED7 -eq 50 && "$OUT7" == *"  ... and 10 more"* && "$OUT7" != *test_root_scratch* ]]; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1)); printf '  [PASS] 1162j 60 offenders block, 50 listed plus a count\n'
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1)); _HARNESS_FAILED_NAMES+=("1162j offender cap")
  printf '  [FAIL] 1162j rc=%s listed=%s: %s\n' "$RC7" "$LISTED7" "${OUT7:0:300}"
fi

report
