# Pinned merge queue requests

The queue lane recognizes a remote operation, rather than a local file write. It needs no local Think gate, local review artifact or local test receipt. Existing merge-role authority, owner holds and GitHub's required checks still apply. Completing those prerequisites does not require another operator confirmation when authority already exists.

Use this lane only after the matching reviewed Core release is installed. Read the actual PR identity and current full head first, then supply literal values in one standalone command. The gate does not execute the mutation.

## CLI form

```sh
gh pr merge 1794 --merge --match-head-commit 8801a13290e9a8cb72e7a2a92fc4c4e7522f954e --repo siege-analytics/siege_utilities
```

These are historical example values, not a request to repeat that merged operation. The hook verifies the resolved PR/head and that its destination branch currently requires a merge queue, using bounded read-only lookups. This form is limited to a required queue. GitHub remains authoritative; a policy-read/execution race is not an atomic queue guarantee.

The normal `GH_REPO` selector is supported when no `--repo` is supplied, including from a workspace directory outside any Git checkout. An explicit repository takes precedence. Both the proof and requested CLI operation use the same routing context. This does not create merge authority. Alternate GitHub hosts are outside this supported lane.

## First-class GraphQL enqueue

```sh
gh api graphql -f query='mutation($id:ID!,$oid:GitObjectID!){enqueuePullRequest(input:{pullRequestId:$id,expectedHeadOid:$oid}){mergeQueueEntry{position state}}}' -f id=PR_NODE -f oid=FULL_40_HEX_HEAD
```

Replace both placeholders with the actual literal values. The exact single enqueue operation is supported with bound variables or literal node/head strings. It cannot perform a direct REST merge or another GraphQL mutation. The server validates the pinned head and queue requirements. Do not substitute a generic merge endpoint when this operation is unavailable.

The command must remain standalone. Admin, unpinned merge, auto-merge, REST merge, dequeue, extra mutation/response syntax, wrappers, shell expansions, redirections and chained writes cannot use this exemption. Normal local changes retain their own scope and evidence checks.

## Audit and actual result

Before admission, the resolver appends an own-session `data/merge-queue-decisions.jsonl` entry identifying the target, expected head and session. An entry records permission to attempt the constrained operation; it is not enqueue or merge success. Audit failures are visible denials. Raw credentials and command bodies are not logged.

After invoking the approved queue operation, verify the actual queue entry, required merge-group workflow and final PR state before reporting a merge. Preserve the existing sole-merger ownership; a new command form does not create a parallel merger.

On the inspected ElectInfo deployment, a held legacy global destructive guard still matches `gh pr merge`. Normal managed workspace delivery preserves that hold. The exact GraphQL enqueue form avoids that unrelated CLI-pattern check and is the intended installed canary there. This does not release the hold, authorize arbitrary GraphQL or claim the held CLI path was upgraded.
