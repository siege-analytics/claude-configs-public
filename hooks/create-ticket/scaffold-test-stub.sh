#!/usr/bin/env bash
# hooks/create-ticket/scaffold-test-stub.sh
#
# Reads a ticket body containing one or more Automation: blocks,
# renders per-AC stub files from templates/tests/, and emits a modified
# body appended with a Generated stubs: list and (when applicable)
# Blocked-by: lines from tool-availability probes.
#
# Part of epic #655 (falsifiable acceptance criteria + auto-gen test stubs).
#
# Usage:
#   scaffold-test-stub.sh --body-file <path> [--out-file <path>] [--repo-root <path>]
#   scaffold-test-stub.sh --stdin              (read body from stdin, write to stdout)
#
# Automation block shape (from ticket-decomposition #658, create-ticket #657):
#   Automation:
#   Tool: pytest
#   Stub: tests/test_paginated_search.py
#   Probe: installed
#   Ticket-id: 656
#   AC-id: 1
#   Feature: paginated_search
#
# The block may span multiple lines; blank line delimits blocks.
#
# Behavior:
#   - Silent (exit 0, body unchanged) if no Automation: block present.
#   - For each block:
#     * If Probe field absent, invoke scripts/probe/<tool>.sh <ticket-id>.
#     * Read layer's automation_template from PROJECT.md testing.layers.
#     * Substitute {ticket_id}, {ac_id}, {feature} via sed into Stub path.
#     * Do not overwrite existing files; warn and skip if target exists.
#     * On probe blocked-on-infra, still render the stub AND record Blocked-by.
#   - Append Generated stubs: block naming all rendered paths.
#   - Emit modified body.
#
# Exit codes:
#   0  = success (with or without stubs rendered; silent if no blocks)
#   2  = usage error (missing required arg, unreadable file)
#   3  = internal error (template not found, sed failure)

set -euo pipefail

BODY_FILE=""
OUT_FILE=""
REPO_ROOT=""
USE_STDIN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --body-file) BODY_FILE="$2"; shift 2 ;;
        --out-file)  OUT_FILE="$2"; shift 2 ;;
        --repo-root) REPO_ROOT="$2"; shift 2 ;;
        --stdin)     USE_STDIN=1; shift ;;
        -h|--help)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *)
            >&2 echo "scaffold-test-stub: unknown arg: $1"
            exit 2
            ;;
    esac
done

if [[ -z "$REPO_ROOT" ]]; then
    REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
fi

if [[ $USE_STDIN -eq 1 ]]; then
    BODY=$(cat)
elif [[ -n "$BODY_FILE" ]]; then
    if [[ ! -f "$BODY_FILE" ]]; then
        >&2 echo "scaffold-test-stub: body file not found: $BODY_FILE"
        exit 2
    fi
    BODY=$(cat "$BODY_FILE")
else
    >&2 echo "scaffold-test-stub: pass --body-file or --stdin"
    exit 2
fi

# Silent-noop: if body has no Automation: block, echo the body unchanged and exit.
if ! echo "$BODY" | grep -q '^Automation:'; then
    if [[ -n "$OUT_FILE" ]]; then
        printf '%s\n' "$BODY" > "$OUT_FILE"
    else
        printf '%s\n' "$BODY"
    fi
    exit 0
fi

