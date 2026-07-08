---
name: compound
description: "Post-merge success compounding step. After a PR merges, answer three questions to capture what worked: What wasn't obvious? Would a future session find this? Does a skill/rule need updating? Produces a solutions catalog entry, a skill-update ticket, or a nothing-novel declaration."
---

# Success Compounding

Run this skill after a PR merges to develop. The pipeline learns from
failure (post-mortem, post-error-revision, distill-lessons) but not
from success. This step closes that gap by asking three questions
after every successful merge.

## When to run

After a PR merges to develop (or main for hotfixes). Before branch
cleanup. This step is advisory -- it cannot block the merge and does
not gate any downstream action. Its output is artifacts, not approval.

## The three questions

Answer each question in 2-3 sentences. The compound note is
lightweight -- not a full investigation.

### Q1: What worked that wasn't obvious?

Name techniques, patterns, or approaches that succeeded in this PR
and would not be discovered by a fresh session reading only the
code. Examples:

- A specific data transformation that handles an edge case
  elegantly
- An error recovery pattern that survived adversarial review
- A configuration approach that resolved a dependency conflict
- A testing strategy that caught a bug the existing suite missed

If nothing non-obvious was done, say so: "Standard implementation
following existing patterns in <module>."

### Q2: Would a future session find this solution without re-deriving it?

Look at Q1's answer. If the technique or pattern is:
- Already documented in a skill, rule, or solutions catalog entry
  → YES, discoverable
- Implicit in the code (readable from source but not documented) →
  MAYBE, depends on investigation depth
- Novel to this session's work → NO, not discoverable

**If NO:** create a solutions catalog entry. Follow the
solutions-catalog skill's schema and authoring instructions. The
entry captures the non-obvious solution so future investigate
Phase 0 finds it.

**If YES or MAYBE:** note which existing documentation covers it.

### Q3: Does any existing skill or rule need updating?

Review the work against the skills and rules that applied during
implementation. Ask:

- Did this PR expose a gap in a skill's coverage?
- Did the self-review checklists miss something relevant?
- Did a rule fire on something it shouldn't have, or fail to fire
  on something it should have?
- Did the investigation discover a pattern worth codifying?

**If YES:** file a ticket on claude-configs-public describing the
skill/rule update needed. Reference the PR and the specific gap.

**If NO:** note "Skills and rules were adequate for this work."

## Output format

The compound note is posted as a PR comment (on the merged PR) or
as a ticket comment. Choose one of:

### Solutions catalog entry created

```
Compound: solutions catalog entry created — solutions/<slug>.md

Q1: <2-3 sentences on what worked>
Q2: Not discoverable — <why>
Q3: <skills adequate or ticket filed>
```

### Skill-update ticket filed

```
Compound: skill-update ticket filed — #NNN

Q1: <2-3 sentences on what worked>
Q2: <discoverable or not>
Q3: Gap in <skill/rule> — <1 sentence description>
```

### Nothing novel

```
Compound: nothing novel — <brief reason>
```

Use this when the work followed established patterns, the solution
is already documented, and no skill/rule gaps were found. This is
a valid and common outcome. Not every merge teaches the system
something new.

## Worked example

After merging a PR that fixed CRS handling in the geocoding fallback:

```
Compound: solutions catalog entry created — solutions/geocoder-crs-transform.md

Q1: The geocoding fallback path returned coordinates in NAD83 while
    the primary path returned WGS84. The fix adds an explicit CRS
    check after the fallback call, transforming to match the primary
    path's CRS before returning. The non-obvious part: NAD83 and
    WGS84 are close enough (~2m difference) that unit tests with
    low-precision assertions passed with either CRS.

Q2: Not discoverable — the CRS mismatch between primary and fallback
    geocoders is not documented anywhere. A future session would
    need to read both code paths and compare output CRS to find it.

Q3: Skills and rules were adequate — the Geospatial conditional
    review checklist's CRS agreement item would catch this if
    activated (which it would be, since the diff touched geo/).
```

## Non-goals

- This step does not replace post-mortem (which traces failures)
- This step does not replace distill-lessons (which promotes
  recurring observations to rules)
- This step does not produce a formal investigation artifact
- This step is not blocking -- skipping it produces a visible
  absence (no compound comment on the PR) but does not gate
  anything
