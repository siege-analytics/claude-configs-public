#!/usr/bin/env bash
# #1168: a commit lacking review trailers gets ONE rejection that lists every
# absent trailer (and only those), from each of the three trailer hooks:
# .githooks/commit-msg, hooks/git/pre-push-self-review.sh, hooks/git/self-review.sh.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; pass=0; fail=0
ok(){ echo "  PASS: $1"; pass=$((pass+1)); }; bad(){ echo "  FAIL: $1" >&2; fail=$((fail+1)); }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
TIER_C_ALL=(Review-Tier Self-Review Self-Review-Source Hostile-Review)

# lists NAME OUT: OUT has a list item naming trailer NAME (item lines start with "- ").
lists(){ printf '%s\n' "$2" | grep -Eq "^[[:space:]]+- ${1}:"; }
expect_all(){ # label out names...
  local label="$1" out="$2"; shift 2; local name absent=""
  for name in "$@"; do lists "$name" "$out" || absent="$absent $name"; done
  [[ -z "$absent" ]] && ok "$label" || bad "$label (not listed:$absent) :: ${out:0:400}"
}
expect_none(){ # label out names...
  local label="$1" out="$2"; shift 2; local name present=""
  for name in "$@"; do lists "$name" "$out" && present="$present $name"; done
  [[ -z "$present" ]] && ok "$label" || bad "$label (wrongly listed:$present) :: ${out:0:400}"
}
one_rejection(){ # label out pattern: exactly one rejection header
  local n; n=$(printf '%s\n' "$2" | grep -c "$3" || true)
  [[ "$n" -eq 1 ]] && ok "$1" || bad "$1 (found $n rejection headers) :: ${2:0:300}"
}

R="$TMP/repo"; mkdir -p "$R/.githooks" "$R/bin" "$R/catalog" "$R/hooks/git" "$R/plans"
cp "$ROOT/.githooks/commit-msg" "$R/.githooks/"
cp "$ROOT/bin/review-risk.py" "$R/bin/"
cp "$ROOT/catalog/review-risk-policy.json" "$R/catalog/"
cp "$ROOT/hooks/git/pre-push-self-review.sh" "$R/hooks/git/"
cp -R "$ROOT/hooks/lib" "$R/hooks/lib"
git -C "$R" init -q; git -C "$R" config user.email test@example.com; git -C "$R" config user.name Test
git -C "$R" remote add origin git@github.com:siege-analytics/test-repo.git
printf 'docs\n' > "$R/README.md"; git -C "$R" add README.md
git -C "$R" commit --no-verify -q -m 'docs: base [task: authorized fixture]' -m $'Review-Tier: A\nSelf-Review: fixture base'
run_msg(){ (cd "$R" && bash .githooks/commit-msg "$1" 2>&1); }

# A Tier C change (hooks/git/ is a high-risk path).
printf '#!/bin/bash\n' > "$R/hooks/git/x.sh"; git -C "$R" add hooks/git/x.sh

echo "== commit-msg =="
printf 'fix: gate\n' > "$TMP/none.msg"
out=$(run_msg "$TMP/none.msg"); rc=$?
[[ $rc -ne 0 ]] && ok "commit-msg: trailerless Tier C commit rejected" || bad "commit-msg accepted trailerless Tier C commit"
one_rejection "commit-msg: one rejection, not a silent exit" "$out" '^BLOCKED:'
expect_all "AC1 commit-msg: lists every Tier C trailer" "$out" "${TIER_C_ALL[@]}"
expect_all "commit-msg: lists the absent task reference too" "$out" "task reference"
printf '%s\n' "$out" | grep -q 'Review-Tier: C' && ok "commit-msg: computed tier names the example value" || bad "commit-msg: no computed Review-Tier example :: $out"

