# Task-owned GitHub project addition

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1161 and root's authorized isolated implementation assignment.
Baseline: f004df3c66cf6374548cfc49d0e49c375aa4376c. Recorded before implementation.

## Existing authority and investigated flow

ElectInfo tracked standing policy already requires every issue on electinfo/tasks: resident/AGENTS.md:15-18 and skills/_ticket-lifecycle--electinfo-workflow.md:34-37,74,164-165. The latter identifies project1, owner electinfo, host github.com. Client main a79d2a89 pins resident SHA256 f0fa6c0f331ccaf3c85d7781c7210abb1aad29a4518ac0cb8b6893d3b43b832b and lifecycle03642c1ba9725fdc2214d891910e42b0300fe66191e10765644f324d09d3cb37. This task does not invent or ask again for that grant; the client owner will encode and deliver it separately.

Current action classifier recognizes remote issue/PR text metadata as metadata_only and otherwise falls back to cwd file scope. Neither is suitable for Projects. Resolver selects filesystem ownership only; hook then applies code-edit evidence tiers. Broad file ownership can conceal unsupported remote mutations, while a narrow legitimate task scope cannot represent the desired board operation.

## Design before code

Add a typed literal gh project item-add grammar to the existing bounded shell classifier. It emits remote_actions, not file paths or metadata_only. Reject unsupported project mutation shapes and GraphQL before cwd fallback, including destructive operations even when a broad file gate exists. Preserve proven project readers.

Use fixed hook-owned hooks/github-project-policy.json, never an environment/task-selected path. Core ships an empty grants list. Client source overlays this fixed policy through existing approved deployment. Strict grants contain host,owner,project,operation,issue_owner,issue_binding,authority_source. Only item-add/current-task-ticket is supported. Host and issue canonical URL are explicit, no global/env gh host/repository switches. Policy symlinks, malformed/duplicate fields and unknown grants fail closed. This is an installed hook policy trust boundary, not a new effective-policy engine.

Resolve exact issue against current-session active task gate.ticket, or a full canonical task_id when ticket is absent; a slug alone supplies no issue identity. Require unique ownership, implementing status, consistent command/environment binding and matching installed standing policy. A task-written remote_resources field supplies no authority. Remote-only administrative adds receive an explicit remote_only_authorized result after these checks: no fabricated path and no code-review tier/evidence fiction for board hygiene. This does not authorize source edits. Mixed local/remote operations require the same task, actual local path ownership and its ordinary tier/artifacts; no early bypass. Mixed remote operations all need matching grants. Retain shell expansion, substitution, redirection and opaque execution boundaries.

Item-edit requires verified item membership/field/value mapping not available in current source. It remains denied, with negative controls. GraphQL remains denied rather than adding an unsafe generic parser. These are explicit limitations; do not claim all intended outcomes or close1161.

## Risks and test plan

Launch-blocking Tiger: remote grant early allow could hide local writes. Red tests must include same-task allowed local writes and other-task/outside writes, redirections, tee, chains, substitution and destructive remote companions.
Launch-blocking Tiger: caller chooses host/project/issue or policy. Test wrong host/owner/project/issue, duplicate/extra/global flags, task-written grant, malformed/symlink policy, wrong session, stale/terminal/nonimplementing/mismatched ticket and ambiguous tasks. Test broad local gate cannot authorize unsupported remote operation.
Launch-blocking Tiger: deployment drift. Fixed policy default deny and client source parity tests are separate; no Core ElectInfo wildcard grant and no live installation here.

Red-first hook/resolver tests operate on isolated installed hook fixtures and never execute gh. Run focused cases, then relevant gate/classifier suites, full hook suite and config validation as required. Independent review before publication; coherent local commit only is authorized. Root owns merges/releases/installation. Preserve no-bypass/hold/destructive boundaries.
