# Self-review: PR for #663 (infra-ticket-tool-install.md template)

## Assumptions

Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #663
Goal source verification: `PASS: ticket 663 is fit for execution` (from `bash scripts/discipline/evaluate-ticket.sh 663` at 2026-08-31 07:44 CDT)
Plan reference: `sessions/260525-long-swan/plans/falsifiable-acceptance-criteria-epic.md` + `## Design` on ticket #663
Pre-author-inventory: ticket #663 carries `## Design` + `## Assumptions`. Inventory verified `templates/infra-ticket-tool-install.md` did not exist before this PR and that `scripts/probe/_common.sh` (from #662, staged in PR #668) already invokes `sed` substitution on this exact filename.
Investigate-artifact: TRIVIAL (see declaration)
Pre-mortem-artifact: TRIVIAL (see declaration)
Hostile-review-artifact: WAIVED (see waiver)
Project-contribution: closes the last dangling reference from #662's `_common.sh` — with this template in place, the probe's blocked-on-infra branch produces a properly formatted body instead of the fallback prose string.

## Trivial-investigation declaration

Reason: single new markdown template file with plain `sed` placeholders. No executable code. No consumer changes (the consumer `_common.sh` from #662 already references this exact path with the sed pattern, so this PR just makes the referenced file exist).
Evidence: `git diff --stat` shows 2 files (`CHANGELOG.md`, `templates/infra-ticket-tool-install.md`), all additions. The rendered template (via sample sed substitution) contains 0 leftover `{...}` placeholders.
Falsification: not trivial if the placeholder syntax collides with real markdown/GitHub-issue-body syntax that the render output would corrupt. Verified: `{tool}` etc. are prose braces, harmless in GitHub markdown.

## Hostile-review-waiver

Reason: single template file with no runtime behavior. The renderer (`_common.sh` from PR #668) already lives elsewhere; this PR only supplies the substrate.
Evidence: no code changes. Only new template + CHANGELOG entry.
Falsification: waiver invalid if the template introduces a XSS/injection vector when substituted with unsanitized values. Values come from probe internals (tool name, version string from `--version`, hardcoded install command, blocking ticket ref, layer name, repo basename, session id); none are user-facing free-form input. GitHub issue bodies are sanitized on render.

## Pre-implementation comprehension

Current behavior: `scripts/probe/_common.sh` (from #662) sed-substitutes into `templates/infra-ticket-tool-install.md` if it exists; otherwise it uses a fallback plain-prose body. The fallback is uglier and lacks the structured fields Steve's queue wants.

Intended behavior: after this PR, `templates/infra-ticket-tool-install.md` exists with seven placeholder fields, and the probe renders proper structured tickets.

Steps executed: branch → write template with all seven placeholders + verification + notes for installer → CHANGELOG entry → verify ACs → self-review → push → PR.

Success criteria: template exists; all 7 placeholders present; substitution produces zero leftovers; CHANGELOG has 2 matching lines. All verified.

Risks: (a) sed's `|` as delimiter interferes with a value containing `|` — install commands could conceivably contain `|`, mitigated by the probe using `sed -e 's|X|Y|g'` and by our install commands not containing raw `|` (verified against the six shipped probes); (b) values with `&` cause sed replacement magic — again, no `&` in the shipped install strings, but flag for follow-up if a future probe needs one (escape via `\&`).

## Senior adversarial checklist

- Do the placeholders cover the information Steve needs to act? Tool name, version, install commands (per-tool), blocking tickets, layer, repo, requester session — yes, matches the fields the probe collects.
- Is the "notes for the installer" section helpful or padding? Two useful notes: (1) blocking tickets retry automatically once tool lands; (2) explicit close-with-alternative path if this tool is intentionally not installed. Both are actionable for Steve. Retained.
- Would a reviewer figure out the sed substitution semantics from this file alone? Yes — comment block at the top explicitly names all seven placeholders and links to the renderer file (`scripts/probe/_common.sh`).
- Anything cargo-culted from the epic? Trailer note `Part-of epic #655; template landed via #663; renderer in #662` mirrors the shape of other files in the epic. Retained for cross-ref consistency.

## Peer review

- **grep AC1**: `test -f` returns 0. PASS.
- **grep AC2**: `grep -cE '\{tool\}|...'` returns 17 (well above 7 required). PASS.
- **grep AC3**: sed substitution with sample values, then `grep -c '\{[a-z_]+\}'` returns 0. PASS.
- **grep AC4**: `grep -cE '#663|infra-ticket-tool-install' CHANGELOG.md` returns 2. PASS.
- **writing-prose:1**: 0 em-dashes / en-dashes in added lines. PASS.
- **writing-prose:2** (Why:/How to apply:): none. PASS.
- **writing-prose:3** (self-justifying adverbs): re-read; none.
- **writing-prose:4** (commit shape): subject under 72 chars, plain-prose body.
- **writing-code:2** (no history refs in code comments): template comment references #655/#662/#663 as cross-refs to companion epic tickets. Same judgment as #662 review — architectural cross-refs, not historical PR/sprint rot.
- **testing-frameworks:3**: no test files; the substitution grep IS the test evidence.
- **output rule**: no AI attribution.

## Quantified claims

Claim: "single new template file + one CHANGELOG entry."
Verified-by: `git diff --stat` shows exactly 2 files touched (1 new, 1 modified). PASS.

Claim: "seven placeholders, rendered zero leftover."
Verified-by: `grep -cE` returned 17 placeholder occurrences (multiple uses per field); post-substitution leftover count = 0. PASS.

## Lead review

- Junior solved the stated goal: yes.
- Junior over-scoped: no — did not touch the renderer (already in #662 PR #668).
- Junior under-scoped: no — added the "notes for the installer" section with actionable follow-up guidance.
- Standards affirmatively met: writing-prose:1-4, writing-code:2, definition-of-done (a-e).

## Rework ledger

- Cycle 0: initial. No rework — all ACs green on first check.

## Evidence-predates-work

All AC greps + sed-substitution check captured on the working tree pre-commit.
