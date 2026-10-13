#!/usr/bin/env bash
# Static regression checks for the main-only release boundary.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WF="$ROOT/.github/workflows/build-and-publish.yml"
MODEL="$ROOT/.claude/deploy-model"

fail() { echo "FAIL: $*" >&2; exit 1; }

grep -qF "branches: [main, develop]" "$WF" || fail "develop/main validation trigger missing"
grep -qF "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" "$WF" \
  || fail "publish job is not restricted to main pushes"
if grep -qE '^[[:space:]]+tags:' "$WF"; then
  fail "tag pushes must not retrigger the publishing workflow"
fi
if grep -q "refs/heads/develop" "$WF"; then
  fail "develop appears in an executable publish condition"
fi
[[ "$(cat "$MODEL")" == "merge-then-deploy" ]] || fail "committed deployment model missing or invalid"
deploy_checks="$(grep -cF "validate_deploy_source(REPO_ROOT)" "$ROOT/bin/build.py")"
[[ "$deploy_checks" -eq 3 ]] \
  || fail "build.py must verify deploy source at startup, before mutation, and after mutation (got $deploy_checks checks)"

echo "release_source_policy_test: PASS"
