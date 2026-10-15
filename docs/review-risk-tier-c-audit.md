# Tier C enforcement dependency audit

This audit defines when a path belongs to Tier C because changing it can bypass, downgrade, or falsely validate blocking enforcement. It closes epic #962 finding F4. The audit follows executable dependency edges instead of promoting every hook or every CI utility.

## Classification rule

A tracked path is Tier C when at least one of these statements is true:

1. It is a blocking hook or native Git-hook entrypoint.
2. A blocking entrypoint sources, executes, or imports it and a changed result can turn a block into an allow or downgrade a hard block to an advisory.
3. It generates the hook registry, enforcement manifest, native pre-push runtime, or packaged enforcement files used by consumers.
4. It is a required CI checker whose implementation determines whether an enforcement invariant passes.
5. It supplies authoritative discovery to one of those checkers.

Deletion and rename source paths are part of the same boundary. The classifier reads Git changes with `--no-renames`, so a moved Tier C source cannot inherit the tier of its benign destination.

## Dependency graph and Tier C rationale

| Enforcement surface | Dependency path(s) | Why a change is Tier C |
|---|---|---|
| Hook registry | `hooks/settings-snippet.json`, `.claude/settings.json` | Controls which blocking entrypoints execute. These paths were already Tier C. |
| Shell and write blockers | `hooks/bash/`, `hooks/git/`, `hooks/write/` | Existing family floors cover blocking entrypoints. |
| Agent communication blockers | `hooks/agent-comms/hub-concurrency-gate.sh`, `hooks/agent-comms/no-slug-form-outbound.sh`, `hooks/agent-comms/spawn-guard.sh` | Each is a configured PreToolUse entrypoint and can allow a forbidden send/spawn when weakened. The pattern names the three entrypoints rather than the whole directory. |
| Infrastructure mutation blocker | `hooks/infrastructure/catalog-guard.sh` | Configured Bash entrypoint; changing command parsing or catalog matching can allow protected catalog mutation. |
| Command and message extraction | `hooks/lib/extract-json.py`, `hooks/lib/commit-message.py` | Most Bash, Git, write, infrastructure, and message blockers trust parsed tool input; `ticket-required.sh` and native `commit-msg` both trust the effective-message resolver and ticket validator. Returning an empty or altered value can bypass matching or ticket enforcement. |
| Repository scope | `hooks/lib/scope-check.sh` | Sourced by blocking Git hooks. Returning false makes callers exit successfully before enforcement. |
| Runtime policy | `hooks/lib/detect-host.sh`, `hooks/lib/gate-registry.sh` | The Craft/Claude/Codex identity and manifest policy determine whether resolver block signals hard-stop or become advisory. |
| Gate signal resolution | `hooks/lib/resolve-think-gate.py` | Blocking mutation and resolver gates trust it to find the applicable task/repository evidence. Returning no gate can suppress enforcement. |
| Write after-image and path identity | `hooks/lib/after-image.py`, `hooks/lib/canonical-path.py`, `hooks/lib/artifact-casefold-candidate.py`, `hooks/lib/split-frontmatter.py` | The ticket-propagation blocker trusts these helpers to identify the target, resulting content, case variants, and frontmatter. Altered successful output can make a noncompliant write appear compliant. |
| Machine probe evidence | `hooks/lib/probe-runner.py` | Self-review enforcement accepts its result format as machine-generated evidence. Weakening result computation can admit false passing evidence. |
| Consumer runtime generation | `bin/build.py` | Defines blocking gates and runtime policy, generates the enforcement manifest and native pre-push hook, and packages hooks, helpers, settings, classifier, and policy. |
| Hook wiring validation | `bin/validate-hooks.py` | Required CI checker for missing, non-executable, syntactically invalid, or drifted hook wiring. Weakening it can falsely validate a dark guard. |
| Generated-source authority | `bin/generated-source-authority.py` | Required CI checker for canonical/generated drift, collisions, missing ownership, and fresh isolated consumer builds. |
| Authority discovery | `bin/skill-inventory.py` | Supplies the source inventory consumed by generated-source authority. Narrowing discovery can remove sources from enforcement while keeping derived catalogs internally consistent. |
| Kernel enforcement budget | `bin/kernel-budget.py` | Required CI checker for kernel structure, size, shelf isolation, and agreement with fresh generated-source authority. |
| Review classifier, policy, and required CI suites | `bin/review-risk.py`, `catalog/review-risk-policy.json`, `bin/_test/review_risk_test.py`, `hooks/_test/review_risk_policy.test.sh` | Code-owned and policy-owned tier floors plus the two required suites that validate classification and commit/push rejection. Weakening either suite can falsely validate this boundary. |
| Other existing enforcement | `.githooks/`, `.github/workflows/`, `scripts/ci/`, release/deploy/install/wiring scripts, resolver guard entrypoints, lifecycle/data-scope checkers | Existing Tier C patterns remain in force and were not broadened by F4. |

