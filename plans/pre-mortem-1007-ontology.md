# Pre-mortem: shared ontology (#1007)

The proposed change adds canonical terminology validation to CI and generates an
on-demand wiki page. It does not change runtime policy decisions or host adapters.
Base: `abe0bb0a3fe2dd99594bb5d4d61583ba61ea367a` (`develop`).

| Failure | Consequence | Prevention and evidence |
|---|---|---|
| A shared word silently retains two meanings | Contracts disagree while appearing compatible | Distinct canonical IDs; ambiguous/deprecated references reject with alternatives. |
| An annotation is treated as behavioral proof | Installed or configured hooks are reported as live enforcement | Definitions separate evidence stages; legacy blocking fields bind only to configured; no runtime inference exists. |
| The wiki becomes another editable authority | Definitions and implementation drift | Generate from one registry and checked bindings; CI rejects stale output. |
| A wildcard ignores a missing field in one project | Partial adoption is reported as complete | Every wildcard branch must resolve; an incomplete second branch is a negative fixture. |
| Missing generated artifacts skip validation | A green check hides absent coverage | Missing artifacts fail; CI builds before checking bindings. |
| Generation follows a symlink | Unrelated working-tree content is overwritten | Reject symlink components and paths outside the repository; preserve-work canary. |
| Optional prose feedback becomes another operational gate | Ordinary work stalls on vocabulary | Lint warnings exit successfully; no runtime hook calls this tool. |
| Consumer conventions become universal defaults | A valid project is forced into the wrong workflow | Sanitized examples preserve both composition shapes; vocabulary defines concepts without importing private policy. |
| The separate GitHub Wiki is unavailable | A source page is falsely reported as published | Track repository-backed documentation and mirror publication separately. |

Rollout is a PR to `develop`. No release, deployment, workspace installation or
shared runtime mutation is part of this change. Revert the CI step and ontology
files together if validation requires rollback; existing runtime artifacts and
their policy remain unchanged.
