# Hostile review: shared-parent provider event normalization (#1002)

## Falsified baseline

The existing direct evaluator permits both approved profiles, but the old registered event path rejects strict-release because it equates parent revision with consumer base and rejects synthetic-trunk because a hardcoded strict topology runs first. Reproducer and bounded direction are preserved on #1002, comments 6210428270 and 6210551816.

## Local negative corpus

Nine registered-event scenarios use two actual Git consumers, local bare remotes and one unchanged parent. They compare direct/event decisions and test different parent/consumer/workflow revisions; missing-ticket repair; wrong parent repository/revision; wrong workflow repository, checkout/ref/SHA; candidate-store substitution; absent event/default ref; stale head; fork confusion; missing installed content; invalid interior commits; candidate policy, validator and workflow edits; shallow parent recovery; and unavailable parent history. Protected main refs remain unchanged by evaluation. Synthetic host facts remain local non-authorizing evidence.

The reviewed preparation example contains separate pinned-parent, candidate-data and canonical-workflow checkouts. The consumer checkout fetches history while authenticated; credentials are removed afterwards. No second anonymous consumer fetch is needed. Parent shallow recovery is restricted to its independently validated configured origin.

A tenth regression calls the public self-hosted shell entrypoint from a real shallow protected-base clone. Its unchanged canonical default workflow remains a distinct revision. Missing ticket and wrong branch deny, an amended ticketed head becomes eligible, and mismatched workflow provenance errors. The fixture creates its own default-branch ref and requires no local runner branch named main.

## Reviewer-directed correction

The first local prototype used the same-repository candidate store for workflow object reads. Direction review required independent canonical provenance. Shared-parent mode now requires a separate canonical consumer workflow checkout, verifies its repository/HEAD/default-main ref, and refuses the candidate checkout as authority. Parent repository identity is independently configured and checked before ancestry recovery. The public self-hosted case retains its separately verified canonical base checkout.

Further self-review reproduced a false rejection for a host-reported mixed-case repository: canonical identity normalized correctly but the whole workflow ref was compared against a lowercased expected string. One shared validator now normalizes only owner/repository components, keeps workflow path and branch ref exact, and preserves the original observed ref in the receipt. Both profiles have event/direct positive coverage plus altered path/ref-case negatives.

Hosted run `38873970873` exposed a fixture dependency on local branches: its freshly committed synthetic parent remained on an unadvertised detached HEAD, so recovery via `refs/heads/*` correctly failed closed. A branchless detached source reproduced the error locally; a normal detached worktree sharing local branch refs did not. Fixture setup now creates its own advertised parent branch and synthetic default-workflow ref before committing, without weakening the adapter's unavailable-history error.

## Boundaries

No local flag, receipt, role label or template authorizes installation or host operation. Forks are unsupported. Non-provider strict compatibility remains labeled and pending separate #849 retirement. Live private-consumer registration, Craft/backend acceptance and runtime rollout remain unverified until their own host evidence is obtained. Exact-head independent review and the public GitHub denial/repair regression are required before declaring provider integration complete.
