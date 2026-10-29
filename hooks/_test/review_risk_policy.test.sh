#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; pass=0; fail=0
ok(){ echo "  PASS: $1"; pass=$((pass+1)); }; bad(){ echo "  FAIL: $1" >&2; fail=$((fail+1)); }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
R="$TMP/repo"; mkdir -p "$R/.githooks" "$R/bin" "$R/catalog" "$R/hooks/git"
cp "$ROOT/.githooks/commit-msg" "$R/.githooks/"
cp "$ROOT/bin/review-risk.py" "$R/bin/"
cp "$ROOT/catalog/review-risk-policy.json" "$R/catalog/"
cp "$ROOT/hooks/git/pre-push-self-review.sh" "$R/hooks/git/"
git -C "$R" init -q; git -C "$R" config user.email test@example.com; git -C "$R" config user.name Test
run_msg(){ (cd "$R" && bash .githooks/commit-msg "$1"); }
printf 'docs\n' > "$R/README.md"; git -C "$R" add README.md
cat > "$TMP/a.msg" <<'EOF'
docs: clarify [no-ticket]

Review-Tier: A
Self-Review: focused diff checked
EOF
run_msg "$TMP/a.msg" >/dev/null 2>&1 && ok "Tier A accepts short review without artifact" || bad "Tier A short review blocked"
git -C "$R" commit --no-verify -q -F "$TMP/a.msg"
mkdir -p "$R/skills/x"; printf 'behavior\n' > "$R/skills/x/SKILL.md"; git -C "$R" add skills/x/SKILL.md
cat > "$TMP/low.msg" <<'EOF'
feat: skill

Review-Tier: A
Self-Review: checked
EOF
if run_msg "$TMP/low.msg" >/dev/null 2>&1; then bad "Tier B downgrade accepted"; else ok "Tier B downgrade rejected"; fi
cat > "$TMP/b-missing.msg" <<'EOF'
feat: skill [no-ticket]

Review-Tier: B
Self-Review: focused review
Self-Review-Source: plans/missing.md
EOF
if run_msg "$TMP/b-missing.msg" >/dev/null 2>&1; then bad "commit-msg accepted missing Tier B artifact"; else ok "commit-msg rejects missing Tier B artifact"; fi
mkdir -p "$R/plans"; cat > "$R/plans/review.md" <<'EOF'
## Assumptions
Goal source: fixture
Working as: software engineer
## Test plan
focused fixture
EOF
git -C "$R" add plans/review.md
cat > "$TMP/b.msg" <<'EOF'
feat: skill [no-ticket]

Review-Tier: B
Self-Review: focused review
Self-Review-Source: plans/review.md
EOF
run_msg "$TMP/b.msg" >/dev/null 2>&1 && ok "Tier B accepts focused artifact" || bad "Tier B focused artifact blocked"
git -C "$R" commit --no-verify -q -F "$TMP/b.msg"
printf '#!/bin/bash\n' > "$R/hooks/git/x.sh"; git -C "$R" add hooks/git/x.sh
cat > "$TMP/c-low.msg" <<'EOF'
fix: gate

Review-Tier: B
Self-Review: checked
Self-Review-Source: plans/review.md
EOF
if run_msg "$TMP/c-low.msg" >/dev/null 2>&1; then bad "Tier C downgrade accepted"; else ok "Tier C downgrade rejected"; fi
cat > "$TMP/c-incomplete.msg" <<'EOF'
fix: gate [no-ticket]

Review-Tier: C
Self-Review: incomplete
Self-Review-Source: plans/review.md
Hostile-Review: plans/hostile.md
EOF
if run_msg "$TMP/c-incomplete.msg" >/dev/null 2>&1; then bad "Tier C incomplete evidence accepted"; else ok "Tier C incomplete evidence rejected"; fi
cat > "$TMP/duplicate.msg" <<'EOF'
fix: duplicate tier [no-ticket]

Review-Tier: C
Review-Tier: A
Self-Review: duplicate
EOF
if run_msg "$TMP/duplicate.msg" >/dev/null 2>&1; then bad "duplicate tier accepted"; else ok "duplicate tier rejected"; fi
printf 'risk evidence\n' > "$R/plans/pre.md"; printf 'independent findings\n' > "$R/plans/hostile.md"
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
git -C "$R" add plans/full.md plans/pre.md plans/hostile.md
cat > "$TMP/c.msg" <<'EOF'
fix: gate [no-ticket]

Review-Tier: C
Self-Review: full review
Self-Review-Source: plans/full.md
Hostile-Review: plans/hostile.md
Negative-Tests: review_risk_policy.test.sh
Full-Suite: hook suites
Canary-Rollback: fixture and revert
EOF
run_msg "$TMP/c.msg" >/dev/null 2>&1 && ok "Tier C accepts full trailers/artifact" || bad "Tier C valid evidence blocked"
git -C "$R" commit --no-verify -q -F "$TMP/c.msg"
ZERO=0000000000000000000000000000000000000000
printf 'refs/heads/test %s refs/heads/test %s\n' "$(git -C "$R" rev-parse HEAD)" "$ZERO" | (cd "$R" && bash hooks/git/pre-push-self-review.sh) >/dev/null 2>&1 && ok "pre-push validates tiered commit history" || bad "pre-push rejected valid tiered history"
: > "$R/plans/full.md"; git -C "$R" add plans/full.md; git -C "$R" commit --amend --no-verify -q -F "$TMP/c.msg"
if printf 'refs/heads/test %s refs/heads/test %s\n' "$(git -C "$R" rev-parse HEAD)" "$ZERO" | (cd "$R" && bash hooks/git/pre-push-self-review.sh) >/dev/null 2>&1; then bad "pre-push accepted empty review artifact"; else ok "pre-push rejects empty review artifact"; fi
cat > "$TMP/bad-pointer.msg" <<'EOF'
fix: bad pointer [no-ticket]

Review-Tier: C
Self-Review: invalid pointer
Self-Review-Source: plans/missing.md
Hostile-Review: plans/missing-hostile.md
Negative-Tests: fixture
Full-Suite: fixture
Canary-Rollback: revert
EOF
git -C "$R" commit --amend --no-verify -q -F "$TMP/bad-pointer.msg"
if printf 'refs/heads/test %s refs/heads/test %s\n' "$(git -C "$R" rev-parse HEAD)" "$ZERO" | (cd "$R" && bash hooks/git/pre-push-self-review.sh) >/dev/null 2>&1; then bad "pre-push accepted missing evidence pointers"; else ok "pre-push rejects missing evidence pointers"; fi
cat > "$TMP/tierless.msg" <<'EOF'
fix: tierless bypass [no-ticket]

Self-Review: attempted bypass
Self-Review-Source: plans/full.md
EOF
git -C "$R" commit --amend --no-verify -q -F "$TMP/tierless.msg"
if printf 'refs/heads/test %s refs/heads/test %s\n' "$(git -C "$R" rev-parse HEAD)" "$ZERO" | (cd "$R" && bash hooks/git/pre-push-self-review.sh) >/dev/null 2>&1; then bad "pre-push accepted post-policy tierless commit"; else ok "pre-push rejects post-policy tierless commit"; fi
echo "review_risk_policy: $pass passed, $fail failed"; [[ $fail -eq 0 ]]
