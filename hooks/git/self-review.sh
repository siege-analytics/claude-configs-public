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
# call surface and this hook does not fire for them. Partial mitigation:
# pre-action-guard.sh (UserPromptSubmit) injects branch/ticket warnings
# in Craft Agent sessions. See #261.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

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
#
# Statement-separator detection uses a shell-builtin `case` rather than grep so
# the test is unambiguously portable across BSD (macOS) and GNU greps. The
# earlier single-regex form ($'\n|;|\\|\\|') triggered BSD grep's "empty
# (sub)expression" error on macOS because BSD ERE treats `\|` as just `|`,
# which then parses as adjacent empty alternations. The case approach also
# avoids the `echo "$cmd" | grep -qF $'\n'` false-positive from echo's trailing
# newline.
CD_COUNT=$(echo "$COMMAND" | grep -oE '(^|[^[:alnum:]])cd[[:space:]]' 2>/dev/null | wc -l | tr -d ' ')
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

    # v1.3: Investigate-artifact and Pre-mortem-artifact fields must be
    # present and non-empty. TRIVIAL is accepted only when a
    # ## Trivial-investigation declaration block is also present with
    # all four required fields (Category / Cannot produce error / Evidence /
    # Falsification). If the value looks like a file path, the file must exist.
    for FIELD_NAME in "Investigate-artifact" "Pre-mortem-artifact"; do
        FIELD_VALUE=$(grep -E "^${FIELD_NAME}:[[:space:]]+\\S" "$SOURCE_PATH" | head -1 | sed -E "s/^${FIELD_NAME}:[[:space:]]+'*//" || true)
        if [[ -z "$FIELD_VALUE" ]]; then
            cat >&2 <<HOOKEOF
BLOCKED: Self-Review-Source: $SOURCE_PATH is missing '${FIELD_NAME}:'
in the Assumptions section.

