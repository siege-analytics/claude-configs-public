#!/usr/bin/env bash
# Sync repo hooks/rules into a Craft Agent workspace and verify no deploy drift.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="$HOME/.craft-agent/workspaces/my-workspace"
YES=0

usage() {
  cat <<'USAGE'
Usage: bash bin/sync-workspace-hooks.sh --yes [--workspace <path>]

Defaults to ~/.craft-agent/workspaces/my-workspace, but --yes is required
because this command mutates the workspace hook deployment.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace)
      [[ -z "${2:-}" ]] && { echo "ERROR: --workspace requires a path" >&2; exit 2; }
      WORKSPACE="$2"; shift 2 ;;
    --yes)
      YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

WORKSPACE="${WORKSPACE/#\~/$HOME}"

if [[ "$YES" -ne 1 ]]; then
  echo "ERROR: --yes is required before mutating workspace hook deployment: $WORKSPACE" >&2
  echo "       Rerun with: bash bin/sync-workspace-hooks.sh --yes --workspace '$WORKSPACE'" >&2
  exit 2
fi

echo "=== Sync workspace hooks ==="
echo "Repo:      $REPO_ROOT"
echo "Workspace: $WORKSPACE"
echo

python3 "$REPO_ROOT/bin/build.py" --layout flat --deploy --craft-workspace "$WORKSPACE"
bash "$REPO_ROOT/bin/install-hooks.sh" --workspace "$WORKSPACE" --hooks-root "$WORKSPACE"
if [[ -f "$REPO_ROOT/bin/wire-enforcement.py" ]]; then
  python3 "$REPO_ROOT/bin/wire-enforcement.py" --workspace "$WORKSPACE"
fi
bash "$REPO_ROOT/bin/verify-enforcement.sh" --target "$WORKSPACE" --mode craft-agent
python3 "$REPO_ROOT/bin/check-deploy-drift.py" --repo-root "$REPO_ROOT" --workspace "$WORKSPACE" --scope hooks --verbose
