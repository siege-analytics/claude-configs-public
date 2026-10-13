#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$ROOT/hooks/resolver/inject-resolver.sh"
pass=0; fail=0
ok(){ echo "  PASS: $1"; pass=$((pass+1)); }
bad(){ echo "  FAIL: $1"; fail=$((fail+1)); }
run(){ printf '%s' "$1" | CRAFT_AGENT_PLANS_PATH=/nonexistent bash "$HOOK"; }
generic='{"prompt":"write a friendly greeting","cwd":"/tmp"}'
out1="$(run "$generic")"; out2="$(run "$generic")"
[[ "$out1" == "$out2" ]] && ok "identical input produces identical injection" || bad "injection is nondeterministic"
grep -q 'state: unknown' <<<"$out1" && ok "unknown is visible" || bad "unknown state missing"
! grep -q 'load: python\|load: spark\|load: shelves' <<<"$out1" && ok "generic task excludes domains and shelves" || bad "generic task over-loaded"
python_out="$(run '{"prompt":"review this Python module","cwd":"/tmp"}')"
grep -q 'load: coding' <<<"$python_out" && grep -q 'load: python' <<<"$python_out" && ok "Python task selects coding capabilities" || bad "Python route missing"
! grep -q 'slow is smooth' <<<"$python_out" && ok "legacy resolver prose not injected" || bad "legacy resolver still injected"
chars=$(printf '%s' "$python_out" | wc -c | tr -d ' ')
[[ "$chars" -lt 12000 ]] && ok "injection stays below 12k chars ($chars)" || bad "injection too large ($chars)"
overflow_out="$(run '{"prompt":"[skill:branch] [skill:commit] [skill:create-pr] [skill:merge] [skill:code-review] [skill:skillbuilder] [skill:ticket-guard] [skill:create-ticket] [skill:update-ticket] [skill:coding] [skill:python] [skill:testing-frameworks] [skill:sql]","cwd":"/tmp"}')"
if grep -q 'state: over-budget' <<<"$overflow_out" && ! grep -q '^load:' <<<"$overflow_out"; then
  ok "oversized explicit selection is visibly rejected kernel-only"
else
  bad "oversized explicit selection was partially or silently loaded"
fi
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir "$TMP/many-plans"
: > "$TMP/many-plans/think-many.md"
for i in $(seq 1 25); do
  : > "$TMP/many-plans/investigate-$i.md"
  : > "$TMP/many-plans/pre-mortem-$i.md"
  : > "$TMP/many-plans/self-review-$i.md"
done
many_plans="$(printf '%s' "$generic" | CRAFT_AGENT_PLANS_PATH="$TMP/many-plans" bash "$HOOK")"
grep -q 'state: unknown' <<<"$many_plans" && ok "large plan inventory does not SIGPIPE under pipefail" || bad "large plan inventory terminated hook"
git -C "$TMP" init -q; git -C "$TMP" remote add origin git@github.com:siege-analytics/siege_utilities.git
project_out="$(run "{\"prompt\":\"review this diff\",\"cwd\":\"$TMP\"}")"
grep -q 'project: siege-utilities' <<<"$project_out" && grep -q 'load: siege-utilities--rules' <<<"$project_out" && ok "matching repo loads project overlay" || bad "project overlay missing"
outside="$(run '{"prompt":"review this diff","cwd":"/tmp"}')"
! grep -q 'siege-utilities--' <<<"$outside" && ok "project overlay does not leak" || bad "project overlay leaked"
malformed="$(printf '%s' 'not-json' | bash "$HOOK")"
grep -q 'state: unknown' <<<"$malformed" && ok "malformed payload fails to kernel-only" || bad "malformed payload did not fail safely"
missing_kernel="$(printf '%s' "$generic" | CLAUDE_KERNEL_PATH="$TMP/missing-kernel.md" bash "$HOOK")"
if [[ "$missing_kernel" == *'"continue":false'* ]] && [[ "$missing_kernel" != *'<skill-kernel'* ]]; then
  ok "missing kernel blocks as sole structured output"
else
  bad "missing kernel failed open or mixed blocking output"
fi
cp "$ROOT/skills/KERNEL.md" "$TMP/tampered-kernel.md"
printf '\nFull compatibility bundle content must never mount globally.\n' >> "$TMP/tampered-kernel.md"
tampered_kernel="$(printf '%s' "$generic" | CLAUDE_KERNEL_PATH="$TMP/tampered-kernel.md" bash "$HOOK")"
if [[ "$tampered_kernel" == *'"continue":false'* ]] && [[ "$tampered_kernel" != *'<skill-kernel'* ]]; then
  ok "noncanonical kernel override fails closed as sole structured output"
else
  bad "noncanonical kernel override injected caller-controlled content"
fi
cp "$ROOT/skills/KERNEL.md" "$TMP/kernel-copy.md"
identical_kernel="$(printf '%s' "$generic" | CLAUDE_KERNEL_PATH="$TMP/kernel-copy.md" bash "$HOOK")"
grep -q 'state: unknown' <<<"$identical_kernel" && ok "byte-identical packaged kernel override is accepted" || bad "identical kernel override was rejected"
canary="$(printf '%s' '{"prompt":"review this Python module","cwd":"/tmp"}' | CLAUDE_PROGRESSIVE_LOADING=canary bash "$HOOK")"
if grep -q 'candidate: python' <<<"$canary" && ! grep -q 'load: python' <<<"$canary"; then
  ok "canary reports candidates without load instructions"
else
  bad "canary mode activated or hid candidate routing"
fi
kernel_only="$(printf '%s' '{"prompt":"review this Python module","cwd":"/tmp"}' | CLAUDE_PROGRESSIVE_LOADING=kernel-only bash "$HOOK")"
if grep -q 'state: disabled' <<<"$kernel_only" && ! grep -q 'load: python\|candidate: python' <<<"$kernel_only"; then
  ok "kernel-only control disables selection without broad fallback"
else
  bad "kernel-only control did not disable selection safely"
fi
echo "progressive_loading: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
