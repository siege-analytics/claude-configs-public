---
ticket_refs:
  - siege-analytics/claude-configs-public#709: pre-mortem
---

# Pre-mortem: #709

Goal source: siege-analytics/claude-configs-public#709
Design: `plans/design-709.md`

Written before implementation. Each threat states what the failure looks like
after the fact, and the check that would have caught it.

## Severity summary

- Tiger 1 (CRITICAL): documentation corrected but example still incomplete on another axis. Severity: CRITICAL.
- Tiger 2 (CRITICAL): new scenario asserts nothing (repeats the #713 measurement-gap failure). Severity: CRITICAL.
- Tiger 3 (HIGH): fix reasons from an archived signal file rather than current reader source. Severity: HIGH.
- Paper tiger 1 (LOW): the skill file is inside the build; must run bin/build.py deploy after commit. Severity: LOW.
- Paper tiger 2 (LOW): ticket's acceptance criteria contradict the design; state the disagreement on the PR. Severity: LOW.
- Paper tiger 3 (LOW): no existing test scenario for investigate portion of mutation-gate; surrounding signal-file state is where silent failures happen. Severity: LOW.

## T1, CRITICAL: the documentation is corrected and still does not work

The design's whole claim is that an operator following the skill gets blocked
because one required key is undocumented. The obvious fix is to add that key to
the worked example. The failure mode is that the example is still missing
something else, and the ticket closes on a diff that looks right while the
procedure it describes still fails.

This is not hypothetical. The skill has been wrong about this file for long
enough that nobody noticed, which is evidence that nobody has run the documented
example end to end. There is no reason to believe a second omission would have
been noticed either.

Catches it: build a signal file by transcribing the skill's example and nothing
else, then run both guards against it. Reading the diff does not catch it, and
neither does reasoning about the two keys. Design acceptance 1 is written as
this procedure for that reason.

Abandon condition: if the transcribed example fails on a third requirement that
is not a documentation defect but a genuine disagreement between the two guards,
this stops being a docs fix and the design is wrong about scope. Stop and
re-file rather than growing the change.

## T2, CRITICAL: the new scenario asserts nothing

The scenario in acceptance 3 checks that the mutation gate does not say
"investigation has no findings". The gate has several paths to a pass and
several to a block. A scenario that runs the gate against a well-formed file
and sees exit 0 may be seeing exit 0 for an unrelated reason: the gate may not
have reached the investigate check at all, because the think-gate was absent,
or the ticket did not match, or the workspace did not resolve.

This is the defect #713 found in three of its own fixtures, in this same test
harness, and the harness now carries `expect_block_because` because of it. A
scenario written here without that lesson would repeat it inside the epic that
recorded it.

Catches it: run the scenario against a file with `findings` removed and require
it to fail with the specific message. A scenario that passes both with and
without the key is measuring nothing. Assert on the message text, not on the
exit code.

## T3, HIGH: the fix is written for the archive rather than for the reader

The evidence for the design's central claim came from a signal file in a
`.signal-archive-*` directory, written for #683. Archived files are not
necessarily current practice. If the two keys were merged or split since, the
design is reasoning from a superseded shape.

Catches it: check the shape against the readers rather than against the file.
The reader table in the design is derived from hook source at the branch head,
not from the archive. The archived file is corroboration for the claim that both
keys coexist in practice; the requirement claim rests on the source.

## Paper cuts

**E1: the skill file is inside the build.** `bin/build.py` renders skills into
four package layouts and scores them. A documentation edit changes rendered
output in `dist/`. Do not stage `dist/`; run the deploy build after the commit,
as the standing order requires.

**E2: the ticket's acceptance criteria contradict the design.** #709's criteria
1 and 2 ask for one canonical key name. The design rejects that and explains
why. This must be stated on the PR rather than quietly satisfied by a different
change, otherwise the ticket closes against criteria that were never met.

**E3: `hooks/_test/` has no existing scenario for the investigate portion of
the mutation gate.** Adding one means building the surrounding signal-file
state, which is the part most likely to go wrong silently. See T2.

## Abandon condition for the unit

If satisfying the documented example requires changing a guard's behaviour
rather than the documentation, the change is no longer a docs fix, the two
guards genuinely disagree about the contract, and the correct action is to stop
and file that as its own ticket rather than to pick a winner here.
