#!/usr/bin/env bash
# hooks/create-ticket/scaffold-test-stub.sh
#
# Reads a ticket body containing one or more Automation: blocks,
# renders per-AC stub files from templates/tests/, and emits a modified
# body appended with a Generated stubs / Skipped / Blocked-by summary.
#
# Part of epic #655 (falsifiable acceptance criteria + auto-gen test stubs).
#
# Usage:
#   scaffold-test-stub.sh --body-file <path> [--out-file <path>] [--repo-root <path>]
#   scaffold-test-stub.sh --stdin              (read body from stdin, write to stdout)
#
# Automation block shape (from ticket-decomposition #658, create-ticket #657):
#   Automation:
#   Tool: pytest                  (required; from KNOWN_TOOLS allowlist)
#   Layer: unit                   (optional; disambiguates template when a tool ships multiple)
#   Stub: tests/test_ac{ac_id}_{feature}.py
#   Probe: installed              (optional; when absent, hook probes automatically)
#   Ticket-id: 656
#   AC-id: 1
#   Feature: paginated_search
#
# Blocks INSIDE Markdown fenced code (```...``` or ~~~...~~~) are ignored.
# Substitution values must match ^[A-Za-z0-9._-]+$; unsafe values skip.
# Tool names are normalized (underscore -> dash) and matched against
# KNOWN_TOOLS; unknown tools skip.
# Stub paths are canonicalized and rejected if they resolve outside REPO_ROOT.
#
# Round-1 GPT-5.5 review (PR #672): findings 1-1, 1-2, 1-3, 1-4, 2-1, 2-2, 9-1.
# Round-2 Opus 5 review (PR #672): findings P0-4, P1-3, P1-4, P1-5, P1-6, latent-tool-traversal.
# Deferred to follow-up: P1-2, P1-7, P1-8, all P2 (see PR #672 discussion).
#
# Exit codes:
#   0  = success (with or without stubs rendered; silent if no blocks)
#   2  = usage error
#   3  = internal error (mktemp/python3/awk failure; see #675 P1-7)

set -euo pipefail

