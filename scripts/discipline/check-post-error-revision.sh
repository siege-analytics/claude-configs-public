#!/bin/bash
# check-post-error-revision.sh — block-structure validator for the
# writing-rules:6 Post-error revision block.
#
# Usage: check-post-error-revision.sh <artifact-path>
#
# Validates that a referenced ticket / artifact contains a properly-
# formed `## Post-error revision` block with all five required fields:
#
#   ## Post-error revision
#     Triggered by: <PR # / commit SHA / incident link / failed
#                    Trivial-change block path>
#     Observed: <empirical evidence; must carry a writing-rules:4
#                evidence-token: fenced code block, file path with
#                extension, git command, stat/count, or URL>
#     Falsified assumption: <quoted Assumption from the originating
#                            ticket / artifact>
#     Revised model: <falsifiable corrected version>
#     Implication: <what changes>
#
# Per writing-rules:6 (claude-configs-public#167, #168), the Post-
# error revision block is the structured response when a documented
# Assumption is contradicted by empirical evidence. The Observed:
# field carries the same writing-rules:4 evidence-token requirement
# as the Trivial-change Evidence: field — free-text assertions
# like "it broke" do not satisfy the rule.
#
# Exits 0 on PASS (or no block present — absence is not a per-file
# failure, only relevant when the calling hook expected one). Exits
# 2 on BLOCK with the gap.

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: check-post-error-revision.sh <artifact-path>" >&2
    exit 64
fi

ARTIFACT_PATH="$1"

if [[ ! -f "$ARTIFACT_PATH" ]]; then
    echo "BLOCK: $ARTIFACT_PATH does not exist" >&2
    exit 2
fi

# Same evidence-token regex as check-trivial-claim.sh — kept in sync.
# Any change here should also land in check-trivial-claim.sh.
EVIDENCE_TOKEN_RE='```|[/-][a-zA-Z0-9_-]+\.[a-zA-Z]{1,5}|git[[:space:]]+(diff|log|status|rev-parse|merge-base|blame|show)|[0-9]+[[:space:]]+(lines?|files?|bytes?|insertions?|deletions?)|https?://'

HEADER="## Post-error revision"

if ! grep -qE "^${HEADER}\$" "$ARTIFACT_PATH"; then
    # Block not present. Caller (hook) decides whether absence is fatal.
    exit 0
fi

# Extract the block content: lines after the header, up to the next
# top-level heading ("## " at line start).
content=$(awk -v h="^${HEADER}\$" '$0 ~ h {flag=1; next} /^## /{flag=0} flag' "$ARTIFACT_PATH")

required_fields=("Triggered by:" "Observed:" "Falsified assumption:" "Revised model:" "Implication:")
missing=()
for field in "${required_fields[@]}"; do
    if ! echo "$content" | grep -qE "^[[:space:]]*${field}[[:space:]]+\S"; then
        missing+=("$field")
    fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
    cat >&2 <<EOF
BLOCK: $ARTIFACT_PATH '## Post-error revision' block missing fields:
EOF
    printf '  - %s\n' "${missing[@]}" >&2
    cat >&2 <<EOF

Per writing-rules:6 (claude-configs-public#167, #168), every Post-
error revision block requires all five fields:
  Triggered by / Observed / Falsified assumption / Revised model / Implication

See skills/post-error-revision/SKILL.md for the full template and a
worked example.
EOF
    exit 2
fi

# Observed: must carry a writing-rules:4 evidence-token. Same shape as
# the Trivial-change Evidence: field — see check-trivial-claim.sh.
observed_block=$(echo "$content" | awk '
    /^[[:space:]]*Observed:/{flag=1}
    /^[[:space:]]*(Triggered by|Falsified assumption|Revised model|Implication):/{
        if ($0 !~ /Observed:/) flag=0
    }
    flag
')

if ! echo "$observed_block" | grep -qE "$EVIDENCE_TOKEN_RE"; then
    cat >&2 <<EOF
BLOCK: $ARTIFACT_PATH '## Post-error revision' block 'Observed:' field
has no verifiable observation token.

The Observed: field carries the writing-rules:4 evidence-token
requirement (same as Trivial-change Evidence:). It must contain at
least one of:
  - a fenced code block (\`\`\` ... \`\`\`)
  - a file path with extension
  - a git command (git diff/log/status/rev-parse/merge-base/blame/show)
  - a stat or count (e.g., "1 file, 5 lines")
  - a URL (https?://)

Found:
$observed_block

Free-text assertions like "it broke" or "there was an error" do not
satisfy this requirement — paste a log line, a test output, a stat,
or a URL.
EOF
    exit 2
fi

exit 0
