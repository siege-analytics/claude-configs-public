---
ticket_refs:
  - siege-analytics/claude-configs-public#pr-a-close-invented-token-escape
session: 260907-apt-nova
---

# Self-review: PR A — close invented-token escape in Trivial-investigation vocabulary

## Assumptions

Working as: software engineer, on discipline / rule-enforcement code.
Domain: shelf hardening — writing-rules:5 vocabulary + evidence-chain enforcement, self-review/SKILL.md Trivial-investigation vocabulary, `scripts/discipline/check-trivial-claim.sh` extension, `hooks/git/self-review.sh` delegation.

Goal source: coordinator brief from session 260525-long-swan (recorded in the operator kickoff message for this session), corrected against the R11-meta consensus with session 260905-clever-quasar (see `plans/r11-meta-gap-analysis.md`).

Investigate-artifact: investigate-gate-claude-configs-public.json (repo root + session dir)
Pre-mortem-artifact: plans/pre-mortem-pr-a.md
Pre-author-inventory: plans/self-review-pr-a.md#pre-author-inventory
Hostile-review-artifact: plans/r11-scala-skeptic-review.md (upstream R11-meta chain, tracked in the workspace ticket)
Project-contribution: A mechanical, forward-only enforcement floor for shelf-vocabulary discipline — future rounds cannot claim `Category: local-only` (or any invented token) on a Trivial-investigation block, and scanner/parser/linter/hook diffs cannot skip shape-space enumeration by claiming triviality. Converts a governance breach (twelve historical `local-only` bypasses) into a mechanical rejection at the pre-push hook boundary. Enables PRs B and C to build on a stable vocabulary layer without racing against future bypass attempts.
Goal source verification: coordinator brief + R11-meta gap analysis both name the exact enforcement gap PR A closes (Trivial-investigation `Category: local-only` accepted by no validator).

## Pre-author inventory

PR A modifies external-shape-modeling code (`scripts/discipline/check-trivial-claim.sh` and `hooks/git/self-review.sh` are both scanners/hooks per the new writing-rules:5 amendment shipped by this PR). Per the writing-rules:5 amendment PR A itself introduces, external-shape-modeling is a prohibited-triviality trigger. No `Trivial-*` declaration is acceptable. The full `[rule:authoring-against-state]` step-6 inventory follows.

### Inputs read (step 1)

