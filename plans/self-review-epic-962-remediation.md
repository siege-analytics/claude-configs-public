# Self-review: epic #962 release-blocking remediation

## Assumptions

Domain(s): software engineering, runtime policy, review governance
Geospatial cross-cut: no
Working as: software engineer and coordinating lead
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/962
Goal source verification: the epic requires falsifiable progressive-loading claims, develop-only integration, independent review, and no release/deployment/install.
Plan reference: `/Users/dheerajchand/.craft-agent/workspaces/my-workspace/sessions/261012-refined-storm/plans/skill-library-simplification.md`
Pre-author-inventory: independent reviewer reports preserved in issue #972 and `plans/hostile-review-epic-962-remediation.md`
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/972
Pre-mortem-artifact: `plans/pre-mortem-epic-962-remediation.md`
Hostile-review-artifact: `plans/hostile-review-epic-962-remediation.md`
Project-contribution: close independently reproduced bypasses without publishing, deploying, installing, or promoting beyond `develop`.

The implementation assumes project inventory kinds authoritatively identify project-only skills/rules; packaged resolver manifests may carry deterministic size metadata; Craft workspace hooks resolve runtime dependencies relative to workspace root; and the compatibility bundle remains available on demand but is never a valid global mount.

## Peer review

- Kernel integrity: caller-selected paths must be byte-identical to canonical `KERNEL.md`, remain under the source-bound budget, and fail closed as one JSON object otherwise.
- Mount integrity: operator files remain untouched, but kernel-only verification accepts only direct verified-kernel symlinks or exact kernel bytes across `CLAUDE.md` and `AGENTS.md`; arbitrary prose fails.
- Project scope: project kinds require exact matched project membership even for bracket/slash explicit forms; shelves are invalid in every automatic source including `project.always`.
- Review governance: Git pathname discovery uses NUL delimiters and surrogateescape; kernel, settings, resolver, and lifecycle governance have Tier C floors.
- Lifecycle governance: approval records enumerate the exact current missing/invalid gap set and cannot authorize a later different set.
- Deployment: Craft deployment copies the selector and self-contained manifest alongside hooks; the temporary-workspace fixture executes Python routing.
- Runtime budget: selected unions over 12 items, 80,000 characters, or 20,000 estimated tokens reject the whole set visibly and emit no `load:` instructions.
- Coordination: canonical rule 9 includes post-handoff, post-wait, pre-decision, and status/latest-reply checks.
- Generated artifacts: inventory, authority, kernel, progressive-loading, review-risk, package, and lifecycle evidence are regenerated and freshness checked.

## Lead review

Approach fit: the fixes are placed at authoritative boundaries instead of documenting around failures—runtime hook, selector, deploy function, classifier, lifecycle checker, and verifier. The blast radius is high because these surfaces govern safety and review, so the change is Tier C and uses hostile negative fixtures. No finding was dismissed because current CI was green; reproducible counterexamples overrode prior passing fixtures.

Residual risk: exact-byte composition proves repository-managed kernel-only mounting but intentionally rejects otherwise legitimate operator prose because arbitrary semantic equivalence is not mechanically decidable. Operator files remain untouched; the verifier fails until the operator chooses an allowed composition. Shelf ownership/path integrity and documented capability-route reconciliation remain separate tickets and are not claimed fixed here.

## Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| E1 | P1 | Kernel override could inject full bundle. | byte-identity and size validation plus tampered/identical fixtures |
| E2 | P1 | Explicit project slugs crossed host/repository scope; project always allowed shelves. | exact matched-project eligibility and shelf validation with foreign-host fixtures |
| E3 | P1 | Kernel/control paths and unusual Git names could downgrade to Tier B. | NUL parsing, surrogateescape, explicit/code-owned Tier C floors, odd-path fixtures |
| E4 | P1 | Historical lifecycle approval could authorize a different later gap. | exact `approved_gaps` equality and replay fixture |
| E5 | P1 | Deployed hook omitted selector and manifest. | deploy both dependencies and execute Python route in fresh workspace fixture |
| E6 | P1 | Explicit union had no selected-content bound. | code-owned count/character/token limits and atomic over-budget rejection |
| E7 | P2 | Coordination alias lost timing/status obligations. | restore obligations in canonical rule and pin them in focused test |
| E8 | P2 | Craft documentation still prescribed full-bundle mounting. | document kernel-only global mount and compatibility-only bundle |

## Test plan

Run all Python test modules with installed Python 3.14, all hook suites, workflow policy tests, package build, deployment parity, generated authority, lifecycle, inventory, kernel budget, progressive metrics, review-risk metrics, and diff checks. Require hosted checks and targeted exact-SHA re-review from all three independent reviewers before merge.

