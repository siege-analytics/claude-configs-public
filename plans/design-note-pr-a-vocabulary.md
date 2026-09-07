---
session: 260907-apt-nova
supersedes: coordinator draft of same filename (pre-R11-meta-correction)
reply-channel: session:260525-long-swan (send_agent_message)
---

# Design note — PR A: close the invented-token escape in Trivial-investigation vocabulary

## Ticket-shape

PR A of a three-PR sequence remediating the R11-meta finding that ten
rounds of alternating-provider hostile review on `detect-ai-fingerprints`
converged on GREEN, and R11 (Scala-skeptic frame) then surfaced 3
INVALIDATING + 4 MAJOR shape misses in one pass. The R11-meta trace
identified `Category: local-only` in every R5-R10 self-review as the
enforcement-bypass token.

## Diagnosis (verified against source 2026-09-07, session 260907-apt-nova)

**The R11-meta first-pass framing conflated two distinct block types.**
The corrected diagnosis:

1. `_authoring-against-state-rules.md` lines 440-445 defines the
   **Trivial-against-state** controlled vocabulary:
   `docs-only | comment-only | local-only | inputs-already-measured`.
   `local-only` is defined here as "change to a code path that does not
   run under shared cluster state." **`local-only` is legitimate for
   Trivial-against-state.** Do NOT remove or restrict it.

2. `skills/self-review/SKILL.md` line 448 defines the
   **Trivial-investigation** controlled vocabulary:
   `single-line-fix | doc-only | config-only | test-only`.
   **`local-only` is NOT valid for Trivial-investigation.** No agent
   should have used it; twelve did.

3. `scripts/discipline/check-trivial-claim.sh` currently validates only
   `## Trivial-change declaration` (writing-rules:5) and `## Exemption:`
   blocks. It does NOT check `## Trivial-investigation declaration`
   blocks for Category-token membership. `hooks/git/self-review.sh` at
   lines 382-388 does *field-presence* checks for the four required
   fields inside Trivial-investigation, but never validates the Category
   value against the vocabulary. **That is the enforceable hole.**

4. R5-R10 self-reviews (e.g., `plans/self-review-810-r9.md` lines 22-34)
   ship both a `## Trivial-against-state declaration` block AND a
   `## Trivial-investigation declaration` block, each carrying
   `Category: local-only`. The first is fine; the second is the
   invented-token escape.

## What this PR does (narrower than coordinator draft)

1. **Extend `scripts/discipline/check-trivial-claim.sh`** to also
   validate `## Trivial-investigation declaration` blocks. Requires
   the same four fields as Trivial-change (Category / Cannot produce
   error / Evidence / Falsification), with Evidence containing at
   least one `EVIDENCE_TOKEN_RE` match. Category must be one of
   `single-line-fix | doc-only | config-only | test-only` — default
   deny for any other token (including `local-only`,
   `internal-refactor`, `scoped-only`, and any token this PR did not
   anticipate). This is an **allowlist**, not a denylist, so future
   invented tokens are also rejected.

2. **Add `external-shape-modeling` as a NEVER-TRIVIAL category across
   all three declaration types** (`Trivial-change`,
   `Trivial-investigation`, `Trivial-against-state`). Per reviewer
   guardrail: this is a **prohibited triviality claim**, not a token
   added to any of the three allowlists. When the diff touches
   external-shape-modeling code, NO Trivial-* declaration is acceptable
   — the author must produce a full `authoring-against-state:6`
   inventory. Enforced by an optional `--diff-files` argument to
   `check-trivial-claim.sh` that lets the caller pass the diff scope;
   `hooks/git/self-review.sh` (which already computes `$DIFF_FILES`)
   passes it through.

3. **Define `external-shape-modeling` broadly**: scanners, parsers,
   linters, hooks that infer semantics from source syntax, config
   files, CLI arguments, API payloads, schemas, notebooks, or
   framework conventions. Domain-general. Detection is filename-based
   (per reviewer preference over content-based, which is fragile):
   - Any path under `hooks/**`.
   - Basenames matching `scan*|*_scan*|scanner*|*_scanner|lint*|linter*|parse_*|parser*|check-*|check_*|_check*`
     with extension `.py|.sh|.js|.ts|.rb|.go`.

4. **Update `_writing-rules-rules.md` writing-rules:5 body** to
   document the block-type-specific vocabularies (referencing the
   canonical definition locations for Trivial-against-state and
   Trivial-investigation) and to name `external-shape-modeling` as a
   prohibited-triviality trigger. Do NOT introduce writing-rules:8 —
   reserved for PR C.

5. **Update `skills/self-review/SKILL.md` Trivial-investigation
   section** to enforce the four-token allowlist and to name
   external-shape-modeling as a prohibited-triviality trigger. Add a
   short worked example showing the required
   `authoring-against-state:6` inventory when the trigger fires.

