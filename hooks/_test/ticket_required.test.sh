#!/bin/bash
# Test: hooks/git/ticket-required.sh
#
# Exercises platform-agnostic ticket enforcement at PreToolUse on
# git commit. Blocks commits without a ticket reference, accepts
# GitHub, GitLab, Jira, URL, and [task: ...] formats.
#
# Ref: claude-configs-public#320

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/git/ticket-required.sh"

# shellcheck source=./run_scenarios.sh
source "$SCRIPT_DIR/run_scenarios.sh"

make_payload() {
    jq -n --arg cmd "$1" '{"tool_input":{"command":$cmd}}'
}

# --- BLOCKS: no ticket reference ---

expect_block "(a) bare commit, no ticket" "$HOOK" \
    "$(make_payload 'git commit -m "fix: typo in readme"')"
expect_block "(b) descriptive message, still no ticket" "$HOOK" \
    "$(make_payload 'git commit -m "refactor: extract helper for boundary lookup"')"

# --- ALLOWS: GitHub/GitLab style ---

expect_pass "(c) GitHub #NNN" "$HOOK" \
    "$(make_payload 'git commit -m "fix: boundary lookup Refs: #42"')"
expect_pass "(d) GitHub repo#NNN" "$HOOK" \
    "$(make_payload 'git commit -m "fix: lookup Refs: electinfo/enterprise#42"')"
expect_pass "(e) GitLab #NNN (same pattern)" "$HOOK" \
    "$(make_payload 'git commit -m "fix: pipeline issue #15"')"

# --- ALLOWS: Jira/Linear style ---

expect_pass "(f) Jira PROJ-NNN" "$HOOK" \
    "$(make_payload 'git commit -m "fix: auth flow Part-of: PROJ-123"')"
expect_pass "(g) Linear ELE-NNN" "$HOOK" \
    "$(make_payload 'git commit -m "fix: login crash Refs: ELE-42"')"
expect_pass "(h) SU- prefix" "$HOOK" \
    "$(make_payload 'git commit -m "fix: error handling SU-7"')"

# --- ALLOWS: URL-based references ---

expect_pass "(i) Jira browse URL" "$HOOK" \
    "$(make_payload 'git commit -m "fix: auth Refs: https://jira.example.com/browse/PROJ-123"')"
expect_pass "(j) GitHub issues URL" "$HOOK" \
    "$(make_payload 'git commit -m "fix: crash Refs: https://github.com/org/repo/issues/42"')"
expect_pass "(k) GitLab merge_requests URL" "$HOOK" \
    "$(make_payload 'git commit -m "fix: pipeline Refs: https://gitlab.com/group/repo/-/merge_requests/15"')"
expect_pass "(l) Shortcut stories URL" "$HOOK" \
    "$(make_payload 'git commit -m "fix: story Refs: https://app.shortcut.com/org/stories/12345"')"
expect_pass "(m) Generic tasks URL" "$HOOK" \
    "$(make_payload 'git commit -m "fix: task Refs: https://tracker.example.com/tasks/99"')"

# --- ALLOWS: [task: ...] marker ---

expect_pass "(n) [task: spreadsheet row]" "$HOOK" \
    "$(make_payload 'git commit -m "fix: geocoder [task: Sprint Q2 sheet row 14]"')"
expect_pass "(o) [task: shared doc reference]" "$HOOK" \
    "$(make_payload 'git commit -m "chore: config update [task: geocoder refactor from shared planning doc]"')"

# --- BLOCKS: invalid [task] markers ---

expect_block "(p) bare [task] without colon" "$HOOK" \
    "$(make_payload 'git commit -m "fix: something [task]"')"
expect_block "(q) [task:] with no description" "$HOOK" \
    "$(make_payload 'git commit -m "fix: something [task:]"')"

# --- ALLOWS: overrides ---

expect_pass "(r) [no-ticket] override" "$HOOK" \
    "$(make_payload 'git commit -m "chore: formatting [no-ticket]"')"

# --- ALLOWS: non-commit commands (not in scope) ---

expect_pass "(s) git status (not a commit)" "$HOOK" \
    "$(make_payload 'git status')"
expect_pass "(t) git push (not a commit)" "$HOOK" \
    "$(make_payload 'git push origin develop')"

# --- ALLOWS: amend/merge commits (skip enforcement) ---

expect_pass "(u) git commit --amend" "$HOOK" \
    "$(make_payload 'git commit --amend')"
expect_pass "(v) git commit --no-edit" "$HOOK" \
    "$(make_payload 'git commit --no-edit')"

if [[ "${_HARNESS_FAIL:-0}" -gt 0 ]]; then
    printf '\nFAIL: %d test(s) failed.\n' "$_HARNESS_FAIL" >&2
    exit 1
fi
printf '\nALL PASS: %d scenarios passed.\n' "${_HARNESS_PASS:-0}"
