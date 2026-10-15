#!/bin/bash
# Test: hooks/git/ticket-required.sh
#
# Exercises effective-message resolution, hostile shell/file inputs, Git source
# precedence, and platform-agnostic ticket validation.
#
# Ref: claude-configs-public#320, #994

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/git/ticket-required.sh"

# shellcheck source=./run_scenarios.sh
source "$SCRIPT_DIR/run_scenarios.sh"

TMP=$(mktemp -d)
trap 'chmod -R u+rwX "$TMP" 2>/dev/null || true; rm -rf "$TMP"' EXIT
FIXTURE="$TMP/repo with spaces"
mkdir -p "$FIXTURE/sub/dir"
git -C "$FIXTURE" init -q
git -C "$FIXTURE" config user.email test@example.com
git -C "$FIXTURE" config user.name Test
git -C "$FIXTURE" remote add origin git@github.com:siege-analytics/ticket-fixture.git
git -C "$FIXTURE" commit -q --allow-empty -m 'base without reference'
git -C "$FIXTURE" tag no-ticket
git -C "$FIXTURE" commit -q --allow-empty -m $'ticketed subject\n\nRefs: #994'
git -C "$FIXTURE" tag with-ticket

printf 'file subject\n\nRefs: #331\n' > "$FIXTURE/message file.txt"
printf 'file subject without reference\n' > "$FIXTURE/no-ticket.txt"
printf 'literal question path Refs: #994\n' > "$FIXTURE/message?.txt"
printf 'template subject\n\nRefs: #444\n' > "$FIXTURE/template.txt"
printf 'first source Refs: #111\n' > "$FIXTURE/first.txt"
printf 'second source without reference\n' > "$FIXTURE/second.txt"
printf 'unreadable Refs: #994\n' > "$FIXTURE/unreadable.txt"
chmod 000 "$FIXTURE/unreadable.txt"
dd if=/dev/zero bs=1048577 count=1 2>/dev/null | tr '\0' x > "$FIXTURE/oversized.txt"
printf 'outside Refs: #994\n' > "$TMP/outside.txt"
ln -s "$TMP/outside.txt" "$FIXTURE/outside-link.txt"
mkdir -p "$FIXTURE/real-message-dir"
printf 'inside Refs: #994\n' > "$FIXTURE/real-message-dir/message.txt"
ln -s "$FIXTURE/real-message-dir" "$FIXTURE/symlink-message-dir"

HEREDOC_WITH_TICKET=$(cat <<'COMMAND'
git commit -F - <<'EOF'
subject

Refs: #994
EOF
COMMAND
)
HEREDOC_WITHOUT_TICKET=$(cat <<'COMMAND'
git commit --file=- <<'MSG'
subject only
MSG
COMMAND
)
UNQUOTED_HEREDOC=$(cat <<'COMMAND'
git commit -F - <<EOF
Refs: #994
EOF
COMMAND
)
SHELL_EXPANSION_COMMAND=$(cat <<'COMMAND'
git commit -m "subject $(printf 'Refs: #994')"
COMMAND
)
NEWLINE_CHAIN_COMMAND=$(cat <<'COMMAND'
git commit -m "Refs: #994"
git commit --no-verify -m "subject only"
COMMAND
)
FAKE_HEREDOC_ARGUMENT=$(cat <<'COMMAND'
git commit -F - --author="Person <<'EOF'"
Refs: #994
EOF
COMMAND
)
STDERR_HEREDOC=$(cat <<'COMMAND'
git commit -F - 2<<'EOF'
Refs: #994
EOF
COMMAND
)

make_payload() {
    local command="$1"
    local cwd="${2:-$FIXTURE}"
    jq -n --arg cmd "$command" --arg cwd "$cwd" \
        '{"cwd":$cwd,"tool_input":{"command":$cmd,"cwd":$cwd}}'
}

make_top_level_cwd_payload() {
    jq -n --arg cmd "$1" --arg cwd "$FIXTURE" \
        '{"cwd":$cwd,"tool_input":{"command":$cmd}}'
}

# --- Basic and multiple-paragraph -m/--message forms ---
expect_block "(a) -m without ticket" "$HOOK" \
    "$(make_payload 'git commit -m "fix: typo"')"
expect_pass "(b) -m GitHub ticket" "$HOOK" \
    "$(make_payload 'git commit -m "fix: lookup Refs: #42"')"
expect_pass "(c) multiple -m paragraphs" "$HOOK" \
    "$(make_payload 'git commit -m "subject" -m "body with spaces" -m "Refs: #994"')"
expect_pass "(d) --message= with Jira ticket" "$HOOK" \
    "$(make_payload 'git commit --message="subject Refs: PROJ-123"')"