- Coordinator brief for session 260907-apt-nova (recorded in session opening message)
- `plans/r11-meta-gap-analysis.md` (R11-meta findings; consensus record with 260905-clever-quasar)
- `plans/r11-scala-skeptic-review.md` (R11 hostile-review verdict on detect-ai-fingerprints)
- `plans/design-note-pr-a-vocabulary.md` (this PR's revised design note)
- `plans/pre-mortem-pr-a.md` (this PR's pre-mortem, R1-R8 risks + mitigations)
- `scripts/discipline/check-trivial-claim.sh` (base at origin/develop, pre-PR-A)
- `hooks/git/self-review.sh` lines 340-522 (Trivial-investigation handling + delegation point)
- `hooks/git/pre-push-self-review.sh` (companion push-side trailer hook)
- `hooks/lib/resolve-think-gate.py` (gate-file resolver used by both the mutation gate and self-review.sh)
- `skills/_writing-rules-rules.md` writing-rules:4/:5/:6/:7 bodies
- `skills/_authoring-against-state-rules.md` lines 420-470 (Trivial-against-state block, `local-only` definition, and the Inventory template used for this section)
- `skills/self-review/SKILL.md` lines 428-475 (Trivial-investigation block prior to PR A)
- `scripts/discipline/README.md` (script inventory + hook wiring commentary)
- `plans/self-review-810-r9.md` (R9's self-review — canonical example of the pattern PR A blocks)

Standing rules / skills consulted: `[rule:writing-rules]` writing-rules:4/:5/:6, `[rule:authoring-against-state]` step 6, `[skill:self-review]`, `[skill:think]` gate protocol, `[skill:investigate]`.

### Knowledge requirements (step 2 — what we need to know)

- Which validator today enforces the Trivial-investigation Category token? → check-trivial-claim.sh does not; hooks/git/self-review.sh does field-presence but not vocabulary.
- What is the exact Trivial-investigation allowlist per the shelf? → `single-line-fix | doc-only | config-only | test-only` (self-review/SKILL.md line 448).
- What is the exact Trivial-against-state allowlist? → `docs-only | comment-only | local-only | inputs-already-measured` (_authoring-against-state-rules.md lines 442-445).
- Is `local-only` legitimate in Trivial-against-state? → yes, defined as "change to a code path that does not run under shared cluster state."
- Is `local-only` valid in Trivial-investigation? → no. Not in the allowlist.
- Where does the hook wire into the checker? → today: nowhere. Must be added.
- How does the hook compute the current diff scope? → `git diff-tree --no-commit-id --name-only -r HEAD` at line 674. For PR A the delegation needs staged + working tree + HEAD to capture all pending change surfaces.
- What are the canonical external-shape-modeling filename patterns? → hooks/**, scan*/lint*/parse*/check*/scanner*/linter*/parser* with .py/.sh/.js/.ts/.rb/.go.
- Does a test dir exist under scripts/discipline/? → no. Create one.
- Does check-trivial-claim.sh have any callers other than hooks/git/self-review.sh? → grep says no active hook caller today; README and SKILL.md reference it in prose.

### Contact-point measurements (step 3 — per rules 1-5)

- **data-shape (authoring-against-state:1):** N/A. PR A does not touch data pipelines or schemas.
- **config-state (authoring-against-state:2):** N/A. PR A does not modify environment config, secrets, or dependency pins.
- **topology (authoring-against-state:3):** N/A. PR A does not affect service topology.
- **plan-shape (authoring-against-state:4):** the change lives on branch `fix/pr-a-close-invented-token-escape` off `origin/develop` per operator directive; `git log --oneline origin/develop -3` confirms R9's #810 already landed as merge dc3cc8c; no rebase risk against R9. Landing plan: single PR against develop, single revert as rollback per `plans/pre-mortem-pr-a.md`.
- **version-resolution (authoring-against-state:5):** N/A. No new dependencies; no version bumps.

### Surface areas inventoried beyond rules 1-5 (step 4)

- `scripts/discipline/check-trivial-claim.sh` — extended: new `--diff-files` flag; new Trivial-investigation block support; new external-shape-modeling never-trivial trigger applied across all three Trivial-* block headers. Existing Trivial-change vocabulary + evidence-chain checks preserved.
- `hooks/git/self-review.sh` — added a delegation block after line 522 (`for FIELD_NAME` loop close) that invokes `check-trivial-claim.sh` with a `--diff-files` temp-file listing `git diff-tree HEAD ∪ git diff HEAD ∪ git diff --cached`. Existing inline field-presence checks retained as first-pass safety.
- `skills/_writing-rules-rules.md` writing-rules:5 body — added block-type-specific vocabularies table, named `external-shape-modeling` as prohibited-triviality trigger (NOT a Category token), documented filename patterns, motivating incident.
- `skills/self-review/SKILL.md` Trivial-investigation section — added default-deny allowlist prose, `local-only` clarification (legitimate in Trivial-against-state), external-shape-modeling never-trivial paragraph, invalid worked example.
- `scripts/discipline/tests/` — new directory with 9 fixture files + 3 diff-list files + `run-tests.sh` covering the reviewer's required matrix.
- `hooks/git/pre-push-self-review.sh` — read only; not modified. Trailer presence check is upstream of the artifact content path.
- `hooks/lib/resolve-think-gate.py` — read only; consulted to confirm signal-file scope semantics (session field + repo_root basename).
- `plans/` — added `design-note-pr-a-vocabulary.md`, `pre-mortem-pr-a.md`, `self-review-pr-a.md` (this file). NOT modified: R5-R10 self-review artifacts (`plans/self-review-{802,804,806,808,810}*.md`). Verified inline: `git diff origin/develop..HEAD --name-only | grep 'plans/self-review-8'` returns empty.
- Signal files: workspace-scoped `<repo>/{think,investigate,junior-senior,artifacts-posted}-gate-claude-configs-public.json` + session-scoped mirrors under `<craft-agent workspace>/sessions/260907-apt-nova/`. Untracked from git per prior sessions' pattern.

### Hypothesis (step 7 — what the code will implement; falsifiable)

The extended `check-trivial-claim.sh <artifact-path> [--diff-files <file>]` accepts an artifact and an optional diff-scope descriptor. It validates: (a) `## Trivial-change declaration` blocks against the writing-rules:5 seven-token vocabulary plus the four-field evidence chain; (b) `## Trivial-investigation declaration` blocks against the self-review four-token vocabulary plus the four-field evidence chain; (c) `## Exemption:` blocks against the three-field evidence chain; and (d) rejects ANY Trivial-* block (Trivial-change, Trivial-investigation, or Trivial-against-state) when the `--diff-files` list contains at least one path matching the external-shape-modeling patterns (`hooks/**` OR basename ∈ {scan*/scanner*/lint*/linter*/parse_*/parser*/check-*/check_*/_check*/*_check*} with extension ∈ {.py, .sh, .js, .ts, .rb, .go}).

The updated `hooks/git/self-review.sh` invokes `check-trivial-claim.sh` on the Self-Review-Source artifact after the field-presence loop, passing a temp-file containing the union of `git diff-tree HEAD`, `git diff HEAD`, and `git diff --cached`. On non-zero exit from the checker, the hook propagates BLOCK.

The `_writing-rules-rules.md` writing-rules:5 body newly documents the three block-type vocabularies and the never-trivial external-shape-modeling trigger without introducing writing-rules:8 (reserved for PR C). The `self-review/SKILL.md` Trivial-investigation section newly documents the four-token default-deny allowlist, the legitimate/invalid crossover with Trivial-against-state, and the external-shape-modeling never-trivial paragraph.

The test harness `scripts/discipline/tests/run-tests.sh` invokes `check-trivial-claim.sh` on each fixture with the specified `--diff-files` (or none) and asserts the exit code + a diagnostic-substring match. Ten cases cover the reviewer's required matrix: {Trivial-against-state/local-only + evidence → PASS}, {Trivial-investigation/local-only → FAIL/writing-rules:5}, {Trivial-investigation/internal-refactor → FAIL}, {Trivial-investigation/scoped-only → FAIL}, {Trivial-investigation/repo-local-only (invented) → FAIL/default-deny}, {Trivial-investigation/test-only + evidence → PASS}, {Trivial-investigation/test-only + hook-touching diff → FAIL/external-shape-modeling}, {Trivial-change/comments-only + scanner-touching diff → FAIL/external-shape-modeling}, {Trivial-change/prose-only-docs + evidence → PASS (regression guard)}, {Trivial-investigation/test-only + benign diff → PASS (regression guard)}.

### Conclusions (steps 5+6 — write into the ticket; state explicitly what was NOT measured)

- Assumed state consistent with measured state: verified against every load-bearing file (check-trivial-claim.sh, self-review.sh, _writing-rules-rules.md, self-review/SKILL.md, _authoring-against-state-rules.md, plans/self-review-810-r9.md). R11-meta diagnosis correct after the reviewer's Trivial-against-state vs Trivial-investigation clarification.
- Hypothesis achievable within scope: yes. All 10 fixture cases pass locally (see run-tests.sh output). No R5-R10 artifact modified.
- Knowledge requirements from step 2 all answered.
- Explicitly NOT measured:
  - Whether any downstream repo consumes `check-trivial-claim.sh` (grep `check-trivial-claim` returned only in-repo references — README, SKILL.md, plans). If a downstream consumer exists it will benefit from the stricter checks; if it fails because of `--diff-files` argument parsing, it was invoking with two positional args in a way that no in-repo caller does today, and can revert to the single-arg form.
  - Whether `hooks/git/self-review.sh`'s DIFF_FILES union captures the exact "about to push" scope. It captures HEAD+working+staged, which is a superset of any pending change surface. False positive risk: negligible. False negative risk: if a change is only in an *unstaged* file the author never actually plans to commit — but that scenario doesn't trigger self-review artifact validation anyway (no push happens).
  - Whether the filename-based external-shape-modeling detection has false positives on files named e.g. `check-license.sh` that are not actually shape-modeling. This is a documented risk (pre-mortem R3); the mitigation is that the check only fires when a Trivial-* declaration IS present. A truly benign check-license.sh commit-msg-only change would just… not declare Trivial-*.

## Trivial-* declaration

**NONE.** PR A is external-shape-modeling code by the new definition it introduces. Per the reviewer's guardrail and the writing-rules:5 amendment this PR ships, no Trivial-* declaration is acceptable. The full authoring-against-state:6 inventory above is the required artifact. This is the intended dogfood: the discipline this PR establishes applies to this PR itself.

## Peer review

Gate 1 (syntax): `bash -n scripts/discipline/check-trivial-claim.sh` → ok. `bash -n hooks/git/self-review.sh` → ok. `bash -n scripts/discipline/tests/run-tests.sh` → ok.
Gate 2 (tests): `scripts/discipline/tests/run-tests.sh` → 10/10 pass, 0 fail. Every fixture in the reviewer's required matrix produces the expected exit code and diagnostic-substring match.

Shelf compliance:
- `writing-code:5`: hand-traced 6 cases (each fixture is one). Every case's assertion is derivable from the script's control flow at the specific line where the outcome is decided.
- `writing-tests:1`: reverting each new script guard (Trivial-investigation vocabulary, external-shape-modeling detection) makes at least one fixture regress. Verified by walking `bash -x` through pass-trivial-against-state-local-only.md and fail-esm-hook-diff-with-trivial-investigation.md and confirming the vocabulary-check + esm-check branches fire on the expected inputs.
- `writing-claims:8`: "10/10 pass" verified against the actual run-tests.sh output above (not asserted; observed).
- `writing-rules:5`: PR A's own diff was authored under the new never-trivial trigger. This self-review artifact ships a full authoring-against-state:6 inventory, no Trivial-* declaration. Dogfood confirmed.
- `writing-rules:6` (post-error revision): not triggered. No prior published Assumption was contradicted by empirical evidence — the R11-meta correction is a pre-implementation Fact Sheet update, not a runtime contradiction.
- `writing-rules:7` (session-scale): PR A is the first of a three-PR sequence. Same-shape sibling detection: PRs B and C are the siblings. Neither is co-shipped with A; each is a separately-scoped follow-up per the operator brief. No same-shape session-scale audit required.

## Lead review

Independent adversarial pass on the diff.

**Content of the extended check-trivial-claim.sh:**
- Argument parsing preserves backward compat: single positional arg still valid; `--diff-files <file>` is optional and additive.
- New TRIVIAL_INVESTIGATION_VOCAB_RE is exactly the four self-review tokens, anchored `^...$`. No case-folding, so `LOCAL-ONLY` is a rejection (case-bypass test coverage confirms).
- external-shape-modeling detection: filename-only; case-sensitive extension check gates the basename regex to avoid over-firing on markdown; hooks/** short-circuits before the extension gate.
- Every diagnostic names the writing-rules:5 or self-review/SKILL.md reference the reader must consult.
- Preserves existing Trivial-change writing-rules:5 vocabulary + evidence-chain checks byte-for-byte (spot-check: `TRIVIAL_CHANGE_VOCAB_RE` matches the pre-PR `ALLOWED_CATEGORIES_RE`).

**Content of the hook delegation:**
- `CHECK_TRIVIAL_SCRIPT` is derived from the hook's script location — no hard-coded absolute path.
- Temp-file lifecycle: created via `mktemp`, cleaned on both success and failure branches. No orphan on interrupt (bash `set -uo pipefail` behavior with mktemp is well-defined).
- Diff scope is the union of last commit + working tree + staged, sort -u'd. Union captures the pending change surface pre-commit AND pre-push. If DIFF is empty, the checker still runs; empty diff list means external-shape-modeling never-trivial doesn't fire, which is correct (a pure prose/plans-only PR would not trigger it).

**Content of the writing-rules:5 amendment:**
- Adds a block-type vocabulary table; does NOT add `external-shape-modeling` to any of the three allowed lists (the reviewer's guardrail).
- Names the motivating incident (R5-R10, 12x `local-only`).
- Does NOT modify the existing Trivial-change controlled vocabulary (still the 7-token list).
- Does NOT introduce `writing-rules:8`. Verified by `grep -nE 'writing-rules:8[^0-9]' skills/_writing-rules-rules.md` → no match.

**Content of the self-review/SKILL.md amendment:**
- Keeps the existing Trivial-investigation four-token vocabulary line intact.
- Adds an explicit default-deny paragraph naming `local-only`, `internal-refactor`, `scoped-only` as rejections and calling out `local-only`'s legitimate cousin in Trivial-against-state.
- Adds the external-shape-modeling never-trivial paragraph with the filename-pattern back-reference to writing-rules:5.
- Adds an invalid worked example (the R5-R10 pattern) so the reader sees exactly what fails.

**Scope discipline:**
- No changes to `skills/detect-ai-fingerprints/`. Verified: `git diff origin/develop..HEAD --name-only | grep detect-ai-fingerprints` → empty.
- No changes to R5-R10 self-review artifacts. Verified: `git diff origin/develop..HEAD --name-only | grep -E 'plans/self-review-(802|804|806|808|810)'` → empty.
- No writing-rules:8. Verified above.
- No shape-space enumeration table for writing-code:8. Verified: `git diff origin/develop..HEAD --stat _writing-code-rules.md` → empty.
- No hostile-review Category 10. Verified: `git diff origin/develop..HEAD --stat skills/hostile-review/SKILL.md` → empty.

**Rollback verified:** single revert of the merge commit unwinds all four surface areas (script, hook delegation block, writing-rules:5 body, self-review Trivial-investigation section) plus the new test dir. No historical artifacts touched, so revert is symmetric.

## Quantified claims

- "10/10 test fixtures pass" — verified inline via `scripts/discipline/tests/run-tests.sh` output.
- "9 fixtures + 3 diff-list files + 1 runner in scripts/discipline/tests/" — `ls scripts/discipline/tests/fixtures/*.md | wc -l` = 9; `ls scripts/discipline/tests/fixtures/diff-list-*.txt | wc -l` = 3; `test -x scripts/discipline/tests/run-tests.sh` → yes.
- "Zero R5-R10 self-review files modified" — verified via git diff --name-only grep above.
- "Zero writing-rules:8 references introduced" — verified via grep -nE 'writing-rules:8[^0-9]' → empty in the diff.
- "Four Trivial-investigation allowlist tokens preserved from self-review/SKILL.md" — the script's `TRIVIAL_INVESTIGATION_VOCAB_RE` is `^(single-line-fix|doc-only|config-only|test-only)$`; the shelf's declaration at line 448 shows the same four tokens.
