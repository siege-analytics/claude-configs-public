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

TMP=$(mktemp -d)
trap 'chmod -R u+rwX "$TMP" 2>/dev/null || true; rm -rf "$TMP"' EXIT
FIXTURE="$TMP/repo with spaces"
mkdir -p "$FIXTURE/message-dir"
git -C "$FIXTURE" init -q
git -C "$FIXTURE" remote add origin git@github.com:siege-analytics/ticket-fixture.git
printf 'file subject\n\nRefs: #994\n' > "$FIXTURE/ticketed message.txt"
printf 'file subject without reference\n' > "$FIXTURE/no-ticket.txt"
printf 'filename token is incidental\n' > "$FIXTURE/incidental-#994.txt"
printf 'quoted operator path\n\nRefs: #994\n' > "$FIXTURE/ticketed;message.txt"
printf 'quoted operator path without reference\n' > "$FIXTURE/no-ticket;message.txt"
printf 'subject only\n\n# ------------------------ >8 ------------------------\nRefs: #994\n' > "$FIXTURE/scissors-after.txt"
printf 'subject\n\nRefs: #994\n\n# ------------------------ >8 ------------------------\nignored\n' > "$FIXTURE/scissors-before.txt"
printf 'unreadable Refs: #994\n' > "$FIXTURE/unreadable.txt"
chmod 000 "$FIXTURE/unreadable.txt"
mkfifo "$FIXTURE/message-fifo"

make_payload() {
    local command="$1"
    local cwd="${2:-$FIXTURE}"
    jq -n --arg cmd "$command" --arg cwd "$cwd" \
        '{"cwd":$cwd,"tool_input":{"command":$cmd,"cwd":$cwd}}'
}

make_top_level_cwd_payload() {
    local command="$1"
    local cwd="${2:-$FIXTURE}"
    jq -n --arg cmd "$command" --arg cwd "$cwd" \
        '{"cwd":$cwd,"tool_input":{"command":$cmd}}'
}

MULTILINE_TICKETED=$(cat <<'COMMAND'
git commit --allow-empty -m 'subject

Refs: #994'
COMMAND
)
MULTILINE_TICKETLESS_AUTHOR=$(cat <<'COMMAND'
git commit --allow-empty -m 'subject

body' --author='Refs: #994 <test@example.com>'
COMMAND
)
BACKTICK_TICKETLESS_AUTHOR=$(cat <<'COMMAND'
git commit --allow-empty -m 'use `ls` here' --author='Refs: #994 <test@example.com>'
COMMAND
)
DOLLAR_PAREN_TICKETLESS_AUTHOR=$(cat <<'COMMAND'
git commit --allow-empty -m 'cost $(x)' --author='Refs: #994 <test@example.com>'
COMMAND
)
DOLLAR_TICKETLESS_AUTHOR=$(cat <<'COMMAND'
git commit --allow-empty -m 'price $5' --author='Refs: #994 <test@example.com>'
COMMAND
)
BACKSLASH_TICKETLESS_AUTHOR=$(cat <<'COMMAND'
git commit --allow-empty -m 'C:\temp' --author='Refs: #994 <test@example.com>'
COMMAND
)
DOUBLE_EXPANSION_TICKETLESS_AUTHOR=$(cat <<'COMMAND'
git commit --allow-empty -m "home $HOME" --author='Refs: #994 <test@example.com>'
COMMAND
)
HEREDOC_TICKETED=$(cat <<'COMMAND'
git commit --allow-empty -m "$(cat <<'EOF'
subject

Refs: #994
EOF
)"
COMMAND
)
HEREDOC_TICKETLESS_AUTHOR=$(cat <<'COMMAND'
git commit --allow-empty -m "$(cat <<'EOF'
subject only
EOF
)" --author='Refs: #994 <test@example.com>'
COMMAND
)

# --- BLOCKS: no ticket reference ---

