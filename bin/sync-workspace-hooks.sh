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

# The deploy build validates frontmatter with PyYAML and fails closed without
# it (#1046). Stop before any workspace mutation, with the same guidance.
if ! DEPENDENCY_STATUS=$(python3 "$REPO_ROOT/bin/frontmatter_validation.py" --check-dependency 2>&1); then
  echo "ERROR: PyYAML is required for frontmatter validation: $DEPENDENCY_STATUS" >&2
  echo "  Supported interpreter: CPython 3.12 (the CI-validated version; 3.9+ is compatible) as python3 on PATH," >&2
  echo "  with the pinned requirement installed:" >&2
  echo "    python3 -m pip install --require-hashes -r \"$REPO_ROOT/requirements-validation.txt\"" >&2
  exit 1
fi

ROUTER_INSTALLER="$REPO_ROOT/bin/install-craft-hook-router.py"
if [[ ! -f "$ROUTER_INSTALLER" ]]; then
  echo "ERROR: required Craft hook router installer missing: $ROUTER_INSTALLER" >&2
  exit 1
fi
SETTINGS_FILE="$WORKSPACE/.claude/craft-settings.json"

echo "=== Sync workspace hooks ==="
echo "Repo:      $REPO_ROOT"
echo "Workspace: $WORKSPACE"
echo

python3 "$REPO_ROOT/bin/build.py" --layout flat --deploy --craft-workspace "$WORKSPACE"
bash "$REPO_ROOT/bin/install-hooks.sh" --workspace "$WORKSPACE" --hooks-root "$WORKSPACE" --target-file "$SETTINGS_FILE"
python3 "$REPO_ROOT/bin/wire-enforcement.py" --workspace "$WORKSPACE" --settings-file "$SETTINGS_FILE"
bash "$REPO_ROOT/bin/verify-enforcement.sh" --target "$WORKSPACE" --mode craft-agent --settings-file "$SETTINGS_FILE"
python3 "$REPO_ROOT/bin/check-deploy-drift.py" --repo-root "$REPO_ROOT" --workspace "$WORKSPACE" --scope hooks --verbose

# Register the scoped bridge only after all local policy/drift checks pass.
python3 "$ROUTER_INSTALLER" --workspace "$WORKSPACE" --apply
python3 "$ROUTER_INSTALLER" --workspace "$WORKSPACE" --verify-registration
