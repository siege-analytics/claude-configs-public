---
ticket_refs:
  - siege-analytics/claude-configs-public#808
---

# Pre-mortem: PR for #808 (R8-F1..F6 source-module-based pairing)

## Status: Cleared. Implementation may proceed: YES.

## Context

R7's strictness on the single-flag path introduced HIGH-severity regressions on `import X as Y` (numpy as np) and `from PKG import Symbol` (from PIL import Image). Both are dominant Python idioms. R8 reviewer's diagnosis: name-match compared flag stem to import BINDING NAME instead of SOURCE MODULE.

## Risks

**Severity: Elephant 1** — Regression on 21 existing writing-code:8 fixtures.
Description: Core algorithm rewrite. All 21 must still pass.
Mitigation: Run test_writing_code_8.sh before commit.

**Severity: Elephant 2** — Reintroduces R7-F2 misdirect if the source_module change dilutes the check.
Description: `import re` + `MRE_AVAILABLE` must still fail open. Source is `re`, stem is `MRE`; case-folded, both are strings — `re` != `mre`, `re.replace('_', '')` != `mre.replace('_', '')`. Mismatch. Fail open. Preserved.
Mitigation: Verify inline.

**Severity: Paper Tiger 3** — F5 consolidation risks introducing a subtle bug in the newly-shared helper.
Description: Hoisting `_flag_stem` to module scope means both single-flag and multi-flag paths share the same logic. If the shared version has a bug, both paths regress.
Mitigation: Preserve the exact stem-strip logic; hoist without modification.

## Rollback

`git revert` restores R7's per-binding stem-match. R8-F1/F2 regressions return but no new regression.