expect_block "(a) bare commit, no ticket" "$HOOK" \
    "$(make_payload 'git commit -m "fix: typo in readme"')"
expect_block "(b) descriptive message, still no ticket" "$HOOK" \
    "$(make_payload 'git commit -m "refactor: extract helper for boundary lookup"')"
expect_block "(b2) incidental ticket in author does not satisfy -m" "$HOOK" \
    "$(make_payload 'git commit --author="Refs: #994 <test@example.com>" -m "subject only"')"
expect_block "(b2a) incidental ticket in pathspec does not satisfy -m" "$HOOK" \
    "$(make_payload 'git commit -m "subject only" -- path-#994.txt')"
expect_block "(b2b) quoted operator message does not fall back to incidental author" "$HOOK" \
    "$(make_payload 'git commit -m ";" --author="Refs: #994 <test@example.com>"')"
expect_pass "(b2c) quoted operator stays literal in ticketed message" "$HOOK" \
    "$(make_payload 'git commit -m "subject; Refs: #994"')"
expect_block "(b2d) malformed quoted message remains denied" "$HOOK" \
    "$(make_payload 'git commit -m "unterminated')"
expect_pass "(b3) repeated -m paragraphs use effective message" "$HOOK" \
    "$(make_payload 'git commit -m "subject" -m "Refs: #994"')"
expect_pass "(b4) attached -m uses effective message" "$HOOK" \
    "$(make_payload 'git commit -mRefs:#994')"

# --- DIRECT MESSAGE MODEL: literals, heredoc, long forms, and clusters ---

expect_block "(model1) multiline ticketless message ignores incidental author" "$HOOK" \
    "$(make_payload "$MULTILINE_TICKETLESS_AUTHOR")"
expect_pass "(model2) multiline ticketed message stays allowed" "$HOOK" \
    "$(make_payload "$MULTILINE_TICKETED")"
expect_block "(model3) single-quoted backticks ignore incidental author" "$HOOK" \
    "$(make_payload "$BACKTICK_TICKETLESS_AUTHOR")"
expect_block "(model4) single-quoted dollar parens ignore incidental author" "$HOOK" \
    "$(make_payload "$DOLLAR_PAREN_TICKETLESS_AUTHOR")"
expect_block "(model5) single-quoted dollar ignores incidental author" "$HOOK" \
    "$(make_payload "$DOLLAR_TICKETLESS_AUTHOR")"
expect_block "(model6) single-quoted backslash ignores incidental author" "$HOOK" \
    "$(make_payload "$BACKSLASH_TICKETLESS_AUTHOR")"
expect_block_because "(model7) double-quoted expansion fails closed" "$HOOK" \
    "$(make_payload "$DOUBLE_EXPANSION_TICKETLESS_AUTHOR")" \
    "outside the narrow message model"
expect_pass "(model8) canonical quoted-delimiter heredoc resolves ticketed body" "$HOOK" \
    "$(make_payload "$HEREDOC_TICKETED")"
expect_block "(model9) canonical heredoc ticketless body ignores incidental author" "$HOOK" \
    "$(make_payload "$HEREDOC_TICKETLESS_AUTHOR")"
expect_pass "(model10) --message value resolves ticketed message" "$HOOK" \
    "$(make_payload 'git commit --message "Refs: #994"')"
expect_block "(model11) --message value ignores incidental author" "$HOOK" \
    "$(make_payload 'git commit --message "subject only" --author="Refs: #994 <test@example.com>"')"
expect_pass "(model12) --message= resolves ticketed message" "$HOOK" \
    "$(make_payload 'git commit --message="Refs: #994"')"
expect_block "(model13) --message= ignores incidental author" "$HOOK" \
    "$(make_payload 'git commit --message="subject only" --author="Refs: #994 <test@example.com>"')"
expect_pass "(model14) unambiguous --mess= resolves ticketed message" "$HOOK" \
    "$(make_payload 'git commit --mess="Refs: #994"')"
