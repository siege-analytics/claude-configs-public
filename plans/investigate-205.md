---
ticket_refs: ["siege-analytics/claude-configs-public#205"]
---

# Fact Sheet: Inventoried-shape trailer enforcement (#205)

## Verified Shapes

### self-review.sh structure
- ATTESTED: COMMIT_MSG captured at line 118 via `git log -1 --pretty=%B`
- ATTESTED: DIFF_FILES captured at line 579 via `git diff-tree --name-only`
- ATTESTED: v2.3 hostile-review-artifact check ends at line 984, exit 0 at line 987
- PROBED: Executable regex `\.(py|sh|js|ts|sql|rb|go|rs|java|c|cpp|h)$` used in v2.3 (line 911) — reused as EXEC_RE_V24

### Existing inventory enforcement (v1.2)
- ATTESTED: Pre-author-inventory: field check at lines 276-315
- ATTESTED: Trivial-against-state: paired check at lines 301-312
- ATTESTED: No Inventoried-shape: commit trailer check exists anywhere in hooks/

### Commit trailer parsing pattern
- ATTESTED: All trailer checks use `echo "$COMMIT_MSG" | grep -E '^TrailerName:[[:space:]]+\S'`
- ATTESTED: Pattern used for Self-Review (line 134), Self-Review-Source (line 135), Design-Note-Source (line 558), Pre-ship-dry-run (line 603), Probe-Matrix (line 604)

### _authoring-against-state-rules.md
- ATTESTED: Rule 1 (line 40) defines `Inventoried-shape:` as the commit trailer for recording measurements
- ATTESTED: No existing hook enforces this trailer
