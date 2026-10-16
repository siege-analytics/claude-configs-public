#!/usr/bin/env bash
# Delegate registered GitHub events to the approved effective-policy adapter.
# The self-hosted workflow supplies this script from the exact protected base.
# Direct/local compatibility checks remain pending their separate retirement.
set -euo pipefail

# Registered host events use the approved effective policy. Do not apply the
# legacy strict-only local branch cases to an authorized alternative profile.
if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request_target" ]]; then
  POLICY_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
  exec python3 "$POLICY_ROOT/scripts/ci/protected-policy-range.py" \
    --host-event --trusted-root "$POLICY_ROOT" --candidate-repo . \
    --receipt /tmp/protected-policy-receipt.json
fi

# Retained direct/local compatibility feedback, pending #849 retirement. This
# path does not establish protected authorization or shared-parent capability.

BASE_BRANCH="${BASE_BRANCH:-}"
HEAD_BRANCH="${HEAD_BRANCH:-}"
HEAD_REPO="${HEAD_REPO:-}"
CANONICAL_REPO="${CANONICAL_REPO:-}"
MAIN_REF="${MAIN_REF:-origin/main}"

if [[ -z "$BASE_BRANCH" || -z "$HEAD_BRANCH" ]]; then
  echo "BLOCKED: BASE_BRANCH and HEAD_BRANCH are required." >&2
  exit 2
fi

case "$BASE_BRANCH" in
  main)
    if [[ "$HEAD_BRANCH" != "develop" ]]; then
      echo "BLOCKED: PRs to main must have head exactly 'develop'; got '$HEAD_BRANCH'." >&2
      echo "Integrate the work into develop, reconcile main there, then promote develop -> main." >&2
      exit 1
    fi
    if [[ -z "$HEAD_REPO" || -z "$CANONICAL_REPO" || "$HEAD_REPO" != "$CANONICAL_REPO" ]]; then
      echo "BLOCKED: main promotion must come from canonical $CANONICAL_REPO:develop; got $HEAD_REPO:$HEAD_BRANCH." >&2
      exit 1
    fi
    ;;
  develop)
    ;;
  *)
    echo "BLOCKED: unsupported protected base '$BASE_BRANCH'." >&2
    exit 1
    ;;
esac

if ! git rev-parse --verify "$MAIN_REF^{commit}" >/dev/null 2>&1; then
  echo "BLOCKED: cannot resolve current main ref '$MAIN_REF'." >&2
  exit 2
fi

if ! git merge-base --is-ancestor "$MAIN_REF" HEAD; then
  echo "BLOCKED: candidate HEAD does not contain current main ($MAIN_REF)." >&2
  echo "Merge main into develop (or update the feature from reconciled develop), resolve and retest there." >&2
  exit 1
fi

echo "PASS: $HEAD_BRANCH -> $BASE_BRANCH follows canonical topology and contains $MAIN_REF."