expect_block "(model15) unambiguous --mess= ignores incidental author" "$HOOK" \
    "$(make_payload 'git commit --mess="subject only" --author="Refs: #994 <test@example.com>"')"
expect_pass "(model16) clustered -am resolves ticketed message" "$HOOK" \
    "$(make_payload 'git commit -am "Refs: #994"')"
expect_block "(model17) clustered -am ignores incidental author" "$HOOK" \
    "$(make_payload 'git commit -am "subject only" --author="Refs: #994 <test@example.com>"')"
expect_block_because "(model18) direct commit without modeled source fails closed" "$HOOK" \
    "$(make_payload 'git commit --author="Refs: #994 <test@example.com>"')" \
    "no modeled message source"

# --- FILE MESSAGE SOURCES: paired allow/deny and fail-closed errors ---

expect_pass "(f1) -F relative ticketed file" "$HOOK" \
    "$(make_payload 'git commit -F "ticketed message.txt"')"
expect_block "(f2) -F relative ticketless file" "$HOOK" \
    "$(make_payload 'git commit -F no-ticket.txt')"
expect_pass "(f3) --file relative ticketed file" "$HOOK" \
    "$(make_payload 'git commit --file "ticketed message.txt"')"
expect_block "(f4) --file relative ticketless file" "$HOOK" \
    "$(make_payload 'git commit --file no-ticket.txt')"
expect_pass "(f5) --file= relative ticketed file" "$HOOK" \
    "$(make_payload 'git commit --file="ticketed message.txt"')"
expect_block "(f6) --file= relative ticketless file" "$HOOK" \
    "$(make_payload 'git commit --file=no-ticket.txt')"
expect_pass "(f7) attached -F relative ticketed file" "$HOOK" \
    "$(make_payload 'git commit -F"ticketed message.txt"')"
expect_block "(f7a) attached -F relative ticketless file" "$HOOK" \
    "$(make_payload 'git commit -Fno-ticket.txt')"
expect_pass "(f7b) quoted operator stays literal in ticketed file path" "$HOOK" \
    "$(make_payload 'git commit -F "ticketed;message.txt"')"
expect_block "(f7c) quoted operator stays literal in ticketless file path" "$HOOK" \
    "$(make_payload 'git commit -F "no-ticket;message.txt"')"
expect_block "(f8) ticket in filename does not satisfy ticketless file" "$HOOK" \
    "$(make_payload 'git commit -F "incidental-#994.txt"')"
expect_pass "(f9) top-level cwd fallback resolves file" "$HOOK" \
    "$(make_top_level_cwd_payload 'git commit -F "ticketed message.txt"')"
expect_block_because "(f10) missing file denies" "$HOOK" \
    "$(make_payload 'git commit -F missing.txt')" \
    "message file is not readable"
expect_block_because "(f10a) quoted operator missing file does not fall back to incidental author" "$HOOK" \
    "$(make_payload 'git commit -F ";" --author="Refs: #994 <test@example.com>"')" \
    "message file is not readable"
expect_block_because "(f11) unreadable file denies" "$HOOK" \
    "$(make_payload 'git commit -F unreadable.txt')" \
    "message file is not readable"
expect_block_because "(f12) directory source denies" "$HOOK" \
    "$(make_payload 'git commit -F message-dir')" \
    "not a regular file"
expect_block_because "(f13) FIFO source denies without reading" "$HOOK" \
    "$(make_payload 'git commit -F message-fifo')" \
    "not a regular file"
expect_block_because "(f14) stdin file source is outside narrow scope" "$HOOK" \
    "$(make_payload 'git commit -F -')" \
    "outside the narrow #994 scope"
expect_block_because "(f15) mixed -m and file source denies" "$HOOK" \
    "$(make_payload 'git commit -m "Refs: #994" -F no-ticket.txt')" \
    "cannot be combined"

