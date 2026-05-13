# Lessons Learned -- `claude-configs-public`

This file is the **Tier 1 ledger** of the rules pipeline. It captures recurring code-review findings, bot comments, and incident lessons as evidence. Entries get promoted to Tier 2 (`.claude/rules/<topic>.md`) by [skill:distill-lessons] when they meet the recurrence threshold, and from there to Tier 3 (the org-wide `_*-rules.md` in `claude-configs-public`) by human PR.

This is the dogfooding instance -- `claude-configs-public` itself uses the pipeline it ships. Findings about the rules, the build, the workflow, and the skills themselves land here.

See [skill:lessons-learned] for the format spec and [skill:rules-audit] for the cross-tier hygiene pass.

## Audit metadata

- **Last audit:** 2026-05-12 (initialized -- never run)
- **Audit cadence target:** quarterly (or on-demand via [skill:rules-audit])
- **Promotion threshold (default):** recurrence ≥ 3, or 1 production incident, or Critical-severity finding

---

## Entries

## 2026-05-13 -- Three more rules and three tooling enhancements from a self-diagnosis pass

- **Source:** Cross-session hand-off from session `260502-vital-channel`. After v1.5.0 shipped, the parent ran a retrospective on whether the rules would have prevented the failures that motivated them; honest answer was 70%. Issue [#52](https://github.com/siege-analytics/claude-configs-public/issues/52); PR [#53](https://github.com/siege-analytics/claude-configs-public/pull/53). Negotiation across two `send_agent_message` rounds; operator delegated authority and weighted parent's lived-experience diagnosis heavily.
- **Rule (draft):** Apply `[rule:no-ai-fingerprints]` v1.6.0 (rules 1-18) including R-16 (mock fidelity), R-17 (doc-edit symmetry), R-18 (silent error swallowing); the `[skill:commit]` step 4 affected-tests gate; and the scanner enhancements for rule 13 (countable claims need `Verified-by:` trailer) and rule 15 (skip messages need actionable verb plus identifier).
- **Why:** The 30% gap was not random. It clustered in three places: honor-system rules (12/13/14/15 all depend on agent honesty about whether something was run), deferred categories from v1.5.0 (silent error swallowing, untested exception handlers, conditional-import callsite hygiene), and patterns the rules cannot catch in their current shape (mock fidelity with shape-correct stubs, asymmetric doc-edit failures). v1.6.0 closes the first two clusters mechanically (T1/T2/T3 add hard checks where rules were honor-system) and rule-text (R-16/R-17/R-18). R-19 and R-20 are committed for v1.6.1 within 7 days; T4 (public-surface differ for rule 14) is on its own track at #51.
- **Recurrence:** 1 (parent's self-diagnosis covering ~40 failure modes from the original arc plus subsequent observations under v1.5.0)
- **Promotion-requested:** parent session 260502-vital-channel (cross-session retrospective)
- **Promoted:** rules 16-18 in `skills/_no-ai-fingerprints-rules.md`; affected-tests gate in `skills/git-workflow/commit/SKILL.md` step 4; rule-13 and rule-15 checks in `skills/meta/detect-ai-fingerprints/scan.sh`. All on 2026-05-13 by PR #53. R-18 wording includes the parent's grace-window refinement for `Optional[T]`-returning functions (one-minor-release window after R-18 lands; existing handlers either pass through or get a one-line docstring update at edit time).

## 2026-05-13 -- Four new rules and three tightenings from extended siege_utilities arc

- **Source:** Cross-session hand-off from session `260502-vital-channel`. Ten siege_utilities PRs through six rounds of hostile review surfaced ~40 distinct failure modes; the existing eleven rules covered roughly 60% of them. Issue [#49](https://github.com/siege-analytics/claude-configs-public/issues/49); PR [#50](https://github.com/siege-analytics/claude-configs-public/pull/50). Negotiation transcript across two `send_agent_message` rounds with parent session 260502-vital-channel; operator delegated authority with explicit "prefer prevention over cure" framing.
- **Rule (draft):** Apply `[rule:no-ai-fingerprints]` v1.5.0 (rules 1-15) plus `[rule:environment-preflight]`. Rules 12 (no hypothetical code), 13 (auditable claims), 14 (BREAKING in changelog), 15 (skip messages name remediation) added contiguously. Rules 7 (test imports the module), 10 (cross-reference verify-before-execute for prose claims), 11 (grep before declaring fix complete) tightened.
- **Why:** The biggest gap in the v1.3.0 rules was hypothetical code: shipping code that depended on Spark/Sedona/credentials without verifying they were installed, and shipping tests that re-implemented the production algorithm in the test body instead of importing it. The narrow narrative was "I forgot SZSH exists." The general principle is that code generation must be grounded in actual installed dependencies and exercised against the real thing, not against mocks the agent wrote alongside the code. The countable-claims gap (rule 13) was the second-biggest: PR bodies asserting "all four engines call X" when only two did.
- **Recurrence:** 1 (extended arc covering ~40 failure modes; rule clusters covering most)
- **Promotion-requested:** parent session 260502-vital-channel (cross-session reviewer flag)
- **Promoted:** `skills/_no-ai-fingerprints-rules.md` v1.5.0 and new `skills/_environment-preflight-rules.md` (Tier 3 directly, since this repo is the org-rules repo) on 2026-05-13 by PR #50. Rule 14's mechanical-differ tooling is a follow-up ticket; the rule is in force with operator-judgment enforcement until the tool exists. The detect-ai-fingerprints scanner enhancement (rule-7 grep for test files importing their module under test) is also follow-up; documented as scoped-out of v1.5.0 for proper project-namespace-detection design.

## 2026-05-12 -- Smoke tests must include the production-default invocation, not just the developer-debug one

- **Source:** v1.4.0 of `[skill:detect-ai-fingerprints]` shipped a bash-3.2 unbound-variable bug. PR [#48](https://github.com/siege-analytics/claude-configs-public/pull/48) fixed it; v1.4.1 superseded v1.4.0 the same hour. Issue [#47](https://github.com/siege-analytics/claude-configs-public/issues/47).
- **Rule (draft):** Every smoke test for a CLI tool must include the no-flags invocation that production callers actually use. Convenience flags used during development do not exercise the production codepath.
- **Why:** During PR #46 development I tested the scanner with `--ignore 'skills/meta/detect-ai-fingerprints/*'` repeatedly to suppress its own self-detection. The flag also happened to populate the `IGNORE_GLOBS` array, so I never hit the empty-array codepath. Production gates (commit step 3, code-review pre-flight) call the scanner without `--ignore`. On bash 3.2 (macOS default) the empty-array expansion under `set -u` errors immediately. The bug shipped because the smoke tests asked "does the scanner work the way I'm calling it" instead of "does the scanner work the way callers will call it."
- **Recurrence:** 1
- **Promotion-requested:** none yet (recurrence threshold)
- **Promoted:** not yet

## 2026-05-12 -- Eleven AI fingerprints from a hostile siege_utilities review

- **Source:** Cross-session hand-off from session `260502-vital-channel` to session `260502-pure-vista`; eleven concrete failure modes named in the inbound message (em-dashes, "Why:" / "How to apply:" blocks, multi-paragraph docstrings on internal helpers, self-justifying adverbs, bulleted commit messages, history references in code comments, vacuous tests, cargo-culted patterns across modules, speculative abstractions, asserting non-existent symbols, single-site patches that need three rounds). Issue [#42](https://github.com/siege-analytics/claude-configs-public/issues/42); PR [#43](https://github.com/siege-analytics/claude-configs-public/pull/43).
- **Rule (draft):** Apply `[rule:no-ai-fingerprints]` (eleven mandatory rules) to all code, comments, docstrings, commit messages, PR bodies, and chat output.
- **Why:** A hostile reviewer surfaced concrete instances of each fingerprint in shipped siege_utilities work. Two of the structural rules (verify before asserting; grep before patching) point at real bugs already shipped (`create_presentation_from_data` method-name mismatch; Paragraph-escape three-round fix). The stylistic rules are the "AI tell" pattern that erodes reviewer trust; the structural rules are the "AI bug" pattern that corrupts the codebase.
- **Recurrence:** 1
- **Promotion-requested:** parent session 260502-vital-channel (cross-session reviewer flag, plus author-reviewer flag from the original siege_utilities reviewer)
- **Promoted:** `skills/_no-ai-fingerprints-rules.md` (Tier 3 directly, since this repo is the org-rules repo) on 2026-05-12 by PR #43; rule 5 wording amended in negotiation with the parent session before merge (counter-proposal accepted -- structural fingerprint banned, length cap dropped)

## 2026-05-12 -- Concurrent build-and-publish runs race when main+tag pushed back-to-back

- **Source:** Run [25768243378](https://github.com/siege-analytics/claude-configs-public/actions/runs/25768243378) failed during v1.2.1 release with `cannot lock ref 'refs/heads/release/nested': is at f03c3b07 but expected 0702ccbe`. Issue [#38](https://github.com/siege-analytics/claude-configs-public/issues/38); PR [#39](https://github.com/siege-analytics/claude-configs-public/pull/39).
- **Rule (draft):** Any GitHub Actions workflow job that force-pushes to a shared branch must declare a concurrency group with `cancel-in-progress: false`, so back-to-back triggers queue rather than race.
- **Why:** Pushing main and immediately pushing the version tag is the standard release sequence (see any CHANGELOG-stamp commit). Two workflow runs trigger ~2 seconds apart; both force-push to `release/nested` + `release/flat`; the loser fails with the lock-ref error. The losing run is the tag-push, so the `vX.Y.Z-nested` / `vX.Y.Z-flat` fan-out tags don't get created and downstream consumers can't pin.
- **Recurrence:** 1
- **Promoted:** `.github/workflows/build-and-publish.yml` on 2026-05-12 by PR #39 (Tier 3 directly -- single-repo workflow fix, doesn't need to traverse Tier 2)

## 2026-05-12 -- Agents take side-effecting actions without first investigating actual state

- **Source:** Reviewer flag from Dheeraj at session 260502-pure-vista; resulted in `[rule:verify-before-execute]` in v1.2.0 and the Design-line tightening in v1.2.1. Issues [#34](https://github.com/siege-analytics/claude-configs-public/issues/34), [#36](https://github.com/siege-analytics/claude-configs-public/issues/36); PRs [#35](https://github.com/siege-analytics/claude-configs-public/pull/35), [#37](https://github.com/siege-analytics/claude-configs-public/pull/37).
- **Rule (draft):** Before any side-effecting action (Write, Edit, side-effecting Bash, commit, push, delete, deploy), emit a visible Verify-before-execute block grounded in same-turn evidence and (for non-trivial actions) a same-conversation think reference.
- **Why:** Recurring observation across multiple sessions -- agents infer state from prior context, stale memory, or conversation summaries instead of observing the current state, then take actions that have to be reverted. Invisible discipline (private "checks") doesn't fire reliably; visible discipline is auditable.
- **Recurrence:** 1
- **Promotion-requested:** Dheeraj (explicit reviewer flag -- promoted to Tier 3 on day of capture, bypassing the recurrence threshold)
- **Promoted:** `skills/_verify-before-execute-rules.md` (Tier 3 directly, since this repo is the org-rules repo) on 2026-05-12 by manual PRs #35 and #37 -- pre-dates the formal `[skill:distill-lessons]` workflow; documented here for the audit trail
