## Self-Review: #477 — Harden universal-mutation-gate (v2)

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #477
Plan reference: #477 ticket description (escape-hatch removal, artifact checks)
Pre-author-inventory: NONE
Investigate-artifact: plans/pre-mortem-476.md (parent investigation)
Pre-mortem-artifact: plans/pre-mortem-476.md

## Peer review

### Shell correctness
- `bash -n hooks/bash/universal-mutation-gate.sh` → exit 0 (syntax valid)
- Syntax check: N/A (no .py changes)
- Test suite: N/A (shell hook, no pytest; validated via `bash -n`)

### Changes verified against #477 requirements

1. **CLAUDE_MUTATION_GATE=off removed** (lines 32-33): env var escape replaced
   with comment explaining auditable disable via settings.json.

2. **[mutation-acknowledged] removed** (lines 113-116): self-authorization
   bypass replaced with comment directing to SAFE_PATTERNS or pipeline
   completion.

3. **Path injection fixed** (line 141): `open('$THINK_GATE')` → `open(sys.argv[1])`
   with `"$THINK_GATE"` passed as shell argument. Prevents filename injection
   via crafted think-gate.json path.

4. **Status split** (lines 147-149 vs 151-207): `designing|reviewing` pass
   immediately (investigation phase). `implementing` requires artifact checks
   before allowing mutations.

5. **Artifact checks** (lines 153-206): When status=implementing, gate
   requires both investigate-gate.json and pre-mortem artifact. Missing
   artifacts produce a specific BLOCKED message listing what's missing.

### Compound command scan unchanged
The MUTATION_INDICATORS array and compound scan logic are unchanged —
these are tracked under #479 (safelist fixes), not #477.

## Lead review

The Junior's changes are narrowly scoped to escape-hatch removal and
artifact enforcement. No new safe patterns added, no existing patterns
changed. The blast radius is limited to: commands that previously
used one of the three escape hatches will now be blocked until proper
artifacts exist.

**Risk**: If an agent reaches `implementing` without having produced
investigate-gate.json or a pre-mortem, it will be blocked. This is
intentional — the previous behavior allowed implementation without
investigation, which is the failure mode #477 addresses.

**Approach-fit**: Correct. Removing self-authorization mechanisms
is the core thesis of #477. The path injection fix is a bonus
security improvement discovered during review.

**Sequencing**: #477 must land before #479 (safelist fixes) because
#479 adds patterns to the same file. #478 (consumer packages) is
independent.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| 1 | P3 | WORKSPACE_CANDIDATE computed twice (line 127 and 153) — could extract to top-level | noted |

## Quantified claims
- "three escape hatches" — `git diff HEAD hooks/bash/universal-mutation-gate.sh | grep -c '^\-.*exit 0'` → 3 removed exit-0 paths (env var, mutation-acknowledged, combined status check split into two)
