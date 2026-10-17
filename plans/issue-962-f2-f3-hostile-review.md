# Issue #962 F2/F3 hostile review

## Review boundary

An independent Claude Opus 5.5 completion reviewed the complete patch against epic #962 F2/F3 from exact base `0bae4ff108de5ad3b339a868818b05ea1e7c70bd`. The prompt required concrete P1/P2/P3 falsifiers for package completeness, clean-build behavior, layout manifests, installed path resolution, hidden source-tree dependencies, project skill coverage, source/consumer parity, negative cases, and actual prompt/push hooks.

## First verdict

**ACCEPT** — no blocking finding.

Residual risks identified by the reviewer:

1. Patch-only review did not independently execute clean builds or hooks.
2. Packaged selector subprocess cwd was inherited from the source checkout.
3. The integration test consumed an existing `dist/` rather than rebuilding it itself.
4. Install paths containing spaces and path escape/unreadable cases were not exercised.
5. Absolute installation roots could make tracked injection-size metrics machine-specific.

## Disposition

- Execution limitation: compensated by the local hosted-equivalent suite and an explicit `rm -rf dist` clean build; reviewer claim is not treated as execution evidence.
- Source-cwd dependency risk: fixed. Package selectors now execute with cwd set to the clean consumer repository.
- Existing-dist risk: CI runs a full build before the test; final local canary removes `dist/` and rebuilds from nothing.
- Space-containing installation root: fixed. The isolated package root now includes `installed packages/`.
- Escape/unreadable defense: hook resolves paths and requires every resolved path to remain under the package root and be a readable file before presenting any instruction.
- Machine-specific metric risk: fixed. The metrics generator normalizes only the absolute installation-root prefix to `<installation-root>/` before measuring output, while runtime output remains absolute.

## Targeted re-review

The independent reviewer received the full updated patch and the residual-risk dispositions above.

**Verdict: ACCEPT.**

No P1, P2, or P3 finding remained. External exact-SHA review will still be requested on the pushed draft PR; this artifact is the pre-commit hostile-review evidence, not the post-push exact-SHA acceptance.
