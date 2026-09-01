#!/bin/bash
# Test: hooks/write/ticket-propagation-guard.sh
#
# Regression coverage for #688: the guard chose its frontmatter branch with
# `echo "$CONTENT" | head -1` under `set -o pipefail`. Above the pipe buffer
# `echo` takes SIGPIPE, pipefail propagates 141, and the branch is skipped, so
# valid `ticket_refs:` frontmatter was ignored on large artifacts only.
#
# The size pairs below are the point of this file. Asserting exit 0 on a large
# compliant artifact alone would also pass if the guard were disabled, so every
# compliant case is paired with a non-compliant one of the same size.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/write/ticket-propagation-guard.sh"

# shellcheck source=./run_scenarios.sh
source "$SCRIPT_DIR/run_scenarios.sh"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/plans"

FRONTMATTER='---
ticket_refs:
  - siege-analytics/claude-configs-public#688: comment pending
---
'
BODY_REF='See siege-analytics/claude-configs-public#251 for the failure evidence.'

# $1 = target file, $2 = "with-fm"|"no-fm", $3 = filler bytes
make_artifact() {
    local path="$1" fm="$2" bytes="$3"
    : > "$path"
    [[ "$fm" == "with-fm" ]] && printf '%s' "$FRONTMATTER" >> "$path"
    printf '# Artifact\n\n%s\n\n' "$BODY_REF" >> "$path"
    # Filler includes `---` horizontal rules, which every real plans artifact has.
    python3 -c "import sys; n=int(sys.argv[1]); sys.stdout.write(('---\n\nfiller paragraph text\n\n')*(n//30))" "$bytes" >> "$path"
}

# The guard now evaluates the content an edit would produce, not the file on
# disk, so an edit payload has to be a real edit. The identity replacement below
# is the one that leaves the artifact unchanged; the previous `a` -> `b` dummy
# rewrote `propagation` to `propbgation` and made scenario (i) block for a
# reason the scenario was not about. Every fixture in this file contains #251.
payload() {
    printf '{"tool_name":"Edit","tool_input":{"file_path":"%s","old_string":"#251","new_string":"#251"}}' "$1"
}

# --- Large artifacts: the #688 regression. 200KB clears any platform pipe buffer.

make_artifact "$TMP/plans/large-compliant.md" with-fm 200000
make_artifact "$TMP/plans/large-noncompliant.md" no-fm 200000

expect_pass "(a) 200KB artifact WITH ticket_refs frontmatter is allowed" "$HOOK" \
    "$(payload "$TMP/plans/large-compliant.md")"
expect_block "(b) 200KB artifact WITHOUT frontmatter is still blocked" "$HOOK" \
    "$(payload "$TMP/plans/large-noncompliant.md")"

# --- Small artifacts: the behaviour that already worked, pinned against regression.

make_artifact "$TMP/plans/small-compliant.md" with-fm 1000
make_artifact "$TMP/plans/small-noncompliant.md" no-fm 1000

expect_pass "(c) 1KB artifact WITH ticket_refs frontmatter is allowed" "$HOOK" \
    "$(payload "$TMP/plans/small-compliant.md")"
expect_block "(d) 1KB artifact WITHOUT frontmatter is still blocked" "$HOOK" \
    "$(payload "$TMP/plans/small-noncompliant.md")"

# --- AC3: refs declared in frontmatter must not be reported as unpropagated.
# Exit-code assertions cannot see this symptom, so it is checked on the message.
# The fixture declares `ticket_refs:` whose entries are commented out, so the
# metadata check correctly fails and the guard still prints its ref list -- but
# #688 appears only in the frontmatter, so a correct body scan must not report it.

cat > "$TMP/plans/ref-leak.md" <<EOF
---
ticket_refs:
# siege-analytics/claude-configs-public#688: commented out
---

# Artifact

Body cites siege-analytics/claude-configs-public#251 only.
EOF
python3 -c "import sys; sys.stdout.write(('---\n\nfiller paragraph text\n\n')*7000)" >> "$TMP/plans/ref-leak.md"

leak_out=$(printf '%s' "$(payload "$TMP/plans/ref-leak.md")" | bash "$HOOK" 2>&1)
leak_exit=$?

