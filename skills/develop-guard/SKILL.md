---
name: develop-guard
description: Normal development starts at develop. Verify remote refs, bootstrap a missing develop safely, and preserve separately authorized release sources.
allowed-tools: Bash
---

# Development source

Normal feature, task, fix, documentation and configuration development uses
`develop` as its source and PR base wherever these configurations apply. Existing
unambiguous local or remote-tracking develop refs remain valid offline; report
cached evidence honestly and refresh when available. Network failure is not a
reason to switch the source to main or require a new approval. The
repository's default branch, recent main-targeted PRs, equal main/develop trees,
or an absent local develop branch do not change this policy. A main-only remote
needs a develop branch; it does not become a main-based feature workflow.

The user's standing instruction authorizes routine creation of a missing
`develop`. Do not ask for that authorization again or introduce a new approval
registry. First successfully fetch and verify the remote's exact refs. A failed
fetch or failed remote query is not proof of absence.

Use the canonical preparation helper from the installed source package:

Replace `/absolute/installed/claude-configs-public` with the canonical package
root backing the active hooks: its `bin/` is a sibling of that active `hooks/`
directory. This may be a workspace, source, or project-local nested installation.
Use that package's helper; a copied or unrelated helper is not equivalent.

```bash
python3 /absolute/installed/claude-configs-public/bin/prepare-task-branch.py --repo /absolute/project --branch feature/ticket_description --worktree /absolute/unique-task-worktree
```

It preserves the active checkout and all local work, attempts a fresh fetch,
and uses an existing known develop ref with an explicit cached-status report if
the fetch fails. When no develop is known locally, a successful fetch and remote
query are required before bootstrap. Online it
positively checks whether `refs/heads/develop` exists, and creates it when absent
from verified remote main (or the advertised default tip when main is absent).
That bootstrap source is used only to create develop. It never becomes the
normal feature source. Creation uses an empty expected-old ref lease so a
racing actor's develop cannot be overwritten. The helper then fetches and pins
the verified develop commit before creating the task branch in a new worktree.
It does not change the repository default branch or any deployment target.

The helper remains an ordinary task-scoped mutation. Record the source repository
and assigned new worktree destination in that existing task's scope. Adding the
assigned destination is routine task bookkeeping under the existing grant, not a
new operator approval. Its bounded parser recognizes only this installed package's
helper; arbitrary Python execution receives no exemption.

When working without the helper, use an explicit known `develop` or `origin/develop`
startpoint with `git checkout -b`, `git switch -c`, `git branch`, or
`git worktree add -b`. Do not omit the startpoint while on main or detached at a
release commit. Refresh when available; local branch lists alone cannot prove remote absence for bootstrap.

# Existing develop and existing work

In the develop-first route, current main must be an ancestor of develop. If it
isn't, use existing scoped sync authority and the reviewed integration procedure.
Do not silently merge main, reset a branch, switch the feature source to main,
or ask for a new grant when the needed sync is already authorized.

Do not rebase, reset or recreate another task's existing branch to repair its
provenance without explicit authority for that history change. Preserve its
commits and worktree. A new normal task can use a separate correctly based branch.
An occupied destination or branch name requires another unique name, not deletion.

# Release exceptions

An explicitly authorized version release, hotfix or backport may have a distinct
exact source, such as the user's requested release tag. Keep that scoped release
work separate from ordinary development. A `hotfix/*`, `release/*` or `promote/*`
name, PR label, repository default, or equal tree alone grants no source exception.
The trusted task caller must supply the already-authorized exact source; never
infer permission from candidate command text.

For a previously authorized CLI version release/backport, record this optional
object on its existing own implementing Task's `think-gate.json` (not a new gate
or permission registry), preserving its current identity and assigned scope:

```json
"branch_source_authorization": {
  "kind": "release-backport",
  "source_ref": "refs/tags/v0.15.6",
  "source_commit": "<exact full commit SHA>",
  "destination_branch": "backport/specific_version_fix",
  "user_grant_reference": "<reference to the existing explicit user instruction>"
}
```

The runtime resolver selects the current own Task for the actual command,
requires implementing lifecycle and existing scope, verifies the approved ref's
exact commit and exact destination branch, and supplies the source exception to
the parser. Invoke the CLI with that exact ref or commit; no new approval is
needed for work already covered by the recorded instruction. Foreign, planned,
stale-source or mismatched-branch records cannot authorize the operation. Native
GitHub creation uses develop for normal work; its exceptional release diagnostic
points to this supported CLI Task route rather than inventing a name/label bypass.

Detached exact-commit review
worktrees do not create development branches and remain available for inspection.

For the Siege scaffold, K5 retains feature/fix -> develop -> main and exact current
remote-main installation. `develop` validates and does not publish, deploy or
install. Other projects keep their approved release/deployment mechanics; a
normal-development bootstrap does not change those targets or authorize release.

# Enforcement

`hooks/lib/branch_source.py`, reused by `hooks/lib/git_command.py --policy branch`,
checks creation startpoints for checkout, switch, branch and worktree commands.
Native GitHub creation must explicitly name `develop` (`base_ref` in the current
connector, `from_branch` in the legacy GitHub MCP). Do not omit it and rely on
the provider default. `hooks/git/native-branch-source.py` checks these typed
payloads when the host delivers its registered PreToolUse hook. Explicit
`develop` from `main` bootstrap is authorized when the provider uses atomic
create-only semantics that reject an existing ref (GitHub POST refs, never
PATCH/update). Verify remote absence and the source before this call; an omitted
source or an unverified SHA-only call uses the canonical helper. The registration
is source policy, not proof that a particular installed host delivers that hook.

CLI enforcement keeps the installed `scope-check.sh` owner allowlist (and its
existing `CLAUDE_SCOPED_OWNERS` override); consumer overlays such as ElectInfo's
`siege-analytics:electinfo` declaration apply to the Python startpoint check too.
The native matcher checks registered GitHub creation tools independently of CLI
owner filtering. Source registration and fixture passes establish configured
coverage, not delivery by every host or deployment to another machine.

The branch guard's protected-commit checks and the PR-base guard remain separate
checks: correct PR destination does not prove correct branch provenance.

# Checklist

- [ ] Develop source verified; cached refs identified honestly when offline
- [ ] Any bootstrap has fresh successful fetch and exact remote absence verification
- [ ] Missing develop safely bootstrapped under the user's standing instruction
- [ ] Normal task branched from verified develop, never default/main fallback
- [ ] Existing checkout, task branches, default branch and deployment targets preserved
- [ ] Distinct release source justified by the actual task's explicit authorization
- [ ] PR base and release procedure match the operation
