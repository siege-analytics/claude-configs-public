---
ticket_refs:
  - siege-analytics/claude-configs-public#713: design note
---

# Design: #713 run hooks/_test in CI

Goal source: siege-analytics/claude-configs-public#713

## What the investigation found

The ticket was filed from a measurement taken on the #703 branch: 12 test files
under `hooks/_test/`, no CI step running any of them, and 3 files failing with 6
failing scenarios. All three failures and all six scenarios reproduce on a clean
`origin/develop` worktree at `2cd567f`, so none of them is an artifact of the
#703 branch.

The ticket's Assumption 1 said the six failures were defects in the hooks rather
than in the fixtures, with evidence for three of them and the other three
unverified. That assumption is **half wrong**, and the half that is wrong is the
half the ticket claimed evidence for the other way round. Settled per scenario:

| Scenario | Determination |
|---|---|
| `detect_ai_fingerprints` (b) em-dash in body | hook defect |
| `detect_ai_fingerprints` (c) banned adverb in body | hook defect |
| `detect_ai_fingerprints` (d) structured Why/How to apply | hook defect |
| `test_guard` (c) `testing:` but no `test-gate.json` | wrong fixture, intent legitimate |
| `test_guard` (e) `[run-skip: reason]` override | wrong fixture, behaviour removed on purpose |
| `ticket_required` (r) `[no-ticket]` override | wrong fixture, behaviour removed on purpose |

Three hook defects, three wrong fixtures. The ticket guessed all six were hook
defects.

### The three `detect_ai_fingerprints` rows are one defect

`hooks/git/detect-ai-fingerprints.sh` walks up from its own directory looking
for `skills/meta/detect-ai-fingerprints/scan.sh`. The repository has no
`skills/meta/` directory. Commit `f76ea4d`, dated 2026-06-02, flattened
`skills/meta/<slug>/` to `skills/<slug>/` and did not update the hook's four
references to the old path. When the walk finds nothing the hook takes its
allow-early exit, which is documented at line 83 as opt-in-by-file-existence
and is the correct behaviour for a checkout that does not carry the scanner.
Here it fires on every push in the repository that owns the scanner.

458 commits have landed on `develop` since `f76ea4d`, and the hook file has not
been touched since that same day. Every push in that window was scanned by a
hook that could not find its scanner.

The flat path is right for the consumer packages too, so the fix is a path
correction and not a dual-path search. Building `dist/` puts the scanner at
`skills/detect-ai-fingerprints/scan.sh` in all four layouts (`claude-code`,
`craft-agent`, `flat`, `nested`) with the hook at `hooks/git/`, so the upward
walk from the hook reaches a package root that contains the flat path.

Replacing the four occurrences turns the file from 2 passed / 3 failed to 5
passed / 0 failed.

### The three fixture rows are two different kinds of wrong

`test_guard` (e) and `ticket_required` (r) encode overrides that were removed on
purpose. Commit `#579` tightened bare `[run-skip: reason]` to require a
`Reason/Evidence/Falsification` chain, and `#580` did the same for
`[no-ticket]`. Both hooks block the bare form with a message naming the ticket
that removed it. The fixtures assert the pre-#579 and pre-#580 contract. They
are corrected to the structured form rather than deleted, because the scenario
they exist to pin down is that a valid override opens the gate, and that is
still a rule worth pinning.

`test_guard` (c) is a different failure. The scenario intends to assert that a
project declaring `testing:` with no `test-gate.json` is blocked. The setup
pushes `develop` to a bare remote before the scenario runs, so at that point the
repo is 0 commits ahead of `origin/develop` and `git diff merge-base...HEAD`
returns an empty set. The hook exits 0 at its empty-touched-files check, which
is correct: a push that touches no source demands no evidence. The fixture
asserts a real rule through a setup that cannot reach it. Corrected by leaving
an unpushed source change, which preserves the intent.

### Two findings that fall out of settling the six

Settling (e) surfaced that `test-guard.sh` blocks the bare `[run-skip: reason]`
form at line 143 and then advertises that same bare form as the remedy at lines
224 and 260, with the header comment at line 15 agreeing with the messages
rather than with the check. The #579 tightening was applied to the check and not
to the three places that tell the operator what to do. A hook whose block
message instructs the operator to do the thing the hook blocks is the shape the
enforcement-contradiction rules exist to catch, and it is not separable from
this ticket: scenario (e) cannot be corrected without deciding which of the two
contracts in the file is the real one.

The same reasoning applied to `ticket-required.sh` found only a stale header
comment at line 12; its block message at line 103 already names the structured
form. A hypothesis that the narrower regex there was a bypass was checked and is
false. `[no-ticket: because I said so]` matches neither the structured pattern
nor the bare-form pattern, falls through to the general no-reference check, and
exits 2. Recorded because it was proposed, not because it needs fixing.

## Design

Two changes, one commit, in the order the ticket argues for. Adding the CI step
first turns a silent gap into a red build on every open PR in the epic; fixing
the scenarios first leaves nothing enforcing them. Neither intermediate state is
committed.

**Change 1: resolve the six scenarios.**

- `hooks/git/detect-ai-fingerprints.sh`: four occurrences of
  `skills/meta/detect-ai-fingerprints` become `skills/detect-ai-fingerprints`.
- `hooks/git/test-guard.sh`: lines 15, 224 and 260 stop advertising the bare
  `[run-skip: reason]` form and name the evidence chain the hook accepts.
- `hooks/git/ticket-required.sh`: the header comment at line 12 names the
  evidence chain.
- `hooks/_test/detect_ai_fingerprints.test.sh`: the setup symlinks are removed.
  They pointed at the stale path, so they were dangling, and they were inert:
  the hook resolves the scanner from its own install location, which the file's
  own closing note already records. Removing them was verified not to change the
  result.
- `hooks/_test/test_guard.test.sh`: scenario (c) gets an unpushed source change;
  scenario (e) uses the structured override.
- `hooks/_test/ticket_required.test.sh`: scenario (r) uses the structured
  override.

**Change 2: run the files in CI.** A step in `build-and-publish.yml` that runs
every file in `hooks/_test/` and fails the job on any non-zero exit, on the same
trigger as the rest of the workflow.

## Assumptions

1. **The flat scanner path is correct for consumers as well as for this repo.**
   Checked rather than assumed: `dist/` was built and the scanner appears at
   `skills/detect-ai-fingerprints/scan.sh` in all four package layouts. If a
   consumer carried the nested layout the fix would have to search both paths.
2. **The 9 currently passing files pass on ubuntu-latest as well as on macOS.**
   Not yet checked. `pr_base_guard.test.sh` and `test_guard.test.sh` build
   temporary git repositories, so a platform difference surfaces there first.
   This is checked on the branch before the step is called done, and it is the
   assumption most likely to be wrong.
3. **The harness propagates scenario failure through the file's exit code.**
   Checked: the 3 failing files exit 1 and the 9 passing files exit 0 on the
   same run. If this were false the CI step would be decoration.

**Not assumed:** that the ticket's Assumption 1 holds. It does not, and the
determinations above replace it.

## Falsification

Restore the pre-fix `hooks/git/detect-ai-fingerprints.sh` and re-run the new CI
step. It goes red, because scenario (b) expects exit 2 on an em-dash in the
commit body and the reverted hook returns exit 0. Before this ticket the same
revert produces a green build, because no step runs the file.
