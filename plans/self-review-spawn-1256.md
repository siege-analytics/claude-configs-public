# Self-review — sibling worktree spawn isolation (#1256 item 3)

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: siege-analytics/claude-configs-public#1256 item 3 and Root's scoped assignment
Goal source verification: evaluate-ticket returned BLOCK for umbrella formatting, not absence of the reported behavior; see evidence exemptions below.
Plan reference: plans/investigate-spawn-1256.md
Pre-author-inventory: plans/investigate-spawn-1256.md
Investigate-artifact: plans/investigate-spawn-1256.md
Pre-mortem-artifact: plans/pre-mortem-spawn-1256.md
Hostile-review-artifact: plans/hostile-review-spawn-1256.md
Project-contribution: accepts actual sibling isolation without weakening shared-checkout protection or unrelated spawn contracts.

## Peer review

Author mechanical review: existing permission/model/reasoning/labels/source/rules
checks retained. Git metadata is read-only and independent of naming. Plain
existing non-Git directories do not require Git. Explicit read-only review stays
available. The new Python fixture invokes the actual registered hook with native
spawn-shaped JSON and real private Git worktrees; no session API is called.

Independent Claude and Root review findings/dispositions are recorded in the
hostile-review artifact. The artifact chronology is explicit: durable records
were authored after implementation; no pre-work artifact is claimed retroactively.

## Lead review

Affirmative standards: prove the directory the host will actually use; separate
physical Git state; bound local metadata operations; retain ordinary non-Git and
read-only routes; keep user authorization separate from isolation evidence.
Root accepted the exact final normalization delta and actual fixture results in
https://github.com/siege-analytics/claude-configs-public/issues/1256#issuecomment-6759510706 .
No protected merge, live install or completion of the other #1256 items is claimed.

## Test plan

Run `bash hooks/_test/spawn_guard.test.sh` from both the repo and /tmp, syntax
checks, full package build and the copied package's spawn suite. Retain all old
contract scenarios and the entire structural suite. Native push checks and CI
remain required before protected integration. Existing installed a0 is unchanged.

## Adversarial shape audit

Shape space: explicit spawn arguments mapped to existing Git or ordinary folders.
Fixture-covered shapes: sibling/subdir/symlink linked targets; canonical checkout
with magic wording/path; copied pointer; parent reuse; non-Git/no-Git; missing or
file target; read-only review; inherited Git targeting; FIFO/oversize; host HOME,
relative/default and lexical-before-symlink normalization.
Prose-vs-implementation gap: removed the parent-cd example and prompt-promise
waiver. Actual host delivery is not claimed from source fixtures.
Adversarial frame this round: security engineer.
Adversarial fixture from frame: copied .git pointer plus nonblocking FIFO and
oversized admin-backpointer denials in spawn_worktree_isolation.py.

## Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| F1 | P1 | Lexical worktree waiver rejects siblings and accepts shared checkout promises | fixed |
| F2 | P1 | Ordinary backpointer read can block on FIFO | fixed |
| F3 | P1 | Relative/HOME/symlink normalization can inspect a different host target | fixed; independently accepted by Root |
| F4 | P2 | Parent setup example cd contradicted separation | fixed |

## Quantified claims

- Initial baseline: real-Git unittest run reported `Ran 8 tests`, `FAILED (failures=5)`.
- Current complete spawn suite: `bash hooks/_test/spawn_guard.test.sh` reports
  `Results: 14 passed, 0 failed` and `Ran 15 tests`, `OK`.
- Root reported actual host normalization suite: 8 tests passed, 9 assertions;
  this author does not represent that as a locally rerun app test.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| FIFO risk during review | Unbounded file read overlooked | private malformed metadata fixture | bounded reader and fixture rerun | not timed |
| Claude parent-cd finding | Setup example retained child-side command | exact example review | remove cd, bind fixture cwd | not timed |
| Root actual-host normalization findings | Parent-relative inference instead of provider contract | actual app path tests | literal target + HOME/order controls | not timed |
| Mac /var fixture assertion | Compared raw path spelling to canonical output | resolve fixture expected path | test-only assertion correction | not timed |

## Evidence-predates-work

These durable artifacts were authored after initial implementation; investigation,
design and red-fixture evidence preceded it in the native transcript. No artifact
is backdated. Commit ancestry records documentation versus committed work only,
not an assertion that the files existed before authoring. Publication waits for
actual independent review and final checks under the existing task grant.

## Exemption: umbrella Context, Goal and Acceptance headings

Reason: #1256 is a multi-item incident report; Root assigned only item 3.
Evidence: its item 3 describes the exact sibling path and lexical gate; the bounded
observable acceptance and negative cases are recorded in the investigation plan.
Falsification: a proposed change cannot be traced to that specific observed fault.

## Exemption: umbrella design reference and Assumptions headings

Reason: do not rewrite unrelated incident items merely to fit a template.
Evidence: the plan and assumptions in these committed records provide the scoped
source/behavior/risk contract; Root explicitly retained the existing task grant.
Falsification: readiness is claimed without actual source, fixture and independent
review evidence, or this change purports to resolve another #1256 item.