expect_pass "(e) clustered -am" "$HOOK" \
    "$(make_payload 'git commit -am "subject Refs: ELE-42"')"
expect_pass "(f) literal newline inside quoted message" "$HOOK" \
    "$(make_payload $'git commit -m "subject\n\nRefs: #994"')"
expect_pass "(g) quoted punctuation" "$HOOK" \
    "$(make_payload "git commit -m 'fix: preserve \"quoted value\"; Refs: #994'")"
expect_pass "(h) top-level cwd fallback" "$HOOK" \
    "$(make_top_level_cwd_payload 'git commit -m "subject Refs: #994"')"

# --- Accepted tracker/task/override shapes are shared with commit-msg ---
expect_pass "(i) repository-qualified GitHub ticket" "$HOOK" \
    "$(make_payload 'git commit -m "Refs: owner/repo#42"')"
expect_pass "(j) tracker URL without hash" "$HOOK" \
    "$(make_payload 'git commit -m "Refs: https://tracker.example.com/tasks/99"')"
expect_pass "(k) task marker" "$HOOK" \
    "$(make_payload 'git commit -m "[task: Sprint Q2 sheet row 14]"')"
expect_pass "(l) structured no-ticket override" "$HOOK" \
    "$(make_payload 'git commit -m "[no-ticket: Reason: local fixture; Evidence: no tracker exists; Falsification: a tracker item is found]"')"
expect_block_because "(m) bare no-ticket override" "$HOOK" \
    "$(make_payload 'git commit -m "[no-ticket]"')" \
    "override now requires evidence chain"
expect_block_because "(n) mixed bare and structured overrides" "$HOOK" \
    "$(make_payload 'git commit -m "[no-ticket] [no-ticket: Reason: local; Evidence: fixture; Falsification: ticket found]"')" \
    "override now requires evidence chain"
expect_block "(o) empty task marker" "$HOOK" \
    "$(make_payload 'git commit -m "[task:]"')"
expect_block "(p) whitespace task marker" "$HOOK" \
    "$(make_payload 'git commit -m "[task:   ]"')"
expect_block "(q) whitespace override evidence" "$HOOK" \
    "$(make_payload 'git commit -m "[no-ticket: Reason:   ; Evidence: fixture; Falsification: ticket found]"')"

# --- -F/--file paths resolve from tool_input.cwd ---
expect_pass "(o) -F relative path with spaces" "$HOOK" \
    "$(make_payload 'git commit -F "message file.txt"')"
expect_pass "(p) --file= relative path with spaces" "$HOOK" \
    "$(make_payload 'git commit --file="message file.txt"')"
expect_pass "(q) -F relative to nested cwd" "$HOOK" \
    "$(make_payload 'git commit -F "../../message file.txt"' "$FIXTURE/sub/dir")"
expect_pass "(r) absolute file inside repository" "$HOOK" \
    "$(make_payload "git commit -F '$FIXTURE/message file.txt'")"
expect_pass "(r2) quoted glob character is literal" "$HOOK" \
    "$(make_payload 'git commit -F "message?.txt"')"
expect_block_because "(r3) unquoted tilde expansion fails closed" "$HOOK" \
    "$(make_payload 'git commit -F ~/message.txt')" \
    "unquoted shell pathname expansion"
expect_block_because "(r4) unquoted glob expansion fails closed" "$HOOK" \
    "$(make_payload 'git commit -F *.txt')" \
    "unquoted shell pathname expansion"
expect_block_because "(r5) unquoted brace expansion fails closed" "$HOOK" \
    "$(make_payload 'git commit -F message{1,2}.txt')" \
    "unquoted shell pathname expansion"
expect_block "(s) file content without ticket" "$HOOK" \
    "$(make_payload 'git commit -F no-ticket.txt')"
expect_block_because "(t) missing file fails closed" "$HOOK" \
    "$(make_payload 'git commit -F missing.txt')" \
    "missing or unreadable"
expect_block_because "(u) unreadable file fails closed" "$HOOK" \
    "$(make_payload 'git commit -F unreadable.txt')" \
    "missing or unreadable"
expect_block_because "(v) outside absolute path is rejected" "$HOOK" \
    "$(make_payload "git commit -F '$TMP/outside.txt'")" \
    "outside the repository"
expect_block_because "(w) symlink escape is rejected" "$HOOK" \
    "$(make_payload 'git commit -F outside-link.txt')" \
    "outside the repository"
expect_pass "(w1) in-repository symlink target is pinned safely" "$HOOK" \
    "$(make_payload 'git commit -F symlink-message-dir/message.txt')"
expect_block_because "(w2) oversized file fails before allocation" "$HOOK" \
    "$(make_payload 'git commit -F oversized.txt')" \
    "exceeds the 1 MiB safety limit"