if [[ "$leak_exit" -ne 2 ]]; then
    printf '  [FAIL] (e) ref-leak fixture should block (expected exit 2, got %d)\n' "$leak_exit"
    _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
    _HARNESS_FAILED_NAMES+=("(e) ref-leak fixture blocks")
elif echo "$leak_out" | grep -q '#688'; then
    printf '  [FAIL] (e) refs declared in frontmatter leaked into the reported ref list\n'
    _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
    _HARNESS_FAILED_NAMES+=("(e) frontmatter refs absent from message")
else
    printf '  [PASS] (e) refs declared in frontmatter are absent from the reported ref list\n'
    _HARNESS_PASS=$((_HARNESS_PASS + 1))
fi

# --- Bypass regression: `propagation-deferred:` in the BODY must not satisfy
# the guard. The old `sed -n '/^---$/,/^---$/p'` frontmatter range restarted at
# every `---` rule, so an unindented line inside a fenced block between two
# rules landed in FRONTMATTER. Quoting the guard's own error message into a
# document disabled the guard for that document.

printf '%s\n' \
    '# Doc with no frontmatter at all' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251 and is unpropagated.' \
    '' \
    '---' \
    '' \
    'Quoting the guard error message in a fenced block:' \
    '' \
    '```' \
    'propagation-deferred: workspace-only draft, will propagate after review' \
    '```' \
    '' \
    '---' \
    '' \
    'More body.' > "$TMP/plans/deferred-in-body.md"

expect_block "(f) body-level propagation-deferred between --- rules does not satisfy the guard" "$HOOK" \
    "$(payload "$TMP/plans/deferred-in-body.md")"

# --- The same bypass through an UNTERMINATED opener. Scenario (f) covers a
# document with no frontmatter at all; this one opens with `---` and never
# closes it, so the first horizontal rule becomes the closing delimiter and the
# prose above it is read as metadata. The first #688 fix closed (f) and left
# this open, and the hostile review on the PR reproduced it (F-1). The split
# now requires the candidate region to be YAML-shaped, so an opener that is
# never closed fails closed.

printf '%s\n' \
    '---' \
    'title: notes on the guard' \
    '' \
    '# Doc' \
    '' \
    'Quoting the guard resolution text:' \
    '' \
    '```' \
    'propagation-deferred: workspace-only draft, will propagate after review' \
    '```' \
    '' \
    '---' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251 and is unpropagated.' > "$TMP/plans/unterminated.md"

expect_block "(g) unterminated --- opener does not turn body prose into frontmatter" "$HOOK" \
    "$(payload "$TMP/plans/unterminated.md")"

# Same shape above the pipe buffer. The guard on origin/develop blocked this by
# accident, via the very SIGPIPE #688 fixes, so the first fix silently widened
# it from BLOCK to ALLOW. Pinning the size pair keeps the fix from trading one
# defect for another.

cp "$TMP/plans/unterminated.md" "$TMP/plans/unterminated-large.md"
python3 -c "import sys; sys.stdout.write(('\nfiller paragraph text\n')*10000)" >> "$TMP/plans/unterminated-large.md"

expect_block "(h) unterminated --- opener above the pipe buffer also fails closed" "$HOOK" \
    "$(payload "$TMP/plans/unterminated-large.md")"

# --- Positive coverage for the escape hatch. Every scenario above asserts the
# guard blocks, or that ticket_refs allows; none asserted that a real
# propagation-deferred declaration allows. Deleting the escape hatch outright
# therefore kept the suite green, which the hostile review found by mutation
# (F-3). This is the scenario that kills that mutant.

printf '%s\n' \
    '---' \
    'propagation-deferred: workspace-only draft, will propagate after review' \
    '---' \
    '' \
    '# Artifact' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251.' > "$TMP/plans/deferred-ok.md"

expect_pass "(i) propagation-deferred with a reason in real frontmatter is allowed" "$HOOK" \
    "$(payload "$TMP/plans/deferred-ok.md")"

# A boolean value is not a reason, and the guard is documented to reject it.
printf '%s\n' \
    '---' \
    'propagation-deferred: true' \
    '---' \
    '' \
    '# Artifact' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251.' > "$TMP/plans/deferred-bool.md"

expect_block "(j) propagation-deferred: true is not a reason and still blocks" "$HOOK" \
    "$(payload "$TMP/plans/deferred-bool.md")"

