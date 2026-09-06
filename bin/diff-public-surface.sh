#!/usr/bin/env bash
# Public-surface differ for writing-releases:1 BREAKING enforcement (#51).
#
# Usage:
#   bin/diff-public-surface.sh <package> <old-ref> [<new-ref>]
#
# Diffs the public surface of <package> between <old-ref> and <new-ref>
# (default: HEAD). Delegates to `griffe check` when available; falls back
# to a diagnostic stub when it isn't so consumers see a clear install
# instruction rather than silent success.
#
# Exit codes:
#   0  = no public-surface changes detected (or griffe reports clean)
#   1  = public-surface changes detected (griffe non-zero)
#   2  = tooling unavailable (griffe not installed); caller must decide
#        whether to fail-closed or fail-open on missing tooling. CI
#        workflows using this script should install griffe explicitly.
#
# Consumer projects: copy this file to their bin/ or symlink from a
# submodule/vendor path. This repo (claude-configs-public) has no
# Python package, so the script is scaffolding for downstream consumers.
#
# Composes with writing-releases:1: griffe catches signature-level breaks
# but cannot detect behavior changes that preserve signatures (validator
# becoming stricter). A green griffe run is not evidence that a change
# is non-BREAKING; a red griffe run IS evidence that BREAKING
# classification is required.
#
# Ref: siege-analytics/claude-configs-public#51

set -uo pipefail

if [[ $# -lt 2 ]]; then
    echo "usage: $0 <package> <old-ref> [<new-ref>]" >&2
    exit 2
fi

PACKAGE="$1"
OLD_REF="$2"
NEW_REF="${3:-HEAD}"

if ! command -v griffe >/dev/null 2>&1; then
    cat >&2 <<EOF
griffe not found. Install it for BREAKING-change mechanical assist:

    python3 -m pip install --user griffe

Then re-run this script. Without griffe, writing-releases:1 falls back
to operator judgment; a signature-level break would ship without a
mechanical check. See skills/_writing-releases-rules.md line 19.
EOF
    exit 2
fi

# griffe check exits non-zero when it finds breaking changes.
# We pass through its exit code so CI can gate on it.
griffe check "$PACKAGE" --against "$OLD_REF" 2>&1 || {
    rc=$?
    echo "" >&2
    echo "griffe reported public-surface changes between $OLD_REF and $NEW_REF." >&2
    echo "Per writing-releases:1, a BREAKING entry is required in the CHANGELOG." >&2
    echo "" >&2
    echo "Note: griffe catches SIGNATURE-level breaks (removed names, changed" >&2
    echo "params, changed return types). It cannot catch BEHAVIOR-level breaks" >&2
    echo "(validator becoming stricter with unchanged signature). Those remain" >&2
    echo "operator-judgment." >&2
    exit "$rc"
}
