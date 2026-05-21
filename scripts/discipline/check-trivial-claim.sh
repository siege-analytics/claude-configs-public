#!/bin/bash
# check-trivial-claim.sh — evidence-chain check for trivial / exemption blocks
#
# Usage: check-trivial-claim.sh <artifact-path>
#
# When the artifact contains '## Trivial-change declaration' or
# '## Exemption:' blocks, each block must have all three fields:
#   Reason: <one sentence WHY, falsifiable>
#   Evidence: <command output or verifiable observation token>
#   Falsification: <observable that would make the claim wrong>
#
# Per writing-rules:4 (claude-configs-public#146), every "this doesn't
# apply" claim requires the same evidence chain as a "this happened"
# claim.
#
# Evidence field validation: must contain at least one of —
#   - a fenced code block ``` ... ```
#   - a file path (slash or hyphen + extension)
#   - a git command shape (`git ...`)
#   - a stat / count shape (digits + "lines" / "files" / "bytes")
#   - a URL (https? ://)
# Free-text assertions like "obviously trivial" or "minor cleanup"
# fail because they have no falsifiable observation.
#
# Exits 0 on PASS (or no blocks present), 2 on BLOCK with the gap.

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: check-trivial-claim.sh <artifact-path>" >&2
    exit 64
fi

ARTIFACT_PATH="$1"

if [[ ! -f "$ARTIFACT_PATH" ]]; then
    echo "BLOCK: $ARTIFACT_PATH does not exist" >&2
    exit 2
fi

EVIDENCE_TOKEN_RE='```|[/-][a-zA-Z0-9_-]+\.[a-zA-Z]{1,5}|git[[:space:]]+(diff|log|status|rev-parse|merge-base)|[0-9]+[[:space:]]+(lines?|files?|bytes?|insertions?|deletions?)|https?://'

check_block() {
    local header="$1"
    if ! grep -qE "^${header}" "$ARTIFACT_PATH"; then
        return 0  # block not present, nothing to check
    fi

    local content
    content=$(awk -v h="^${header}" '$0 ~ h {flag=1; next} /^## /{flag=0} flag' "$ARTIFACT_PATH")

    local missing=()
    for field in "Reason:" "Evidence:" "Falsification:"; do
        if ! echo "$content" | grep -qE "^[[:space:]]*${field}[[:space:]]+\S"; then
            missing+=("$field")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "BLOCK: $ARTIFACT_PATH '${header}' block missing fields:" >&2
        printf '  - %s\n' "${missing[@]}" >&2
        echo "" >&2
        echo "  Per writing-rules:4: Reason / Evidence / Falsification" >&2
        echo "  required for every 'this doesn't apply' claim." >&2
        return 2
    fi

    # Evidence field must contain a verifiable observation token.
    local evidence_line
    evidence_line=$(echo "$content" | grep -E "^[[:space:]]*Evidence:[[:space:]]+" | head -1)
    # Also accept multi-line evidence: take from Evidence: line to next field
    local evidence_block
    evidence_block=$(echo "$content" | awk '/^[[:space:]]*Evidence:/{flag=1} /^[[:space:]]*(Reason|Falsification):/{if($0 !~ /Evidence:/) flag=0} flag')

    if ! echo "$evidence_block" | grep -qE "$EVIDENCE_TOKEN_RE"; then
        cat >&2 <<EOF
BLOCK: $ARTIFACT_PATH '${header}' block Evidence: field has no
verifiable observation token.

The Evidence field must contain at least one of:
  - a fenced code block (\`\`\` ... \`\`\`)
  - a file path with extension
  - a git command (git diff/log/status/rev-parse/merge-base)
  - a stat or count (e.g., "1 file, 5 lines")
  - a URL (https?://)

Found:
$evidence_block

Free-text assertions like "obviously trivial" or "minor cleanup"
do not satisfy this requirement — they have no falsifiable
observation. Paste a command output or a verifiable artifact link.
EOF
        return 2
    fi

    return 0
}

# Check both block kinds; exit on first failure.
check_block "## Trivial-change declaration"
check_block "## Exemption"

exit 0