Observed locally: 12/12 Python modules, 36/36 hook suites, and 2/2 workflow policy suites passed. The macOS default Python 3.9 cannot parse a pre-existing `str | None` annotation in `notebook_edit_guards_test.py`; the complete Python matrix passed under installed Python 3.14.

## Quantified claims

- "12/12 Python modules" — `for t in bin/_test/*_test.py; do python3.14 "$t"; done` → 12 PASS lines, zero failures.
- "36/36 hook suites" — `for t in hooks/_test/*.test.sh; do bash "$t"; done` → 36 PASS lines, zero failures.
- "2/2 workflow policy suites" — `for t in .github/workflows/_test*.sh; do bash "$t"; done` → 2 PASS lines, zero failures.
- "198 sources, 804 snapshots, 2,900 mappings" — `python3 bin/generated-source-authority.py --check` → `generated source authority: current (198 sources, 804 artifact snapshots, 2900 generated file mappings)`.
- "Kernel 6,995 characters / 1,749 estimated tokens" — `python3 bin/kernel-budget.py --check` → `kernel budget: current (6995 chars, 1749 estimated tokens)`.
- "Maximum injection 7,774 characters" — `python3 bin/progressive-loading-metrics.py --check` → `progressive loading: current (max injection 7774 chars)`.
- "0 complete / 198 legacy exceptions" — `python3 bin/skill-lifecycle.py --check` → `skill lifecycle: current (0 complete, 198 legacy exceptions)`.
- "Selection limits 12 / 80,000 / 20,000" — `grep '^MAX_SELECTED_' bin/resolve-load-set.py` → `MAX_SELECTED_ITEMS=12`, `MAX_SELECTED_CHARACTERS=80000`, `MAX_SELECTED_ESTIMATED_TOKENS=20000`.
- "Packaged merge+self-review is 80,261 characters and rejected" — package manifest sum `9604 + 70657` → `80261`; `dist/craft-agent/bin/resolve-load-set.py --prompt '[skill:merge] [skill:self-review]'` → `state: over-budget`, zero selected.

## Rework ledger

The first commit attempt was blocked because this artifact lacked the mechanically required peer, lead, and quantified-claims sections. No bypass was used. The artifact was rewritten to the full Tier C structure before retrying the commit.

Reviewer B then falsified the regular-file mount check with `The KERNEL.md is not included...`; filename presence was not inclusion proof. The verifier now requires the complete non-empty kernel bytes inside an operator file. Positive embedded-kernel and negative decoy fixtures were added.

On re-review, reviewer B chained `CLAUDE.md -> KERNEL.md -> RULES_BUNDLE.md`; trusting the deployed kernel filename was still circular. The verifier now rejects symlinked/altered kernels and checks target bytes against a code-owned packaged-kernel SHA-256 constant. Operator-file checks use only that verified kernel, remove its exact bytes, and reject additional broad-bundle references.

Reviewer A then proved the authored kernel digest differs from the deterministic reference-resolved deployed artifact, and that root `AGENTS.md` could mount the broad bundle independently. The pin now targets the built flat kernel and fresh deployment runs the verifier. Reviewer A also showed authored size metadata understated the generated `merge` + `self-review` pair. Consumer manifests now use inventory-authoritative generated output paths and measure each final package file. The 80,261-character packaged pair rejects atomically.

Reviewers A and B then bypassed filename scanning with pasted bundle bytes and an indirect alias. The verifier now accepts only exact verified-kernel composition (or empty/absent `AGENTS.md`), making arbitrary aliases or pasted policy fail by construction. Exact-kernel positives and AGENTS/CLAUDE pasted-bundle plus alias negatives were added.

Reviewer B then demonstrated a nested `project/AGENTS.md` redirect because Craft auto-injects descendant instruction files as sessions enter their directories. Verification now recursively applies the same exact-content/symlink-target allowlist to every descendant CLAUDE.md/AGENTS.md. Nested exact-kernel positive and nested alias negative fixtures were added.

Reviewer A then hid an external `AGENTS.md` behind a descendant directory symlink, which default `find` traversal skips. The verifier now fails closed on every descendant directory symlink before scanning nested instruction files. Reviewer A then supplied the entire workspace through a symlinked `--target`, which BSD `find` also skips as a starting point. The verifier now rejects a symlinked target root before any check. Paired physical-target and alias-target fixtures both fail for the hidden nested policy.

The Claude reviewer found two final portability/pathname gaps: case-variant nested instruction names on case-insensitive APFS, and a newline inside a resolver gate pathname crossing the policy regex wildcard. Descendant matching is now case-insensitive with regular and symlink fixtures; risk regexes use DOTALL and real Git add/delete fixtures. Target normalization now removes every trailing separator before symlink rejection. The focused verifier now passes 34/34.

## Rollback

Revert the single remediation merge commit from `develop`. Existing `main` and installed v3.5.63 remain untouched.
