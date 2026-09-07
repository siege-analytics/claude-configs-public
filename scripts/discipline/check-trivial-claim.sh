#!/bin/bash
# check-trivial-claim.sh — evidence-chain check for Trivial-change /
# Trivial-investigation / Exemption blocks, plus external-shape-modeling
# never-trivial enforcement.
#
# Usage:
#   check-trivial-claim.sh <artifact-path>
#   check-trivial-claim.sh <artifact-path> --diff-files <diff-file-list-path>
#
# When --diff-files is supplied, the file at <diff-file-list-path> must
# contain one repo-relative path per line (as `git diff --name-only`
# emits). If any listed path is external-shape-modeling code
# (scanners/parsers/linters/hooks, per the filename patterns below), then
# ANY of the three Trivial-* declaration blocks in the artifact
# (`Trivial-change`, `Trivial-investigation`, `Trivial-against-state`)
# is rejected with the "external-shape-modeling never-trivial" diagnostic.
# When --diff-files is omitted, the never-trivial check is skipped —
# callers without diff context (manual invocation) still get vocabulary
# and evidence-chain validation.
#
# Block shapes:
#
# ## Trivial-change declaration (writing-rules:5):
#   Category: <one of the 7-entry Trivial-change vocabulary>
#   Cannot produce error: <falsifiable claim>
#   Evidence: <command output / verifiable observation>
#   Falsification: <observable that would prove the claim wrong>
#
# ## Trivial-investigation declaration (self-review/SKILL.md):
#   Category: <one of single-line-fix | doc-only | config-only | test-only>
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
# "this happened" claim. Trivial-change and Trivial-investigation claims
# additionally require a Category from a controlled vocabulary so the
# operationally-rare trivial-safe categories cannot be free-texted into
# existence.
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
# External-shape-modeling never-trivial (PR A):
# Files whose paths match any of the patterns below are treated as
# code that models an external shape space (scanners, parsers, linters,
# hooks). Per the writing-rules:5 amendment shipped alongside this PR,
# such changes require the full authoring-against-state:6 inventory —
# NO Trivial-* declaration is acceptable. The reviewer's guardrail:
# `external-shape-modeling` is a prohibited-triviality trigger, NOT a
# Category token to add to any of the three allowlists.
#
# Detection patterns (case-sensitive, filename-based):
#   - any path segment under `hooks/`
#   - any basename matching scan* | *_scan* | scanner* | *_scanner
#                           | lint* | linter*
#                           | parse_* | parser*
#                           | check-* | check_* | _check*
#     with extension .py | .sh | .js | .ts | .rb | .go
#
# Exits 0 on PASS (or no blocks present), 2 on BLOCK with the gap.

set -euo pipefail

ARTIFACT_PATH=""
DIFF_FILE_LIST=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --diff-files)
            if [[ $# -lt 2 ]]; then
                echo "usage: check-trivial-claim.sh <artifact-path> [--diff-files <file>]" >&2
                exit 64
            fi
            DIFF_FILE_LIST="$2"
            shift 2
            ;;
        --)
            shift
            ;;
        *)
            if [[ -z "$ARTIFACT_PATH" ]]; then
                ARTIFACT_PATH="$1"
                shift
            else
                echo "usage: check-trivial-claim.sh <artifact-path> [--diff-files <file>]" >&2
                exit 64
            fi
            ;;
    esac
done

if [[ -z "$ARTIFACT_PATH" ]]; then
    echo "usage: check-trivial-claim.sh <artifact-path> [--diff-files <file>]" >&2
    exit 64
fi

if [[ ! -f "$ARTIFACT_PATH" ]]; then
    echo "BLOCK: $ARTIFACT_PATH does not exist" >&2
    exit 2
fi

EVIDENCE_TOKEN_RE='```|[/-][a-zA-Z0-9_-]+\.[a-zA-Z]{1,5}|git[[:space:]]+(diff|log|status|rev-parse|merge-base)|[0-9]+[[:space:]]+(lines?|files?|bytes?|insertions?|deletions?)|https?://'

# writing-rules:5 controlled vocabulary for Trivial-change Category field.
TRIVIAL_CHANGE_VOCAB_RE='^(prose-only-docs|comments-only|whitespace-only|commit-msg-only|private-rename|descriptive-docstring-fix|fixed-string-correction)$'

