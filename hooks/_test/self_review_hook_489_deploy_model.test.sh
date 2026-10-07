#!/usr/bin/env bash
# #226: the #489 deploy-stamp gate must NOT block infra pushes in
# merge-then-deploy repos (those declare .claude/deploy-model=merge-then-deploy;
# deploy happens post-merge, so a pre-push deploy-stamp cannot exist), but MUST
# still block infra pushes in solo-deploy repos (no marker) with no stamp.
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

gitc() {
  local repo="$1" date="$2"; shift 2
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
  local repo="$1" path="$2"
  mkdir -p "$(dirname "$repo/$path")"
  cat > "$repo/$path" <<'MD'
# Self review

## Assumptions
Goal source: #226
Working as: software engineer and tech lead
Pre-author-inventory: plans/investigate.md
Investigate-artifact: plans/investigate.md
Pre-mortem-artifact: plans/pre-mortem.md
Hostile-review-artifact: plans/hostile.md
Project-contribution: validates #489 deploy-model carve-out.

## Peer review
writing-code:5 PASS - hook regression fixture passed.

## Lead review
Approved as focused hook regression coverage.
MD
}

# Build a repo whose HEAD commit is an infra change (skills/*.md), with all
# self-review artifacts/trailers present, and NO deploy-stamp.json -- so the
# only thing standing between it and a clean push is the #489 deploy-stamp gate.
build_infra_repo() {
  local repo="$1" with_marker="${2:-no}"
  init_repo "$repo"
  write_support_artifacts "$repo"
  write_review_artifact "$repo" "plans/self-review.md"
  mkdir -p "$repo/skills/demo"
  echo '# Demo skill (baseline)' > "$repo/skills/demo/SKILL.md"
  git -C "$repo" add .
  gitc "$repo" "2026-01-01T00:00:00Z" commit -q -m 'baseline'
  echo '# Demo skill (edited -- infra change)' > "$repo/skills/demo/SKILL.md"
  # Marker (if any) lands in the SAME trailered commit as the infra change, so
  # the latest-commit trailer check still passes and the marker is on disk.
  if [ "$with_marker" = "yes" ]; then
    mkdir -p "$repo/.claude"
    printf 'merge-then-deploy\n' > "$repo/.claude/deploy-model"
  fi
  cat > "$TMP/msg" <<'MSG'
Edit a skill (infra change)

Self-Review: infra edit reviewed
Self-Review-Source: plans/self-review.md
Design-Note-Source: #226
Hostile-review-artifact: plans/hostile.md
Inventoried-shape: skills/demo/SKILL.md doc edit only
MSG
  git -C "$repo" add .
  gitc "$repo" "2026-01-02T00:00:00Z" commit -q -F "$TMP/msg"
}

# --- Scenario 1: merge-then-deploy repo (marker present), no stamp -> PASS ---
repo_mtd="$TMP/repo_mtd"
build_infra_repo "$repo_mtd" yes
if ! out="$(run_hook "$repo_mtd" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: #226 merge-then-deploy repo with no deploy-stamp should NOT be blocked by #489" >&2
  exit 1
fi
if grep -q "no deploy-stamp.json" <<<"$out"; then
  echo "$out" >&2
  echo "FAIL: #226 merge-then-deploy repo emitted the #489 deploy-stamp block" >&2
  exit 1
fi

# --- Scenario 2: solo-deploy repo (no marker), no stamp -> BLOCK (TP preserved) ---
repo_solo="$TMP/repo_solo"
build_infra_repo "$repo_solo"
if out="$(run_hook "$repo_solo" 2>&1)"; then
  echo "$out" >&2
  echo "FAIL: #226 solo-deploy repo with no deploy-stamp should STILL be blocked by #489 (true positive)" >&2
  exit 1
fi
if ! grep -q "no deploy-stamp.json" <<<"$out"; then
  echo "$out" >&2
  echo "FAIL: #226 expected the #489 deploy-stamp BLOCKED diagnostic for a solo-deploy repo" >&2
  exit 1
fi

echo "self_review_hook_489_deploy_model.test: PASS"
