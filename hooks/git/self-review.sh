#!/bin/bash
# Publication review: short Tier A record, compact Tier B/C outcome evidence,
# and one actual independent review for high-risk publication. Task scope and
# action-specific holds remain owned by their separate admission guards.
set -uo pipefail
source "$(f="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/hook-path.sh"; [[ -f "$f" ]] && printf '%s' "$f" || printf /dev/null)"

INPUT=$(cat)
# Fast skip (#1083): exit before starting python3 when the tool payload's
# command cannot match this hook's trigger. Only taken when tool_input's first
# key is a non-empty "command" (an empty or missing command keeps the git-push
# fallback) and the command uses no JSON escape other than \n \t \r \" \\ \/
# (\u, \f, \b could hide letters or whitespace). \n \t \r become spaces, so an
# escaped newline before the trigger still counts as a boundary. Git-hook
# invocations (refs on stdin, no JSON) take the full path.
_FAST_CMDS=$(printf '%s' "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"(\\.|[^"\\])*"' 2>/dev/null || true)
# A long command takes the full path (#1098): bash substitutions slow down
# superlinearly under a UTF-8 locale, and past the hook timeout a skip check
# would let the command through. 16 KiB keeps the check in milliseconds.
_FAST_FULL=0; (( ${#_FAST_CMDS} > 16384 )) && { _FAST_FULL=1; _FAST_CMDS=""; }
_FAST_ESC="${_FAST_CMDS//'\\'/}"; _FAST_ESC="${_FAST_ESC//'\"'/}"; _FAST_ESC="${_FAST_ESC//'\/'/}"
_FAST_ESC="${_FAST_ESC//'\n'/}"; _FAST_ESC="${_FAST_ESC//'\t'/}"; _FAST_ESC="${_FAST_ESC//'\r'/}"
_FAST_CMDS="${_FAST_CMDS//'\n'/ }"; _FAST_CMDS="${_FAST_CMDS//'\t'/ }"; _FAST_CMDS="${_FAST_CMDS//'\r'/ }"
# The shell rebuilds words from quotes and backslashes (#1098): `git "add"`,
# `g\it add` and `git  add` all run git add. Match the trigger against the text
# as written and against a copy with quote and backslash characters dropped and
# blanks squeezed; skip only if neither matches. A command containing ANSI-C
# $'...' (which can spell any byte) takes the full path.
[[ "$_FAST_CMDS" == *"\$'"* ]] && _FAST_FULL=1
# A quote or backslash between two letters or digits (`pr"x"`, `x\git`) joins
# words; only the full path's quote handling decides what that runs. In the
# JSON text a shell `"` or `\` is itself escaped, hence the leading backslash.
[[ "$_FAST_CMDS" == *[[:alnum:]]\\[\"\\][[:alnum:]]* || "$_FAST_CMDS" == *[[:alnum:]]\'[[:alnum:]]* ]] && _FAST_FULL=1
_FAST_BUILT="${_FAST_CMDS//[\"\'\\]/}"
while [[ "$_FAST_BUILT" == *"  "* ]]; do _FAST_BUILT="${_FAST_BUILT//  / }"; done
_FAST_FIRST='"tool_input"[[:space:]]*:[[:space:]]*[{][[:space:]]*"command"[[:space:]]*:[[:space:]]*"[^"]'
_FAST_RE='(^|[^[:alnum:]])(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+(create|merge)|glab[[:space:]]+mr[[:space:]]+(create|merge))([^[:alnum:]]|$)'
if [[ $_FAST_FULL == 0 && "$INPUT" =~ $_FAST_FIRST && "$_FAST_ESC" != *'\'* ]] && ! [[ "$_FAST_CMDS" =~ $_FAST_RE || "$_FAST_BUILT" =~ $_FAST_RE ]]; then exit 0; fi
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)
# Only a proven required-queue request skips these local publication checks.
# This predicate grants no permission; UMG owns admission and its audit.
if [[ -n "$COMMAND" ]] && python3 "$HOOK_DIR/../lib/github-merge-queue.py" --queue-required "$COMMAND" "$CWD" >/dev/null 2>&1; then
    exit 0
fi
RELEASED_READ="$HOOK_DIR/../lib/read-only-command.py"
# Quoted publication examples in a proven reader are not publication actions.
# Empty/native stdin must continue through the protected native fallback below.
if [[ -n "$COMMAND" ]] && python3 "$RELEASED_READ" "$COMMAND" >/dev/null 2>&1; then
    exit 0
fi

# Native git hook path: when called from .githooks/pre-push, stdin is the
# ref list (not PreToolUse JSON). Detect by checking if COMMAND extraction
# failed but we're in a git repo. Set COMMAND/CWD so the rest of the hook
# works unchanged. Ref: #411
if [[ -z "$COMMAND" ]]; then
    if git rev-parse --git-dir >/dev/null 2>&1; then
        COMMAND="git push"
        CWD="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    else
        exit 0
    fi
fi

# Trigger on git push, gh pr create / merge (GitHub), or glab mr create / merge
# (GitLab). Word boundaries via portable character-class form (not
# BSD-incompatible `\b`); see issue #106. CCP#201 added the GitLab forms.
TRIGGERS='(^|[^[:alnum:]])(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+(create|merge)|glab[[:space:]]+mr[[:space:]]+(create|merge))([^[:alnum:]]|$)'
if ! echo "$COMMAND" | grep -qE "$TRIGGERS"; then
    exit 0
fi

# Content-scope check (#699). Skip out-of-scope repositories.
if [[ -f "$HOOK_DIR/../lib/scope-check.sh" ]]; then
    source "$HOOK_DIR/../lib/scope-check.sh"
    if ! _scope_in_scope "$COMMAND" "${CWD:-$PWD}"; then
        exit 0
    fi
fi

# Multi-statement-with-cd yield (mirrors branch-guard.sh discipline, issue #101).
# Portable word boundary (leading), same reason as TRIGGERS above.
#
# Statement-separator detection uses a shell-builtin `case` rather than grep so
# the test is unambiguously portable across BSD (macOS) and GNU greps. The
# earlier single-regex form ($'\n|;|\\|\\|') triggered BSD grep's "empty
# (sub)expression" error on macOS because BSD ERE treats `\|` as just `|`,
# which then parses as adjacent empty alternations. The case approach also
# avoids the `echo "$cmd" | grep -qF $'\n'` false-positive from echo's trailing
# newline.
CD_COUNT=$(echo "$COMMAND" | { grep -oE '(^|[^[:alnum:]])cd[[:space:]]' 2>/dev/null || true; } | wc -l | tr -d ' ')
if [[ "$CD_COUNT" -gt 0 ]]; then
    case "$COMMAND" in
        *$'\n'*|*';'*|*'||'*) exit 0 ;;
    esac
    if [[ "$CD_COUNT" -gt 1 ]]; then
        exit 0
    fi
fi

# Resolve effective repo dir (follow leading-cd pattern from branch-guard).
EFFECTIVE_CWD="$CWD"
if [[ "$COMMAND" =~ ^[[:space:]]*cd[[:space:]]+([^[:space:];&]+) ]]; then
    CD_TARGET="${BASH_REMATCH[1]}"
    CD_TARGET="${CD_TARGET%\"}"; CD_TARGET="${CD_TARGET#\"}"
    CD_TARGET="${CD_TARGET%\'}"; CD_TARGET="${CD_TARGET#\'}"
    case "$CD_TARGET" in
        /*) ;;
        *) CD_TARGET="$CWD/$CD_TARGET" ;;
    esac
    if [[ -d "$CD_TARGET" ]]; then
        EFFECTIVE_CWD="$CD_TARGET"
    fi
fi

if [[ -z "$EFFECTIVE_CWD" ]] || ! git -C "$EFFECTIVE_CWD" rev-parse --git-dir >/dev/null 2>&1; then
    # Not a git repo (e.g. gh pr merge invoked with -R from anywhere); allow.
    exit 0
fi

COMMIT_MSG=$(git -C "$EFFECTIVE_CWD" log -1 --pretty=%B 2>/dev/null || true)
if [[ -z "$COMMIT_MSG" ]]; then
    exit 0
fi

# Scan the full commit message for the trailer lines. This is intentionally
# looser than `git interpret-trailers --parse`, which only recognizes the
# LAST contiguous trailer block (separated from the body by a blank line,
# with no blank lines between trailers). Multiple trailer-block-shaped
# sections separated by blank lines are silently invisible to that parser
# -- caused a commit-and-amend cycle in claude-configs-public#180.
#
# The hook's contract is "the artifact-pointing trailer is PRESENT in the
# commit," not "the message adheres to RFC-2822 trailer syntax." Grep at
# line-start enforces presence; ordering / contiguity is left to the
# agent's discretion.
TRAILERS=$(printf '%s' "$COMMIT_MSG" | git interpret-trailers --parse 2>/dev/null || true)
REVIEW_COUNT=$(echo "$TRAILERS" | grep -cE '^Self-Review:[[:space:]]+\S')
REVIEW_LINE=$(echo "$TRAILERS" | grep -E '^Self-Review:[[:space:]]+\S' || true)
SOURCE_LINES=$(echo "$TRAILERS" | grep -cE '^Self-Review-Source:[[:space:]]+\S')
TIER_COUNT=$(echo "$TRAILERS" | grep -ci '^Review-Tier:[[:space:]]*[ABC][[:space:]]*$')
REVIEW_TIER=$(echo "$TRAILERS" | grep -i '^Review-Tier:' | sed -E 's/^Review-Tier:[[:space:]]+//' | tr '[:lower:]' '[:upper:]')
RISK_SCRIPT="$HOOK_DIR/../../bin/review-risk.py"
LEGACY_TIER=false
if [[ ! -f "$RISK_SCRIPT" ]]; then
    echo "BLOCKED: canonical review risk classifier is unavailable." >&2
    exit 2
fi
# Every absent or invalid policy trailer is collected and reported in one
# rejection (#1168). An absent or downgraded tier is replaced by the computed
# one so the remaining requirements can be listed; classifier failures and
# the legacy path keep their own handling.
MISSING=()
PROTECTED_RE='^(bin/review-risk\.py|catalog/review-risk-policy\.json|\.githooks/commit-msg|hooks/git/(self-review|pre-push-self-review)\.sh)$'
if [[ "$TIER_COUNT" -ne 1 || ! "$REVIEW_TIER" =~ ^[ABC]$ ]]; then
    POLICY_PATH="$HOOK_DIR/../../catalog/review-risk-policy.json"
    COMMIT_EPOCH=$(git -C "$EFFECTIVE_CWD" log -1 --format=%ct HEAD 2>/dev/null || echo 0)
    LEGACY_EPOCH=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["legacy_before_epoch"])' "$POLICY_PATH" 2>/dev/null || echo 0)
    if ! RISK_RESULT=$(python3 "$RISK_SCRIPT" --repo "$EFFECTIVE_CWD" --commit HEAD 2>&1); then
        echo "BLOCKED: review classifier failure: $RISK_RESULT" >&2; exit 2
    fi
    COMPUTED_TIER=$(printf '%s' "$RISK_RESULT" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read().strip().splitlines()[-1])["computed_tier"])' 2>/dev/null || true)
    if [[ "$COMMIT_EPOCH" -ge "$LEGACY_EPOCH" ]]; then
        if [[ ! "$COMPUTED_TIER" =~ ^[ABC]$ ]]; then
            echo "BLOCKED: post-policy commit requires exactly one Review-Tier: A|B|C trailer." >&2
            exit 2
        fi
        git -C "$EFFECTIVE_CWD" diff-tree --root --no-renames --name-only -r HEAD | grep -Eq "$PROTECTED_RE" && COMPUTED_TIER="C"
        MISSING+=("Review-Tier: $COMPUTED_TIER  (post-policy commit requires exactly one Review-Tier: A|B|C trailer; computed minimum is Tier $COMPUTED_TIER)")
        REVIEW_TIER="$COMPUTED_TIER"
    else
        # Pre-policy history preserves full validation rather than weakening.
        LEGACY_TIER=true
        REVIEW_TIER="C"
        echo "[self-review] warn: legacy commit has no Review-Tier; computed Tier $COMPUTED_TIER and preserving legacy full validation." >&2
    fi
elif [[ "$REVIEW_TIER" != "C" ]] && git -C "$EFFECTIVE_CWD" diff-tree --root --no-renames --name-only -r HEAD | grep -Eq "$PROTECTED_RE"; then
    MISSING+=("Review-Tier: C  (review-policy bootstrap files independently require Tier C)")
    REVIEW_TIER="C"
elif ! RISK_RESULT=$(python3 "$RISK_SCRIPT" --repo "$EFFECTIVE_CWD" --commit HEAD --declared "$REVIEW_TIER" 2>&1); then
    COMPUTED_TIER=$(printf '%s' "$RISK_RESULT" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read().strip().splitlines()[-1]).get("computed_tier", ""))' 2>/dev/null || true)
    if [[ ! "$COMPUTED_TIER" =~ ^[ABC]$ ]]; then
        echo "BLOCKED: review tier downgrade or classifier failure: $RISK_RESULT" >&2
        exit 2
    fi
    MISSING+=("Review-Tier: $COMPUTED_TIER  (declared Tier $REVIEW_TIER downgrades the computed Tier $COMPUTED_TIER)")
    REVIEW_TIER="$COMPUTED_TIER"
fi
if [[ "$REVIEW_TIER" == "C" && "$LEGACY_TIER" == "false" ]]; then
    for EVIDENCE in Hostile-Review; do
        COUNT=$(echo "$TRAILERS" | grep -cE "^${EVIDENCE}:[[:space:]]+\\S")
        if [[ "$COUNT" -ne 1 ]]; then
            case "$EVIDENCE" in
                Hostile-Review) EXAMPLE="<URL, #ticket, or committed file with the independent hostile review>" ;;
            esac
            MISSING+=("${EVIDENCE}: ${EXAMPLE}  (Tier C requires exactly one ${EVIDENCE}: evidence trailer; found $COUNT)")
        fi
    done
fi

NO_REVIEW=false; [[ "$COMMIT_MSG" == *'[no-review]'* ]] && NO_REVIEW=true
if [[ "$NO_REVIEW" == "true" && "$REVIEW_TIER" != "A" ]]; then
    MISSING+=("remove [no-review]: it is allowed only for independently validated Tier A")
fi
if ! echo "$COMMIT_MSG" | grep -qE '(#[0-9]+|\[no-ticket\])'; then
    MISSING+=("ticket reference: #NNN in the message, or [no-ticket] if exempt")
fi
if [[ "$REVIEW_COUNT" -ne 1 ]]; then
    if [[ "$NO_REVIEW" != "true" || "$REVIEW_TIER" != "A" ]]; then
        MISSING+=("Self-Review: <one-line summary of the review pass>  (exactly one non-empty trailer; found $REVIEW_COUNT)")
    fi
fi
if [[ "$REVIEW_TIER" != "A" && "$SOURCE_LINES" -ne 1 ]]; then
    MISSING+=("Self-Review-Source: <path-or-ticket pointing at the review artifact>  (exactly one; found $SOURCE_LINES)")
fi

SOURCE_VALUE=$(echo "$TRAILERS" | grep -E '^Self-Review-Source:[[:space:]]+' | sed -E 's/^Self-Review-Source:[[:space:]]+'//)
if [[ "$REVIEW_TIER" != "A" ]] && { [[ "$SOURCE_VALUE" =~ \.(md|txt)$ ]] || [[ "$SOURCE_VALUE" == /* ]] || [[ "$SOURCE_VALUE" == ./* ]]; }; then
    case "$SOURCE_VALUE" in
        /*) SOURCE_PATH="$SOURCE_VALUE" ;;
        *) SOURCE_PATH="$EFFECTIVE_CWD/$SOURCE_VALUE" ;;
    esac
    if [[ ! -f "$SOURCE_PATH" ]]; then
        MISSING+=("Self-Review-Source: file not found: $SOURCE_VALUE (at $SOURCE_PATH)")
    fi
fi

if [[ ${#MISSING[@]} -gt 0 ]]; then
    {
        echo "BLOCKED: Latest commit lacks ${#MISSING[@]} required review item(s) for Tier $REVIEW_TIER."
        echo ""
        echo "Add every item below to the commit message's trailer block in one amend:"
        printf '  - %s\n' "${MISSING[@]}"
        cat <<HOOKEOF

The review artifact must follow skills/self-review/SKILL.md:
  - ## Assumptions with the actual goal and scope
  - ## Test plan and ## Findings with actual results
  - Tier C: ## Independent review linked to the real review

Amend the commit (git commit --amend) and retry. Ref: #1168
HOOKEOF
    } >&2
    exit 2
fi

# Tier A uses the short review trailer. B/C retain one compact outcome record.
if [[ "$REVIEW_TIER" == "A" ]]; then exit 0; fi
SOURCE_PATH=""
if [[ ! "$SOURCE_VALUE" =~ ^https?:// && ! "$SOURCE_VALUE" =~ ^#[0-9]+$ ]]; then
    case "$SOURCE_VALUE" in
        /*) SOURCE_PATH="$SOURCE_VALUE" ;;
        *) SOURCE_PATH="$EFFECTIVE_CWD/$SOURCE_VALUE" ;;
    esac
    [[ -f "$SOURCE_PATH" ]] || { echo "BLOCKED: review artifact is unavailable: $SOURCE_VALUE" >&2; exit 2; }
    REQUIRED_SECTIONS=("## Assumptions" "## Test plan")
    if [[ "$REVIEW_TIER" == "C" ]]; then
        if grep -Eq '^## Peer review[[:space:]]*$' "$SOURCE_PATH" && grep -Eq '^## Lead review[[:space:]]*$' "$SOURCE_PATH" && grep -Eq '^## Quantified claims[[:space:]]*$' "$SOURCE_PATH"; then
            # Previously valid records remain publishable without history edits.
            REQUIRED_SECTIONS=("## Assumptions" "## Peer review" "## Lead review" "## Quantified claims")
        else
            REQUIRED_SECTIONS+=("## Findings" "## Independent review")
        fi
    fi
    for section in "${REQUIRED_SECTIONS[@]}"; do
        if ! grep -Eq "^${section}[[:space:]]*$" "$SOURCE_PATH"; then
            echo "BLOCKED: review artifact requires $section" >&2; exit 2
        fi
        content=$(awk -v heading="$section" '{line=$0;sub(/[[:space:]]+$/,"",line)} line==heading {active=1;next} /^## / {active=0} active && /[^[:space:]]/ {print;exit}' "$SOURCE_PATH")
        [[ -n "$content" ]] || { echo "BLOCKED: review artifact has empty $section" >&2; exit 2; }
    done

fi
if [[ "$REVIEW_TIER" == "C" ]]; then
    HOSTILE_VALUE=$(echo "$TRAILERS" | grep -E '^Hostile-Review:[[:space:]]+' | sed -E 's/^[^:]*:[[:space:]]+//')
    if [[ ! "$HOSTILE_VALUE" =~ ^https?:// && ! "$HOSTILE_VALUE" =~ ^#[0-9]+$ ]]; then
        case "$HOSTILE_VALUE" in /*) REVIEW_PATH="$HOSTILE_VALUE" ;; *) REVIEW_PATH="$EFFECTIVE_CWD/$HOSTILE_VALUE" ;; esac
        [[ -f "$REVIEW_PATH" && ! -L "$REVIEW_PATH" && -s "$REVIEW_PATH" ]] || { echo "BLOCKED: actual independent review evidence is unavailable" >&2; exit 2; }
    fi
fi

# v1.6: Pre-ship-dry-run check for transformation code.
# If the diff touches transformation-code patterns, require a
# Pre-ship-dry-run: trailer pointing at behavioral verification evidence.
# Level 3 of the investigation enforcement ladder (#255, #275).
DIFF_FILES=$(git -C "$EFFECTIVE_CWD" diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null || true)

TRANSFORM_FILE_RE='\.(sql|sql\.j2)$'
IS_TRANSFORM=false

if [ -n "$DIFF_FILES" ]; then
    if echo "$DIFF_FILES" | grep -qE "$TRANSFORM_FILE_RE" 2>/dev/null; then
        IS_TRANSFORM=true
    fi

    # Also check file contents for transformation patterns
    if [ "$IS_TRANSFORM" = "false" ]; then
        TRANSFORM_CONTENT_RE='(CREATE[[:space:]]+TABLE|INSERT[[:space:]]+INTO|UNION[[:space:]]+ALL|\.write\.|\.saveAsTable|\.to_sql)'
        for f in $DIFF_FILES; do
            # Do not let the transformation-content regex literal in this hook
            # match itself. Editing the enforcement script should require
            # hostile review and inventoried-shape evidence, not a data-pipeline
            # Pre-ship-dry-run trailer for a regex string literal.
            if [ "$f" = "hooks/git/self-review.sh" ]; then
                continue
            fi
            FULL_PATH="$EFFECTIVE_CWD/$f"
            if [ -f "$FULL_PATH" ] && grep -qE "$TRANSFORM_CONTENT_RE" "$FULL_PATH" 2>/dev/null; then
                IS_TRANSFORM=true
                break
            fi
        done
    fi
fi

if [ "$IS_TRANSFORM" = "true" ]; then
    DRYRUN_LINE=$(echo "$COMMIT_MSG" | { grep -E '^Pre-ship-dry-run:[[:space:]]+\S' || true; } | head -1)
    PROBE_LINE=$(echo "$COMMIT_MSG" | { grep -E '^Probe-Matrix:[[:space:]]+\S' || true; } | head -1)
    if [ -z "$DRYRUN_LINE" ] && [ -z "$PROBE_LINE" ]; then
        cat >&2 <<HOOKEOF
BLOCKED: Diff touches transformation code but commit is missing both
Pre-ship-dry-run: and Probe-Matrix: trailers.

Transformation code (SQL, DataFrame pipelines, write operations) requires
behavioral verification before shipping. Add ONE of these to the trailer
block:

  Pre-ship-dry-run: <URL or path to dry-run evidence (prose-form, v1.6)>
  Probe-Matrix:     <path to probe-runner.py result JSON (machine-form, v1.7)>

Prose Pre-ship-dry-run evidence must be one of:
  - EXPLAIN output showing query plan and estimated rows
  - LIMIT-N materialization with row counts
  - .printSchema() / .show(N) output on a sample
  - Rendered template output with concrete values
"I checked and it looks fine" is not evidence.

Probe-Matrix evidence is machine-generated by hooks/lib/probe-runner.py.
See examples/probe-matrices/README.md for the matrix shape and runner
invocation. The hook validates signature + session + all-PASS overall.

Ref: #255 (Level 3 enforcement), #275 (transformation code dry-run),
     #284 (assumption matrix primitive)
HOOKEOF
        exit 2
    fi

    # v1.8: prose dry-runs need scale + falsification coverage (#283).
    # Probe-Matrix is machine-validated below, so this extra prose gate only
    # applies to Pre-ship-dry-run trailers.
    if [ -n "$DRYRUN_LINE" ] && [ -z "$PROBE_LINE" ]; then
        SCALE_LINE=$(echo "$COMMIT_MSG" | { grep -E '^Dry-run-scale:[[:space:]]+\S' || true; } | head -1)
        FALSIFY_LINE=$(echo "$COMMIT_MSG" | { grep -E '^Dry-run-falsification:[[:space:]]+\S' || true; } | head -1)
        if [ -z "$SCALE_LINE" ] || [ -z "$FALSIFY_LINE" ]; then
            cat >&2 <<HOOKEOF
BLOCKED: Transformation-code commit uses prose Pre-ship-dry-run evidence
but is missing Dry-run-scale: and/or Dry-run-falsification: trailers.

Pre-ship-dry-run evidence is not enough by form alone. It must say what
production scale it exercised and which failure modes it falsified.

Required trailers:
  Pre-ship-dry-run: <URL or path to evidence>
  Dry-run-scale: <rows / partitions / files / target scale, or explicit gap>
  Dry-run-falsification: <schema / planner / partition-cardinality / file-commit / catalog behavior covered or not covered>

If the dry-run cannot cover production scale, say so in Dry-run-scale and
name the remaining gap. Do not let a toy probe stand in for scale evidence.

Ref: #283 (dry-run artifact rationalization)
HOOKEOF
            exit 2
        fi
    fi

    # v1.7: if Probe-Matrix: trailer is present, validate the result file.
    if [ -n "$PROBE_LINE" ]; then
        # Extract the path (everything after "Probe-Matrix:" + leading whitespace).
        PROBE_PATH=$(echo "$PROBE_LINE" | sed -E 's/^Probe-Matrix:[[:space:]]+//')
        # Resolve relative paths against the repo root.
        case "$PROBE_PATH" in
            /*) ABS_PROBE_PATH="$PROBE_PATH" ;;
            *)  ABS_PROBE_PATH="$EFFECTIVE_CWD/$PROBE_PATH" ;;
        esac

        if [ ! -f "$ABS_PROBE_PATH" ]; then
            cat >&2 <<HOOKEOF
BLOCKED: Probe-Matrix: trailer points at a missing file:

  Probe-Matrix: $PROBE_PATH
  (resolved to: $ABS_PROBE_PATH)

The result JSON must exist. Run probe-runner.py to generate it:

  python3 hooks/lib/probe-runner.py <matrix.toml>

Ref: #284
HOOKEOF
            exit 2
        fi

        # Validate signature + session + overall_status using a python helper.
        # All validation in one subshell so a single python invocation does it.
        VALIDATION=$(python3 - "$ABS_PROBE_PATH" "${CRAFT_AGENT_SESSION_ID:-}" <<'PYEOF'
import json
import os
import sys

path = sys.argv[1]
expected_session = sys.argv[2] if len(sys.argv) > 2 else ""

try:
    with open(path) as f:
        doc = json.load(f)
except Exception as e:
    print(f"PARSE_ERROR: {e}")
    sys.exit(1)

if doc.get("generator") != "probe-runner.py":
    print(f"WRONG_GENERATOR: {doc.get('generator')!r}")
    sys.exit(1)

overall = doc.get("overall_status")
if overall != "PASS":
    blocked = [r.get("id") + ": " + r.get("reason", "") for r in doc.get("results", []) if r.get("status") == "BLOCK"]
    errored = [r.get("id") + ": " + r.get("reason", "") for r in doc.get("results", []) if r.get("status") == "ERROR"]
    notrun  = [r.get("id") for r in doc.get("results", []) if r.get("status") == "NOT_RUN"]
    parts = [f"overall_status={overall}"]
    if blocked: parts.append("BLOCK: " + " | ".join(blocked))
    if errored: parts.append("ERROR: " + " | ".join(errored))
    if notrun:  parts.append("NOT_RUN: " + ", ".join(notrun))
    print("NOT_PASS: " + " ; ".join(parts))
    sys.exit(1)

# v1.7 Sagan-parody enforcement (#284): every SKIPPED entry must have a
# non-trivial skip_reason. The whole point of the Sagan starter is that the
# universe of assumptions is given and the agent reduces by JUSTIFYING
# omissions. A skip whose reason is "n/a" / "trivial" / 3-word hand-wave
# defeats the design.
TRIVIAL_SKIP_PHRASES = {
    "", "n/a", "na", "n.a.", "n.a",
    "not applicable", "not relevant", "not needed",
    "trivial", "obvious", "skip", "skipped", "no",
}
MIN_SKIP_REASON_LEN = 20
bad_skips = []
for r in doc.get("results", []):
    if r.get("status") != "SKIPPED":
        continue
    reason = (r.get("skip_reason") or "").strip()
    if reason.lower() in TRIVIAL_SKIP_PHRASES:
        bad_skips.append(f"{r.get('id')}: skip reason {reason!r} is in the trivial-phrases list")
    elif len(reason) < MIN_SKIP_REASON_LEN:
        bad_skips.append(f"{r.get('id')}: skip reason ({len(reason)} chars) < {MIN_SKIP_REASON_LEN} char floor")
if bad_skips:
    print("TRIVIAL_SKIPS: " + " | ".join(bad_skips))
    sys.exit(1)

# Session check is warning-only when CRAFT_AGENT_SESSION_ID isn't set —
# the host repo or CI may run the hook outside a Craft Agent session.
if expected_session:
    actual = doc.get("session_id", "")
    if actual != expected_session:
        print(f"SESSION_MISMATCH: result session_id={actual!r}, expected={expected_session!r}")
        sys.exit(1)

print("OK")
sys.exit(0)
PYEOF
        )
        VALIDATION_EXIT=$?
        if [ "$VALIDATION_EXIT" -ne 0 ]; then
            cat >&2 <<HOOKEOF
BLOCKED: Probe-Matrix: result file failed validation.

  File: $ABS_PROBE_PATH
  Reason: $VALIDATION

A valid Probe-Matrix result file must:
  - Have generator field == "probe-runner.py" (machine-written; not authored by hand)
  - Have overall_status == "PASS" (all assumptions passed their thresholds)
  - Have session_id matching the current session (if \$CRAFT_AGENT_SESSION_ID is set)

Re-run probe-runner.py after the underlying assumption is fixed. Do not
edit the result JSON by hand — the hook detects hand-authored result files
by the generator field.

Ref: #284
HOOKEOF
            exit 2
        fi
    fi
fi

# v1.10: P1 findings block (#419, compound engineering adoption).
# If ## Findings contains table or compact P1 findings without an explicit
# fixed resolution, block publication. P2 and P3 are not
# hook-enforced — P2 ticket-existence is agent discipline, P3 is
# documentation-only.
if [[ -n "${SOURCE_PATH:-}" ]] && [[ -f "${SOURCE_PATH:-}" ]] && grep -qF '## Findings' "$SOURCE_PATH"; then
    FINDINGS_BLOCK=$(awk '/^## Findings[[:space:]]*$/ {active=1;next} /^## / {active=0} active {print}' "$SOURCE_PATH")
    UNRESOLVED_P1=$(
        printf '%s\n' "$FINDINGS_BLOCK" | awk '/^\|/ {
            delete cells
            count=1
            for (i=1; i<=length($0); i++) {
                char=substr($0, i, 1)
                if (char == "\\" && i<length($0)) {
                    cells[count]=cells[count] char substr($0, ++i, 1)
                } else if (char == "|") {
                    count++
                } else {
                    cells[count]=cells[count] char
                }
            }
            if (cells[3] ~ /^[[:space:]]*P1[[:space:]]*$/) {
                resolution=cells[5]
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", resolution)
                if ((count != 5 && count != 6) ||
                    (count == 6 && cells[6] !~ /^[[:space:]]*$/) ||
                    tolower(resolution) != "fixed") print
            }
        }'
        printf '%s\n' "$FINDINGS_BLOCK" | grep -Ei '^[[:space:]]*([-*][[:space:]]+)?P1[[:space:]]*:' | grep -viE '(^|;)[[:space:]]*resolution[[:space:]]*:[[:space:]]*fixed[[:space:]]*(;|$)' || true
    )
    if [[ -n "$UNRESOLVED_P1" ]]; then
        cat >&2 <<HOOKEOF
BLOCKED: Self-review artifact has unresolved P1 findings:

$UNRESOLVED_P1

P1 findings must be resolved (Resolution: fixed) before push.
This check blocks P1 findings without a complete fixed resolution.

See skills/self-review/artifact-contract.md for the accepted finding formats.
Ref: #419
HOOKEOF
        exit 2
    fi
fi


exit 0