6. **Add test fixtures under `scripts/discipline/tests/`** (dir does
   not currently exist; create it) covering the reviewer's required
   matrix:
   - `Trivial-against-state / Category: local-only` with full evidence → PASS
   - `Trivial-investigation / Category: local-only` → FAIL with
     writing-rules:5 diagnostic naming the four-token allowlist
   - `Trivial-investigation / Category: internal-refactor` → FAIL
   - `Trivial-investigation / Category: scoped-only` → FAIL
   - `Trivial-investigation / Category: repo-local-only` (invented) →
     FAIL with default-deny diagnostic (proves allowlist not denylist)
   - `Trivial-investigation / Category: test-only` with full evidence → PASS
   - Diff touching `hooks/git/self-review.sh` +
     `Trivial-investigation` declaration (any category) → FAIL with
     external-shape-modeling never-trivial diagnostic
   - Diff touching `scripts/discipline/check-trivial-claim.sh` + any
     Trivial-* declaration → FAIL (same)

## What this PR does NOT do

- No changes to `skills/detect-ai-fingerprints/` — PR B/C scope.
- No shape-space enumeration table for writing-code:8 — PR C scope.
- No hostile-review Category 10 additions — PR B scope.
- No `writing-rules:8` introduction — PR C scope.
- Do NOT remove or restrict `local-only` in
  `_authoring-against-state-rules.md`. It is legitimate there.
- Do NOT retroactively rewrite R5-R10 self-review artifacts under
  `plans/`. Enforcement is forward-only.

## Why this ordering

PR A closes the active invented-token escape first. Without it, PRs B
and C can still be bypassed by any future round declaring
`Category: local-only` (or any other invented token) on the
Trivial-investigation block. Vocabulary hardening is the highest-ROI
change because it converts a governance breach into a mechanical
rejection at the pre-push hook boundary.

## What could go wrong

Detailed in `plans/pre-mortem-pr-a.md`. Summary:

- **Allowlist too tight** — real-world Trivial-investigation
  categories missed. Mitigation: keep the exact four tokens named in
  `self-review/SKILL.md` today; don't shrink.
- **Allowlist too loose via case/spacing bypass** — `LOCAL-ONLY`,
  `local-only ` (trailing space), etc. Mitigation: normalize (trim,
  case-fold) before comparing.
- **External-shape-modeling detection false positives on prose-only
  doc edits** — SKILL.md prose edit tempts `prose-only-docs` claim
  but the file is agent-behavior-driving. Mitigation: PR A limits
  external-shape-modeling detection to scanner/parser/linter/hook
  *code* filenames, not markdown. SKILL.md files remain governed by
  the pre-existing writing-rules:5 never-trivial prose (unenforced
  today, out of scope for PR A per operator directive).
- **PR A composing badly with existing hook chain** — `self-review.sh`
  today reads Trivial-investigation directly; if PR A moves the
  vocabulary check into `check-trivial-claim.sh`, the two enforcement
  paths must not disagree. Mitigation: the hook delegates to the
  script; the script is the single source of truth.
- **Branch rebase risk** — R9 branch `fix/810-r9-*` is the current
  local branch; PR A branches off `origin/develop`, so no direct
  conflict.

## Rollback

Single revert of the merge commit. Rejected tokens become permissive
again. Existing R5-R10 artifacts remain unaltered (forward-only
enforcement means historical files never re-enter the check).

## Success criteria (falsifiable, encoded as think-gate claims)

- `check-trivial-claim.sh <fixture>` exits non-zero when the fixture
  has `## Trivial-investigation declaration / Category: local-only`.
- Same for `internal-refactor`, `scoped-only`, and the invented token
  `repo-local-only`.
- `check-trivial-claim.sh <fixture> --diff-files hooks/git/self-review.sh`
  exits non-zero regardless of which Trivial-* Category is claimed.
- `check-trivial-claim.sh <fixture>` PASSES when the fixture has
  `## Trivial-against-state declaration / Category: local-only` with a
  full evidence chain — i.e., the Trivial-against-state legitimacy is
  preserved.
- No file under `plans/` matching `self-review-{802,804,806,808,810}*.md`
  is modified by this PR.

## Self-review dogfood

PR A modifies external-shape-modeling governance
(`check-trivial-claim.sh` IS external-shape-modeling code by the new
definition). Therefore PR A's own self-review MUST NOT use ANY Trivial-*
declaration; it ships a full `authoring-against-state:6` inventory in
`plans/self-review-pr-a.md` following the template in
`_authoring-against-state-rules.md`'s "Inventory template" section. If
the discipline blocks the PR that establishes the discipline, the
discipline is confirmed working. That is the intended dogfood.

## Verification of preconditions

- `writing-rules:8` does NOT yet exist in `_writing-rules-rules.md`
  (grepped 2026-09-07: seven rules present).
- `authoring-against-state:6` exists as the shape-space-enumeration
  gate this PR restores enforcement for (verified in
  `_authoring-against-state-rules.md`).
- Branch base: `origin/develop` per operator directive.