# --- The Write path. Every scenario above uses an Edit payload, which makes the
# guard read the file from disk. Write carries the content inline through
# tool_input.content, which is the larger of the two variables and the one the
# #688 SIGPIPE actually bit. Zero scenarios covered it (F-3).

write_payload() {
    python3 -c 'import json,sys; print(json.dumps({"tool_name":"Write","tool_input":{"file_path":sys.argv[1],"content":open(sys.argv[1]).read()}}))' "$1"
}

expect_pass "(k) Write payload, 200KB, WITH ticket_refs frontmatter is allowed" "$HOOK" \
    "$(write_payload "$TMP/plans/large-compliant.md")"
expect_block "(l) Write payload, 200KB, WITHOUT frontmatter is still blocked" "$HOOK" \
    "$(write_payload "$TMP/plans/large-noncompliant.md")"
expect_block "(m) Write payload, unterminated --- opener, fails closed" "$HOOK" \
    "$(write_payload "$TMP/plans/unterminated.md")"

# The three above build their payload by reading the same file the payload
# targets, so payload content and disk content are identical and a resolver that
# ignored the payload entirely would pass all three. Write's whole point is that
# the two differ: a new file, or an overwrite. These two pin that difference in
# both directions, on a path that does not exist on disk at all.
new_write_payload() {
    python3 -c 'import json,sys; print(json.dumps({"tool_name":"Write","tool_input":{"file_path":sys.argv[1],"content":sys.argv[2]}}))' "$1" "$2"
}

expect_block "(z) Write creating a NEW non-compliant file is blocked" "$HOOK" \
    "$(new_write_payload "$TMP/plans/does-not-exist.md" "# New

$BODY_REF
")"
expect_pass "(z2) Write creating a NEW compliant file is allowed" "$HOOK" \
    "$(new_write_payload "$TMP/plans/does-not-exist-ok.md" "$FRONTMATTER
# New

$BODY_REF
")"

# --- Round-2 hostile review (PR #689). One scenario per finding.

# R2-F1: an indented fenced block is still ordinary Markdown body. CommonMark
# permits up to three spaces of indentation, and the previous shape check
# accepted any indented line, so scenario (g)'s bypass reopened by indenting it.

printf '%s\n' \
    '---' \
    'title: notes on the guard' \
    '' \
    ' # Doc' \
    '' \
    ' Quoting the guard resolution text:' \
    '' \
    ' ```' \
    'propagation-deferred: workspace-only draft, will propagate after review' \
    ' ```' \
    '' \
    '---' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251 and is unpropagated.' > "$TMP/plans/indented-fence.md"

expect_block "(n) an INDENTED fenced block is body, not frontmatter" "$HOOK" \
    "$(payload "$TMP/plans/indented-fence.md")"

# R2-F2: the edit that introduces the first ticket reference. Judged against the
# pre-image this artifact is clean, so every earlier Edit scenario passed while
# the one edit that creates the obligation went unchecked.

printf '%s\n' '---' 'title: clean' '---' '' 'No ticket references yet.' > "$TMP/plans/add-ref.md"

expect_block "(o) Edit that ADDS the first ticket reference is judged on the after-image" "$HOOK" \
    '{"tool_name":"Edit","tool_input":{"file_path":"'"$TMP"'/plans/add-ref.md","old_string":"No ticket references yet.","new_string":"Body cites siege-analytics/claude-configs-public#251."}}'

# The same after-image on a compliant artifact must still be allowed, so (o)
# cannot pass by the guard blocking every Edit.

printf '%s\n' '---' 'ticket_refs:' '  - siege-analytics/claude-configs-public#688: comment pending' '---' '' 'No ticket references yet.' > "$TMP/plans/add-ref-ok.md"

expect_pass "(p) the same after-image WITH ticket_refs frontmatter is allowed" "$HOOK" \
    '{"tool_name":"Edit","tool_input":{"file_path":"'"$TMP"'/plans/add-ref-ok.md","old_string":"No ticket references yet.","new_string":"Body cites siege-analytics/claude-configs-public#251."}}'

# R2-F5: MultiEdit and NotebookEdit carry no `content` key, so the guard read an
# empty document and allowed them. Both are now resolved to their after-image.

expect_block "(q) MultiEdit payload is checked" "$HOOK" \
    '{"tool_name":"MultiEdit","tool_input":{"file_path":"'"$TMP"'/plans/add-ref.md","edits":[{"old_string":"No ticket references yet.","new_string":"Body cites siege-analytics/claude-configs-public#251."}]}}'