BODY_FILE=""
OUT_FILE=""
REPO_ROOT=""
USE_STDIN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --body-file)
            if [[ $# -lt 2 || -z "${2:-}" ]]; then
                >&2 echo "scaffold-test-stub: --body-file requires a value"
                exit 2
            fi
            BODY_FILE="$2"; shift 2 ;;
        --out-file)
            if [[ $# -lt 2 || -z "${2:-}" ]]; then
                >&2 echo "scaffold-test-stub: --out-file requires a value"
                exit 2
            fi
            OUT_FILE="$2"; shift 2 ;;
        --repo-root)
            if [[ $# -lt 2 || -z "${2:-}" ]]; then
                >&2 echo "scaffold-test-stub: --repo-root requires a value"
                exit 2
            fi
            REPO_ROOT="$2"; shift 2 ;;
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

# Strip fenced markdown code blocks before parsing (Round-1 finding 1-4).
STRIPPED_BODY=$(python3 -c '
import sys, re
src = sys.stdin.read()
pattern = re.compile(r"^(?:```|~~~).*?^(?:```|~~~)\s*$", re.MULTILINE | re.DOTALL)
sys.stdout.write(pattern.sub("", src))
' <<< "$BODY")

# Silent-noop if the stripped body has no live Automation: block.
#
# #675 P1-2 (guard/splitter regex mismatch): the guard used to check
# `^Automation:` (unanchored) but the awk splitter below requires
# `^Automation:[[:space:]]*$` (bare Automation: with optional trailing space).
# A body containing `Automation: pytest` (inline value on the same line)
# passed the guard, produced no blocks, and the hook silently emitted the
# body unchanged. That was indistinguishable from a body with no Automation
# section at all. Fix: use the same anchor as the splitter, and if the guard
# rejects a line but a `^Automation:` occurrence exists elsewhere in the
# body, emit a specific stderr diagnostic naming the offending line so an
# operator can distinguish "no Automation blocks" from "malformed
# Automation blocks".
if ! grep -qE '^Automation:[[:space:]]*$' <<< "$STRIPPED_BODY"; then
    # Look for near-miss shapes so operators writing `Automation: pytest`
    # (inline) get a diagnostic instead of silent no-op.
    NEAR_MISS=$(grep -E '^Automation:.*' <<< "$STRIPPED_BODY" | head -1 || true)
    if [[ -n "$NEAR_MISS" ]]; then
        echo "scaffold-test-stub: Automation: line found but does not match bare-anchor splitter (${NEAR_MISS}); Automation: must be on its own line, followed by fields" >&2
    fi
    if [[ -n "$OUT_FILE" ]]; then
        printf '%s\n' "$BODY" > "$OUT_FILE"
    else
        printf '%s\n' "$BODY"
    fi
    exit 0
fi

# Known-tool allowlist. Round-2 latent finding: constrains $tool so the
# script path can never contain arbitrary segments from the ticket body.
KNOWN_TOOLS="pytest playwright vitest schemathesis great-expectations k6"

_normalize_tool() {
    # underscore -> dash; matches KNOWN_TOOLS canonical form. Round-2 P1-4.
    local t="$1"
    printf '%s' "${t//_/-}"
}

_is_known_tool() {
    local t="$1"
    local k
    for k in $KNOWN_TOOLS; do
        [[ "$k" == "$t" ]] && return 0
    done
    return 1
}

# Extract a single field. Tolerant of absence (returns empty string, exit 0).
# Round-1 finding 1-1.
_field() {
    # #675 P2-3: accept both `Field: value` and `Field:value` (no space).
    # The colon-space requirement rejected legit forms and made the failure
    # look like "field missing" instead of "field format tolerant of both."
    local block="$1"
    local field="$2"
    { echo "$block" | grep -E "^${field}:" | head -1 | sed -E "s/^${field}:[[:space:]]*//"; } || true
}

_safe_value() {
    local val="$1"
    [[ "$val" =~ ^[A-Za-z0-9._-]+$ ]]
}

_substitute() {
    local s="$1"
    s="${s//\{ticket_id\}/$SUB_TICKET_ID}"
    s="${s//\{ac_id\}/$SUB_AC_ID}"
    s="${s//\{feature\}/$SUB_FEATURE}"
    printf '%s' "$s"
}

# Renamed from TMPDIR to SCRATCH_DIR to avoid clobbering the exported
# TMPDIR that macOS launchd and CI runners set. Round-2 P1-5.
# #675 P1-7: exit 3 on internal-tool failure (mktemp / awk / python3).
# Header documents exit 3 as internal-error; before this change nothing
# emitted it. Explicit failure surface is better than a partially-scaffolded
# ticket body with no diagnostic.
if ! SCRATCH_DIR=$(mktemp -d -t scaffold-stub.XXXXXX 2>&1); then
    echo "scaffold-test-stub: mktemp failed: $SCRATCH_DIR" >&2
    exit 3
fi
trap 'rm -rf "$SCRATCH_DIR"' EXIT
BLOCKS_FILE="$SCRATCH_DIR/blocks.txt"
: > "$BLOCKS_FILE"  # ensure it exists even if awk finds no matches

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

# Template lookup: pure fallback map (Round-2 P1-3 deleted the untestable
# PROJECT.md YAML scanner). Layer refines the choice per tool.
_template_for_tool() {
    local tool="$1"
    local layer="${2:-}"
    case "$tool" in
        pytest)
            if [[ "$layer" == "integration" ]]; then
                printf 'templates/tests/pytest-integration.py.tmpl'
            else
                printf 'templates/tests/pytest-unit.py.tmpl'
            fi
            ;;
        playwright)   printf 'templates/tests/playwright-e2e.spec.ts.tmpl' ;;
        vitest)       printf 'templates/tests/vitest-component.spec.ts.tmpl' ;;
        schemathesis) printf 'templates/tests/schemathesis-contract.yaml.tmpl' ;;
        great-expectations) printf 'templates/tests/great-expectations-suite.json.tmpl' ;;
        k6)           printf 'templates/tests/k6-scenario.js.tmpl' ;;
        *) printf '' ;;
    esac
}

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
SKIPPED=()      # Round-2 P1-6: surface degraded outcomes in the ticket body.
BLOCKED_BY=()

