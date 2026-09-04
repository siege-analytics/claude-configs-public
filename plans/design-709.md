---
ticket_refs:
  - siege-analytics/claude-configs-public#709: design note
---

# Design: #709, the investigate-gate schema disagreement

Goal source: siege-analytics/claude-configs-public#709

## The ticket's premise is wrong, and the correction changes the fix

#709 reads the disagreement as one concept under two spellings: the skill
documents `verifiedShapes`, the gate reads `findings`, so pick a canonical name
and use it in both places. Acceptance criterion 1 says as much, "one canonical
key name for the substantive content."

They are not two spellings. They are two different artifacts with different
shapes, and a real signal file on disk carries both with different lengths.
From `investigate-gate-claude-configs-public.json` in the workspace signal
archive, written for #683:

```
findings:       10 entries, each {claim, evidence, disposition}
verifiedShapes:  8 entries, each {entity, file, line, grep, status, dispositions}
```

`findings` records what the investigation concluded. `verifiedShapes` records
which code shapes were read, with a file, a line and a grep pattern that a
guard re-greps to catch fabricated citations. Renaming either onto the other
destroys one of the two.

## What each reader requires

| Reader | Key | Behaviour when the key is absent or empty |
|---|---|---|
| `hooks/bash/universal-mutation-gate.sh:298` | `findings` | blocks, "investigation has no findings" |
| `hooks/resolver/pipeline-state-guard.sh:173` | `findings` | records the artifact as not posted |
| `hooks/resolver/investigate-gate-guard.sh:214` | `verifiedShapes` | warns and proceeds, "no citations to spot-check" |
| `hooks/resolver/investigate-gate-guard.sh:411` | `verifiedShapes` | disposition validation, nothing to validate |
| `hooks/git/self-review.sh:460` | `verifiedShapes` | counts zero |
| `skills/investigate/SKILL.md` | `verifiedShapes` only | documents one of the two required keys |

The asymmetry is the whole defect. The key the skill documents is the one whose
absence produces a warning. The key the skill omits is the one whose absence
produces a hard block. An operator who follows the documentation exactly writes
a file that passes the advisory guard and is refused by the blocking one, and
the refusal message says the investigation is empty.

## Design

Document `findings` in `skills/investigate/SKILL.md` alongside `verifiedShapes`,
with the distinction between them stated, and add it to the worked example.
Do not rename either key and do not change any gate's read.

This is the opposite of the ticket's instruction and it is the smaller change.
No signal file on disk becomes invalid, no reader changes behaviour, and the
two guards keep the division of labour they already have: one asks what you
concluded, the other asks what you read.

### Rejected: rename `findings` to `verifiedShapes` in the two gates

This is what the ticket asks for. It would make the mutation gate block unless
the operator supplies citation-shaped entries with file, line and grep, which
is a much stronger requirement than "the investigation reached a conclusion",
and it would silently reclassify every existing signal file's `findings` as
absent. It also loses the conclusions entirely, since nothing else reads them.

### Rejected: make the gate accept either key

Acceptance criterion 3 offers this as a tolerance for files already on disk.
It is the wrong shape here because the keys are not interchangeable: accepting
`verifiedShapes` in place of `findings` would let a file with citations and no
conclusions pass the conclusions check.

## Assumptions

1. **The two keys are semantically distinct rather than a historical accident.**
   Checked, not carried: their entry shapes share no field, and the guard at
   `investigate-gate-guard.sh:226-244` greps `file`, `line` and `grep` out of
   `verifiedShapes` entries, which `findings` entries do not have.
2. **No reader treats the two as interchangeable today.** Checked by reading
   every file that mentions `investigate-gate`. The table above is the result.
3. **Not assumed: that the skill is otherwise complete.** The audit covered the
   two keys named in the ticket. Whether the documented example satisfies every
   other check in the two guards is unverified, and the acceptance below turns
   that into a measurement rather than leaving it as a hope.

## Acceptance

1. A signal file written by following `skills/investigate/SKILL.md`'s worked
   example, with nothing added from reading hook source, passes both
   `investigate-gate-guard.sh` and the investigate portion of
   `universal-mutation-gate.sh`. This is the ticket's Goal restated as a
   procedure, and it subsumes acceptance criteria 1 and 2.
2. The skill states, for each of `findings` and `verifiedShapes`, which is
   required by which guard and what the failure looks like, so the next reader
   can tell the hard block from the warning.
3. A scenario in `hooks/_test/` builds a file from the documented example and
   asserts the mutation gate does not report "investigation has no findings".

### Falsification

Delete `findings` from the documented example and re-run the scenario. It goes
red with "investigation has no findings". If it stays green, the scenario is
not reaching the check and the fixture is wrong.

The stronger falsification, which is the one that catches a documentation fix
that documents the wrong thing: build the file by transcribing the skill's
example with no other source, and run both guards. If either refuses it, the
skill is still incomplete regardless of what this design says.