expect_block "(r) NotebookEdit payload is checked" "$HOOK" \
    '{"tool_name":"NotebookEdit","tool_input":{"notebook_path":"'"$TMP"'/plans/add-ref.md","new_source":"Body cites siege-analytics/claude-configs-public#251."}}'

# Blocking MultiEdit would also satisfy (q), because an unresolved payload fails
# closed. This scenario is what distinguishes resolving the payload from
# refusing it: dropping MultiEdit from the resolver turns this into a block.

expect_pass "(q2) a compliant MultiEdit is RESOLVED, not merely refused" "$HOOK" \
    '{"tool_name":"MultiEdit","tool_input":{"file_path":"'"$TMP"'/plans/add-ref-ok.md","edits":[{"old_string":"No ticket references yet.","new_string":"Body cites siege-analytics/claude-configs-public#251."}]}}'

expect_pass "(r2) a compliant NotebookEdit is RESOLVED, not merely refused" "$HOOK" \
    '{"tool_name":"NotebookEdit","tool_input":{"notebook_path":"'"$TMP"'/plans/add-ref-ok.md","new_source":"Body cites siege-analytics/claude-configs-public#251."}}'

# The indented-line rule has two clauses and (n) exercises only one: its quoted
# prose is not key-shaped, so it is rejected even if indentation alone were
# accepted. Here every indented line IS key-shaped, so the region is admitted as
# frontmatter unless indentation is required to follow a key with no inline
# value. `title:` has one, which makes the block below body text.

printf '%s\n' \
    '---' \
    'title: notes on the guard' \
    '  quoted: example frontmatter from the docs' \
    'propagation-deferred: workspace-only draft, will propagate after review' \
    '---' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251 and is unpropagated.' > "$TMP/plans/indent-after-value.md"

expect_block "(n2) an indented block under a key that already has a value is not frontmatter" "$HOOK" \
    "$(payload "$TMP/plans/indent-after-value.md")"

# And the legitimate shape it must not break: a key with no inline value opening
# a nested block.

printf '%s\n' \
    '---' \
    'ticket_refs:' \
    '  - siege-analytics/claude-configs-public#688: comment pending' \
    '---' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251.' > "$TMP/plans/nested-ok.md"

expect_pass "(n3) a key with no inline value still opens a nested block" "$HOOK" \
    "$(payload "$TMP/plans/nested-ok.md")"

# The other clause: once a mapping IS open, its indented content still has to be
# a list item or a key. (n2) cannot reach this, because there the mapping is
# closed. Without this clause the region below is admitted and its column-0
# `propagation-deferred:` satisfies the guard.

printf '%s\n' \
    '---' \
    'notes:' \
    '  Quoting the guard resolution text, which is prose and not YAML.' \
    'propagation-deferred: workspace-only draft, will propagate after review' \
    '---' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251 and is unpropagated.' > "$TMP/plans/prose-in-open-mapping.md"

expect_block "(n4) prose indented under an OPEN mapping is not frontmatter" "$HOOK" \
    "$(payload "$TMP/plans/prose-in-open-mapping.md")"

# A block scalar makes every following line a string value rather than a key, so
# a column-0 `propagation-deferred:` after one is body text that the caller's
# column-anchored check would otherwise honour.

printf '%s\n' \
    '---' \
    'notes: |' \
    'propagation-deferred: workspace-only draft, will propagate after review' \
    '---' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251 and is unpropagated.' > "$TMP/plans/block-scalar.md"

expect_block "(n5) a block scalar does not open a region where keys are honoured" "$HOOK" \
    "$(payload "$TMP/plans/block-scalar.md")"

# An unhandled write tool must block rather than resolve to an empty document.
# This is the branch that made MultiEdit and NotebookEdit pass before they were
# resolved, and it stays covered as new write tools appear.

expect_block "(v) a write tool the resolver does not handle fails closed" "$HOOK" \
    '{"tool_name":"FutureWriteTool","tool_input":{"file_path":"'"$TMP"'/plans/add-ref.md","payload":"anything"}}'

# A column-0 line that is not a key. Scenarios (f), (g) and (n2) each carry a
# second violation, so none of them requires this clause on its own. The line
# below contains a colon, so relaxing the key check admits it rather than
# crashing on the split -- which is what makes this fixture discriminating.