CURRENT_BLOCK=""
while IFS= read -r block_line; do
    if [[ "$block_line" == "---END-BLOCK---" ]]; then
        block="$CURRENT_BLOCK"
        CURRENT_BLOCK=""
        [[ -z "$block" ]] && continue

        raw_tool=$(_field "$block" "Tool")
        layer=$(_field "$block" "Layer")
        stub_raw=$(_field "$block" "Stub")
        probe=$(_field "$block" "Probe")
        probe_ticket=""
        ticket_id=$(_field "$block" "Ticket-id")
        ac_id=$(_field "$block" "AC-id")
        feature=$(_field "$block" "Feature")

        if [[ -z "$raw_tool" || -z "$stub_raw" ]]; then
            SKIPPED+=("(missing Tool or Stub)")
            continue
        fi

        # Tool normalization + allowlist. Round-2 P1-4 + latent-traversal.
        tool=$(_normalize_tool "$raw_tool")
        if ! _is_known_tool "$tool"; then
            SKIPPED+=("$raw_tool (unknown tool; allowlist: $KNOWN_TOOLS)")
            continue
        fi

        # Validate substitution values before use (Round-1 finding 2-2).
        unsafe=""
        for v in "$ticket_id" "$ac_id" "$feature"; do
            if [[ -n "$v" ]] && ! _safe_value "$v"; then
                unsafe="$v"
                break
            fi
        done
        if [[ -n "$unsafe" ]]; then
            >&2 echo "scaffold-test-stub: unsafe substitution value '$unsafe'; alphanumeric + . _ - only. Skipping block."
            SKIPPED+=("$stub_raw (unsafe field value: $unsafe)")
            continue
        fi

        # Optional layer must also be safe.
        if [[ -n "$layer" ]] && ! _safe_value "$layer"; then
            SKIPPED+=("$stub_raw (unsafe Layer: $layer)")
            continue
        fi

        # Auto-probe branch. Round-1 finding 1-1 (unlocked by _field fix).
        if [[ -z "$probe" ]]; then
            probe_script="$REPO_ROOT_ABS/scripts/probe/${tool}.sh"
            if [[ -x "$probe_script" ]]; then
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
            probe_ticket="${probe#blocked-on-infra:}"
            probe="blocked-on-infra"
        fi

        if [[ "$probe" == "blocked-on-infra" && -n "$probe_ticket" ]]; then
            BLOCKED_BY+=("$probe_ticket")
        fi

        # Resolve template (fallback-only now; Round-2 P1-3).
        tmpl=$(_template_for_tool "$tool" "$layer")
        if [[ -z "$tmpl" ]]; then
            # Should be unreachable given the allowlist above, but keep safe.
            SKIPPED+=("$stub_raw (no template for tool=$tool layer=$layer)")
            continue
        fi
        tmpl_path="$REPO_ROOT_ABS/$tmpl"
        if [[ ! -f "$tmpl_path" ]]; then
            SKIPPED+=("$stub_raw (template file missing: $tmpl)")
            continue
        fi

        # Substitute placeholders into both Stub path and template content.
        SUB_TICKET_ID="$ticket_id"
        SUB_AC_ID="$ac_id"
        SUB_FEATURE="$feature"
        stub=$(_substitute "$stub_raw")

        # Path-containment. Round-1 finding 2-1.
        stub_path_raw="$REPO_ROOT_ABS/$stub"
        stub_dir=$(dirname "$stub_path_raw")
        mkdir -p "$stub_dir"
        stub_dir_abs=$(cd "$stub_dir" && pwd -P)
        stub_path_abs="$stub_dir_abs/$(basename "$stub_path_raw")"
        case "$stub_path_abs" in
            "$REPO_ROOT_ABS"/*) ;;
            *)
                >&2 echo "scaffold-test-stub: refusing to write outside repo root: $stub_path_abs"
                SKIPPED+=("$stub (path escapes repo root)")
                continue
                ;;
        esac

        if [[ -e "$stub_path_abs" ]]; then
            SKIPPED+=("$stub (already exists; not overwriting)")
            continue
        fi

        # Atomic write: render to temp file in the same directory, mv on success.
        # Round-2 P0-4 (zero-byte-stub-locks-AC) + P1-8 (TOCTOU).
        tmpl_content=$(cat "$tmpl_path")
        rendered=$(_substitute "$tmpl_content")
        tmp_out=$(mktemp "$stub_dir_abs/.scaffold-stub-XXXXXX")
        printf '%s' "$rendered" > "$tmp_out"
        if [[ ! -s "$tmp_out" && -n "$rendered" ]]; then
            rm -f "$tmp_out"
            SKIPPED+=("$stub (render produced empty file)")
            continue
        fi
        if ! mv -n "$tmp_out" "$stub_path_abs" 2>/dev/null; then
            rm -f "$tmp_out"
            SKIPPED+=("$stub (concurrent write won; file already exists)")
            continue
        fi

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

# Build appended footer. Each section is preceded by its own blank-line
# separator so the sections don't glue together (Round-2 P2-4).
APPEND=""
if [[ ${#GENERATED[@]} -gt 0 ]]; then
    APPEND=$'\n\nGenerated stubs:'
    for path in "${GENERATED[@]}"; do
        APPEND="${APPEND}
- ${path}"
    done
fi
if [[ ${#SKIPPED[@]} -gt 0 ]]; then
    APPEND="${APPEND}"$'\n\nSkipped:'
    for note in "${SKIPPED[@]}"; do
        APPEND="${APPEND}
- ${note}"
    done
fi
if [[ ${#BLOCKED_BY[@]} -gt 0 ]]; then
    APPEND="${APPEND}"$'\n\nBlocked-by (from tool-availability probe):'
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
