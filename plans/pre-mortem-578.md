---
ticket_refs:
  - siege-analytics/claude-configs-public#578: open
type: pre-mortem
---

## Risk classification for #578: repo-scoped signal files

### Tiger 1: Resolver returns wrong gate when slug collides
- **Severity:** Medium
- **Urgency:** Low — slug collision requires two repos with identical basenames
- Mitigation: slug derivation uses full basename, not a hash; collision requires identical repo directory names in the same workspace
- Falsification: create two repos named identically, verify resolver returns the correct one per repo_root match
- **Status:** Paper Tiger — repo basenames are naturally unique within a workspace

### Tiger 2: Legacy singleton not found after migration
- **Severity:** Medium
- **Urgency:** Medium — existing workflows write singletons; readers now prefer scoped
- Mitigation: resolver falls through to `<gate-name>.json` when `<gate-name>-<slug>.json` is absent; existing singletons continue to work unchanged
- Falsification: if a singleton exists and the resolver skips it, legacy workflows break
- **Status:** Paper Tiger — fallback chain explicitly checks singleton after scoped miss

### Tiger 3: Pipeline-state-guard writes scoped but mutation gate reads singleton
- **Severity:** High
- **Urgency:** High — if writer and reader disagree on path, artifacts silently vanish
- Mitigation: writer (pipeline-state-guard) and reader (universal-mutation-gate) both derive slug from the same source (think-gate repo_root). The resolver normalizes the path.
- Falsification: if think-gate has no repo_root, both fall back to singleton — no mismatch
- **Status:** Addressed — both sides use the same repo_root → slug derivation

### Elephant 1: Four extra Python invocations per mutation gate check
- **Severity:** Low
- **Urgency:** Low — `--resolve-many` batches into a single call
- Impact: ~50ms additional latency per mutation check
- Mitigation: `--resolve-many` resolves all four gates in one Python invocation
- **Status:** Accepted — single-call batch eliminates the concern

Implementation may proceed: YES
