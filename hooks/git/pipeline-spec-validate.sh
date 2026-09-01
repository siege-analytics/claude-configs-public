#!/bin/bash
# Hook: pipeline-spec-validate
# Enforces: target-pipeline-imports skill (validation rules section)
# Trigger: PreToolUse on Bash(git commit *)
#
# Validates pipeline spec YAML files staged for commit.
# Checks: required keys, storage prefix, catalog consistency,
# no wildcard utility imports (unless DEPRECATED).

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Only check git commit commands
if ! echo "$COMMAND" | grep -qE '^git commit\b'; then
    exit 0
fi

# Find the git root
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z "$GIT_ROOT" ]]; then
    exit 0
fi

# Only apply to the rundeck repo
if [[ "$(basename "$GIT_ROOT")" != "rundeck" ]]; then
    exit 0
fi

# Get staged pipeline spec files
STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '^pipelines/[^/]+/pipeline-.*\.yml$' || true)

if [[ -z "$STAGED" ]]; then
    exit 0
fi

ERRORS=""

for spec_file in $STAGED; do
    full_path="$GIT_ROOT/$spec_file"
    if [[ ! -f "$full_path" ]]; then
        continue
    fi

    file_errors=""

    # Extract catalog directory from path
    dir_catalog=$(echo "$spec_file" | sed 's|pipelines/||; s|/pipeline-.*||')

    # Check required top-level keys exist (simple grep — these are always at column 0)
    for key in name catalog storage configuration libraries; do
        if ! grep -qE "^${key}:" "$full_path"; then
            file_errors="${file_errors}    - Missing required key: ${key}\n"
        fi
    done

    # If missing required keys, skip further checks
    if [[ -n "$file_errors" ]]; then
        ERRORS="${ERRORS}\n  ${spec_file}:\n${file_errors}"
        continue
    fi

    # Extract values (top-level keys, no leading whitespace)
    yaml_catalog=$(grep -E '^catalog:' "$full_path" | head -1 | sed 's/^catalog: *//')
    yaml_storage=$(grep -E '^storage:' "$full_path" | head -1 | sed 's/^storage: *//')
    default_catalog=$(grep -E '^\s+spark\.sql\.defaultCatalog:' "$full_path" | head -1 | sed 's/.*spark\.sql\.defaultCatalog: *//')

    # Check storage prefix
    if [[ ! "$yaml_storage" =~ ^s3a:// ]]; then
        file_errors="${file_errors}    - storage must start with s3a://, got: ${yaml_storage}\n"
    fi

    # Check catalog matches directory
    if [[ "$yaml_catalog" != "$dir_catalog" ]]; then
        file_errors="${file_errors}    - catalog \"${yaml_catalog}\" != directory \"${dir_catalog}\"\n"
    fi

    # Check defaultCatalog matches catalog
    if [[ -n "$default_catalog" && "$default_catalog" != "$yaml_catalog" ]]; then
        file_errors="${file_errors}    - spark.sql.defaultCatalog \"${default_catalog}\" != catalog \"${yaml_catalog}\"\n"
    fi

    # Check for wildcard utility imports (unless DEPRECATED)
    if ! grep -q 'DEPRECATED' "$full_path"; then
        if grep -qE 'include:.*\.\./utilities/\*\*' "$full_path"; then
            file_errors="${file_errors}    - Wildcard utility import ../utilities/** found (use targeted imports per #467)\n"
        fi
    fi

    if [[ -n "$file_errors" ]]; then
        ERRORS="${ERRORS}\n  ${spec_file}:\n${file_errors}"
    fi
done

if [[ -n "$ERRORS" ]]; then
    cat >&2 <<EOF
BLOCKED: Pipeline spec validation failed.

The following pipeline spec files have issues:
$(echo -e "$ERRORS")
Fix the issues above before committing. See the target-pipeline-imports
skill for the full validation rules and fix process.

Tracking issue: electinfo/rundeck#467
EOF
    exit 2
fi

exit 0
