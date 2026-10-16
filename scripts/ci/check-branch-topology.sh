#!/usr/bin/env bash
# Enforce the canonical integration/promotion graph, then (for the registered
# pull_request_target path) evaluate the exact candidate range under trusted
# base policy. GitHub executes the workflow from the default branch; the exact
# PR base checkout supplies this script and policy implementation.
set -euo pipefail

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

# Local/direct topology probes stop here. Provider evaluation is activated only
# by the host's registered pull_request_target event path.
if [[ "${GITHUB_EVENT_NAME:-}" != "pull_request_target" ]]; then
  exit 0
fi

for required in GITHUB_EVENT_PATH GITHUB_REPOSITORY GITHUB_SERVER_URL GITHUB_WORKFLOW_REF GITHUB_WORKFLOW_SHA; do
  if [[ -z "${!required:-}" ]]; then
    echo "BLOCKED: provider input $required is required." >&2
    exit 2
  fi
done
if [[ ! -f "$GITHUB_EVENT_PATH" ]]; then
  echo "BLOCKED: provider event payload is unavailable: $GITHUB_EVENT_PATH" >&2
  exit 2
fi

IFS=$'\t' read -r EVENT_BASE_SHA EVENT_BASE_BRANCH EVENT_BASE_REPO \
  EVENT_HEAD_SHA EVENT_HEAD_BRANCH EVENT_HEAD_REPO EVENT_REPOSITORY < <(
  python3 - "$GITHUB_EVENT_PATH" <<'PY'
import json, sys
p = json.load(open(sys.argv[1], encoding="utf-8"))
pr = p.get("pull_request") or {}
base = pr.get("base") or {}
head = pr.get("head") or {}
values = (
    base.get("sha"), base.get("ref"), (base.get("repo") or {}).get("full_name"),
    head.get("sha"), head.get("ref"), (head.get("repo") or {}).get("full_name"),
    (p.get("repository") or {}).get("full_name"),
)
if any(not isinstance(v, str) or not v or any(c in v for c in "\t\n\r") for v in values):
    raise SystemExit("invalid pull_request_target identity payload")
print("\t".join(values))
PY
) || { echo "BLOCKED: cannot parse exact pull_request_target identities." >&2; exit 2; }

if [[ "$BASE_BRANCH" != "$EVENT_BASE_BRANCH" || "$HEAD_BRANCH" != "$EVENT_HEAD_BRANCH" \
   || "$HEAD_REPO" != "$EVENT_HEAD_REPO" || "$CANONICAL_REPO" != "$EVENT_REPOSITORY" \
   || "$EVENT_BASE_REPO" != "$EVENT_REPOSITORY" || "$GITHUB_REPOSITORY" != "$EVENT_REPOSITORY" ]]; then
  echo "BLOCKED: workflow inputs disagree with exact host event identities." >&2
  exit 2
fi

CANDIDATE_ROOT=$(git rev-parse --show-toplevel)
POLICY_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
if [[ "$(git -C "$CANDIDATE_ROOT" rev-parse HEAD)" != "$EVENT_HEAD_SHA" ]]; then
  echo "BLOCKED: candidate checkout differs from exact host event head." >&2
  exit 2
fi
if [[ "$(git -C "$POLICY_ROOT" rev-parse HEAD)" != "$EVENT_BASE_SHA" ]]; then
  echo "BLOCKED: trusted policy checkout differs from exact host event base." >&2
  exit 2
fi

# actions/checkout from the default-branch workflow may provide a depth-1 base
# checkout. Fetch complete canonical history before policy ancestor/blob checks.
if [[ "$(git -C "$POLICY_ROOT" rev-parse --is-shallow-repository)" == "true" ]]; then
  git -C "$POLICY_ROOT" fetch --quiet --no-tags --unshallow origin \
    '+refs/heads/*:refs/remotes/origin/*'
else
  git -C "$POLICY_ROOT" fetch --quiet --no-tags origin \
    '+refs/heads/*:refs/remotes/origin/*'
fi
for revision in "$EVENT_BASE_SHA" "$GITHUB_WORKFLOW_SHA"; do
  git -C "$POLICY_ROOT" cat-file -e "$revision^{commit}" 2>/dev/null || {
    echo "BLOCKED: required trusted revision is unavailable: $revision" >&2
    exit 2
  }
done
DEFAULT_WORKFLOW_HEAD=$(git -C "$POLICY_ROOT" rev-parse refs/remotes/origin/main 2>/dev/null || true)
if [[ "$DEFAULT_WORKFLOW_HEAD" != "$GITHUB_WORKFLOW_SHA" ]]; then
  echo "BLOCKED: host workflow SHA differs from fetched canonical default branch." >&2
  exit 2
fi

case "$GITHUB_SERVER_URL" in
  https://*) CANONICAL_HOST=${GITHUB_SERVER_URL#https://} ;;
  *) echo "BLOCKED: unsupported provider server URL." >&2; exit 2 ;;
esac
if [[ -z "$CANONICAL_HOST" || "$CANONICAL_HOST" == *:* || "$CANONICAL_HOST" == */* ]]; then
  echo "BLOCKED: provider server URL is not an exact host." >&2
  exit 2
fi

python3 "$POLICY_ROOT/scripts/ci/protected-policy-range.py" \
  --trusted-root "$POLICY_ROOT" --trusted-revision "$EVENT_BASE_SHA" \
  --candidate-repo "$CANDIDATE_ROOT" --base "$EVENT_BASE_SHA" --head "$EVENT_HEAD_SHA" \
  --canonical-identity "$CANONICAL_HOST/$EVENT_REPOSITORY" \
  --head-branch "$EVENT_HEAD_BRANCH" --target-branch "$EVENT_BASE_BRANCH" \
  --executed-workflow-ref "$GITHUB_WORKFLOW_REF" \
  --executed-workflow-revision "$GITHUB_WORKFLOW_SHA" \
  --receipt /tmp/protected-policy-receipt.json
