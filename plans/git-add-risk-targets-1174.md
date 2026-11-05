# Explicit Git staging risk targets

Goal source: siege-analytics/claude-configs-public#1174; related #1171/#1152. Root approved this named-file staging slice before code. Base c4d2f8a includes the reviewed #1161 candidate; no other worktree is modified.

## Design and investigation

The current action classifier selects the Git repository toplevel as ownership target. That must remain: an index is repository-wide state, so a nested-path task cannot borrow a repository owner's authority. The defect is in task_tier: that ownership root becomes every tracked file for risk classification. The existing lone-commit exception already distinguishes this question for commit targets.

Add a similarly narrow explicit-named-file Git-add risk derivation, using the existing shell and Git normalizer. Accept one literal git add with explicit existing regular named files; known path-preserving flags and -- are allowed. Resolve actual command cwd and -C correctly; filenames without slashes are real operands. Reject narrowing for directories, symlinks, deleted/missing paths, globs/pathspec syntax, unknown/configuration options, no paths, nonliteral dispatch, compositions or failed metadata inspection. Those forms keep the existing conservative classification; this is not a new command denial. The classifier and declared-tier maximum still apply.

Alternatives: dropping the repository ownership target would let a nested task mutate an index it does not own. Classifying only the branch diff for every execution/merge command would conflate different effects and expand this repair beyond its evidence. A named-file risk view is bounded and leaves those operations unchanged.

## Pre-mortem

Tiger: treating ownership and risk as one list could loosen task isolation. Preserve action paths exactly and verify real cross-task hook denials. Tiger: option/pathspec or compound commands could hide C targets. Narrow only proved grammar, keep all other forms conservative, test actual code/workflow/policy paths and mixed commands. Tiger: lost cwd could classify an identically named file in the wrong tree. Pass actual tool cwd and reuse git prefix -C resolution; test workspace cwd and nested cwd. Paper tiger: missing/deleted exact file stays C in this initial slice; operational usefulness is existing explicit files, not claiming complete Git add semantics.

## Test plan

Red-first floor checks with unrelated workflow files in the fixture: prose A, ordinary code B, enforcement/workflow/policy C; declared tier raises. Actual universal-hook A positive, B/C prerequisite denials and positives, repository-owner vs nested-only task denial, wrong current session/task denial. Unknown options/no paths/directories/pathspecs/symlinks/compounds stay conservative. Existing source/consumer validators and required exact-head protected CI; no installation or protected merge here.

Pre-mortem-artifact: plans/git-add-risk-targets-1174.md#pre-mortem
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1174
