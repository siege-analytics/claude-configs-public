---
ticket_refs:
  - siege-analytics/claude-configs-public#1166
---

# Git archive outputs and apply inspection operands

Goal source: issue1166 comments6783523709/6783549411. Fresh normal helper-created branch bugfix/git_read_output_targets_1166 starts at verified develop19506a4559fa3525b6e897ea27e313ae199aed2f. This investigation/design note precedes runtime edits. Existing1152 tar/venv/scratch author retains that separate worktree; only Git operand/reader regions belong here.

## Problem and intended behavior

The action parser's generic Git mutation path always includes the effective repository and slash-bearing read operands. That is correct for actual apply, but falsely requires source-repository mutation scope for archive output and inspection-only apply. The released reader also lacks those subcommands. Preserve one shared narrow option grammar rather than certify unknown shapes by subcommand name.

Model archive stdout as a read, and archive with one explicit output as only that file mutation. Resolve relative outputs from Git's effective -C directory. Preserve normal destination alias/task checks and shell redirection semantics. Model only check/stat/numstat/summary apply forms without an apply/write override or auxiliary output. Actual apply remains repository mutation; unsupported options retain conservative handling. Candidate commands are never executed by the guard.

## Risks and controls

Launch-blocking risks: custom archive format commands or remote upload helpers execute programs; filename-based format inference can select them. An apply dry-run may still request a fake-ancestor output; --apply can restore mutation after a summary/check mode. Unknown/global configuration/alias forms must not acquire reader status accidentally. Inspect actual Git behavior in private repositories and preserve conservative unsupported handling.

Red-first fixtures must observe archive -o ownership against an unowned source repository, stdout without an output, apply --check with no file effects, actual apply still writing its repository, foreign-output denial, aliases/symlinks and compound mutations. Private actual Git archive/apply effects corroborate classifier claims; no live repository writes or installed configuration changes. Run focused readers/ownership and affected negative audit checks once source freezes. Normal source review, genuine native commit/push, develop PR with Refs1166 and exact-head CI follow; no protected-branch push/merge or installation from this source lane.

Official behavior references: https://git-scm.com/docs/git-archive and https://git-scm.com/docs/git-apply. No new global gate, task registry, credential/configuration mutation or permission exception is part of this repair.