printf '%s\n' \
    '---' \
    'Quoting the guard resolution text: see the block below.' \
    'propagation-deferred: workspace-only draft, will propagate after review' \
    '---' \
    '' \
    'Body cites siege-analytics/claude-configs-public#251 and is unpropagated.' > "$TMP/plans/prose-at-col0.md"

expect_block "(n6) a column-0 line that is not a key disqualifies the region" "$HOOK" \
    "$(payload "$TMP/plans/prose-at-col0.md")"

# --- The resolver's replacement count, asserted directly.
# The guard's verdict is insensitive to over-replacement in most documents, so
# no exit-code scenario pins this. An Edit without replace_all replaces the
# first occurrence only, and an after-image that replaces every occurrence is a
# different document from the one the write would produce.

AFTER_IMAGE="$REPO_ROOT/hooks/lib/after-image.py"
printf 'alpha\nalpha\n' > "$TMP/plans/count.md"
count_out=$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s","old_string":"alpha","new_string":"beta"}}' \
    "$TMP/plans/count.md" | python3 "$AFTER_IMAGE" content)

# $(...) strips trailing newlines, so the fixture is compared without one.
if [[ "$count_out" == $'beta\nalpha' ]]; then
    printf '  [PASS] (w) an Edit without replace_all resolves to a single replacement\n'
    _HARNESS_PASS=$((_HARNESS_PASS + 1))
else
    printf '  [FAIL] (w) expected only the first occurrence replaced, got %q\n' "$count_out"
    _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
    _HARNESS_FAILED_NAMES+=("(w) single replacement without replace_all")
fi

count_all=$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s","old_string":"alpha","new_string":"beta","replace_all":true}}' \
    "$TMP/plans/count.md" | python3 "$AFTER_IMAGE" content)

if [[ "$count_all" == $'beta\nbeta' ]]; then
    printf '  [PASS] (x) replace_all resolves to every occurrence replaced\n'
    _HARNESS_PASS=$((_HARNESS_PASS + 1))
else
    printf '  [FAIL] (x) expected every occurrence replaced, got %q\n' "$count_all"
    _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
    _HARNESS_FAILED_NAMES+=("(x) replace_all replaces every occurrence")
fi

# R2-F4: the docs/investigations scope was registered and documented but no
# scenario covered it, so deleting that case from the path filter left the suite
# green while disabling half the artifact surface.

mkdir -p "$TMP/docs/investigations"
make_artifact "$TMP/docs/investigations/probe.md" no-fm 1000
make_artifact "$TMP/docs/investigations/probe-ok.md" with-fm 1000

expect_block "(s) docs/investigations artifact WITHOUT frontmatter is blocked" "$HOOK" \
    "$(payload "$TMP/docs/investigations/probe.md")"
expect_pass "(t) docs/investigations artifact WITH ticket_refs is allowed" "$HOOK" \
    "$(payload "$TMP/docs/investigations/probe-ok.md")"

# Found by widening the mutation set past the reviewer's findings, not by review.
#
# (y) The markdown-only filter is deliberate scope, so deleting it has to break
# something. Every other fixture in this file is `.md`, which is why removing the
# filter left the suite green: the mutant widens the guard onto files it was
# never meant to govern and no scenario stood on that ground.
printf '%s\n' "$BODY_REF" > "$TMP/plans/notes.txt"
expect_pass "(y) a non-markdown file in plans/ is out of scope" "$HOOK" \
    "$(payload "$TMP/plans/notes.txt")"

# (y2) A *truly* unterminated opener: `---` on line 1 and no second `---`
# anywhere in the document. Scenarios (g), (h), (m) and (n) all contain a later
# horizontal rule, so they exit the split through the shape check rather than
# through the end-of-document path, and a mutant that returned the whole
# remainder as frontmatter with an empty body survived all four. An empty body
# has no refs, so that mutant is fail-open.
cat > "$TMP/plans/no-closer.md" <<EOF
---
title: an opener that is never closed
$BODY_REF
propagation-deferred: quoted in prose, not declared in metadata
EOF
expect_block "(y2) an opener with no closing --- anywhere fails closed" "$HOOK" \
    "$(payload "$TMP/plans/no-closer.md")"

