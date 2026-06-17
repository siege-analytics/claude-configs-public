## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #438
Goal source verification: Manual — ticket has Context, Goal, Acceptance criteria, Originating evidence. Structurally fit.
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/438#issuecomment-4725235378
Pre-author-inventory: NONE (adding to existing rule file, no pre-existing code to inventory)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Single rule file modified (markdown only). No executable code. Investigation: verified standing-approval:1-4 cover readiness interpretation, not execution disposition. Verified standing-order continuity (RESOLVER #12) covers continuity, not commitment quality. No existing rule covers the execution-disposition gap. The new rule fills a gap between preparation gates and verification gates.

## Trivial-pre-mortem declaration
Risk surface: rule text addition to markdown file. No hooks fire from this rule. No executable code changes. Enforcement is judgment-based via self-review Lead phase. The only failure mode is "rule text gives bad guidance" — correctable by editing the file. Fully reversible.

## Peer review

### Syntax check
Syntax check: N/A (no .py changes). Rule file is markdown only.

### Test suite
Test suite: N/A (no executable code changes).

### Build validation
Build: `python bin/build.py --check` → "Build check complete." (exit 0).

### Shelf: conventions
Rule follows existing cohort pattern in `_standing-approval-rules.md`: numbered rule (standing-approval:5), bold rule statement, elaboration, sub-rules (5a-5d). "Why this rule exists" section follows the pattern of the originating-incident section above (standing-approval:1-4). Relationship section updated from "three rules" to "four rules" chain.

## Lead review

### Phase A: Structural coherence
Design note on #438 matches implementation. Four sub-rules implemented as described: infer-before-asking (5a), decide-before-presenting (5b), finish-before-reporting (5c), contractor test (5d). Philosophical grounding preserved verbatim from operator. Relationship section expanded to include standing-order continuity cross-reference.

### Phase B: Did this close the gap?
The three failure modes from the originating diagnosis are addressed:
- Stub-and-declare → 5c (finish before reporting, verify deliverables non-trivial)
- Ask-instead-of-infer → 5a (infer before asking, "I wasn't sure" ≠ "I couldn't determine")
- Options-instead-of-decisions → 5b (decide before presenting, defend-your-choice test)

The contractor test (5d) provides the meta-heuristic: scope and irreversible-consequence questions warrant asking; method and sequence questions do not.

### Phase C: Findings triage

## Findings

No findings.

## Quantified claims

- "Four sub-rules" — counted: 5a, 5b, 5c, 5d → 4. Verified.
- "Three failure modes" — counted in originating evidence: stub-and-declare, ask-instead-of-infer, options-instead-of-decisions → 3. Verified.

## Evidence-predates-work
Artifact: plans/self-review-438.md
