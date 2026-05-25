#!/bin/bash
# Hook: self-review
# Enforces: skills/self-review/SKILL.md, feedback_self_code_review memory entry
# Trigger: PreToolUse on Bash(git push *), Bash(gh pr create *), Bash(gh pr merge *)
#
# Blocks pushes/PR-creates/PR-merges unless the latest commit being
# pushed has Self-Review: and Self-Review-Source: trailers (proper
# trailer-block placement, parsed via git interpret-trailers), and the
# referenced source artifact has the required structural sections.
#
# v1 scope (what this hook mechanically enforces today):
#   - Both trailers present in the trailer block of the latest commit
#   - Exactly one Self-Review-Source value
#   - If the value is a file path: file exists, has the three required
#     section headers, has a non-empty Goal source line, the Assumptions
#     section names at least one role, the Peer section cites at least
#     one shelf
# v1.2 (this version):
#   - Pre-author-inventory: field present and non-empty in Assumptions
#     section (structural check only; content quality is operator-auditable).
#     NONE is accepted only when a Trivial-against-state: declaration
#     is also present in the artifact.
# v2 scope (deferred follow-ups, tracked in SKILL.md):
#   - Goal source does not point at the commit being pushed
#   - Lead section's role-tagged affirmative standard format
#   - detect-ai-fingerprints scan against the source
#   - Verified-by: trailers on countable claims inside the source
#
# Surface limitation: this hook fires only in Claude Code sessions via
# PreToolUse in settings.json. Craft Agent sessions use a separate tool-
# call surface and this hook does not fire for them. Enforcement in Craft
# sessions is operator-auditable only. See SKILL.md Known limitations.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Trigger on git push, gh pr create / merge (GitHub), or glab mr create / merge
# (GitLab). Word boundaries via portable character-class form (not
# BSD-incompatible `\b`); see issue #106. CCP#201 added the GitLab forms.
TRIGGERS='(^|[^[:alnum:]])(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+(create|merge)|glab[[:space:]]+mr[[:space:]]+(create|merge))([^[:alnum:]]|$)'
if ! echo "$COMMAND" | grep -qE "$TRIGGERS"; then
    exit 0
fi

# Multi-statement-with-cd yield (mirrors branch-guard.sh discipline, issue #101).
# Portable word boundary (leading), same reason as TRIGGERS above.
CD_COUNT=$(echo "$COMMAND" | grep -oE '(^|[^[:alnum:]])cd[[:space:]]' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$CD_COUNT" -gt 0 ]]; then
    if [[ "$CD_COUNT" -gt 1 ]] || echo "$COMMAND" | grep -qE $'\n|;|\\|\\|'; then
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
REVIEW_LINE=$(echo "$COMMIT_MSG" | grep -E '^Self-Review:[[:space:]]+\S' | head -1)
SOURCE_LINES=$(echo "$COMMIT_MSG" | grep -cE '^Self-Review-Source:[[:space:]]+\S')

if [[ -z "$REVIEW_LINE" ]]; then
    cat >&2 <<HOOKEOF
BLOCKED: Latest commit is missing the Self-Review: trailer.

Add to the commit message's trailer block (after the last paragraph):
  Self-Review: <one-line summary of the review pass>
  Self-Review-Source: <path-or-ticket pointing at the review artifact>

The review artifact must follow skills/self-review/SKILL.md:
  - ## Assumptions (with Goal source: from outside the diff, role(s) named,
                    Pre-author-inventory: pointing at the investigation record)
  - ## Peer review (shelf checks with grep/test-output evidence)
  - ## Lead review (role-tagged affirmative standards)

Amend the commit (git commit --amend) and retry.
HOOKEOF
    exit 2
fi

if [[ "$SOURCE_LINES" -eq 0 ]]; then
    cat >&2 <<HOOKEOF
BLOCKED: Latest commit has Self-Review: but is missing Self-Review-Source:.

Add to the commit trailer block:
  Self-Review-Source: <path-or-ticket pointing at the review artifact>
HOOKEOF
    exit 2
fi

if [[ "$SOURCE_LINES" -gt 1 ]]; then
    cat >&2 <<HOOKEOF
BLOCKED: Latest commit has multiple Self-Review-Source: trailers.

Provide exactly one. The hook cannot disambiguate which artifact is canonical.
HOOKEOF
    exit 2
