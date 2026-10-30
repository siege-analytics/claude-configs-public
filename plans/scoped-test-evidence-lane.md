# Scoped test-evidence producer execution lane (#386)

Goal source: #386
Plan reference: plans/scoped-test-evidence-lane.md
Investigate-artifact: plans/scoped-test-evidence-lane.md
Pre-mortem-artifact: plans/pre-mortem-scoped-test-evidence-lane.md
Hostile-review-artifact: plans/hostile-review-scoped-test-evidence-lane.md
Project-contribution: Give the content-bound test producer a usable execution route without treating arbitrary test code as an ungated reader.

The operator authorized the remaining repairs. The coordinator explicitly delegated this lane after accepting P1 and the reader/protected Git safety slice. Base: e876812 on bugfix/complete_runtime_recovery. Work occurs only in an isolated worktree; no live runtime settings or deployed source are changed.

## Design

Use the existing literal shell tokenizer and task selection, not a second authorization system. Recognize only the exact sibling hooks/lib/test-evidence.py from the current policy generation, invoked by the known Python interpreter with optional -I/-B. Accept one literal record command with exact --repo, repeated unique --source, --output, --think-gate, --framework and -- followed by opaque actual test argv. Copied/renamed/symlink producers and unsupported CLI forms do not acquire the lane.

The action is computation/mutation: read_only, investigation and self_managed_shape are false. Mutation targets are the canonical target Git root and each canonical declared source. The known executable is read policy code, not an invented mutation target. Receipt and think-gate locations are typed metadata validated after selecting repository authority; putting them into general mutation paths would incorrectly demand that a repository gate own another namespace.

The resolver requires the selected gate to be implementing, match the requested exact own-task think-gate.json and repo_root, and own the exact adjacent test-gate.json. Both paths must be canonical own-session lifecycle files, without symlink or hardlink escape. Normal effective-tier calculation and artifact checks still run over the repository computation. Task identity disambiguates; it never expands scope. An own-scratch working directory cannot create an early allowance.

The actual test argv stays opaque computation and can execute project code. Repository task authority is not an OS sandbox or a proof of every test effect. This route does not make bare pytest, arbitrary interpreter commands, foreign scripts or diagnostic wrappers read-only. Native terminal receipt compatibility remains unchanged.

## Alternatives and risks

Restoring the blanket pytest exception would repeat the reader write/execute bug. Adding producer and receipt paths to ordinary targets would make the valid own-task workflow unresolvable or require an excessive cross-namespace scope. The selected typed fields separate execution authority from exact lifecycle receipt ownership while retaining one task/tier selector.

The critical boundary is _test_receipt_record -> resolve_action -> select_task -> universal-mutation-gate. Real-hook tests must deny without an implementing task, deny missing effective-tier evidence, reject sibling/alias paths, then allow the exact producer and actually record successful content-bound evidence. Shared classifiers/resolver have high fan-out; public verdict fields and ordinary task/read paths remain compatible.
