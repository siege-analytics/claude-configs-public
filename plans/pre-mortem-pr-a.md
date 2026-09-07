---
session: 260907-apt-nova
ticket_refs:
  - siege-analytics/claude-configs-public#pr-a-close-invented-token-escape
reply-channel: session:260525-long-swan (send_agent_message)
---

# Pre-mortem: PR A — close invented-token escape in Trivial-investigation

## Status: cleared, implementation proceeds

## Context

Vocabulary + evidence-chain hardening for `## Trivial-investigation
declaration` blocks plus a new prohibited-triviality trigger
(`external-shape-modeling`) applied across all three Trivial-* block
types. Enforcement lives in
`scripts/discipline/check-trivial-claim.sh` (extended) and is invoked
by `hooks/git/self-review.sh` (already computes `$DIFF_FILES`; will
pass it through as `--diff-files`). Test fixtures under a new
`scripts/discipline/tests/` directory.

## Risks

### R1. Allowlist too tight (Severity: MEDIUM — Real Risk 2)

Real-world Trivial-investigation claims that today are legitimate get
rejected because PR A froze the vocabulary to the four tokens named in
`self-review/SKILL.md`. Historical R5-R10 artifacts already use
`local-only` — but those are historical and forward-only enforcement
does not re-scan them.

- **Mitigation**: PR A enshrines exactly the four tokens the shelf
  already documents (`single-line-fix | doc-only | config-only |
  test-only`). No shrinking. Any legitimate new category must ship as
  a paired edit to `self-review/SKILL.md` + `check-trivial-claim.sh`
  in one PR — per the same discipline writing-rules:5 already uses.

### R2. Allowlist too loose via case / spacing bypass (Severity: MEDIUM — Real Risk 2)

A future artifact declares `Category: LOCAL-ONLY` (uppercase),
`Category:  local-only` (extra space), or `Category:local-only` (no
space) and slips past the check.

- **Mitigation**: strip leading/trailing whitespace after the
  `Category:` field name, before comparing. Use case-sensitive
  comparison but explicitly document that tokens are lowercase; any
  case variant is rejected as an invented token. Test fixtures cover
  both spacing and case.

### R3. External-shape-modeling false positives on prose-only doc edits (Severity: LOW — Real Risk 3)

A benign typo fix in a `SKILL.md` file tempts a `prose-only-docs`
Trivial-change claim. If PR A's detection sweep is too broad and
flags markdown as external-shape-modeling, the claim is blocked and
the author is forced into a full inventory for a five-word typo.

- **Mitigation**: PR A's detection is filename-based and limited to
  scanner/parser/linter/hook *code* files (extensions `.py .sh .js
  .ts .rb .go`). Markdown is NOT in scope. The pre-existing
  writing-rules:5 never-trivial list already names skill/rule/hook
  files as never-trivial in prose; PR A does not extend enforcement
  to markdown files. SKILL.md prose edits remain governed by the
  same rules as today (unenforced never-trivial for prose-only-docs).
  Widening to markdown is a separate concern out of PR A scope.

### R4. External-shape-modeling false negatives on renamed scanner files (Severity: LOW — Paper Tiger 2)

A scanner named `analyze_source.py` (does not match `scan*`, `lint*`,
`parse*`, `check*` patterns) legitimately IS external-shape-modeling
code but PR A's filename regex misses it.

- **Mitigation**: PR A's detection is a floor, not a ceiling. It
  catches the canonical shapes (scan_*, check_*, lint*, parse*, and
  everything under `hooks/**`). The floor closes the loophole the
  R5-R10 arc actually exploited. Broader coverage is a follow-up
  (PR C's writing-rules:8 rule-authoring discipline will require
  each new rule to enumerate its shape space, which forces authors
  of new scanners to declare their file as external-shape-modeling).

### R5. PR A composes badly with existing hook chain (Severity: MEDIUM — Real Risk 2)

`hooks/git/self-review.sh` today reads `## Trivial-investigation
declaration` blocks inline and checks the four field-presence
requirements at lines 382-388. If PR A moves vocabulary validation
into `check-trivial-claim.sh` but the hook still does its own inline
checks, the two paths can disagree and the hook's inline logic wins
silently.

- **Mitigation**: PR A delegates Trivial-investigation vocabulary
  and evidence-chain validation to `check-trivial-claim.sh` — the
  hook continues doing its structural TRIVIAL-vs-file-path
  dispatch, but the *content* validation moves fully into the
  script. Test fixture harness invokes the script directly; a
  separate integration case invokes the hook to prove the delegation
  works end-to-end.

### R6. R9 branch (`fix/810-r9-*`) rebase risk (Severity: LOW — Paper Tiger 3)

Current local branch is `fix/810-r9-dotted-source-group-binding`.
PR A branches off `origin/develop`. If the R9 branch is merged
mid-work, PR A's branch base may diverge; if it isn't, there is no
conflict because PR A touches different files.

- **Mitigation**: branch explicitly off `origin/develop` at the
  start. If merge conflicts arise at PR-open time, rebase onto
  `origin/develop` at that point. PR A touches
  `scripts/discipline/check-trivial-claim.sh`,
  `hooks/git/self-review.sh`,
  `skills/_writing-rules-rules.md`,
  `skills/self-review/SKILL.md`, and a new
  `scripts/discipline/tests/` directory — none overlaps with R9's
  scan_ast.py-only changes.

### R7. Dogfood self-block (Severity: LOW — Expected, by design)

PR A modifies `check-trivial-claim.sh` and `hooks/git/self-review.sh`
— both are external-shape-modeling code by the new definition.
Therefore PR A's own self-review CANNOT use a Trivial-* declaration;
if the author drafts one, the newly-installed check rejects it.

- **Mitigation**: PR A's self-review artifact
  (`plans/self-review-pr-a.md`) ships a full
  `authoring-against-state:6` inventory from the outset — no
  Trivial-* attempted. This is the intended dogfood: the discipline
  the PR establishes must apply to the PR itself.

### R8. Test fixture false positives via unintended header match (Severity: LOW — Paper Tiger 3)

If test fixtures are markdown files with `## Trivial-investigation
declaration` headers, and the hook or check-trivial-claim.sh scans
`plans/**` or the whole tree, the fixtures could be rejected as if
they were real artifacts.

- **Mitigation**: fixtures live under `scripts/discipline/tests/`,
  not `plans/`, and are invoked explicitly by a test runner script
  (`scripts/discipline/tests/run-tests.sh`) that passes each fixture
  path to `check-trivial-claim.sh` and asserts the expected exit
  code. `hooks/git/self-review.sh` only scans the artifact named in
  `Self-Review-Source:` trailers, so it never sees these fixtures
  unless a commit references one — none will.

## Rollback

Single revert of the merge commit. All rejected tokens become
permissive again; historical artifacts remain unmodified. Test
fixtures + runner are removed with the revert. `check-trivial-claim.sh`
returns to its pre-PR-A behavior of only validating
`## Trivial-change declaration` and `## Exemption:` blocks.

## Cleared

R1-R8 all have mitigations named. Implementation proceeds.
