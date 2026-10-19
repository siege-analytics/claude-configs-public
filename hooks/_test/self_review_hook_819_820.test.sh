#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$ROOT/hooks/git/self-review.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

run_hook() {
  local repo="$1"
  mkdir -p "$TMP/home"
  printf '{"tool_input":{"command":"git push"},"cwd":"%s"}\n' "$repo" | HOME="$TMP/home" bash "$HOOK"
}

write_deploy_stamp() {
  local repo="$1"
  local head
  head="$(git -C "$repo" rev-parse HEAD)"
  printf '{"commit":"%s","timestamp":"fixture","repo_root":"%s"}\n' "$head" "$repo" > "$repo/deploy-stamp.json"
}

gitc() {
  local repo="$1"
  local date="$2"
  shift 2
  GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git -C "$repo" "$@"
}

init_repo() {
  local repo="$1"
  mkdir -p "$repo"
  git -C "$repo" init -q
  git -C "$repo" config user.email test@example.com
  git -C "$repo" config user.name Test
  git -C "$repo" remote add origin git@github.com:siege-analytics/test-repo.git
}

write_support_artifacts() {
  local repo="$1"
  mkdir -p "$repo/plans"
  cat > "$repo/plans/investigate.md" <<'MD'
# Investigate

### Verified Shapes
**S1** ATTESTED: fixture verifies the relevant hook branch.
MD
  cat > "$repo/plans/pre-mortem.md" <<'MD'
# Pre-mortem

### Tiger 1
**Severity:** LOW
Likelihood: low
Mitigation: focused regression test.
Trigger: hook exits non-zero unexpectedly.
Fallback: inspect stderr.
MD
  cat > "$repo/plans/hostile.md" <<'MD'
# Hostile review

PASS: fixture hostile review evidence.
MD
}

write_review_artifact() {
  local repo="$1"
  local path="$2"
  local include_inventory="$3"
  mkdir -p "$(dirname "$repo/$path")"
  {
    cat <<'MD'
# Self review

## Assumptions
Goal source: #819/#820
Working as: software engineer and tech lead
MD
    if [[ "$include_inventory" = "yes" ]]; then
      echo "Pre-author-inventory: plans/investigate.md"
    fi
    cat <<'MD'
Investigate-artifact: plans/investigate.md
Pre-mortem-artifact: plans/pre-mortem.md
Hostile-review-artifact: plans/hostile.md
Project-contribution: validates self-review hook regression behavior.

## Peer review
writing-code:5 PASS - hook regression fixture passed.

## Lead review
Approved as focused hook regression coverage.
MD
  } > "$repo/$path"
}

commit_all() {
  local repo="$1"
  local date="$2"
  local msgfile="$3"
  git -C "$repo" add .
  gitc "$repo" "$date" commit -q -F "$msgfile"
}

# #819: editing hooks/git/self-review.sh must not match its own
# TRANSFORM_CONTENT_RE literal and demand Pre-ship-dry-run for a hook edit.
repo819="$TMP/repo819"
init_repo "$repo819"
write_support_artifacts "$repo819"
write_review_artifact "$repo819" "plans/self-review.md" yes
mkdir -p "$repo819/hooks/git"
echo '# initial hook placeholder' > "$repo819/hooks/git/self-review.sh"
cat > "$TMP/msg819a" <<'MSG'
Initial

Self-Review: initial
Self-Review-Source: plans/self-review.md
Design-Note-Source: #819
Hostile-review-artifact: plans/hostile.md
Inventoried-shape: initial fixture
MSG
commit_all "$repo819" "2026-01-01T00:00:00Z" "$TMP/msg819a"
cat >> "$repo819/hooks/git/self-review.sh" <<'SH'
TRANSFORM_CONTENT_RE='(CREATE[[:space:]]+TABLE|INSERT[[:space:]]+INTO|UNION[[:space:]]+ALL|\.write\.|\.saveAsTable|\.to_sql)'
SH
cat > "$TMP/msg819b" <<'MSG'
Edit self-review hook

Self-Review: hook edit reviewed
Self-Review-Source: plans/self-review.md
Design-Note-Source: #819
Hostile-review-artifact: plans/hostile.md
Inventoried-shape: self-review hook diff contains TRANSFORM_CONTENT_RE literal only
MSG
commit_all "$repo819" "2026-01-02T00:00:00Z" "$TMP/msg819b"
write_deploy_stamp "$repo819"
if ! out="$(run_hook "$repo819" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: #819 self-review hook edit should not require Pre-ship-dry-run" >&2
  exit 1
fi
if grep -q "Pre-ship-dry-run" <<<"$out"; then
  echo "$out" >&2
  echo "FAIL: #819 emitted transformation dry-run diagnostic" >&2
  exit 1
fi

mkdir -p "$repo819/src"
echo 'df.write.format("delta").saveAsTable("target")' > "$repo819/src/job.py"
cat > "$TMP/msg819c" <<'MSG'
Real transformation still needs dry-run

