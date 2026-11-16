# Task-owned GitHub project operations

The mutation resolver supports the literal command:

```sh
gh project item-add 1 --owner electinfo --url https://github.com/electinfo/enterprise/issues/3300
```

The numbers and names above are examples, not Core grants. Core ships `hooks/github-project-policy.json` with an empty grant list. A client must deliver its reviewed standing policy at that exact installed path, alongside the hooks. Environment variables, task JSON fields, cwd files and symlink policy files cannot select or replace the policy. The policy shares the installed hook source trust boundary; its `authority_source` records existing authority rather than creating a new approval.

A client policy has this bounded schema:

```json
{
  "schema_version": 1,
  "grants": [{
    "host": "github.com",
    "owner": "electinfo",
    "project": 1,
    "operation": "item-add",
    "issue_owner": "electinfo",
    "issue_binding": "current-task-ticket",
    "authority_source": "resident/AGENTS.md:15-18;skills/_ticket-lifecycle--electinfo-workflow.md:34-37,74,164-165"
  }]
}
```

The ElectInfo references already require its issues on Tasks project1. Client source integration owns encoding that grant and checking parity with those instructions. Other clients supply their own approved policy; Core does not infer one.

Core deployment replaces the managed hooks tree, including its empty default policy. A client deployment must assemble its current reviewed policy after the Core copy, then verify the assembled hooks and policy together before activation. ElectInfo's client builder owns that overlay step. A Core-only install does not deliver an ElectInfo profile. Do not preserve an old installed policy as a fallback: it may contain revoked grants. Reapply the current client source through normal client delivery.

An add requires one current-session implementing task with an exact canonical `ticket` (or full canonical `task_id` when ticket is absent), for example `electinfo/enterprise#3300`. A slug `task_id` cannot substitute for the canonical issue identity; the default current-ticket grant does not authorize a child issue. Explicit task binding disambiguates only. Task-written `remote_resources`, arbitrary allowed URLs and local `scope_paths` do not grant project permission. Revoking the installed grant or terminating the task removes this lane. Existing role limits, owner holds and destructive confirmation still apply.

The classifier emits `remote_actions` instead of a fake filesystem path. After installed-policy and task ownership checks, remote-only board hygiene receives `remote_only_authorized`, distinct from the existing metadata-edit exception. This administrative operation does not need source-edit investigation/review artifacts. It does not authorize code edits: any composed local write must belong to the same task and pass its ordinary local evidence tier. Other remote writes, shell substitution, opaque execution, unapproved redirects and mismatched tasks remain guarded. Ambient GH_HOST/GH_REPO overrides are rejected for this lane.

For `item-add`, only literal `gh`, project number, `--owner`, canonical issue `--url` and optional `--format json` are supported, in any flag order. Extra/duplicate/global flags and alternate hosts are rejected. The hook classifies the requested mutation; it does not execute it, authenticate, confirm mutation success or claim the item appeared. The separate Status verifier below performs a fixed read-only GitHub query.

## Explicit item-add targets in an existing Task

A board-management mission can opt into `issue_binding: "current-task-or-declared-targets"` for an installed `item-add` grant. That grant also declares `declared_issue_repositories`, a nonempty list of exact full repository names under its fixed `issue_owner`. The installed owner, board and operation remain the ceiling; the repository allowlist limits declared targets. The original own-ticket lane remains available. Core ships no such grants. Status grants keep `current-task-ticket` and their live membership checks.

The existing own implementing Task keeps its real ticket and Task identity. It may record exact metadata targets in `github_project_targets`, for example:

```json
{"github_project_targets": [{"owner": "electinfo", "project": 4, "repository": "electinfo/airflow", "issue": 1074, "operation": "item-add"}]}
```

Each declaration names one literal board/repository/issue/operation pair. Use the existing explicit `CCP_TASK_ID` binding to select that Task; missing or ambiguous bindings, foreign session ownership and other lifecycle states cannot use this lane. Task fields cannot create the installed grant or expand its repository allowlist. No role name grants authority. This is metadata-only target selection, not parent-to-child source authorization: local writes, services, other remote operations and merges retain their existing checks. A compound action still needs the same Task for every effect; split unsupported mixed operations rather than widening local scope or creating a substitute Task per issue. Actual native results, not a classifier decision, establish whether the board operation succeeded.

## Bounded Status edits

An independently reviewed client policy can add this separate grant alongside its `item-add` grant:

```json
{
  "host": "github.com",
  "owner": "electinfo",
  "project": 1,
  "operation": "item-edit",
  "issue_owner": "electinfo",
  "issue_binding": "current-task-ticket",
  "field_name": "Status",
  "field_type": "SINGLE_SELECT",
  "values": ["In Progress", "In Review"],
  "authority_source": "<client instruction requiring these task-owned transitions>"
}
```

Only a literal Status single-select `item-edit` is supported. The fixed read-only verifier must independently confirm the project, item, issue, field and option membership and current task ownership. Caller-provided node IDs do not supply authority. Done items cannot be reset through this lane. Other fields, values and `item-edit` forms remain unsupported, as do item/project deletion and arbitrary caller GraphQL.

Deliver a Status grant only with the matching reviewed Core parser and verifier; an older parser rejects unknown grant fields. Core still ships no grants. Issue1161 remains open until actual client delivery and the original session's operation are verified.
