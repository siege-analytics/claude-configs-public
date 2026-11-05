# PR1203 remote-wrapper and ignored-selector repair

Goal source: siege-analytics/claude-configs-public#1193
Related: #1161, #1171; CodeRabbit review of PR1203
Pre-author-inventory: exact reviewed0c08266150b2f89fc932d07e8eee8c1acc72c2ed, task_actions.finish/github_project_action and resolver pytest selector enumeration inspected before edits in isolated worktree.

## Design and investigation

After a wrapped remote command fails positive reader proof, wrapper argv can reach generic cwd targeting without a remote action. A valid local C gate must not authorize that remote operation. Reject unproven known-wrapper commands containing a literal gh executable before cwd fallback; do not build an unwrapping engine. Proven wrapped reads, direct supported gh operations and normal conservative local test execution retain their contracts.

Explicit pytest directories enumerate tracked Git files only. Ignored high-risk files inside the selected directory can therefore disappear from the execution floor even though pytest can collect them. Include cached and all other files for that exact directory without exclude-standard. Preserve Git listing failure-to-C and ordinary ignored B files; no global scope or task ownership change.

## Pre-mortem

Launch-Blocking Tiger: local gate authorizes remote deletion through wrappers. Mitigate actual broad-local-gate denial fixtures, pure action target checks and direct supported remote positive controls.
Launch-Blocking Tiger: ignored high-risk execution remains classified B or benign ignored tests become universally C. Mitigate explicit ignored C/B directory fixtures and failed enumeration C case.
Falsification: wrapped gh mutation still falls through local scope, a reader requires a new grant, ignored selected C files vanish or another task supplies authority.

## Test plan

Red-first real classifier/action/universal gate cases for timeout/nice/time wrapped remote mutations; preserve direct typed add and wrapped reads. Existing execution-risk fixture gets ignored-only C selector, benign ignored B selector, listing-failure and conservative normal wrapper controls. No network, pytest execution, live publication, installation or integration-tree changes. Root/source peer review precedes publication.
