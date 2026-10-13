# Hostile review: deterministic progressive loading

## Scope

Reviewed the executable selector, manifest, prompt hook, package layout, Craft Agent mount migration, enforcement verification, fixtures, and metrics for severe bypasses. The target contract is compact-kernel global policy plus deterministic on-demand task/project selection, with visible kernel-only failure and no load-all fallback.

## Review rounds

Two independent deep hostile-review calls returned five S2 findings. Every finding was fixed and regression-tested. Two later independent final-review calls timed out without returning findings; timeouts were not counted as approval. The complete hosted-equivalent local matrix was then run.

| ID | Severity | Finding | Resolution and regression evidence |
|---|---|---|---|
| H1 | S2 | Explicit skill markers replaced normal task routing, allowing a marker to suppress mandatory ticket/task guards. | Explicit skills are additive. Fixture `create ticket [skill:python]` requires Python plus ticket guard/create-ticket routes. |
| H2 | S2 | `/slug` matching could interpret an ordinary path as an explicit command. | Slash commands must be isolated whitespace tokens. `/tmp/python` is not an explicit route; mandatory task routing remains active. |
| H3 | S2 | Repository normalization discarded the remote host, allowing a foreign host with the same owner/path to receive project rules. | Manifest identities include canonical host. Foreign-host fixture proves no Siege Utilities overlay leaks. |
| H4 | S2 | `ssh://git@github.com/...` retained `git@` as part of the host and silently omitted valid project scope. | URI userinfo is stripped while the canonical host remains. SSH URI fixture resolves to `github.com/siege-analytics/siege_utilities`. |
| H5 | S2 | Missing `KERNEL.md` warned and continued, leaving an ungoverned session. | Missing kernel now emits a sole `{"continue":false,...}` response and exits. Hook fixture proves no mixed context output. |

## Additional hardening during self-review

- Unknown and shelf explicit slugs are rejected visibly in diagnostics without suppressing legitimate task routes.
- Malformed manifest shapes return structured `state:error` output without a traceback.
- Workspace deployment refuses to proceed if either the compact kernel or compatibility rollback bundle is missing.
- `CLAUDE_PROGRESSIVE_LOADING=canary` reports `candidate:` routes but does not activate them.
- `CLAUDE_PROGRESSIVE_LOADING=kernel-only` disables selection without loading broad resolver prose.
- Installer-owned `CLAUDE.md -> RULES_BUNDLE.md` migrates to `KERNEL.md`; operator-owned symlinks and regular files are preserved.

## Residual risks and boundaries

- Lexical routing can under-select; the compact kernel and mechanical hooks remain invariant, and unknown is visible rather than broad-loading.
- Git remote identity is local configuration, not an authentication claim. It scopes overlays deterministically but does not establish repository trust.
- The full bundle remains available as a rollback/reference artifact. It is not globally mounted by the installer.
- Runtime rollback is one PR revert; safe canary controls permit diagnostic-only or kernel-only operation before that revert.

## Verdict

No unresolved S1/S2 finding remains from completed review rounds. Merge remains conditional on protected hosted checks.
