# Issue #962 F2/F3 pre-mortem

## Scope

Tier C remediation of epic #962 F2/F3 from exact base `0bae4ff108de5ad3b339a868818b05ea1e7c70bd`. This plan changes package/runtime enforcement surfaces but authorizes no installation, deployment, release, main promotion, or merge.

## Failure modes and controls

### Tiger: stale-output false green

**Severity:** HIGH

**Likelihood:** Medium unless `dist/` is deleted before the final canary.

**Mitigation:** Remove the ignored generated tree, rebuild all layouts from nothing, copy each package outside the checkout, and execute actual prompt and push hooks there.

| Risk | Severity | Failure signal | Preventive control | Rollback |
|---|---|---|---|---|
| Nested/flat still omit one runtime dependency | Tiger / P1 | isolated prompt warns selector unavailable or push blocks classifier unavailable | central `install_hook_runtime`; assert all four files in all four copied packages | revert the feature commit |
| Manifest is flat-correct but nested-wrong | Tiger / P1 | manifest `package_path` is absent in copied nested package | derive path from `dist/<layout>/skills/` inventory output; validate every manifest entry against final package bytes | revert manifest refactor |
| Hook resolves against consumer cwd | Tiger / P1 | emitted path points into clean target repo or source checkout | resolve from hook-derived installation root; assert absolute emitted paths stay inside copied package | revert hook output change |
| Canonical provenance is replaced by runtime path | High / P2 | source/consumer parity loses `projects/...` identity | retain `source_path`; add `load_path`; compare canonical route shapes across source and four packages | remove additive field and reassess interface |
| Project overlay only proves one skill | High / P2 | rule, notebook-impact, or error-path-tests missing | one exact-host prompt selects review + signature + error path; assert rule plus all three project sources and files | revert and split route fixture if ambiguity appears |
| A stale `dist/` masks missing files | Tiger / P1 | test passes only after earlier builds | delete ignored `dist/`, build from nothing, copy packages to a new temp root | revert feature commit |
| Test reconstructs hidden mapping instead of checking instructions | Tiger / P1 | selector passes but hook presents absent paths | parse actual hook output, assert every presented path is absolute/readable/in-package | revert hook and test together |
| Host/shelf/unknown boundaries regress | Tiger / P1 | foreign origin gets project content, shelf selects, or unknown gets capabilities | source/four-consumer parity cases plus full 51 language and 78 data fixture matrices | revert selector changes |
| Valid Tier A push still fails in a clean repo | Tiger / P1 | self-review hook exits 2 | create a new scoped Git repo with a real Tier A commit and invoke each copied package hook | revert packaging changes |
| Workspace sync leaves stale runtime | High / P2 | install validates hooks but bin/catalog missing | document four-directory sync; installer explicitly validates each runtime file | revert docs/validation and keep issue open |
| Hook paths escape package through traversal/symlink | High / P2 | emitted resolved path is outside installation root | hook resolves then requires every path to be relative to package root and readable | revert absolute-path emission |
| Larger emitted paths exceed budget | Medium / P2 | progressive metric reaches 12,000 characters | regenerate measured metric and retain existing hard limit | shorten output format or revert |
| Existing attested ledgers are rewritten as fake historical evidence | High / P2 | nested/flat keys appear in old baseline records | validate current nested/flat parity while preserving existing evidence forms | revert ledger checker expansion |

## Canary and rollback

Canary is the isolated copied-package integration test plus a from-scratch `dist/` rebuild. It exercises actual prompt and push hooks without installing into a user workspace. Rollback is a single commit revert on the feature branch/develop if independent review or CI falsifies any closure claim. No migration or external state needs reversal because this change does not install, deploy, release, publish, or mutate consumer workspaces.
