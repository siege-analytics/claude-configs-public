#!/bin/bash
# Hook: no-slug-form-outbound
# Enforces: parser-drop guard for cross-session agent messaging
# Trigger: PreToolUse on mcp__session__send_agent_message
#
# Blocks outbound agent messages whose body contains the literal slug-form
# tokens [skill:<word>] or [rule:<word>]. The host parser tries to resolve
# these even inside backticks and silently drops the entire carrier message
# when resolution fails (compound finding on LESSON 323a0f5).
#
# The angle-bracket form [skill:<name>] is the documentation-safe shape and
# is NOT matched by this pattern (because the first char after the colon is
# `<`, not a letter).

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH:/usr/local/bin:/opt/homebrew/bin"

INPUT=$(cat)

# Extract the message body. The exact field name on
# mcp__session__send_agent_message is `message`; fall back to scanning the
# entire tool_input JSON if the field is absent so the hook fails open
# rather than silently passing on a future schema change.
BODY=$(echo "$INPUT" | jq -r '.tool_input.message // .tool_input.body // .tool_input.text // empty' 2>/dev/null || true)
if [[ -z "$BODY" ]]; then
    BODY=$(echo "$INPUT" | jq -r '.tool_input // empty' 2>/dev/null || true)
fi

if [[ -z "$BODY" ]]; then
    exit 0
fi

# BSD-grep compatible: -E (POSIX extended), explicit char classes (no \d, no -P).
# Pattern matches `[skill:` or `[rule:` followed by a letter and a closing `]`,
# deliberately excluding the angle-bracket form `[skill:<name>]` (the first
# char after the colon is `<`, not a letter) and ignoring partial fragments
# without a closing bracket.
PATTERN='\[(skill|rule):[a-zA-Z][a-zA-Z0-9-]*\]'

TMPFILE=$(mktemp -t slug-form-hits.XXXXXX) || exit 0
trap 'rm -f "$TMPFILE"' EXIT

if echo "$BODY" | grep -oE "$PATTERN" >"$TMPFILE" 2>/dev/null && [[ -s "$TMPFILE" ]]; then
    HITS=$(sort -u "$TMPFILE" | head -10 | sed 's/^/  /')
    cat >&2 <<HOOKEOF
BLOCKED: Outbound agent message contains literal [skill:slug] / [rule:slug] tokens.

The host parser tries to resolve these even inside backticks and drops the
entire message when resolution fails (LESSON 323a0f5 compound finding).

Offending tokens:
$HITS

Use the angle-bracket form instead: [skill:<name>] or [rule:<name>].
The angle-bracket form is documentation-safe and survives the parser.

Then retry send_agent_message.
HOOKEOF
    exit 2
fi

exit 0