# --- COMMENTS, OPTION VALUES, TRAILERS, AND CLEANUP ---

expect_block "(parse1) unquoted comment hides later ticketed -m" "$HOOK" \
    "$(make_payload 'git commit -m "subject only" # -m "Refs: #994"')"
expect_pass "(parse2) quoted hash remains message data" "$HOOK" \
    "$(make_payload 'git commit -m "subject # Refs: #994"')"
expect_block "(parse3) --author value that looks like -m is consumed" "$HOOK" \
    "$(make_payload 'git commit --author "-mRefs: #994 <test@example.com>" -m "subject only"')"
expect_pass "(parse4) consumed --author value does not hide ticketed -m" "$HOOK" \
    "$(make_payload 'git commit --author "Test <test@example.com>" -m "Refs: #994"')"
expect_block "(parse5) --date value that looks like -m is consumed" "$HOOK" \
    "$(make_payload 'git commit --date "-mRefs: #994" -m "subject only"')"
expect_pass "(parse6) consumed --date value does not hide ticketed -m" "$HOOK" \
    "$(make_payload 'git commit --date now -m "Refs: #994"')"
expect_block "(parse7) --pathspec-from-file value that looks like -m is consumed" "$HOOK" \
    "$(make_payload 'git commit --pathspec-from-file "-mRefs: #994" -m "subject only"')"
expect_pass "(parse8) consumed pathspec option does not hide ticketed -m" "$HOOK" \
    "$(make_payload 'git commit --pathspec-from-file paths.txt -m "Refs: #994"')"
expect_block_because "(parse9) -C supplied message fails closed" "$HOOK" \
    "$(make_payload 'git commit -C "Refs: #994"')" \
    "supplies a message this helper cannot model"
expect_block_because "(parse10) -c supplied message fails closed" "$HOOK" \
    "$(make_payload 'git commit -c "Refs: #994"')" \
    "supplies a message this helper cannot model"
expect_block_because "(parse11) template supplied message fails closed" "$HOOK" \
    "$(make_payload 'git commit -t "Refs: #994"')" \
    "supplies a message this helper cannot model"
expect_block_because "(parse12) fixup supplied message fails closed" "$HOOK" \
    "$(make_payload 'git commit --fixup "Refs: #994"')" \
    "supplies a message this helper cannot model"
expect_block_because "(parse13) squash supplied message fails closed" "$HOOK" \
    "$(make_payload 'git commit --squash "Refs: #994"')" \
    "supplies a message this helper cannot model"
expect_pass "(parse14) ticket trailer contributes to effective message" "$HOOK" \
    "$(make_payload 'git commit -m "subject" --trailer "Refs: #994"')"
expect_block "(parse15) ticketless trailer ignores incidental author" "$HOOK" \
    "$(make_payload 'git commit -m "subject" --trailer "Reviewed-by: Test" --author="Refs: #994 <test@example.com>"')"
expect_block "(parse16) cleanup strip removes hash-only ticket paragraph" "$HOOK" \
    "$(make_payload 'git commit --cleanup=strip -m "subject" -m "#994"')"
expect_pass "(parse17) cleanup strip preserves non-comment ticket paragraph" "$HOOK" \
    "$(make_payload 'git commit --cleanup=strip -m "subject" -m "Refs: #994"')"
expect_block "(parse18) cleanup scissors truncates ticket after marker" "$HOOK" \
    "$(make_payload 'git commit --cleanup=scissors -F scissors-after.txt')"
expect_pass "(parse19) cleanup scissors preserves ticket before marker" "$HOOK" \
    "$(make_payload 'git commit --cleanup=scissors -F scissors-before.txt')"
git -C "$FIXTURE" config commit.cleanup strip
expect_block "(parse20) configured cleanup strip removes hash-only ticket paragraph" "$HOOK" \
    "$(make_payload 'git commit -m "subject" -m "#994"')"
