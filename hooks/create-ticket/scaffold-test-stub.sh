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
#   Stub: tests/test_ac{ac_id}_{feature}.py
#   Probe: installed                (optional; when absent, hook probes automatically)
#   Ticket-id: 656
#   AC-id: 1
#   Feature: paginated_search
#
# The block spans consecutive non-blank lines starting at "Automation:";
# a blank line delimits blocks. Blocks INSIDE Markdown fenced code
# (triple-backtick or triple-tilde) are ignored per Round-1 finding 1-4.
#
# Behavior:
#   - Silent (exit 0, body unchanged) if no live Automation: block present.
#   - For each block:
#     * If Probe field absent, invoke scripts/probe/<tool>.sh <ticket-id>.
#     * Parse probe stdout as JSON (python3), extract .status and .ticket.
#     * Resolve template path from PROJECT.md testing.layers or fallback map.
#     * Substitute {ticket_id}, {ac_id}, {feature} into BOTH the Stub path
#       AND the template content (Round-1 finding 1-3).
#     * Validate substituted values against safe regex (Round-1 finding 2-2);
#       reject values with sed metacharacters or shell metacharacters.
#     * Reject Stub paths that resolve outside REPO_ROOT (Round-1 finding 2-1).
#     * Do not overwrite existing files.
#     * On probe blocked-on-infra, still render the stub AND record Blocked-by
#       using the probe's .ticket field (Round-1 finding 1-2).
#   - Append Generated stubs: block naming all rendered paths.
#   - Append Blocked-by: lines when the probe blocked.
#   - Emit modified body.
#
# Exit codes:
#   0  = success (with or without stubs rendered; silent if no blocks)
#   2  = usage error (missing required arg, unreadable file)
#   3  = internal error (template not found, sed failure, path escapes REPO_ROOT)

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
            sed -n '2,40p' "$0"
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
# Canonicalize REPO_ROOT for containment checks (Round-1 finding 2-1).
REPO_ROOT_ABS=$(cd "$REPO_ROOT" 2>/dev/null && pwd -P || echo "$REPO_ROOT")

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

# Strip fenced markdown code blocks from the body before parsing
# (Round-1 finding 1-4). Preserve non-fence content verbatim so line
# numbers do not shift for the output (we still emit the ORIGINAL body,
# just parse from the stripped view).
STRIPPED_BODY=$(python3 -c '
import sys, re
src = sys.stdin.read()
# Match ```...``` and ~~~...~~~ fences (multi-line, non-greedy).
pattern = re.compile(r"^(?:```|~~~).*?^(?:```|~~~)\s*$", re.MULTILINE | re.DOTALL)
sys.stdout.write(pattern.sub("", src))
' <<< "$BODY")

# Silent-noop: if body (after fence strip) has no Automation: block, echo
# the original body unchanged and exit.
if ! grep -q '^Automation:' <<< "$STRIPPED_BODY"; then
    if [[ -n "$OUT_FILE" ]]; then
        printf '%s\n' "$BODY" > "$OUT_FILE"
    else
        printf '%s\n' "$BODY"
    fi
    exit 0
fi

# Extract a single field from a multi-line block. Tolerant of absence
# (returns empty string, exit 0). Round-1 finding 1-1.
_field() {
    local block="$1"
    local field="$2"
    { echo "$block" | grep -E "^${field}:[[:space:]]" | head -1 | sed -E "s/^${field}:[[:space:]]*//"; } || true
}

# Validate a substitution value: only alphanumeric, underscore, dash, dot.
# Rejects sed metacharacters (& | \) and shell metacharacters. Round-1 finding 2-2.
_safe_value() {
    local val="$1"
    [[ "$val" =~ ^[A-Za-z0-9._-]+$ ]]
}

# Substitute {ticket_id}, {ac_id}, {feature} into any string.
# Uses bash parameter expansion (not sed) so metacharacters are literal.
_substitute() {
    local s="$1"
    s="${s//\{ticket_id\}/$SUB_TICKET_ID}"
    s="${s//\{ac_id\}/$SUB_AC_ID}"
    s="${s//\{feature\}/$SUB_FEATURE}"
    printf '%s' "$s"
}

# Split stripped body into Automation blocks.
TMPDIR=$(mktemp -d -t scaffold-stub.XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT
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
' <<< "$STRIPPED_BODY"

# Resolve template path for a tool by scanning PROJECT.md testing.layers.
# Falls back to conventional path in templates/tests/.
_template_for_tool() {
    local tool="$1"
    local project_md="$REPO_ROOT_ABS/PROJECT.md"
    local result=""
    if [[ -f "$project_md" ]]; then
        result=$(python3 - "$project_md" "$tool" <<'PYEOF' 2>/dev/null || true
import sys, re
proj = open(sys.argv[1]).read()
want = sys.argv[2]
lines = proj.splitlines()
i = 0
while i < len(lines):
    line = lines[i]
    if re.match(r'^\s*-\s+name:', line):
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
)
    fi
    if [[ -z "$result" ]]; then
        case "$tool" in
            pytest) result="templates/tests/pytest-unit.py.tmpl" ;;
            playwright) result="templates/tests/playwright-e2e.spec.ts.tmpl" ;;
            vitest) result="templates/tests/vitest-component.spec.ts.tmpl" ;;
            schemathesis) result="templates/tests/schemathesis-contract.yaml.tmpl" ;;
            great-expectations|great_expectations) result="templates/tests/great-expectations-suite.json.tmpl" ;;
            k6) result="templates/tests/k6-scenario.js.tmpl" ;;
            *) result="" ;;
        esac
    fi
    printf '%s' "$result"
}