fi

SOURCE_VALUE=$(echo "$COMMIT_MSG" | grep -E '^Self-Review-Source:[[:space:]]+' | head -1 | sed -E 's/^Self-Review-Source:[[:space:]]+'//)

# If source looks like a path, run the structural checks against the file.
# Ticket references (e.g. "#123") are accepted but not yet validated --
# v2 follow-up.
if [[ "$SOURCE_VALUE" =~ \.(md|txt)$ ]] || [[ "$SOURCE_VALUE" == /* ]] || [[ "$SOURCE_VALUE" == ./* ]]; then
    case "$SOURCE_VALUE" in
        /*) SOURCE_PATH="$SOURCE_VALUE" ;;
        *)  SOURCE_PATH="$EFFECTIVE_CWD/$SOURCE_VALUE" ;;
    esac

    if [[ ! -f "$SOURCE_PATH" ]]; then
        cat >&2 <<HOOKEOF
BLOCKED: Self-Review-Source: points at $SOURCE_VALUE which does not exist
at $SOURCE_PATH.

Either fix the path or produce the artifact at that location before pushing.
HOOKEOF
        exit 2
    fi

    # Required section headers.
    MISSING_SECTIONS=()
    for section in "## Assumptions" "## Peer review" "## Lead review"; do
        if ! grep -qF "$section" "$SOURCE_PATH"; then
            MISSING_SECTIONS+=("$section")
        fi
    done

    if [[ ${#MISSING_SECTIONS[@]} -gt 0 ]]; then
        cat >&2 <<HOOKEOF
BLOCKED: Self-Review-Source: $SOURCE_PATH is missing required sections:
$(printf '  - %s\n' "${MISSING_SECTIONS[@]}")

See skills/self-review/SKILL.md for the required artifact format.
HOOKEOF
        exit 2
    fi

    # Non-empty Goal source line.
    if ! grep -qE '^Goal source:[[:space:]]+\S' "$SOURCE_PATH"; then
        cat >&2 <<HOOKEOF
BLOCKED: Self-Review-Source: $SOURCE_PATH is missing or has empty
'Goal source:' line in the Assumptions section.

The Goal source must point at something OUTSIDE the diff (ticket #N,
design-note path, or quoted user-request paragraph) so the review is
not a restatement of the diff's own commit subject.
HOOKEOF
        exit 2
    fi

    # v1.1: Goal-source artifact-mtime sanity check.
    # If the Goal source value looks like a file path, verify that file's
    # mtime is not NEWER than the artifact itself (which would suggest
    # the goal was written AFTER the work -- the substantive-empty failure
    # mode the Goal-source field was designed to prevent).
    # Uses file mtime, which is a heuristic (touch can defeat it); a stronger
    # check would inspect git history for the goal source, but session-scoped
    # plans/ files aren't in any git repo, so mtime is the v1.1 floor.
    # Caveats inside the source file are unblocked: ticket-shaped sources
    # (#NNN) and quoted-user-request goal-sources skip this check.
    GOAL_SOURCE_VALUE=$(grep -E '^Goal source:[[:space:]]+' "$SOURCE_PATH" | head -1 | sed -E 's/^Goal source:[[:space:]]+'//)
    if [[ "$GOAL_SOURCE_VALUE" =~ \.(md|txt|json|yaml|yml|sh|py|sql)$ ]] || [[ "$GOAL_SOURCE_VALUE" == /* ]] || [[ "$GOAL_SOURCE_VALUE" == ./* ]]; then
        case "$GOAL_SOURCE_VALUE" in
            /*) GOAL_SOURCE_PATH="$GOAL_SOURCE_VALUE" ;;
            *)  GOAL_SOURCE_PATH="$EFFECTIVE_CWD/$GOAL_SOURCE_VALUE" ;;
        esac
        if [[ -f "$GOAL_SOURCE_PATH" ]]; then
            GOAL_MTIME=$(stat -f %m "$GOAL_SOURCE_PATH" 2>/dev/null || stat -c %Y "$GOAL_SOURCE_PATH" 2>/dev/null || echo "")
            ARTIFACT_MTIME=$(stat -f %m "$SOURCE_PATH" 2>/dev/null || stat -c %Y "$SOURCE_PATH" 2>/dev/null || echo "")
            if [[ -n "$GOAL_MTIME" && -n "$ARTIFACT_MTIME" && "$GOAL_MTIME" -gt "$ARTIFACT_MTIME" ]]; then
                cat >&2 <<HOOKEOF
BLOCKED: Goal source ($GOAL_SOURCE_PATH) has mtime newer than the review
artifact ($SOURCE_PATH). The Goal source should pre-date the work it
grounds; a Goal source written AFTER the artifact suggests post-hoc
justification rather than a pre-existing target to verify against.

If this is legitimate (e.g., you updated the design note after starting
work and the artifact captures that updated design), touch the artifact
to refresh its mtime, then retry.
HOOKEOF
                exit 2
            fi
        fi
    fi

    # Assumptions section must name at least one role. Use the canonical
    # role names from SKILL.md; tolerate variants via case-insensitive match.
    ROLE_RE='(software engineer|tech lead|data engineer|data analyst|geospatial)'
    if ! grep -qiE "^Working as:[[:space:]]+.*$ROLE_RE" "$SOURCE_PATH"; then
        cat >&2 <<HOOKEOF
BLOCKED: Self-Review-Source: $SOURCE_PATH does not name a role on the
'Working as:' line.

Expected at least one of: software engineer, tech lead, data engineer,
data analyst, geospatial. See skills/self-review/SKILL.md.
HOOKEOF
        exit 2
    fi

    # v1.2: Pre-author-inventory field must be present and non-empty.
    # Points at the ## Pre-author inventory section in the ticket or plan,
    # per _authoring-against-state-rules.md:6. NONE is accepted only when
    # paired with a Trivial-against-state: declaration in the artifact.
    INVENTORY_VALUE=$(grep -E '^Pre-author-inventory:[[:space:]]+\S' "$SOURCE_PATH" | head -1 | sed -E 's/^Pre-author-inventory:[[:space:]]+'// || true)
    if [[ -z "$INVENTORY_VALUE" ]]; then
        # Field entirely missing or empty -- block regardless of Trivial-against-state.
        cat >&2 <<HOOKEOF
BLOCKED: Self-Review-Source: $SOURCE_PATH is missing 'Pre-author-inventory:'
in the Assumptions section.

Per _authoring-against-state-rules.md:6, a pre-author inventory must be
completed BEFORE authoring and recorded in the ticket. Point at it here:

  Pre-author-inventory: enterprise#2094#pre-author-inventory
  Pre-author-inventory: plans/feature-x/pre-author-inventory.md

If the change genuinely does not trigger any authoring-against-state
contact category, use NONE and include a Trivial-against-state:
declaration in the artifact (see SKILL.md).
HOOKEOF
        exit 2
    fi

    if [[ "$INVENTORY_VALUE" == "NONE" ]]; then
        # NONE is allowed only when a Trivial-against-state declaration exists.
        if ! grep -qF 'Trivial-against-state:' "$SOURCE_PATH"; then
            cat >&2 <<HOOKEOF
BLOCKED: Pre-author-inventory: is NONE in $SOURCE_PATH but no
Trivial-against-state: declaration is present.

NONE is accepted only when the change does not trigger any authoring-
against-state contact category. That claim requires a
Trivial-against-state: declaration per the usual evidence-chain
requirements (writing-rules:4). Add the declaration or provide
a real inventory link.
HOOKEOF
            exit 2
        fi
    fi

    # Peer review section must cite at least one shelf.
    SHELF_RE='writing-(code|tests|claims|prose|releases):'
    # Extract Peer review section content (between '## Peer review' header
    # and the next '## ' header) and check for shelf citation.
    PEER_BLOCK=$(awk '/^## Peer review/{flag=1; next} /^## /{flag=0} flag' "$SOURCE_PATH")
    if ! echo "$PEER_BLOCK" | grep -qE "$SHELF_RE"; then
        cat >&2 <<HOOKEOF
BLOCKED: Self-Review-Source: $SOURCE_PATH '## Peer review' section does
not cite a shelf.

Expected at least one shelf reference (e.g. writing-code:1, writing-claims:3).
Empty Peer sections are allowed ONLY if the diff genuinely doesn't engage
any shelf, but the section must then explicitly state that.
HOOKEOF
        exit 2
    fi
fi

# v1 checks passed.
exit 0