expect_pass "(parse21) configured cleanup strip preserves non-comment ticket paragraph" "$HOOK" \
    "$(make_payload 'git commit -m "subject" -m "Refs: #994"')"
git -C "$FIXTURE" config --unset commit.cleanup
expect_pass "(parse22) cleanup scissors preserves pre-cut comment ticket like Git" "$HOOK" \
    "$(make_payload 'git commit --cleanup=scissors -m "subject" -m "#994"')"
expect_pass "(parse23) last cleanup option whitespace preserves comment ticket" "$HOOK" \
    "$(make_payload 'git commit -m "subject" -m "#994" --cleanup=strip --cleanup=whitespace')"
expect_block "(parse24) last cleanup option strip removes comment ticket" "$HOOK" \
    "$(make_payload 'git commit -m "subject" -m "#994" --cleanup=whitespace --cleanup=strip')"

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

# The bare [no-ticket] form this scenario used was blocked on purpose by #580,
# which requires the Reason/Evidence/Falsification chain. The scenario still
# pins down that a valid override opens the gate; the accepted shape changed.
expect_pass "(r) structured [no-ticket] override" "$HOOK" \
    "$(make_payload 'git commit -m "chore: formatting [no-ticket: Reason: whitespace only; Evidence: diff is all trailing spaces; Falsification: any semantic change in the diff]"')"

# The bare form is now blocked rather than allowed; assert that too, so a
# regression that re-opens it fails here rather than passing by omission.
expect_block_because "(r2) bare [no-ticket] is blocked" "$HOOK" \
    "$(make_payload 'git commit -m "chore: formatting [no-ticket]"')" \
    "'\[no-ticket\]' override now requires evidence chain"

# --- ALLOWS: non-commit commands (not in scope) ---

expect_pass "(s) git status (not a commit)" "$HOOK" \
    "$(make_payload 'git status')"
expect_pass "(t) git push (not a commit)" "$HOOK" \
    "$(make_payload 'git push origin develop')"

# Finding #7 regression matrix: routine reads must stay outside message parsing.
expect_pass "(read1) git diff tilde revision" "$HOOK" \
    "$(make_payload 'git diff HEAD~1')"
expect_pass "(read2) git log revision range" "$HOOK" \
    "$(make_payload 'git log --oneline HEAD~1..HEAD')"
expect_pass "(read3) git show reflog expression" "$HOOK" \
    "$(make_payload 'git show HEAD@{0} --stat')"
expect_pass "(read4) workflow glob" "$HOOK" \
    "$(make_payload 'ls .github/workflows/*.yml')"
expect_pass "(read5) home gitconfig" "$HOOK" \
    "$(make_payload 'cat ~/.gitconfig')"
expect_pass "(read6) expanded HOME path containing git" "$HOOK" \
    "$(make_payload 'echo $HOME/git')"
expect_pass "(read7) newline-separated git reads" "$HOOK" \
    "$(make_payload $'git status\ngit log -1 --oneline')"
expect_pass "(read8) piped git status" "$HOOK" \
    "$(make_payload 'git status --short | cat')"
expect_pass "(read9) printf HOME" "$HOOK" \
    "$(make_payload 'printf '\''%s\\n'\'' "${HOME}"')"
expect_pass "(read10) literal cd then status" "$HOOK" \
    "$(make_payload "cd '$FIXTURE' && git status")"
expect_pass "(read11) expanded cd then ls" "$HOOK" \
    "$(make_payload 'cd "$HOME" && ls')"
expect_pass "(read12) expanded cd then status" "$HOOK" \
    "$(make_payload 'cd "$HOME" && git status')"
expect_pass "(read13) caret revision" "$HOOK" \
    "$(make_payload 'git diff HEAD^ --stat')"
expect_pass "(read14) plain status" "$HOOK" \
    "$(make_payload 'git status')"
expect_pass "(read15) plain log" "$HOOK" \
    "$(make_payload 'git log -1 --oneline')"

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