# Parse a probe's JSON stdout, extract .status and .ticket.
# Emits two lines: STATUS\n TICKET (either may be empty).
_parse_probe_json() {
    local json="$1"
    PROBE_JSON="$json" python3 -c '
import os, json
raw = os.environ.get("PROBE_JSON", "")
try:
    obj = json.loads(raw)
    print(obj.get("status", ""))
    print(obj.get("ticket", ""))
except Exception:
    print("")
    print("")
'
}

GENERATED=()
BLOCKED_BY=()

CURRENT_BLOCK=""
while IFS= read -r block_line; do
    if [[ "$block_line" == "---END-BLOCK---" ]]; then
        block="$CURRENT_BLOCK"
        CURRENT_BLOCK=""
        [[ -z "$block" ]] && continue

        tool=$(_field "$block" "Tool")
        stub_raw=$(_field "$block" "Stub")
        probe=$(_field "$block" "Probe")
        probe_ticket=""
        ticket_id=$(_field "$block" "Ticket-id")
        ac_id=$(_field "$block" "AC-id")
        feature=$(_field "$block" "Feature")

        if [[ -z "$tool" || -z "$stub_raw" ]]; then
            >&2 echo "scaffold-test-stub: skipping block (missing Tool or Stub)"
            continue
        fi

        # Validate substitution values before use (Round-1 finding 2-2).
        # ticket_id / ac_id / feature must be safe.
        for v in "$ticket_id" "$ac_id" "$feature"; do
            if [[ -n "$v" ]] && ! _safe_value "$v"; then
                >&2 echo "scaffold-test-stub: unsafe substitution value '$v'; alphanumeric + . _ - only. Skipping block."
                continue 2
            fi
        done

        # If Probe field absent, invoke the probe script. Round-1 finding 1-1.
        if [[ -z "$probe" ]]; then
            probe_script="$REPO_ROOT_ABS/scripts/probe/${tool}.sh"
            if [[ -x "$probe_script" ]]; then
                # Capture stdout only; probe stderr is diagnostic.
                probe_json=$("$probe_script" "$ticket_id" 2>/dev/null || true)
                if [[ -n "$probe_json" ]]; then
                    parsed=$(_parse_probe_json "$probe_json")
                    probe=$(echo "$parsed" | sed -n '1p')
                    probe_ticket=$(echo "$parsed" | sed -n '2p')
                fi
                if [[ -z "$probe" ]]; then
                    probe="unknown"
                fi
            else
                probe="probe-missing"
            fi
        elif [[ "$probe" == blocked-on-infra:* ]]; then
            # Legacy hand-shaped Probe: field carries the ticket inline.
            probe_ticket="${probe#blocked-on-infra:}"
            probe="blocked-on-infra"
        fi

        if [[ "$probe" == "blocked-on-infra" && -n "$probe_ticket" ]]; then
            BLOCKED_BY+=("$probe_ticket")
        fi

        # Resolve template.
        tmpl=$(_template_for_tool "$tool")
        if [[ -z "$tmpl" ]]; then
            >&2 echo "scaffold-test-stub: no template resolvable for tool=$tool; skipping"
            continue
        fi
        tmpl_path="$REPO_ROOT_ABS/$tmpl"
        if [[ ! -f "$tmpl_path" ]]; then
            >&2 echo "scaffold-test-stub: template not found: $tmpl_path"
            continue
        fi

        # Substitute placeholders into BOTH the Stub path AND the template.
        # Round-1 finding 1-3.
        SUB_TICKET_ID="$ticket_id"
        SUB_AC_ID="$ac_id"
        SUB_FEATURE="$feature"
        stub=$(_substitute "$stub_raw")

        # Path-containment check. Round-1 finding 2-1.
        stub_path_raw="$REPO_ROOT_ABS/$stub"
        stub_dir=$(dirname "$stub_path_raw")
        mkdir -p "$stub_dir"
        stub_dir_abs=$(cd "$stub_dir" && pwd -P)
        stub_path_abs="$stub_dir_abs/$(basename "$stub_path_raw")"
        case "$stub_path_abs" in
            "$REPO_ROOT_ABS"/*) ;;  # inside root, ok
            *)
                >&2 echo "scaffold-test-stub: refusing to write outside repo root: $stub_path_abs"
                continue
                ;;
        esac

        if [[ -e "$stub_path_abs" ]]; then
            >&2 echo "scaffold-test-stub: stub already exists, not overwriting: $stub_path_abs"
            GENERATED+=("$stub (exists)")
            continue
        fi

        # Render template content with substitution. Uses bash parameter
        # expansion (not sed), so metacharacters in values are literal.
        tmpl_content=$(cat "$tmpl_path")
        rendered=$(_substitute "$tmpl_content")
        printf '%s' "$rendered" > "$stub_path_abs"

        GENERATED+=("$stub")
    else
        if [[ -z "${CURRENT_BLOCK}" ]]; then
            CURRENT_BLOCK="$block_line"
        else
            CURRENT_BLOCK="${CURRENT_BLOCK}
${block_line}"
        fi
    fi
done < "$BLOCKS_FILE"

# Build appended footer.
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