cat > "$TMP/partial.msg" <<'EOF'
fix: gate (#1168)

Review-Tier: C
Self-Review: partial evidence
Self-Review-Source: https://example.com/review
EOF
out=$(run_msg "$TMP/partial.msg"); rc=$?
[[ $rc -ne 0 ]] && ok "commit-msg: partial Tier C trailers rejected" || bad "commit-msg accepted partial Tier C trailers"
expect_all "AC2 commit-msg: lists the absent trailers" "$out" Hostile-Review
expect_none "AC2 commit-msg: omits trailers already present" "$out" Review-Tier Self-Review Self-Review-Source "task reference"
sed 's@https://example.com/review@plans/nonexistent.md@' "$TMP/partial.msg" > "$TMP/missing-source.msg"
out=$(run_msg "$TMP/missing-source.msg"); rc=$?
[[ $rc -eq 1 ]] && ok "commit-msg: missing path with other absent trailers is rejected" || bad "commit-msg: missing path expected exit 1, got $rc"
expect_all "commit-msg: reports missing file and absent trailers together" "$out" Self-Review-Source Hostile-Review
one_rejection "commit-msg: missing source has one aggregate rejection" "$out" '^BLOCKED:'
printf '%s\n' "$out" | grep -q 'file not found: plans/nonexistent.md' && ok "commit-msg: aggregate names the actual absent file" || bad "commit-msg: absent file diagnostic missing"

cat > "$TMP/down.msg" <<'EOF'
fix: gate (#1168)

Review-Tier: B
Self-Review: downgraded
EOF
out=$(run_msg "$TMP/down.msg")
expect_all "commit-msg: downgrade lists tier and every Tier C trailer" "$out" Review-Tier Self-Review-Source Hostile-Review
expect_none "commit-msg: downgrade omits present Self-Review" "$out" Self-Review

cat > "$TMP/full.msg" <<'EOF'
fix: gate (#1168)

Review-Tier: C
Self-Review: full
Self-Review-Source: https://example.com/review
Hostile-Review: https://example.com/hostile
Negative-Tests: fixture
Full-Suite: suites
Canary-Rollback: revert proof
EOF
run_msg "$TMP/full.msg" >/dev/null && ok "commit-msg: complete Tier C trailers pass" || bad "commit-msg rejected complete Tier C trailers"
# An interpreter that writes a warning to stderr must not read as a classifier failure.
REAL_PY="$(command -v python3)"; mkdir -p "$TMP/noisy"
printf '#!/bin/bash\necho "warning: interpreter shim notice" >&2\nexec "%s" "$@"\n' "$REAL_PY" > "$TMP/noisy/python3"; chmod +x "$TMP/noisy/python3"
(cd "$R" && PATH="$TMP/noisy:$PATH" bash .githooks/commit-msg "$TMP/full.msg" >/dev/null 2>&1) && ok "commit-msg: stderr noise from python3 does not block a valid commit" || bad "commit-msg: stderr noise blocked a valid commit"
out=$(cd "$R" && PATH="$TMP/noisy:$PATH" bash .githooks/commit-msg "$TMP/partial.msg" 2>&1)
expect_all "commit-msg: noisy interpreter still lists the absent trailers" "$out" Hostile-Review

# Tier B: only B requirements are named.
git -C "$R" reset -q hooks/git/x.sh
mkdir -p "$R/skills/x"; printf 'behavior\n' > "$R/skills/x/SKILL.md"; git -C "$R" add skills/x/SKILL.md
printf 'feat: skill\n\nReview-Tier: B\n' > "$TMP/b.msg"
out=$(run_msg "$TMP/b.msg")
expect_all "commit-msg Tier B: lists Self-Review, source and ticket" "$out" Self-Review Self-Review-Source "task reference"
expect_none "commit-msg Tier B: does not demand Tier C trailers" "$out" Review-Tier Hostile-Review
git -C "$R" reset -q skills/x/SKILL.md

echo "== pre-push-self-review =="
ZERO=0000000000000000000000000000000000000000
push_hook(){ printf 'refs/heads/test %s refs/heads/test %s\n' "$(git -C "$R" rev-parse HEAD)" "$ZERO" | (cd "$R" && bash hooks/git/pre-push-self-review.sh 2>&1); }
git -C "$R" add hooks/git/x.sh
git -C "$R" commit --no-verify -q -F "$TMP/none.msg"
out=$(push_hook); rc=$?
[[ $rc -ne 0 ]] && ok "pre-push: trailerless Tier C commit rejected" || bad "pre-push accepted trailerless Tier C commit"
expect_all "AC1 pre-push: lists every Tier C trailer" "$out" "${TIER_C_ALL[@]}"
expect_all "pre-push: lists the absent task reference too" "$out" "task reference"
git -C "$R" commit --amend --no-verify -q -F "$TMP/partial.msg"
out=$(push_hook)
expect_all "AC2 pre-push: lists the absent trailers" "$out" Hostile-Review
expect_none "AC2 pre-push: omits trailers already present" "$out" Review-Tier Self-Review Self-Review-Source
cat > "$R/plans/full.md" <<'EOF'
## Assumptions
Goal source: fixture
Pre-mortem-artifact: plans/pre.md
Hostile-review-artifact: plans/hostile.md
## Peer review
checked
## Lead review
checked
## Quantified claims
one file
EOF
git -C "$R" add plans/full.md
git -C "$R" commit --amend --no-verify -q -F "$TMP/full.msg"
push_hook >/dev/null && ok "pre-push: complete Tier C trailers pass" || bad "pre-push rejected complete Tier C trailers :: $(push_hook)"

echo "== self-review (PreToolUse) =="
HOOK="$ROOT/hooks/git/self-review.sh"; mkdir -p "$TMP/home"
sr_hook(){ printf '{"tool_input":{"command":"git push"},"cwd":"%s"}\n' "$R" | HOME="$TMP/home" bash "$HOOK" 2>&1; }
git -C "$R" commit --amend --no-verify -q -F "$TMP/none.msg"
out=$(sr_hook); rc=$?
[[ $rc -eq 2 ]] && ok "self-review: trailerless Tier C commit rejected" || bad "self-review: expected exit 2, got $rc :: ${out:0:300}"
one_rejection "self-review: one rejection" "$out" '^BLOCKED:'
expect_all "AC1 self-review: lists every Tier C trailer" "$out" "${TIER_C_ALL[@]}"
expect_all "self-review: lists the absent task reference too" "$out" "task reference"
git -C "$R" commit --amend --no-verify -q -F "$TMP/partial.msg"
out=$(sr_hook); rc=$?
[[ $rc -eq 2 ]] && ok "self-review: partial Tier C trailers rejected" || bad "self-review: partial expected exit 2, got $rc"
expect_all "AC2 self-review: lists the absent trailers" "$out" Hostile-Review
expect_none "AC2 self-review: omits trailers already present" "$out" Review-Tier Self-Review Self-Review-Source "task reference"
git -C "$R" commit --amend --no-verify -q -F "$TMP/missing-source.msg"
out=$(sr_hook); rc=$?
[[ $rc -eq 2 ]] && ok "self-review: missing path with absent trailers is rejected" || bad "self-review: missing path expected exit 2, got $rc"
expect_all "self-review: reports missing file and absent trailers together" "$out" Self-Review-Source Hostile-Review
one_rejection "self-review: missing source has one aggregate rejection" "$out" '^BLOCKED:'
printf '%s\n' "$out" | grep -q 'file not found: plans/nonexistent.md' && ok "self-review: aggregate names the actual absent file" || bad "self-review: absent file diagnostic missing"
git -C "$R" commit --amend --no-verify -q -F "$TMP/down.msg"
out=$(sr_hook)
expect_all "self-review: downgrade lists tier and every Tier C trailer" "$out" Review-Tier Self-Review-Source Hostile-Review

echo "tier_trailer_aggregation_1168: $pass passed, $fail failed"; [[ $fail -eq 0 ]]
