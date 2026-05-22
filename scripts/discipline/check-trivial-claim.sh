#!/bin/bash
# check-trivial-claim.sh — evidence-chain check for Trivial-change /
# Exemption blocks
#
# Usage: check-trivial-claim.sh <artifact-path>
#
# Two block shapes, both required to carry a writing-rules:4 evidence
# chain. The Trivial-change shape additionally requires the
# writing-rules:5 Category field from the controlled vocabulary.
#
# ## Trivial-change declaration (writing-rules:5):
#   Category: <one of the 7-entry controlled vocabulary>
#   Cannot produce error: <falsifiable claim>
#   Evidence: <command output / verifiable observation>
#   Falsification: <observable that would prove the claim wrong>
#
# ## Exemption: <criterion-name> (writing-rules:4 generic):
#   Reason: <falsifiable WHY>
#   Evidence: <command output / verifiable observation>
#   Falsification: <observable that would prove the exemption wrong>
#
# Per writing-rules:4 + :5 (claude-configs-public#146, #163), every
# "this doesn't apply" claim requires the same evidence chain as a
# "this happened" claim. Trivial-change claims additionally require a
# Category from a controlled vocabulary so the operationally-rare
# trivial-safe categories cannot be free-texted into existence.
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

# writing-rules:5 controlled vocabulary for Trivial-change Category field.
ALLOWED_CATEGORIES_RE='^(prose-only-docs|comments-only|whitespace-only|commit-msg-only|private-rename|descriptive-docstring-fix|fixed-string-correction)$'

check_block() {
    local header="$1"
    local kind="$2"  # "trivial" or "exemption"
    if ! grep -qE "^${header}" "$ARTIFACT_PATH"; then
        return 0  # block not present, nothing to check
    fi

    local content
    content=$(awk -v h="^${header}" '$0 ~ h {flag=1; next} /^## /{flag=0} flag' "$ARTIFACT_PATH")

    # Required fields per block kind.
    local required_fields=()
    if [[ "$kind" == "trivial" ]]; then
        required_fields=("Category:" "Cannot produce error:" "Evidence:" "Falsification:")
    else
        required_fields=("Reason:" "Evidence:" "Falsification:")
    fi

    local missing=()
    for field in "${required_fields[@]}"; do
        if ! echo "$content" | grep -qE "^[[:space:]]*${field}[[:space:]]+\S"; then
            missing+=("$field")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "BLOCK: $ARTIFACT_PATH '${header}' block missing fields:" >&2
        printf '  - %s\n' "${missing[@]}" >&2
        echo "" >&2
        if [[ "$kind" == "trivial" ]]; then
            echo "  Per writing-rules:5: Trivial-change requires" >&2
            echo "  Category / Cannot produce error / Evidence / Falsification." >&2
            echo "  See _writing-rules-rules.md writing-rules:5 for the controlled" >&2
            echo "  vocabulary." >&2
        else
            echo "  Per writing-rules:4: Reason / Evidence / Falsification" >&2
            echo "  required for every 'this doesn't apply' claim." >&2
        fi
        return 2
    fi

    # Category validation for Trivial-change blocks.
    if [[ "$kind" == "trivial" ]]; then
        local category
        category=$(echo "$content" | grep -E "^[[:space:]]*Category:[[:space:]]+" | head -1 | sed -E 's/^[[:space:]]*Category:[[:space:]]+//;s/[[:space:]]*$//')
        if ! echo "$category" | grep -qE "$ALLOWED_CATEGORIES_RE"; then
            cat >&2 <<EOF
BLOCK: $ARTIFACT_PATH '${header}' block Category: '$category' is not
in the writing-rules:5 controlled vocabulary.

Allowed values (trivial-safe):
  prose-only-docs       — narrative docs that don't describe behavior
  comments-only         — comment-line-only changes in code files
  whitespace-only       — whitespace-only in non-significant-whitespace files
  commit-msg-only       — git commit --amend -m with no file change

Allowed values (borderline, conditional):
  private-rename             — rename of private symbol; needs grep evidence
  descriptive-docstring-fix  — docstring matches actual behavior; needs cite
  fixed-string-correction    — non-machine-consumed string typo; needs consumer grep

If your change doesn't fit a category, it's NOT trivial. File a full
ticket per the never-trivial list in writing-rules:5.

Adding a new category is a writing-rules:5 edit + a one-line constant
edit in this script. Both ship in one PR.
EOF
            return 2
        fi
    fi

    # Evidence field must contain a verifiable observation token.
    local evidence_block
    evidence_block=$(echo "$content" | awk '/^[[:space:]]*Evidence:/{flag=1} /^[[:space:]]*(Category|Cannot produce error|Reason|Falsification):/{if($0 !~ /Evidence:/) flag=0} flag')

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
check_block "## Trivial-change declaration" "trivial"
check_block "## Exemption" "exemption"

exit 0
