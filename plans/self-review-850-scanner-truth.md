# #850 scanner source truth and explicit errors

Pre-mortem-artifact: this document, Failure analysis
Hostile-review-artifact: this document, Peer review (independent review pending)

## Assumptions

Scanning is a diagnostic operation; it does not execute candidate Python or grant
authorization. Index and PR scans must inspect the selected object contents.
Working mode intentionally inspects working files. Existing writing-rule behavior
and controlled exception vocabulary remain applicable.

## Plan

Freeze staged/PR identity once, use it for textual diff and an isolated Python/
cross-file/config snapshot, and preserve logical paths. Keep existing rule engines
while propagating all incomplete scans as exit 2. Add source-mismatch/error tests,
retain the existing scanner fixtures, document self-scan scope, and review the
exact final commit independently before integration.

## Failure analysis

- A staged violation disappears in the working file: both scanner paths must read
  the same frozen index tree, with inverse-direction controls.
- PR changes between diff and file retrieval: capture base/head once and derive
  data from those exact objects; missing objects must fail, not use checkout files.
- Unstaged tests or config satisfy checks for staged source: snapshot related
  Python/config files from the same selected tree.
- A source/test/config read or parse error looks clean: separate incomplete exit 2
  from violation exit 1, and never suppress child status before a clean result.
- Symlinks or unusual paths escape the snapshot: accept only bounded regular
  source inputs, validate paths, preserve NUL-safe file names and never extract
  arbitrary archives or follow candidate symlinks.
- Scanner-self friction causes blanket exclusions: use actual regression evidence
  and narrowly documented exceptions only; unrelated style findings stay visible.

## Peer review

Confirmed the three original mismatch/parse reproductions on accepted develop.
Independent exact-head review will be requested from the existing Craft agent;
all findings and final verdicts belong on the PR.

## Lead review

Keep snapshot selection distinct from policy authority and from rule severity.
No general shell parser, separate policy registry or broad baseline is introduced.
Source material remains in temporary local fixtures and is not posted publicly.

## Quantified claims

- 18 selected-source/error contract tests pass, including index/worktree mismatch
  in both directions, PR object fetch/mismatch, same-tree cross-file evidence and
  config, unborn/unmerged index, symlink rejection, and subprocess/input faults.
- All 11 existing scanner shell suites pass. Both scanner Python files pass
  their own AST scanner with only named, fixture-backed bootstrap exceptions.
- Full repository validation: 82/82 commands pass in 404.2 seconds on Python
  3.13, including all Python modules, 36 hook suites, two workflow policy suites,
  both output builds, freshness and hook validators.
- Generated authority remains current: 198 sources, 804 artifact snapshots,
  2,916 generated file mappings. The new helper is packaged in both layouts.
- Validation logs: `/tmp/cc-850-focused.log`, `/tmp/cc-850-skill-tests.log` and
  `/tmp/cc-850-full-validation.log` on the implementation workstation. Hosted
  validation and independent review are pending on the published exact head.

## Limits

Working mode is deliberately mutable; it detects observed concurrent byte/diff
changes, but does not claim an atomic filesystem snapshot. Index selection can
refresh Git index metadata while preserving its selected tree. PR mode requires
`gh` metadata and exact Git objects; missing inputs return incomplete status.
This fixes source provenance and incomplete-result handling, not every historic
repository style finding in #765. No blanket self-exclusion is introduced.

## Canary and rollback

Use disposable Git repositories and exact local PR objects. Preserve selected
index/worktree bytes during scans, test missing/inert subprocesses and error
propagation, then run the full scanner and repository suites. No shared runtime
installation is part of this change. Revert through normal develop workflow if
the accepted scanner regresses; never report an incomplete scan as clean.
