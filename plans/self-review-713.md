---
ticket_refs:
  - siege-analytics/claude-configs-public#713: self-review for changes 1 and 2
---

# Self-review: #713 changes 1 and 2

Goal source: siege-analytics/claude-configs-public#713
Working as: software engineer

Unit under review: the scanner-path fix in `hooks/git/detect-ai-fingerprints.sh`,
the override-message corrections in `hooks/git/test-guard.sh` and
`hooks/git/ticket-required.sh`, the three corrected fixtures and the
`expect_block_because` harness assertion, and the `Hook scenario tests` workflow
step. Design: `plans/design-713.md`. Pre-mortem: `plans/pre-mortem-713.md`.

## Assumptions

Roles named: software engineer, implementing the design's changes 1 and 2. The
reviewing roles this unit stands up to are software engineer, for the fixture
corrections and the step body, and tech lead, for the two scope decisions under
Lead review.

1. **The flat scanner path is correct for consumers as well as this repo.**
   Checked rather than carried: `dist/` was built and the scanner resolves to
   `skills/detect-ai-fingerprints/scan.sh` in all four package layouts, with the
   hook at `hooks/git/`, so the upward walk reaches it. A dual-path search is
   therefore unnecessary.
2. **The 9 previously passing files pass on ubuntu-latest.** Design assumption 2.
   Settled by the CI run, and it was wrong: 11 of 12 passed and
   `test_guard.test.sh` failed. See S-7. The assumption is now closed rather
   than open, and the prediction that "several files build temporary git
   repositories, so a platform difference surfaces there first" was right about
   the mechanism and wrong about it being a platform difference.
3. **A scenario named for one rule should fail when that rule stops being
   enforced.** Asserted rather than assumed at the outset, and the measurement
   below shows the first version of three corrected scenarios failed it.

## Quantified claims

| Claim | Value | How derived |
|---|---|---|
| test files under `hooks/_test/` | 12 | `hooks/_test/*.test.sh` |
| files failing before, on clean `origin/develop` | 3 | each file run at `2cd567f` |
| failing scenarios before | 6 | same run |
| files failing after | 0 | same command, post-change |
| settled as hook defect | 3 of 6 | table below |
| settled as wrong fixture | 3 of 6 | table below |
| stale path occurrences in the hook | 4 | replacement asserted the count before writing |
| commits on `develop` since the path went stale | 458 | `git rev-list --count f76ea4d..origin/develop` |
| corrected fixtures killed by their mutation, first attempt | 1 of 4 | mutation run before `expect_block_because` |
| corrected fixtures killed by their mutation, after | 4 of 4 | same mutations, post-harness-change |
| recent `develop` commit bodies the scanner refuses | 18 of 60 | scanner replayed in `--message-file` mode |
| open PR branches whose HEAD body the scanner refuses | 10 of 19 | same scanner, `origin/<headRefName>` |
| step body verdict, non-last file fails | exit 1 | step text extracted from the workflow and run |
| naive `for` loop verdict, same tree | exit 0 | same tree, same files |
| files passing on the first ubuntu-latest run | 11 of 12 | run 33715787987, step 11 |
| test files creating repos without a declared identity | 1 of 5 | `grep -n 'git init\|user.email' hooks/_test/*.test.sh` |
| `test_guard` scenarios passing vacuously with setup broken | 4 of 8 | fix reverted under an empty global git config |

## Findings

**S-1, P1: the ticket's Assumption 1 was wrong on half the scenarios, and wrong
in the direction that flatters the ticket.** #713 assumed all six failures were
hook defects, with evidence claimed for three and the other three unverified.
Settled per scenario, it is three and three:

| Scenario | Determination |
|---|---|
| `detect_ai_fingerprints` (b), (c), (d) | hook defect, one cause |
| `test_guard` (c) | wrong fixture, intent legitimate |
| `test_guard` (e) | wrong fixture, behaviour removed on purpose by #579 |
| `ticket_required` (r) | wrong fixture, behaviour removed on purpose by #580 |

The three the ticket claimed evidence for were the three that were real. The
three it guessed at were all wrong, and each of the three encoded a contract the
repository had changed on purpose. A ticket that had been believed rather than
checked would have "fixed" three hooks to restore overrides that #579 and #580
removed, reopening two escape hatches this repository closed.

