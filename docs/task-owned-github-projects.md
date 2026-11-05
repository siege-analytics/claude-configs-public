# Task-owned GitHub project additions

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

An add requires one current-session implementing task with an exact canonical `ticket` (or full canonical `task_id` when ticket is absent), for example `electinfo/enterprise#3300`. A slug `task_id` cannot substitute for the canonical issue identity; a parent issue cannot authorize its child. Explicit task binding disambiguates only. Task-written `remote_resources`, arbitrary allowed URLs and local `scope_paths` do not grant project permission. Revoking the installed grant or terminating the task removes this lane. Existing role limits, owner holds and destructive confirmation still apply.

The classifier emits `remote_actions` instead of a fake filesystem path. After installed-policy and task ownership checks, remote-only board hygiene receives `remote_only_authorized`, distinct from the existing metadata-edit exception. This administrative operation does not need source-edit investigation/review artifacts. It does not authorize code edits: any composed local write must belong to the same task and pass its ordinary local evidence tier. Other remote writes, shell substitution, opaque execution, unapproved redirects and mismatched tasks remain guarded. Ambient GH_HOST/GH_REPO overrides are rejected for this lane.

Only literal `gh`, project number, `--owner` and canonical issue `--url` are supported, with either flag order. Extra/duplicate/global flags and alternate hosts are rejected. The hook classifies commands; it does not execute gh, authenticate, confirm network success or claim the item appeared.

`item-edit`, item/project deletion and arbitrary GraphQL remain unsupported and fail closed even with broad file ownership. Bounded item-edit needs independently verified project/item/issue/field/value membership. No caller-provided node ID alone supplies it. Issue1161 remains open for that follow-up; this slice addresses exact task-owned item-add only.