# Parse Automation blocks. A block starts at "^Automation:" and continues until
# a blank line or another Automation: line or EOF.
TMPDIR=$(mktemp -d -t scaffold-stub.XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

# Split body into blocks.
BLOCKS_FILE="$TMPDIR/blocks.txt"
awk '
    BEGIN { in_block = 0; block = "" }
    /^Automation:[[:space:]]*$/ {
        if (in_block && block != "") {
            print block > "'"$BLOCKS_FILE"'"
            print "---END-BLOCK---" > "'"$BLOCKS_FILE"'"
        }
        in_block = 1
        block = $0
        next
    }
    in_block && /^[[:space:]]*$/ {
        if (block != "") {
            print block > "'"$BLOCKS_FILE"'"
            print "---END-BLOCK---" > "'"$BLOCKS_FILE"'"
        }
        in_block = 0
        block = ""
        next
    }
    in_block {
        block = block "\n" $0
        next
    }
    END {
        if (in_block && block != "") {
            print block > "'"$BLOCKS_FILE"'"
            print "---END-BLOCK---" > "'"$BLOCKS_FILE"'"
        }
    }
' <<< "$BODY"

# Extract a single field value from a block.
_field() {
    local block="$1"
    local field="$2"
    echo "$block" | grep -E "^${field}:[[:space:]]" | head -1 | sed -E "s/^${field}:[[:space:]]*//"
}

# Resolve template path for a tool by scanning PROJECT.md testing.layers.
_template_for_tool() {
    local tool="$1"
    local project_md="$REPO_ROOT/PROJECT.md"
    if [[ ! -f "$project_md" ]]; then
        return 1
    fi
    # Minimal YAML scan: look for a layer whose assertion_tools list contains
    # the tool, and grab its automation_template. Not a full YAML parser.
    python3 - "$project_md" "$tool" <<'PYEOF' 2>/dev/null || true
import sys, re
proj = open(sys.argv[1]).read()
want = sys.argv[2]
lines = proj.splitlines()
# Naive scan: find each layer block, extract assertion_tools + automation_template
i = 0
while i < len(lines):
    line = lines[i]
    if re.match(r'^\s*-\s+name:', line):
        # Read subsequent indented lines
        indent = len(line) - len(line.lstrip())
        j = i + 1
        tools = ""
        tmpl = ""
        while j < len(lines):
            l = lines[j]
            if l.strip() == "":
                j += 1; continue
            l_indent = len(l) - len(l.lstrip())
            if l_indent <= indent and re.match(r'^\s*-\s+name:', l) is None and l.strip():
                # Same-or-lower indent that isn't another layer field ends this layer
                if l_indent <= indent:
                    break
            m = re.match(r'^\s+assertion_tools:\s*\[([^\]]*)\]', l)
            if m:
                tools = m.group(1)
            m = re.match(r'^\s+automation_template:\s*(\S+)', l)
            if m:
                tmpl = m.group(1)
            j += 1
        if want in [t.strip() for t in tools.split(",") if t.strip()] and tmpl:
            print(tmpl)
            sys.exit(0)
        i = j
        continue
    i += 1
sys.exit(1)
PYEOF
}

GENERATED=()
BLOCKED_BY=()

while IFS= read -r block_line; do
    # Accumulate block until END-BLOCK sentinel.
    if [[ "$block_line" == "---END-BLOCK---" ]]; then
        block="$CURRENT_BLOCK"
        CURRENT_BLOCK=""
        [[ -z "$block" ]] && continue

        tool=$(_field "$block" "Tool")
        stub=$(_field "$block" "Stub")
        probe=$(_field "$block" "Probe")
        ticket_id=$(_field "$block" "Ticket-id")
        ac_id=$(_field "$block" "AC-id")
        feature=$(_field "$block" "Feature")

        if [[ -z "$tool" || -z "$stub" ]]; then
            >&2 echo "scaffold-test-stub: skipping block (missing Tool or Stub): $block"
            continue
        fi

        # If probe absent, invoke it.
        if [[ -z "$probe" ]]; then
            probe_script="$REPO_ROOT/scripts/probe/${tool}.sh"
            if [[ -x "$probe_script" ]]; then
                probe_json=$("$probe_script" "$ticket_id" 2>/dev/null || true)
                probe=$(echo "$probe_json" | grep -oE '"status":[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"([^"]+)"$/\1/')
                if [[ -z "$probe" ]]; then
                    probe="unknown"
                fi
            else
                probe="probe-missing"
            fi
        fi

        # If probe is blocked-on-infra, extract infra ticket.
        if [[ "$probe" == blocked-on-infra* ]]; then
            infra=$(echo "$probe" | sed -E 's/^blocked-on-infra:?//')
            if [[ -n "$infra" ]]; then
                BLOCKED_BY+=("$infra")
            fi
        fi

        # Resolve template.
        tmpl=$(_template_for_tool "$tool" || true)
        if [[ -z "$tmpl" ]]; then
            # Fallback: guess conventional path in templates/tests/.
            case "$tool" in
                pytest) tmpl="templates/tests/pytest-unit.py.tmpl" ;;
                playwright) tmpl="templates/tests/playwright-e2e.spec.ts.tmpl" ;;
                vitest) tmpl="templates/tests/vitest-component.spec.ts.tmpl" ;;
                schemathesis) tmpl="templates/tests/schemathesis-contract.yaml.tmpl" ;;
                great-expectations|great_expectations) tmpl="templates/tests/great-expectations-suite.json.tmpl" ;;
                k6) tmpl="templates/tests/k6-scenario.js.tmpl" ;;
                *) tmpl="" ;;
            esac
        fi

        if [[ -z "$tmpl" ]]; then
            >&2 echo "scaffold-test-stub: no template resolvable for tool=$tool; skipping"
            continue
        fi

        tmpl_path="$REPO_ROOT/$tmpl"
        if [[ ! -f "$tmpl_path" ]]; then
            >&2 echo "scaffold-test-stub: template not found: $tmpl_path"
            continue
        fi

        stub_path="$REPO_ROOT/$stub"
        stub_dir=$(dirname "$stub_path")
        mkdir -p "$stub_dir"

        if [[ -e "$stub_path" ]]; then
            >&2 echo "scaffold-test-stub: stub already exists, not overwriting: $stub_path"
            GENERATED+=("$stub (exists)")
            continue
        fi

        sed \
            -e "s|{ticket_id}|${ticket_id}|g" \
            -e "s|{ac_id}|${ac_id}|g" \
            -e "s|{feature}|${feature}|g" \
            "$tmpl_path" > "$stub_path"

        GENERATED+=("$stub")
    else
        if [[ -z "${CURRENT_BLOCK:-}" ]]; then
            CURRENT_BLOCK="$block_line"
        else
            CURRENT_BLOCK="${CURRENT_BLOCK}
${block_line}"
        fi
    fi
done < "$BLOCKS_FILE"

# Build appended block.
APPEND=""
if [[ ${#GENERATED[@]} -gt 0 ]]; then
    APPEND=$'\n\nGenerated stubs:'
    for path in "${GENERATED[@]}"; do
        APPEND="${APPEND}
- ${path}"
    done
fi
if [[ ${#BLOCKED_BY[@]} -gt 0 ]]; then
    APPEND="${APPEND}
Blocked-by (from tool-availability probe):"
    for t in "${BLOCKED_BY[@]}"; do
        APPEND="${APPEND}
- ${t}"
    done
fi

OUT_BODY="${BODY}${APPEND}"

if [[ -n "$OUT_FILE" ]]; then
    printf '%s\n' "$OUT_BODY" > "$OUT_FILE"
else
    printf '%s\n' "$OUT_BODY"
fi
exit 0
