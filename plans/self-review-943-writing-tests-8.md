# Self-review — writing-tests:8 (CCP#943)

## Assumptions

Working as: tech lead, software engineer
Goal source: #943
Pre-author-inventory: #943 — grep-verified that no rule in _writing-tests / _verify-before-execute / _writing-code covers editable-install / __file__ provenance or existing-caller-test execution; the provenance trap lived only in the feedback_reproduce_loaded_package_state operator memory. Editor agreed to both clauses with four adjustments (heuristic -> separate ticket #944; keep behavior-change-on-shared-function scope; embed the worktree-isolation interaction; promote the memory instance into the shelf).
Investigate-artifact: #943
Pre-mortem-artifact: #943
Project-contribution: Prevents recurrence of a miss that already happened (the #1345 false-pass that broke a caller test) by making provenance + caller-coverage a named, reviewable standard for behavior changes to shared functions across the whole workspace.

Key assumptions:
- _writing-tests-rules.md is a general source rule editable directly in skills/ (not a build artifact). Verified: edited directly in #932.
- Judgment-enforcement v1 matches how writing-code:7/:15 were introduced. Verified against their Override sections.

## Peer review

- **writing-prose:1 (no AI typography/adverbs).** Added rule text uses ASCII `--`, no em/en-dashes, no banned adverbs. Evidence: `git diff | grep '^+' | grep -nE 'dashes|adverbs'` -> empty.
- **writing-tests:1 (self-consistency).** The new rule operationalizes writing-tests:1 at the shared-function seam: a test that passes against unchanged (shadow-loaded) code is not a test of the change; the rule names the two checks that prove it is.
- **Editor adjustments applied.** (1) mechanical heuristic is a SEPARATE ticket (#944), not this PR; (2) scope is behavior changes on shared functions, not all test edits; (3) the worktree-isolation / spawn-protocol #12b interaction is embedded; (4) the feedback_reproduce_loaded_package_state instance is promoted into the shelf as a concrete case. Evidence: grep markers writing-tests:8 / "Worktree-isolation interaction" / feedback_reproduce_loaded_package_state = 1 each.
- Gate 1 (syntax): N/A -- markdown only.
- Gate 2 (tests): N/A -- no executable change. Validation: `python3 bin/build.py --check` -> exit 0 (all `[skill:...]`/`[rule:...]` tokens in the new text resolve).
- Gate 3/4: N/A.

## Lead review

- **As tech lead:** one-rule addition to an existing shelf file, judgment-enforced v1 (no scanner in this PR), matching the established ratchet for writing-code:7/:15. LOW blast radius (prose). The mechanical follow-up is tracked (#944) so the rule is not left half-mechanized.
- **As software engineer:** both clauses are each independently grounded in the #1345 miss (provenance: the worktree __file__ pointed at the main clone; caller-coverage: running test_testing_runner.py would have caught the break), so the rule is evidence-backed, not speculative.
- No AI/assistant attribution anywhere.

## Quantified claims

- **1 rule added** (writing-tests:8) with 2 clauses + the worktree-isolation interaction + the #1345 instance. Evidence: grep writing-tests:8 = 1.
- **4 Editor adjustments applied.** Evidence: the markers above + the absence of any scanner code in the diff (heuristic deferred to #944).
- **build --check exit 0.** Evidence: command output.
- **1 file changed** (skills/_writing-tests-rules.md) + this artifact. Evidence: `git status -s`.