expect_block "(x) repeated -F uses last file" "$HOOK" \
    "$(make_payload 'git commit -F first.txt -F second.txt')"
expect_pass "(y) repeated -F last file can satisfy" "$HOOK" \
    "$(make_payload 'git commit -F second.txt -F first.txt')"
expect_block_because "(z) conflicting -m and -F fail closed" "$HOOK" \
    "$(make_payload 'git commit -m "Refs: #994" -F no-ticket.txt')" \
    "conflicting git commit message sources"

# --- stdin is accepted only when it is a literal quoted heredoc ---
expect_pass "(aa) -F - quoted heredoc" "$HOOK" \
    "$(make_payload "$HEREDOC_WITH_TICKET")"
expect_block "(ab) heredoc content without ticket" "$HOOK" \
    "$(make_payload "$HEREDOC_WITHOUT_TICKET")"
expect_block_because "(ac) opaque -F - stdin fails closed" "$HOOK" \
    "$(make_payload 'git commit -F -')" \
    "requires a literal quoted heredoc"
expect_block_because "(ad) unquoted heredoc fails closed" "$HOOK" \
    "$(make_payload "$UNQUOTED_HEREDOC")" \
    "must use one quoted delimiter"
expect_block_because "(ae) piped stdin fails closed" "$HOOK" \
    "$(make_payload 'printf "Refs: #994" | git commit -F -')" \
    "pipelines, redirects, and command chains"
expect_block_because "(ae2) quoted argv is not a heredoc operator" "$HOOK" \
    "$(make_payload "$FAKE_HEREDOC_ARGUMENT")" \
    "newline-separated shell commands"
expect_block_because "(ae3) stderr heredoc cannot satisfy -F -" "$HOOK" \
    "$(make_payload "$STDERR_HEREDOC")" \
    "must redirect standard input"

# --- Repository-state sources follow Git edit semantics ---
expect_pass "(af) -C reuses ticketed commit" "$HOOK" \
    "$(make_payload 'git commit -C with-ticket')"
expect_block "(ag) --reuse-message reuses unticketed commit" "$HOOK" \
    "$(make_payload 'git commit --reuse-message=no-ticket')"
expect_pass "(ah) -c with --no-edit is deterministic" "$HOOK" \
    "$(make_payload 'git commit -c with-ticket --no-edit')"
expect_block "(ai) -c --no-edit preserves missing ticket" "$HOOK" \
    "$(make_payload 'git commit --no-edit --reedit-message=no-ticket')"
expect_block_because "(aj) -c without --no-edit fails closed" "$HOOK" \
    "$(make_payload 'git commit -c with-ticket')" \
    "changed by an editor"
expect_block_because "(ak) -C with --edit fails closed" "$HOOK" \
    "$(make_payload 'git commit --edit -C with-ticket')" \
    "changed by an editor"
expect_pass "(al) --amend --no-edit reads HEAD" "$HOOK" \
    "$(make_payload 'git commit --amend --no-edit')"
expect_pass "(am) amend explicit -m replaces HEAD" "$HOOK" \
    "$(make_payload 'git commit --amend --no-edit -m "replacement Refs: #994"')"
expect_pass "(an) amend explicit -F replaces HEAD" "$HOOK" \
    "$(make_payload 'git commit --amend --no-edit -F "message file.txt"')"

git -C "$FIXTURE" reset -q --hard no-ticket
expect_block "(ao) amend no-edit blocks unticketed HEAD" "$HOOK" \
    "$(make_payload 'git commit --amend --no-edit')"
git -C "$FIXTURE" reset -q --hard with-ticket

# --- Templates and option order match Git's editor behavior ---
expect_pass "(ap) template is ignored beside -m" "$HOOK" \
    "$(make_payload 'git commit -t template.txt -m "Refs: #994"')"
expect_pass "(aq) template is ignored beside -C" "$HOOK" \
    "$(make_payload 'git commit --template=template.txt -C with-ticket')"
expect_pass "(ar) template is ignored by amend no-edit" "$HOOK" \
    "$(make_payload 'git commit --template template.txt --amend --no-edit')"
expect_block_because "(as) template-only message requires editor" "$HOOK" \
    "$(make_payload 'git commit -t template.txt')" \
    "still requires an editor"
expect_block_because "(at) -F with --edit requires editor" "$HOOK" \
    "$(make_payload 'git commit --edit -F "message file.txt"')" \
    "changed by an editor"
expect_block_because "(at2) strip cleanup fails closed" "$HOOK" \
    "$(make_payload 'git commit --cleanup=strip -m "subject Refs: #994"')" \
    "can remove validated message content"