## Advisory and generated-output exclusions

These paths remain below Tier C for a specific reason:

- `hooks/lib/log-block.sh` records audit events only. Blocking callers source it with ignored failures; its return value does not change their allow/block decision.
- `hooks/create-ticket/scaffold-test-stub.sh` is not in the configured hook registry or generated blocking manifest. Its nonzero exits report invocation/input failures rather than enforce a registered mutation boundary.
- `bin/review-risk-metrics.py` derives freshness metrics. It neither classifies production changes nor participates in commit/push enforcement.
- `catalog/generated-source-authority.json` and `catalog/kernel-budget.json` are generated evidence, not policy inputs. Their Tier C checkers recompute expected content from source and reject hand-edited, deleted, or stale output.
- An unrecognized `hooks/agent-comms/*.sh` path remains Tier B. Only the three configured blocking entrypoints are elevated, preventing a directory-wide hook floor without evidence.

Warning-only behavior inside a path does not automatically remove that path from Tier C when the same file also participates in a blocking chain or is already covered by a conservative established floor. This change adds no `^hooks/` or `^hooks/(lib|infrastructure)/` catch-all.

## Machine-checked graph contract

`bin/_test/review_risk_test.py` does not rely only on the path list above. It independently:

- compares `hooks/settings-snippet.json` against independently maintained path/occurrence counts and a hash of every complete event, matcher, and hook record; it removes, duplicates, and neutralizes every command occurrence with `>/dev/null 2>&1; true`, requiring each mutation to fail, including helper-free blockers;
- runs `bin/build.py` into an isolated temporary distribution and separately hash-pins every complete generated manifest gate and generated settings registration in addition to path/count checks; generated settings receive the same removal, duplication, and forced-success mutations;
- recognizes helper assignments only when the quoted value ends at the helper path and the exact quoted variable is subsequently the sourced file or a `python3` script operand in shell command position; it hash-pins all 47 exact invocation lines and all 60 exact assignment-use occurrence lines in addition to edge/count snapshots, including the two blocking callers of `commit-message.py`;
- removes and duplicates each downstream use by its actual line index, replaces its script operand while retaining the audited variable in a comment, and prefixes the apparent execution with `echo`; every mutation must fail the assignment-to-execution audit;
- replaces each helper assignment with another path while retaining the audited helper basename only in a trailing comment, which must remove the edge;
- pins exact generated-source-authority, kernel-budget, workflow, runtime-generator, hook-validator, and review-risk-suite invocation lines with occurrence counts, then removes each occurrence in memory and requires the invocation audit to fail;
- requires every derived entrypoint and decision-changing helper to classify Tier C, with only `hooks/lib/log-block.sh` accepted as a non-decision-changing helper edge.

Removing or renaming an invocation therefore makes the graph audit fail until the implementation and audit are reconciled.

## Regression contract

The same test enumerates every F4-added dependency and proves all of the following for each path:

- direct classification is Tier C;
- a staged modification is Tier C and rejects `--declared B`;
- a staged deletion is Tier C and rejects `--declared B`;
- a staged rename to a documentation path remains Tier C through its source path and rejects `--declared B`.

The same test pins the listed advisory and unrecognized-hook exclusions at Tier B and the two generated catalogs at Tier A. For each generated catalog it invokes the real Tier C checker against a modified temporary copy and a deleted path, requires both to fail, then requires the checked-in catalog to pass `--check`. `bin/review-risk-metrics.py` records representative helper, guard, checker, generator, and exclusion fixtures.

## Rollback

Revert the F4 commit. That restores the prior Tier C path set, tests, metrics, and this audit. No install, deployment, publication, release, or promotion is part of this change.