Self-Review: transform edit reviewed
Self-Review-Source: plans/self-review.md
Design-Note-Source: #819
Hostile-review-artifact: plans/hostile.md
Inventoried-shape: real transformation fixture
MSG
commit_all "$repo819" "2026-01-03T00:00:00Z" "$TMP/msg819c"
if out="$(run_hook "$repo819" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: real transformation file should still require dry-run evidence" >&2
  exit 1
fi
if ! grep -q "Pre-ship-dry-run" <<<"$out"; then
  echo "$out" >&2
  echo "FAIL: expected transformation dry-run diagnostic for real transform file" >&2
  exit 1
fi

# #820: a historical self-review artifact that predates the hook commit
# introducing Pre-author-inventory enforcement is grandfathered with a warning.
repo820="$TMP/repo820"
init_repo "$repo820"
write_support_artifacts "$repo820"
write_review_artifact "$repo820" "plans/old-review.md" no
cat > "$TMP/msg820a" <<'MSG'
Historical artifact

Self-Review: historical
Self-Review-Source: plans/old-review.md
Design-Note-Source: #820
MSG
commit_all "$repo820" "2026-01-01T00:00:00Z" "$TMP/msg820a"
mkdir -p "$repo820/hooks/git"
echo '# hook introduces Pre-author-inventory: enforcement' > "$repo820/hooks/git/self-review.sh"
cat > "$TMP/msg820b" <<'MSG'
Introduce inventory enforcement

Self-Review: enforcement
Self-Review-Source: plans/old-review.md
Design-Note-Source: #820
MSG
commit_all "$repo820" "2026-01-02T00:00:00Z" "$TMP/msg820b"
gitc "$repo820" "2026-01-03T00:00:00Z" commit --allow-empty -q -m $'Follow-up using historical artifact\n\nSelf-Review: historical artifact remains authoritative\nSelf-Review-Source: plans/old-review.md\nDesign-Note-Source: #820'
if ! out="$(run_hook "$repo820" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: #820 historical artifact should be grandfathered" >&2
  exit 1
fi
if ! grep -q "grandfathering missing field" <<<"$out"; then
  echo "$out" >&2
  echo "FAIL: #820 expected grandfather warning" >&2
  exit 1
fi
cat >> "$repo820/plans/old-review.md" <<'MD'

Dirty edit after enforcement without adding inventory.
MD
if out="$(run_hook "$repo820" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: dirty historical artifact missing Pre-author-inventory should block" >&2
  exit 1
fi
if ! grep -q "missing 'Pre-author-inventory:'" <<<"$out"; then
  echo "$out" >&2
  echo "FAIL: expected missing Pre-author-inventory diagnostic for dirty historical artifact" >&2
  exit 1
fi

# Current/untracked missing Pre-author-inventory artifacts still block.
repo820strict="$TMP/repo820strict"
init_repo "$repo820strict"
write_support_artifacts "$repo820strict"
mkdir -p "$repo820strict/hooks/git"
echo '# hook introduces Pre-author-inventory: enforcement' > "$repo820strict/hooks/git/self-review.sh"
git -C "$repo820strict" add .
gitc "$repo820strict" "2026-01-02T00:00:00Z" commit -q -m 'baseline'
write_review_artifact "$repo820strict" "plans/current-review.md" no
cat > "$TMP/msg820strict" <<'MSG'
Current missing inventory

Self-Review: current missing inventory
Self-Review-Source: plans/current-review.md
Design-Note-Source: #820
MSG
git -C "$repo820strict" add .
gitc "$repo820strict" "2026-01-03T00:00:00Z" commit -q -F "$TMP/msg820strict"
if out="$(run_hook "$repo820strict" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: current missing Pre-author-inventory should still block" >&2
  exit 1
fi
if ! grep -q "missing 'Pre-author-inventory:'" <<<"$out"; then
  echo "$out" >&2
  echo "FAIL: expected missing Pre-author-inventory diagnostic" >&2
  exit 1
fi

repo820untracked="$TMP/repo820untracked"
init_repo "$repo820untracked"
write_support_artifacts "$repo820untracked"
mkdir -p "$repo820untracked/hooks/git"
echo '# hook introduces Pre-author-inventory: enforcement' > "$repo820untracked/hooks/git/self-review.sh"
git -C "$repo820untracked" add .
gitc "$repo820untracked" "2026-01-02T00:00:00Z" commit -q -m 'baseline'
write_review_artifact "$repo820untracked" "plans/untracked-review.md" no
gitc "$repo820untracked" "2026-01-03T00:00:00Z" commit --allow-empty -q -m $'Untracked current review\n\nSelf-Review: untracked current missing inventory\nSelf-Review-Source: plans/untracked-review.md\nDesign-Note-Source: #820'
if out="$(run_hook "$repo820untracked" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: untracked missing Pre-author-inventory artifact should block" >&2
  exit 1
fi
if ! grep -q "missing 'Pre-author-inventory:'" <<<"$out"; then
  echo "$out" >&2
  echo "FAIL: expected missing Pre-author-inventory diagnostic for untracked artifact" >&2
  exit 1
fi

echo "self_review_hook_819_820.test: PASS"
