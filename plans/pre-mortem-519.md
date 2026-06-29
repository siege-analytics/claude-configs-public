---
ticket_refs:
  - siege-analytics/claude-configs-public#519
---
# Pre-mortem: #519 — self-review posted to ticket enforcement

## Risks

### Tiger 1 — review variable undefined
**Severity:** Medium
**Status:** Mitigated

The `review` variable is set inside `if has_changes:` at line 219. If no code changes exist, the variable would be undefined when the posting check references it.

**Mitigation:** Added `review = None` initialization before the `has_changes` block. The posting check tests `if review:` — None is falsy, so the check is skipped.

### Tiger 2 — Cross-contamination of stems
**Severity:** Low
**Status:** Mitigated

"findings" appears in both investigation stems and self-review stems. A ticket with only investigation content could partially match self-review stems.

**Mitigation:** Threshold requires 3/5 stems. "peer review" and "lead review" are distinctive to self-review — they won't appear in investigation or pre-mortem postings. Single-stem overlap cannot reach the threshold alone.

### Paper Tiger 1 — Old signal files lack selfreview_posted
**Severity:** Low (Paper Tiger)

Mutation gate uses `'selfreview_posted' in ap` — only checks when the field is present. Old signal files without the field are not affected.

**Implementation may proceed: YES**
