#!/usr/bin/env bash
# Idempotent harmonisation entrypoint for workspace consumers.
#
# The problem this solves: a recurring "sync" that copies skills/ into a
# workspace keeps the advisory markdown fresh while leaving enforcement dark.
# The skills pane looks complete and current; the hooks, the RULES_BUNDLE
# mount, and the watchdog automation are never wired. This is the failure
# mode of #96 (rules without compelling adherence) observed in production:
# skills present, enforcement absent, and nothing that fails loudly to say so.
#
# harmonize.sh is what a consumer's recurring job should call INSTEAD of a bare
# copy. It (re)runs the full install wiring and then runs verify-enforcement.sh,
# which fails non-zero if enforcement did not actually come up. Copying skills/
# alone can no longer masquerade as harmonisation.
#
# It does NOT pull from a remote. Fetching upstream (git subtree, subtree-pull,
# rsync from a release tag) is consumer-specific and stays in the consumer's
# job. harmonize.sh takes whatever is on disk and makes enforcement live from
# it, idempotently.
#
# Usage:
#   bash bin/harmonize.sh                       # auto-detect CA workspace
#   bash bin/harmonize.sh --workspace <slug>    # explicit CA workspace slug
#   bash bin/harmonize.sh --no-craft-agent      # direct-clone mode
#
# Exit codes:
#   0  wiring succeeded AND enforcement verified live
#   1  wiring or verification failed (enforcement is NOT live)
#   2  bad invocation
#
# Refs: #96.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CA_ROOT="$HOME/.craft-agent/workspaces"
PASSTHROUGH=()

usage() {
    cat <<'USAGE'
Usage: bash bin/harmonize.sh [--workspace <slug>] [--no-craft-agent]

Runs the install wiring (bin/install.sh) then verifies enforcement is live
(bin/verify-enforcement.sh). Idempotent. Intended as the canonical entrypoint
for a consumer's recurring harmonisation job -- a bare `cp skills/` is not
harmonisation and will be caught by the verification step.
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        *) PASSTHROUGH+=("$1"); shift ;;
    esac
done

echo "=== harmonize: wiring enforcement from $REPO_ROOT ==="
echo

# Delegate the actual deploy + hook wiring + automation registration to
# install.sh, which already knows how to detect Craft Agent and now also wires
# the blocking gate, registers the watchdog automation, and self-verifies.
if bash "$REPO_ROOT/bin/install.sh" "${PASSTHROUGH[@]}"; then
    echo
    echo "HARMONIZE OK: enforcement wired and verified live."
    exit 0
fi

status=$?
echo >&2
echo "HARMONIZE FAILED (exit $status): enforcement is NOT live." >&2
echo "The skills may have synced, but a bare skills copy is not enforcement." >&2
echo "Inspect the install/verify output above and re-run once resolved." >&2
exit 1
