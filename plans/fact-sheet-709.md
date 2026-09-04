---
ticket_refs:
  - siege-analytics/claude-configs-public#709: investigation fact sheet
---

# Investigation Fact Sheet (Focused): #709

Goal source: siege-analytics/claude-configs-public#709
Task: the investigate-gate schema disagreement between the skill and the gates
Investigated: 2026-09-03
Scope justification: two files change, `skills/investigate/SKILL.md` and a
docstring in `hooks/resolver/investigate-gate-guard.sh`, plus one new test.
No interface changes and no reader behaviour changes. Escalation was considered
and declined: the impact chain is the reader table below, which is complete
because it was derived by reading every file that mentions the signal file.

## Prior Knowledge (Phase 0)

- **Ticket body read:** YES. #709 asserts that `verifiedShapes` and `findings`
  are one concept under two spellings, and asks in acceptance criteria 1 and 2
  for a single canonical key name. This investigation refutes that premise.
- **Related tickets:** #683 produced the archived signal file used as
  corroboration below. #255 and #578 are the origin tickets for the guard and
  for repo-scoped gate resolution.
- **Recent git history:** no commit touches the `findings` read at
  `universal-mutation-gate.sh:298` or the `verifiedShapes` read at
  `investigate-gate-guard.sh:191` in the range examined.
- **Post-error revisions:** none found for this code area.

## Knowledge Loci

- **The investigate-gate signal file schema.** Locus is
  `skills/investigate/SKILL.md`, the "Write investigate-gate.json" section. It
  is the only operator-facing description of the file. Secondary locus is the
  schema docstring at the top of `hooks/resolver/investigate-gate-guard.sh`.
  Will this task invalidate it: YES, both. Updating both is the deliverable.

## Verified Shapes (Assumption Universe)

### Reader set for `investigate-gate.json` (the impact chain)

Derived by reading every file that references the signal file, at branch head.

| Reader | Key | Behaviour when the key is absent or empty |
|---|---|---|
| `hooks/bash/universal-mutation-gate.sh:298` | `findings` | **blocks**, "investigation has no findings" |
| `hooks/resolver/pipeline-state-guard.sh:173` | `findings` | records the artifact as not posted |
| `hooks/resolver/investigate-gate-guard.sh:191` | `verifiedShapes` | warns, exits 0 |
| `hooks/resolver/investigate-gate-guard.sh:390` | `verifiedShapes` | disposition validation, nothing to validate |
| `hooks/git/self-review.sh:460` | `verifiedShapes` | counts zero |
| `skills/investigate/SKILL.md` | `verifiedShapes` only | documents one of the two required keys |

- **`findings` reader count** | probe: `grep -rn "get('findings'" hooks/` |
  result: 2 hits, `universal-mutation-gate.sh:298` and
  `pipeline-state-guard.sh:173` | threshold: PASS
- **Both readers test non-emptiness only** | source:
  `universal-mutation-gate.sh:298-300` and `pipeline-state-guard.sh:173` |
  value: `findings = ig.get('findings', [])` then `if not findings:`, and
  `if not ig.get('findings', []):`. Neither inspects an entry.
- **The asymmetry** | source: `investigate-gate-guard.sh:192-197` | value:
  prints "No citations to spot-check. Proceeding, but this is suspicious."
  then `sys.exit(0)`. The documented key warns; the undocumented key blocks.

### `findings` entry shape in signal files on disk

Four signal files in one workspace, four different entry shapes. This refutes
the design's first draft, which called `{claim, evidence, disposition}` the
convention every file follows on the strength of a single archived example.

| Signal file for | findings entry keys | verifiedShapes count |
|---|---|---|
| #683 (archived) | `claim`, `evidence`, `disposition` | 8 |
| #704 | `id`, `statement`, `status`, `verifiedBy` | 0 |
| #718 | `id`, `finding`, `surface`, `evidence`, `severity` | 0 |
| untagged archive | `finding`, `source` | 0 |