Investigation is non-discretionary. Provide one of:
  ${FIELD_NAME}: <ticket-comment-link>
  ${FIELD_NAME}: <committed-file-path>
  ${FIELD_NAME}: plans/investigate-*.md
  ${FIELD_NAME}: TRIVIAL (with ## Trivial-investigation declaration below)

See skills/self-review/SKILL.md and skills/thinking/investigate/SKILL.md.
HOOKEOF
            exit 2
        fi

        if [[ "$FIELD_VALUE" == "TRIVIAL" ]]; then
            if ! grep -qF '## Trivial-investigation declaration' "$SOURCE_PATH"; then
                cat >&2 <<HOOKEOF
BLOCKED: ${FIELD_NAME}: is TRIVIAL in $SOURCE_PATH but no
## Trivial-investigation declaration block is present.

TRIVIAL requires a declaration with all four fields:
  Category / Cannot produce error / Evidence / Falsification

"This is simple" is not falsifiable evidence. See SKILL.md.
HOOKEOF
                exit 2
            fi
            # Validate declaration has the four required fields.
            DECL_BLOCK=$(awk '/^## Trivial-investigation declaration/{flag=1; next} /^## /{flag=0} flag' "$SOURCE_PATH")
            for DECL_FIELD in "Category:" "Cannot produce error:" "Evidence:" "Falsification:"; do
                if ! echo "$DECL_BLOCK" | grep -qF "$DECL_FIELD"; then
                    cat >&2 <<HOOKEOF
BLOCKED: ## Trivial-investigation declaration in $SOURCE_PATH is missing
required field: $DECL_FIELD

All four fields are required: Category / Cannot produce error / Evidence /
Falsification. See skills/self-review/SKILL.md.
HOOKEOF
                    exit 2
                fi
            done
        elif [[ "$FIELD_VALUE" =~ \.(md|txt)$ ]] || [[ "$FIELD_VALUE" == /* ]] || [[ "$FIELD_VALUE" == ./* ]]; then
            # Value looks like a file path — verify the file exists.
            case "$FIELD_VALUE" in
                /*) FIELD_PATH="$FIELD_VALUE" ;;
                *)  FIELD_PATH="$EFFECTIVE_CWD/$FIELD_VALUE" ;;
            esac
            if [[ ! -f "$FIELD_PATH" ]]; then
                cat >&2 <<HOOKEOF
BLOCKED: ${FIELD_NAME}: points at $FIELD_VALUE which does not exist
at $FIELD_PATH.

Either fix the path, produce the artifact, or post it to the ticket
and use the ticket comment link instead.
HOOKEOF
                exit 2
            fi
        fi
        # Ticket-comment-links (URLs, #NNN references) are accepted but
        # not yet validated against the ticket API — v2 follow-up.
    done

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

    # v1.4: Post-mortem awareness check. If the commit message indicates
    # a revert or regression fix, the self-review should acknowledge
    # post-mortem applicability. This is a WARNING, not a block — the
    # post-error-revision-required hook handles the hard gate for trailers.
    # But the self-review artifact should show awareness.
    if echo "$COMMIT_MSG" | grep -qiE 'revert|regression|fix\([^)]+\):[[:space:]]+regression'; then
        if ! grep -qiE 'post-mortem|postmortem' "$SOURCE_PATH"; then
            cat >&2 <<HOOKEOF
WARNING: Commit message suggests a revert or regression fix, but the
self-review artifact at $SOURCE_PATH does not mention post-mortem.

Per skills/post-mortem/SKILL.md, a post-mortem is required when:
  - A shipped implementation contradicts its ticket hypothesis
  - A pre-mortem Tiger materializes
  - A test failure reveals a shipped bug that passed self-review

If this is a revert or regression fix for shipped code, a post-mortem
should be triggered. Add a note to the Lead review section acknowledging
post-mortem applicability (or explaining why it doesn't apply).

This is a warning, not a block. The post-error-revision-required hook
enforces the Refs: + Post-error-revision: trailers.
HOOKEOF
            # WARNING only — do not exit 2
        fi
    fi
fi

# v1.5: Design-Note-Source trailer check.
# Non-trivial commits should reference the design note that authorized
# the work. WARNING only (not a block) — the trailer is new (#262).
# Promotes to a block in v2 after adoption stabilizes.
DESIGN_NOTE_LINE=$(echo "$COMMIT_MSG" | grep -cE '^Design-Note-Source:[[:space:]]+\S')
if [[ "$DESIGN_NOTE_LINE" -eq 0 ]]; then
    cat >&2 <<HOOKEOF
WARNING: Latest commit has no Design-Note-Source: trailer.

Non-trivial commits should reference the design note that authorized
the work:
  Design-Note-Source: https://github.com/org/repo/issues/N#issuecomment-...
  Design-Note-Source: #N (ticket with design note in comments)

This is a warning, not a block. See #262.
HOOKEOF
    # WARNING only — do not exit 2
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
            FULL_PATH="$EFFECTIVE_CWD/$f"
            if [ -f "$FULL_PATH" ] && grep -qlE "$TRANSFORM_CONTENT_RE" "$FULL_PATH" 2>/dev/null; then
                IS_TRANSFORM=true
                break
            fi
        done
    fi
fi

if [ "$IS_TRANSFORM" = "true" ]; then
    DRYRUN_LINE=$(echo "$COMMIT_MSG" | grep -E '^Pre-ship-dry-run:[[:space:]]+\S' | head -1)
    if [ -z "$DRYRUN_LINE" ]; then
        cat >&2 <<HOOKEOF
BLOCKED: Diff touches transformation code but commit is missing
Pre-ship-dry-run: trailer.

Transformation code (SQL, DataFrame pipelines, write operations) requires
behavioral verification before shipping. Add to the commit trailer block:

  Pre-ship-dry-run: <URL or path to dry-run evidence>

Evidence must be one of:
  - EXPLAIN output showing query plan and estimated rows
  - LIMIT-N materialization with row counts
  - .printSchema() / .show(N) output on a sample
  - Rendered template output with concrete values

The evidence must be posted to the ticket or committed to the repo.
"I checked and it looks fine" is not evidence.

Ref: #255 (Level 3 enforcement), #275 (transformation code dry-run)
HOOKEOF
        exit 2
    fi
fi

# All checks passed.
exit 0