# self-review/SKILL.md controlled vocabulary for Trivial-investigation Category field.
TRIVIAL_INVESTIGATION_VOCAB_RE='^(single-line-fix|doc-only|config-only|test-only)$'

# External-shape-modeling filename detection. Case-sensitive on basename.
# Any path under hooks/ is external-shape-modeling by definition (hooks
# infer semantics from source syntax / commit shape / diff shape).
is_external_shape_modeling_path() {
    local path="$1"
    # Any component under hooks/
    if [[ "$path" == hooks/* || "$path" == */hooks/* ]]; then
        return 0
    fi
    local base
    base="$(basename "$path")"
    # Extension gate
    case "$base" in
        *.py|*.sh|*.js|*.ts|*.rb|*.go) ;;
        *) return 1 ;;
    esac
    # Basename patterns
    case "$base" in
        scan*|*_scan*|scanner*|*_scanner*) return 0 ;;
        lint*|linter*|*_linter*) return 0 ;;
        parse_*|parser*|*_parser*) return 0 ;;
        check-*|check_*|_check*|*_check*) return 0 ;;
    esac
    return 1
}

# Read diff file list (if any) and identify external-shape-modeling matches.
# Sets DIFF_ESM_MATCHES to a newline-separated list of matched paths.
DIFF_ESM_MATCHES=""
if [[ -n "$DIFF_FILE_LIST" ]]; then
    if [[ ! -f "$DIFF_FILE_LIST" ]]; then
        echo "BLOCK: --diff-files argument '$DIFF_FILE_LIST' does not exist" >&2
        exit 2
    fi
    while IFS= read -r diff_path; do
        [[ -z "$diff_path" ]] && continue
        if is_external_shape_modeling_path "$diff_path"; then
            DIFF_ESM_MATCHES="${DIFF_ESM_MATCHES}${diff_path}"$'\n'
        fi
    done < "$DIFF_FILE_LIST"
fi

emit_esm_never_trivial() {
    local header="$1"
    cat >&2 <<EOF
BLOCK: $ARTIFACT_PATH declares '${header}' but the push touches
external-shape-modeling code:

$(printf '%s' "$DIFF_ESM_MATCHES" | sed 's/^/  - /')

Per writing-rules:5 and self-review/SKILL.md, external-shape-modeling
code (scanners, parsers, linters, hooks that infer semantics from
source syntax, config files, CLI arguments, API payloads, schemas,
notebooks, or framework conventions) is NEVER TRIVIAL. No Trivial-*
declaration is acceptable — 'external-shape-modeling' is a
prohibited-triviality trigger, not a Category token you can claim.

Remove the '${header}' block from $ARTIFACT_PATH and ship the full
authoring-against-state:6 inventory instead (Inputs read / Knowledge
requirements / Contact-point measurements / Surface areas / Hypothesis
/ Conclusions). See _authoring-against-state-rules.md for the
inventory template.
EOF
}

# Emit the writing-rules:5 vocabulary rejection diagnostic for Trivial-change.
emit_change_vocab_error() {
    local category="$1"
    cat >&2 <<EOF
BLOCK: $ARTIFACT_PATH '## Trivial-change declaration' block Category:
'$category' is not in the writing-rules:5 controlled vocabulary.

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
}

# Emit the self-review/SKILL.md vocabulary rejection diagnostic for
# Trivial-investigation. Default-deny — any token outside the four-entry
# allowlist fails, including 'local-only' (legitimate in
# Trivial-against-state, NOT here), 'internal-refactor', 'scoped-only',
# or arbitrary invented tokens.
emit_investigation_vocab_error() {
    local category="$1"
    cat >&2 <<EOF
BLOCK: $ARTIFACT_PATH '## Trivial-investigation declaration' block
Category: '$category' is not in the self-review/SKILL.md controlled
vocabulary for skipping investigation.

Allowed values (default-deny — any other token, including
'local-only', 'internal-refactor', 'scoped-only', and any invented
category, is rejected):

  single-line-fix   — a single-line change with no downstream effect
  doc-only          — pure documentation edit, no behavior implied
  config-only       — config change whose effect the author has already measured
  test-only         — test-only change (fixture/expectation, not implementation)

Reference: skills/self-review/SKILL.md '## Trivial-investigation
declaration' section and writing-rules:5 (Category-value discipline).

Note: 'local-only' IS a legitimate Category for
'## Trivial-against-state declaration' blocks (per
_authoring-against-state-rules.md), but not for
'## Trivial-investigation declaration'. If your intent was the
authoring-against-state claim, use that block instead. Otherwise,
if the work has any external contact — which any change to code
that runs, tests, config, or fixture behavior does — investigation
is required. Ship an investigate artifact and pre-mortem, and cite
them in Investigate-artifact: / Pre-mortem-artifact: fields per
self-review/SKILL.md.
EOF
}

check_block() {
    local header="$1"
    local kind="$2"  # "trivial-change" | "trivial-investigation" | "exemption"
    if ! grep -qE "^${header}" "$ARTIFACT_PATH"; then
        return 0  # block not present, nothing to check
    fi

    # External-shape-modeling never-trivial applies to any Trivial-* block.
    if [[ -n "$DIFF_ESM_MATCHES" && ( "$kind" == "trivial-change" || "$kind" == "trivial-investigation" ) ]]; then
        emit_esm_never_trivial "$header"
        return 2
    fi

    local content
    content=$(awk -v h="^${header}" '$0 ~ h {flag=1; next} /^## /{flag=0} flag' "$ARTIFACT_PATH")

    # Required fields per block kind.
    local required_fields=()
    if [[ "$kind" == "trivial-change" || "$kind" == "trivial-investigation" ]]; then
        required_fields=("Category:" "Cannot produce error:" "Evidence:" "Falsification:")
    else
        required_fields=("Reason:" "Evidence:" "Falsification:")
    fi

    local missing=()
    local field
    for field in "${required_fields[@]}"; do
        if ! echo "$content" | grep -qE "^[[:space:]]*${field}[[:space:]]+\S"; then
            missing+=("$field")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "BLOCK: $ARTIFACT_PATH '${header}' block missing fields:" >&2
        printf '  - %s\n' "${missing[@]}" >&2
        echo "" >&2
        case "$kind" in
            trivial-change)
                echo "  Per writing-rules:5: Trivial-change requires" >&2
                echo "  Category / Cannot produce error / Evidence / Falsification." >&2
                echo "  See _writing-rules-rules.md writing-rules:5 for the controlled" >&2
                echo "  vocabulary." >&2
                ;;
            trivial-investigation)
                echo "  Per self-review/SKILL.md: Trivial-investigation requires" >&2
                echo "  Category / Cannot produce error / Evidence / Falsification." >&2
                echo "  See skills/self-review/SKILL.md '## Trivial-investigation" >&2
                echo "  declaration' section for the four-token vocabulary." >&2
                ;;
            *)
                echo "  Per writing-rules:4: Reason / Evidence / Falsification" >&2
                echo "  required for every 'this doesn't apply' claim." >&2
                ;;
        esac
        return 2
    fi

    # Category validation for Trivial-change and Trivial-investigation blocks.
    if [[ "$kind" == "trivial-change" || "$kind" == "trivial-investigation" ]]; then
        local category
        category=$(echo "$content" | grep -E "^[[:space:]]*Category:[[:space:]]+" | head -1 | sed -E 's/^[[:space:]]*Category:[[:space:]]+//;s/[[:space:]]*$//')
        if [[ "$kind" == "trivial-change" ]]; then
            if ! echo "$category" | grep -qE "$TRIVIAL_CHANGE_VOCAB_RE"; then
                emit_change_vocab_error "$category"
                return 2
            fi
        else
            if ! echo "$category" | grep -qE "$TRIVIAL_INVESTIGATION_VOCAB_RE"; then
                emit_investigation_vocab_error "$category"
                return 2
            fi
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

# External-shape-modeling never-trivial for Trivial-against-state.
# Vocabulary/evidence validation for Trivial-against-state remains
# governed by _authoring-against-state-rules.md and is out of PR A
# scope; this block only enforces the never-trivial trigger.
if [[ -n "$DIFF_ESM_MATCHES" ]] && grep -qE '^## Trivial-against-state declaration' "$ARTIFACT_PATH"; then
    emit_esm_never_trivial "## Trivial-against-state declaration"
    exit 2
fi

# Check block kinds; exit on first failure.
check_block "## Trivial-change declaration" "trivial-change"
check_block "## Trivial-investigation declaration" "trivial-investigation"
check_block "## Exemption" "exemption"

exit 0