expect_block_because "(at3) scissors cleanup fails closed" "$HOOK" \
    "$(make_payload 'git commit -m "subject Refs: #994" --cleanup scissors')" \
    "can remove validated message content"
expect_pass "(at4) whitespace cleanup preserves content" "$HOOK" \
    "$(make_payload 'git commit --cleanup=whitespace -m "subject Refs: #994"')"
git -C "$FIXTURE" config commit.cleanup strip
expect_block_because "(at5) configured strip cleanup fails closed" "$HOOK" \
    "$(make_payload 'git commit -m "subject Refs: #994"')" \
    "configured commit.cleanup=strip"
git -C "$FIXTURE" config --unset commit.cleanup
expect_pass "(au) git global -C before commit" "$HOOK" \
    "$(make_payload "git -C '$FIXTURE' commit -m 'Refs: #994'")"
expect_pass "(av) absolute cd prefix with quoted spaces" "$HOOK" \
    "$(make_payload "cd '$FIXTURE/sub/dir' && git commit -m 'Refs: #994'")"
expect_block_because "(av2) relative cd prefix fails closed" "$HOOK" \
    "$(make_payload "cd sub/dir && git commit -m 'Refs: #994'")" \
    "relative cd prefixes are unsupported"

# --- Tickets outside the selected message cannot bypass the guard ---
expect_block "(aw) ticket in pathspec is ignored" "$HOOK" \
    "$(make_payload 'git commit -m "subject only" -- "unrelated-#994.txt"')"
expect_block "(ax) ticket in author argv is ignored" "$HOOK" \
    "$(make_payload 'git commit --author="Person #994 <p@example.com>" -m "subject only"')"
expect_block "(ay) ticket in template filename is ignored" "$HOOK" \
    "$(make_payload 'git commit -t "ticket-#994.txt" -m "subject only"')"
expect_block "(az) ticket in cleanup argv is ignored" "$HOOK" \
    "$(make_payload 'git commit --cleanup="#994" -m "subject only"')"
expect_block "(az2) ticket-bearing option in shell comment is ignored" "$HOOK" \
    "$(make_payload 'git commit -m "subject only" # -m "Refs: #994"')"
expect_block "(az3) bare ticket in shell comment is ignored" "$HOOK" \
    "$(make_payload 'git commit -m "subject only" #994')"
expect_block_because "(ba) ticket in earlier shell command cannot bypass" "$HOOK" \
    "$(make_payload 'echo "#994" && git commit -m "subject only"')" \
    "only a literal 'cd <path> && git commit' prefix"
expect_block_because "(ba2) subshell commit fails closed" "$HOOK" \
    "$(make_payload '(git commit -m "Refs: #994")')" \
    "pipelines, redirects, and command chains"
expect_block_because "(bb) shell expansion fails closed" "$HOOK" \
    "$(make_payload "$SHELL_EXPANSION_COMMAND")" \
    "shell expansion"
expect_block_because "(bb2) newline-separated second commit fails closed" "$HOOK" \
    "$(make_payload "$NEWLINE_CHAIN_COMMAND")" \
    "newline-separated shell commands"
expect_block_because "(bb3) unsupported git global config fails closed" "$HOOK" \
    "$(make_payload 'git -c core.hooksPath=/dev/null commit --allow-empty -m "subject only"')" \
    "unsupported git global options before commit"
expect_block_because "(bc) environment wrapper fails closed" "$HOOK" \
    "$(make_payload 'env GIT_EDITOR=true git commit -m "Refs: #994"')" \
    "wrappers and environment prefixes"
expect_block_because "(bd) assignment prefix fails closed" "$HOOK" \
    "$(make_payload 'GIT_EDITOR=true git commit -m "Refs: #994"')" \
    "wrappers and environment prefixes"
expect_pass "(be) absolute git executable is supported" "$HOOK" \
    "$(make_payload '/usr/bin/git commit -m "Refs: #994"')"
expect_pass "(bf) optional -S does not consume -m" "$HOOK" \
    "$(make_payload 'git commit -S -m "Refs: #994"')"
expect_pass "(bg) optional -u does not consume -m" "$HOOK" \
    "$(make_payload 'git commit -u -m "Refs: #994"')"

# --- Commands outside this hook's surface pass ---
expect_pass "(bh) git status" "$HOOK" "$(make_payload 'git status')"
expect_pass "(bi) git push" "$HOOK" "$(make_payload 'git push origin develop')"

if [[ "${_HARNESS_FAIL:-0}" -gt 0 ]]; then
    printf '\nFAIL: %d test(s) failed.\n' "$_HARNESS_FAIL" >&2
    exit 1
fi
printf '\nALL PASS: %d scenarios passed.\n' "${_HARNESS_PASS:-0}"