# R2-F3: both helpers are fail-open dependencies. With either removed the guard
# used to produce empty halves and allow a non-compliant artifact.

HOOK_COPY_DIR=$(mktemp -d)
cp -R "$REPO_ROOT/hooks" "$HOOK_COPY_DIR/hooks"
COPY_HOOK="$HOOK_COPY_DIR/hooks/write/ticket-propagation-guard.sh"

for helper in split-frontmatter after-image; do
    mv "$HOOK_COPY_DIR/hooks/lib/$helper.py" "$HOOK_COPY_DIR/$helper.bak"
    expect_block "(u:$helper) a missing hooks/lib/$helper.py fails closed" "$COPY_HOOK" \
        "$(payload "$TMP/plans/small-noncompliant.md")"
    mv "$HOOK_COPY_DIR/$helper.bak" "$HOOK_COPY_DIR/hooks/lib/$helper.py"
done

rm -rf "$HOOK_COPY_DIR"

# --- Round-3 findings. Both are fail-open: the guard exits 0 on a document it
# is meant to block, so no existing scenario could see either one. Every fixture
# below is paired with a control that must come back positive, because a
# scenario asserting BLOCK on a broken path filter would also pass if the guard
# blocked unconditionally.

# R3-F1: a repo-relative file_path skipped the path filter entirely. Every arm
# of the case required a leading path component: `*` matches the empty string
# but the literal `/` before `plans` still has to be there, so `plans/a.md` fell
# through to ALLOW while `./plans/a.md` blocked.

R3_PWD="$PWD"
cd "$TMP" || exit 1

make_artifact "$TMP/plans/relative.md" no-fm 1000
make_artifact "$TMP/plans/relative-ok.md" with-fm 1000
make_artifact "$TMP/docs/investigations/relative.md" no-fm 1000

expect_block "(aa) a repo-relative plans/ path is in scope" "$HOOK" \
    "$(payload "plans/relative.md")"
expect_pass "(ab) a repo-relative plans/ path with ticket_refs is allowed" "$HOOK" \
    "$(payload "plans/relative-ok.md")"
expect_block "(ac) a repo-relative docs/investigations/ path is in scope" "$HOOK" \
    "$(payload "docs/investigations/relative.md")"

# (ab) alone does not prove the relative path reached the guard, because a path
# that is still out of scope also exits 0. This is the discriminator: a relative
# path the guard does not claim must stay allowed, so (aa) and (ac) cannot be
# satisfied by widening the filter to every relative path.

printf '%s\n' "$BODY_REF" > "$TMP/notes-at-root.md"
expect_pass "(ab2) a relative path outside the artifact directories stays out of scope" "$HOOK" \
    "$(payload "notes-at-root.md")"

cd "$R3_PWD" || exit 1

# R3-F2: GitHub treats owner, repo and host casing as equivalent, so a
# mixed-case reference addresses the same issue as the lower-case spelling while
# evading a case-sensitive TICKET_REGEX. No refs found means nothing to enforce,
# which is the guard's earliest exit and so its widest fail-open.

printf '%s\n' \
    '# Artifact' \
    '' \
    'Body cites Siege-Analytics/Claude-Configs-Public#251 and is unpropagated.' > "$TMP/plans/mixed-case.md"

expect_block "(ad) a mixed-case owner reference is still a ticket reference" "$HOOK" \
    "$(payload "$TMP/plans/mixed-case.md")"

printf '%s\n' \
    '# Artifact' \
    '' \
    'Body cites GitHub.com/siege-analytics/claude-configs-public/issues/251 unpropagated.' > "$TMP/plans/mixed-case-host.md"

expect_block "(ae) a mixed-case github.com host in a full URL is still a reference" "$HOOK" \
    "$(payload "$TMP/plans/mixed-case-host.md")"

# The control for both. Matching case-insensitively must not turn every document
# into a match: text that names no governed org still carries no obligation, and
# a guard that blocked it would satisfy (ad) and (ae) for the wrong reason.

printf '%s\n' \
    '# Artifact' \
    '' \
    'Body cites Some-Other-Org/unrelated-repo#251, which this guard does not govern.' > "$TMP/plans/foreign-org.md"

expect_pass "(af) a reference to an org the guard does not govern is not a match" "$HOOK" \
    "$(payload "$TMP/plans/foreign-org.md")"

report