**S-2, P1: the hook could not find its scanner for 458 commits, and nothing
said so.** `f76ea4d`, dated 2026-06-02, flattened `skills/meta/<slug>/` to
`skills/<slug>/`. Four references in `hooks/git/detect-ai-fingerprints.sh` were
left on the old path, so the upward walk found nothing and the hook took its
allow-early exit at line 83. That exit is correct behaviour for a checkout
without the scanner and is the reason the failure was silent: the hook is
opt-in by file existence, and a missing file is indistinguishable from a
deliberate opt-out. 458 commits landed on `develop` in that window and the hook
file was last touched on the same day the path went stale.

This is the same shape as #703's four instruments, arriving by a different
route. There the instrument was scoped to the set whose absence it should
detect. Here the instrument had a correct fail-open branch and no way to
distinguish "no scanner here" from "the scanner moved."

**S-3, P1: three of the four corrected fixtures asserted nothing, and the
mutation test is the only reason that is known.** The pre-mortem's T3 said a
corrected fixture must fail against a hook mutated to remove the behaviour it
names. Run against four mutations, the first version of the corrections scored 1
of 4. `test_guard` (c) and (e2) and `ticket_required` (r2) all still passed,
because each hook has more than one path to exit 2 and the harness compared only
the exit code. With the bare override accepted again, `[run-skip: ...]` fell
through to the missing-evidence block; with the signal-file check removed, the
empty `SIGNAL_FILE` failed the evidence lookup instead. Every one of them
blocked for the wrong reason and read as a pass.

`expect_block_because` was added to the harness for this: it asserts exit 2 and
that the output matches a pattern naming the reason. The same four mutations now
score 4 of 4. Without the mutation run these three scenarios would have shipped
green, inside the very commit whose purpose is to stop `hooks/_test/` from being
decorative.

**S-4, P2: turning the hook on refuses a third of the epic's recent commit
bodies, and the first reading of that number was wrong.** The pre-mortem's T1
set an abandon condition on this. Replayed against 60 recent `develop` bodies
the scanner refuses 18, and against the HEAD body of 19 open PR branches it
refuses 10, four of which are on tickets this epic may not touch. Read
literally, T1 fires and change 1 splits.

That reading is wrong, and the measurement that shows it is the one the earlier
figures did not contain. The hook scans `HEAD` only, so those numbers describe a
push that transfers nothing. Varying only whether a further commit exists:

```
no-op push, dirty body is HEAD:  exit=2  ahead=0
real push, clean body on top:    exit=0  ahead=1
```

The next real push to any of the 10 branches carries a body written after this
merges and is gated on that body, not on the stale one. The forward-looking
figure is 3 of the last 12 commit bodies written under the current discipline,
and all three are true positives on rules the operator has stated: an adverb,
bullets in a commit body, an em-dash. A gate refusing those is the gate working,
which is what separates this from #703's T2, where the gate refused legitimate
read-only commands.

T1 is therefore resolved as not-met rather than waived. The residual is the
no-op push itself, which is a real defect: a push that transfers nothing cannot
introduce a violation. Filed as #714 rather than fixed here, per Lead review.

**S-5, P2: two hooks blocked an override and then advertised it.**
`test-guard.sh` rejects the bare `[run-skip: reason]` form and named that same
bare form as the remedy in both of its block messages and in its header comment.
`ticket-required.sh` had the same staleness confined to its header comment; its
block message already named the structured form. #579 and #580 were applied to
the checks and not to the text that tells the operator what to do. Corrected in
all four places. Not separable from scenario (e): deciding whether the fixture or
the hook was wrong is deciding which of the two contracts in the file is real,
and leaving the messages would have settled that question one way in code and
the other way in prose.

**S-6, P3: a hypothesis about `ticket-required.sh` was checked and is false.**
Its bare-form regex is narrower than `test-guard.sh`'s and matches only
`[no-ticket]` and `[no-ticket:]`. That looked like a bypass for
`[no-ticket: any bare reason]`. It is not: that form matches neither pattern,
falls through to the general no-reference check, and exits 2. Recorded because
it was proposed and could otherwise be re-proposed by a reviewer.

**S-7, P1: the new CI step failed on its first run, and the reason is that
`test_guard.test.sh` had been passing on ambient machine state it never
declared.** Step 11 ran and reported 11 of 12 files passing.
`test_guard.test.sh` is the one that failed, and it is a file this commit
touches.