Two consequences. First, entry shape is a recommendation and the skill must say
so rather than presenting three fields as a schema. Second, three of the four
files carry zero `verifiedShapes`, so the guard's warning fires on most real
files and is routinely ignored, which is corroborating evidence that the
warning is not what holds the line.

### The skill's worked example

- **Exactly one fenced JSON block** | probe: `grep -c '^```json$'
  skills/investigate/SKILL.md` | result: `1` | threshold: PASS. The new test
  relies on this and asserts it in setup rather than assuming it.
- **Pre-change key set** | source: `skills/investigate/SKILL.md`, the block at
  line 441 | value: `ticket`, `factSheetLocation`, `timestamp`, `tier`,
  `verifiedShapes`, `designNote`. No `findings`.

## Coherence

The findings agree. The reader table says `findings` is required by a blocking
reader and `verifiedShapes` by an advisory one; the skill documents only the
advisory one; the on-disk files show both keys coexisting with unrelated
shapes. The one contradiction found during investigation was internal to this
work: the design initially claimed a single conventional entry shape, and the
four-file survey refuted it. The design and the skill text were corrected
before implementation rather than after, and the correction is recorded here
rather than removed.

## Hypothesis and Falsification

**Hypothesis.** The defect is a documentation omission, not a naming collision.
Adding `findings` to the worked example, with a statement of which guard reads
which key, makes a transcribed example satisfy both guards. No rename and no
reader change is required, and renaming either key onto the other would destroy
one of two distinct artifacts.

**Falsification, run.** Build a signal file by transcribing the skill's worked
example and nothing else, then run both guards.

- Before the change: `universal-mutation-gate.sh` reports "investigation has no
  findings"; `investigate-gate-guard.sh` exits 0.
- After the change: the mutation gate does not report it; the guard still
  exits 0.

The test at `hooks/_test/investigate_gate_schema.test.sh` runs this pair on
every invocation, extracting the example from `SKILL.md` at run time so the
documentation and the gate cannot drift apart silently.

**Falsification that would have sunk the design.** If satisfying the documented
example had required changing a guard's behaviour rather than the
documentation, the two guards would genuinely disagree about the contract and
this would stop being a docs fix. It did not: the example passes both guards
after a documentation-only change.

## Findings

- **Finding 1: the skill documents the advisory key and omits the blocking
  one.** Severity: HIGH. Evidence: reader table above. Impact: an operator who
  follows the documentation exactly is refused by the mutation gate with a
  message saying the investigation is empty. Recommendation: fix, this ticket.
- **Finding 2: #709's acceptance criteria 1 and 2 are unsafe as written.**
  Severity: HIGH. Evidence: the two keys share no field, and
  `investigate-gate-guard.sh:199-209` greps `file`, `line` and `grep` out of
  `verifiedShapes` entries, which `findings` entries do not carry.
  Impact: a canonical rename would reclassify every existing file's `findings`
  as absent and would lose the conclusions entirely, since nothing else reads
  them. Recommendation: reject the criteria and say so on the PR.
- **Finding 3: `findings` entry shape is unvalidated and practice has drifted
  four ways.** Severity: MEDIUM. Evidence: the four-file table above. Impact:
  documenting three fields as a schema would be a false claim about
  enforcement. Recommendation: document as recommendation, and test that a
  differently-shaped array still passes so the wording stays true.
- **Finding 4: hook directives name `skills/thinking/<name>/SKILL.md`, which
  does not exist.** Severity: MEDIUM. Evidence: 28 references across 11 files;
  all five named skills exist at `skills/<name>/`; `SKILL_CATEGORIES` at
  `bin/build.py:46` is defined and referenced nowhere. Impact: a blocked
  operator is told to read a file that is not there, including the operator
  blocked by the very defect this ticket fixes. Recommendation: out of scope
  here, filed as #719 with an audit matrix requirement.
