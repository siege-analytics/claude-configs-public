#!/usr/bin/env bash
# Scenario tests for hooks/git/fix-shape-guard.sh merge-base selection (#937).
# Reproduces the stale-local-develop topology: a skills-upstream/develop remote
# ref AHEAD of a stale local develop. The guard must compute the scope-count
# against the freshest reachable develop, not the stale local pointer.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
HOOK="$ROOT/hooks/git/fix-shape-guard.sh"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

payload() {  # payload <command> <cwd>
  python3 - "$1" "$2" <<'PY'
import json, sys
print(json.dumps({"tool_input": {"command": sys.argv[1]}, "cwd": sys.argv[2]}))
PY
}

gc() {  # gc <repo> <scope> <msg> [extra-trailer]
  local d="$1" scope="$2" msg="$3" trailer="${4:-}"
  echo "$RANDOM $msg" > "$d/${scope}_$RANDOM.txt"
  git -C "$d" add -A
  if [[ -n "$trailer" ]]; then
    git -C "$d" commit -q -m "fix($scope): $msg

$trailer"
  else
    git -C "$d" commit -q -m "fix($scope): $msg"
  fi
}

newrepo() {
  local d="$WORK/$1"; mkdir -p "$d"
  git -C "$d" init -q -b main
  git -C "$d" config user.email t@t
  git -C "$d" config user.name t
  echo seed > "$d/README.md"; git -C "$d" add -A; git -C "$d" commit -q -m seed
  echo "$d"
}

# ---- AC1: stale local develop + 1-commit feature branch -> NOT flagged ----
# skills-upstream/develop is 3 same-scope commits ahead of a stale local develop.
# Old behaviour (merge-base vs stale local develop) would see 3x fix(core) and
# block; the fix counts against skills-upstream/develop -> range is 1 commit.
R1=$(newrepo ac1)
git -C "$R1" branch develop            # stale local develop pinned at seed
gc "$R1" core "a"; gc "$R1" core "b"; gc "$R1" core "c"   # fresh develop line
git -C "$R1" update-ref refs/remotes/skills-upstream/develop HEAD
git -C "$R1" checkout -q -b feat/one
gc "$R1" geo "x"                        # 1 real commit on the feature branch
expect_pass \
  "AC1 1-commit branch vs stale local develop is not flagged (counts against fresh develop)" \
  "$HOOK" "$(payload "git push" "$R1")"

# ---- AC2: genuine 3 same-scope commits ahead of fresh develop -> flagged ----
R2=$(newrepo ac2)
git -C "$R2" branch develop
gc "$R2" core "a"; gc "$R2" core "b"
git -C "$R2" update-ref refs/remotes/skills-upstream/develop HEAD
git -C "$R2" checkout -q -b feat/three
gc "$R2" geo "p"; gc "$R2" geo "q"; gc "$R2" geo "r"      # 3 same-scope, no Class-Audit
expect_block \
  "AC2 genuine 3 same-scope commits ahead of fresh develop blocks" \
  "$HOOK" "$(payload "git push" "$R2")"

# ---- AC2b: same 3-commit cluster WITH Class-Audit trailer -> passes ----
R3=$(newrepo ac2b)
git -C "$R3" branch develop
git -C "$R3" update-ref refs/remotes/skills-upstream/develop HEAD
git -C "$R3" checkout -q -b feat/three-audited
gc "$R3" geo "p"; gc "$R3" geo "q"
gc "$R3" geo "r" "Class-Audit: geo -- independent fixes, same scope is coincidental"
expect_pass \
  "AC2b 3 same-scope commits with Class-Audit trailer passes" \
  "$HOOK" "$(payload "git push" "$R3")"

# ---- AC3: local-only repo (no skills-upstream ref) preserves behaviour ----
R4=$(newrepo ac3)
git -C "$R4" branch develop             # develop at seed (current)
git -C "$R4" checkout -q -b feat/local
gc "$R4" geo "p"; gc "$R4" geo "q"; gc "$R4" geo "r"      # 3 same-scope, no remote
expect_block \
  "AC3 local-only repo still blocks a genuine 3 same-scope cluster" \
  "$HOOK" "$(payload "git push" "$R4")"

# The suggested trailers are user-facing commit-message input. Exercise both
# real diagnostics through the same scanner used for publication.
check_suggestions() {
  local repo="$1" label="$2" out status line count=0 scan_status
  out=$(printf '%s' "$(payload "git push" "$repo")" | bash "$HOOK" 2>&1)
  status=$?
  while IFS= read -r line; do
    [[ "$line" == "  Class-Audit: "* ]] || continue
    count=$((count + 1))
    printf 'fix: examine repeated changes\n\n%s\n' "${line#  }" > "$WORK/message.txt"
    bash "$ROOT/skills/detect-ai-fingerprints/scan.sh" --commit-message-file "$WORK/message.txt" > "$WORK/scan.txt" 2>&1
    scan_status=$?
    if [[ "$scan_status" -eq 0 ]]; then
      _HARNESS_PASS=$((_HARNESS_PASS + 1))
      printf '  [PASS] %s suggestion %d passes message scanner\n' "$label" "$count"
    else
      _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
      _HARNESS_FAILED_NAMES+=("$label suggestion $count")
      printf '  [FAIL] %s suggestion %d rejected\n' "$label" "$count"
      cat "$WORK/scan.txt"
    fi
  done <<< "$out"
  if [[ "$status" -ne 2 || "$count" -ne 2 ]]; then
    _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
    _HARNESS_FAILED_NAMES+=("$label emitted two suggestions")
    printf '  [FAIL] %s expected block with two suggestions, got %d/%d\n' "$label" "$status" "$count"
  fi
}
check_suggestions "$R2" scope
R5=$(newrepo repeated-file)
git -C "$R5" branch develop
git -C "$R5" checkout -q -b feat/file
for scope in first second third; do
  printf '%s\n' "$scope" >> "$R5/shared.txt"
  git -C "$R5" add shared.txt
  git -C "$R5" commit -q -m "fix($scope): update shared file"
done
check_suggestions "$R5" file

report
