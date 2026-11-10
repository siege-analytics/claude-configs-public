# Pinned merge queue requests

The queue lane recognizes a remote operation, rather than a local file write. It needs no local Think gate, local review artifact or local test receipt. Existing merge-role authority, owner holds and GitHub's required checks still apply. Completing those prerequisites does not require another operator confirmation when authority already exists.

Use this lane only after the matching reviewed Core release is installed. Read the actual PR identity and current full head first, then supply literal values in one standalone command. The gate does not execute the mutation.

## Exempt destination branches

The no-task exemption applies only to a pull request whose destination branch is listed in `QUEUE_EXEMPT_BASES` in `hooks/lib/github-merge-queue.py`. That constant is the single source of this policy; its default is `('develop',)`. The base is the server-reported `baseRefName`, compared exactly. A request into any other branch, for example a queued release `main`, receives no exemption. Not exempt does not mean denied: the CLI form returns to the ordinary task path, which needs an owning task gate and all local publication checks. GraphQL has no ordinary path, so a non-listed base is denied.

## CLI form

```sh
gh pr merge 1794 --merge --match-head-commit 8801a13290e9a8cb72e7a2a92fc4c4e7522f954e --repo siege-analytics/siege_utilities
```

These are historical example values, not a request to repeat that merged operation. The hook verifies the resolved PR/head, that its destination branch is an exempt base, and that the branch currently requires a merge queue, using bounded read-only lookups. This form is limited to a required queue. GitHub remains authoritative; a policy-read/execution race is not an atomic queue guarantee.

The normal `GH_REPO` selector is supported when no `--repo` is supplied, including from a workspace directory outside any Git checkout. An explicit repository takes precedence. The proof reads the hook process environment (`GH_REPO`, `GH_HOST`). The requested command runs in the Bash tool's shell, whose profile can set a different environment. Keep these routing selectors identical, or pass `--repo`. This does not create merge authority. Alternate GitHub hosts are outside this supported lane.

## First-class GraphQL enqueue

```sh
gh api graphql -f query='mutation($id:ID!,$oid:GitObjectID!){enqueuePullRequest(input:{pullRequestId:$id,expectedHeadOid:$oid}){mergeQueueEntry{position state}}}' -f id=PR_NODE -f oid=FULL_40_HEX_HEAD
```

Replace both placeholders with the actual literal values. The exact single enqueue operation is supported with bound variables or literal node/head strings. It cannot perform a direct REST merge or another GraphQL mutation.

The hook performs one fixed read-only `node(id:)` lookup within the same three-second budget. It reads the node's pull request number, `baseRefName`, `headRefOid` and `repository.nameWithOwner`.
- The returned node must be the requested node.
- Its head must equal the pinned head.
- Its base must be an exempt base.

For a pull request from a fork, the policy check and the audit use the base repository and base branch, where the merge lands. They never use the fork's head repository or head branch, so a fork named or branched `develop` that targets a release `main` is not exempt. The lookup reads `PullRequest.repository` and `baseRefName`. That this field names the base repository is taken from GitHub's published schema; it has not been observed in a live `node()` query against a fork.

A failed lookup, a malformed answer or any mismatch denies the request. The lookup does not read branch rules. The hook relies on GitHub to reject an enqueue for a branch without a merge queue; that server behavior has not been observed in this repository. Do not substitute a generic merge endpoint when this operation is unavailable.

The command must remain standalone. Admin, unpinned merge, auto-merge, REST merge, dequeue, extra mutation/response syntax, wrappers, shell expansions, redirections, backslash escapes and chained writes cannot use this exemption. Backslashes are rejected because the shell and the hook's lexer disagree about them inside double quotes, and GraphQL decodes `\uXXXX`; the validated text must be the delivered text. Normal local changes retain their own scope and evidence checks.

## Queue exemption versus ordinary merge scope

Pure `--classify` inspection recognizes grammar and carries no permission. Local publication guards use `--queue-required COMMAND CWD`: both forms perform fresh bounded lookups before skipping unrelated local HEAD/test checks. Only UMG writes the own-session admission audit.

A valid CLI proof that confirms a non-exempt base or no required queue returns to the normal task/scope path and all local publication checks. Supported ordinary CLI options receive no queue exemption and keep those existing checks. These include:
- auto-merge;
- squash or rebase;
- branch deletion;
- body options;
- an equals-style full head pin.

Literal option data is not treated as a bypass flag. Composed ordinary operations need one task covering all their targets; recognizing a queue prefix grants nothing to a companion action.

`gh pr merge --admin` and malformed head pins are denied even when a task gate covers the merge; the hook reports them as `Pinned merge denied:`. Before #1207 a task-scoped `--admin` merge was allowed. Denying it is an intended tightening: this lane never models an admin bypass, under any scope.

Each queue proof has one three-second read budget. Guards prove it afresh rather than trusting an environment flag, task-written decision cache or a role claim. Multiple guards can therefore perform repeated reads; the workspace router's whole-event budget still applies.
- A changed head or a repository mismatch denies the request.
- A CLI proof that cannot be read gives no exemption, but the canonical pinned merge keeps its ordinary task path. A read cannot be done when it fails, times out, is oversized or undecodable, or when an ambient `GH_HOST` override is present.
- A GraphQL lookup that cannot be read denies the request.

Current branch-rule proof and later command execution are not an atomic transaction.

## Audit and actual result

Before admission, the resolver appends an own-session `data/merge-queue-decisions.jsonl` entry. The entry records:
- the repository, pull request number and destination base resolved by the proof;
- the node, for GraphQL;
- the expected head;
- the session.

An entry records permission to attempt the constrained operation; it is not enqueue or merge success. Audit failures are visible denials. Raw credentials and command bodies are not logged.

After invoking the approved queue operation, verify the actual queue entry, required merge-group workflow and final PR state before reporting a merge. Preserve the existing sole-merger ownership; a new command form does not create a parallel merger.

On the inspected ElectInfo deployment, a held legacy global destructive guard still matches `gh pr merge`. Normal managed workspace delivery preserves that hold. The exact GraphQL enqueue form does not match that CLI pattern. Whether to use that form as the installed canary there is an operator decision; this document does not make it. This does not release the hold, authorize arbitrary GraphQL or claim the held CLI path was upgraded.