The file calls `git init` twice and, alone among the five test files that
create repositories, never sets a repo-local identity. Four others set
`user.email` and `user.name` immediately after `git init`. On the runner there
is no global git config, so every commit in the setup failed with `empty ident
name`, the push failed with `src refspec develop does not match any`,
`origin/develop` was never created, and the hook yielded on an unresolvable
merge base with `WARNING: test-guard: cannot determine merge base. Yielding.`

Two properties of that failure matter more than the missing config line.

First, it is the same shape as S-3 one level up. With the setup broken, the
four `expect_pass` scenarios still reported PASS, because a hook that yields
exit 0 is indistinguishable from a hook that allows for the right reason. Only
the scenarios using `expect_block_because` and `expect_block` failed. Reverting
the fix under runner conditions gives 4 passed and 4 failed: the four passes
are vacuous. `expect_pass` is degenerate in exactly the way `expect_block` was,
and the fix for it is not a harness change but a setup assertion, since the
scenarios cannot tell the difference by construction.

Second, this is the CI step earning its place inside the commit that adds it.
The file passed on macOS in every local run because the author's machine has a
global git identity. Nothing in the repository declared that dependency. The
step found it on the first run.

Two corrections: the two `git init` calls now set a repo-local identity, and
the setup asserts `origin/develop` resolves after the push and exits 1 naming
the consequence if it does not. Falsified by reverting both under
`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null` with a scratch
`HOME`, which reproduces the runner result.

## Peer review

writing-claims:3 -- every figure in the table names its derivation. The two
scanner-refusal counts are reported next to the measurement that reinterprets
them rather than on their own, because on their own they support the opposite
conclusion. The step-body figures come from text extracted out of the workflow
file rather than retyped, so the thing measured is the thing that ships.

writing-tests:7 -- all four corrected fixtures were run against knowingly broken
hooks before being trusted, and three of them failed that bar on the first
attempt. The step body was held to the same standard: a broken file was placed
in the real tree rather than a copied one, because the test files resolve the
hooks under test from their own location and in a copied tree all 12 fail, which
would have made the non-last-file property untestable. The first version of that
probe did use a copied tree, reported all 12 files failing in every case, and
proved nothing.

writing-rules:7 -- N >= 3 requires an audit matrix. The Quantified claims table
carries it, and the before and after mutation scores are kept as separate rows
rather than reconciled into one.

## Lead review

Scope grew beyond the design by two items: `expect_block_because` and the four
override-message corrections. Neither is separable. A harness that cannot tell
which block path fired makes three of this commit's own fixtures vacuous, and
this commit exists to stop `hooks/_test/` from being decorative; shipping it with
three decorative scenarios would instantiate the defect it removes. The message
corrections are the other half of the decision that settles scenario (e).

Scope was held at two places. The no-op push is filed as #714 rather than fixed,
because no scenario in this ticket needs it and its measured cost is confined to
pushes that transfer nothing. The broader question of whether the hook should
scan every commit a push would transfer, rather than only `HEAD`, is named in
#714 and not proposed here; against this history it would refuse roughly a third
of pushes and is a decision for the operator, not a detail of a test-wiring fix.

Also not settled here: whether other `expect_block` calls across the remaining
nine test files are exit-code-degenerate in the same way S-3 found. The mutation
test covered the scenarios this commit touches. The rest are untested against
that standard, and the honest statement is that they are unknown rather than
sound.

Assumption 2 is closed rather than accepted as a risk. The step was not called
done on a job colour: the step list was read from the Actions API, which showed
step 11 present and reporting rather than skipped, and showed it failing. That
read is what produced S-7. Had the standard been "the job is red, rebase and
retry", the vacuous-pass property of `expect_pass` would have shipped.

Scope grew once more, by the two `test_guard` setup corrections. Same test as
before: the commit adds a CI step whose purpose is to make `hooks/_test/`
non-decorative, and the step's first run showed one of those files was
decorative on any machine without a global git identity. Shipping the step
with that file failing, or with the file passing vacuously, would instantiate
the defect the commit removes.

Still not settled: whether the other four repository-creating test files have
setup steps that can fail silently in the same way. They set an identity, which
was the failure here, but none of them asserts that its setup succeeded. The
honest statement is that they are unknown rather than sound, which is the same
statement made above about the remaining `expect_block` calls.
