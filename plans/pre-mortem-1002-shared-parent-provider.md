# Pre-mortem: shared-parent provider event normalization (#1002)

## Bounded outcome

One unchanged parent policy installation evaluates real Git/event facts from two consumers with different approved branch profiles. Preserve the accepted public-repository denial/repair behavior and distinguish parent policy revision, consumer base/head and actual executed consumer workflow revision.

## Failure modes

- Equating the parent revision with the consumer base rejects an otherwise valid external consumer. Keep both immutable identities and validate each checkout independently.
- Keeping `main requires develop` before effective-policy evaluation defeats the authorized trunk profile. For the registered event path, delegate branch role decisions to the existing evaluator; keep canonical strict-profile negatives in the corpus. Retained direct/local compatibility paths do not establish migration completion.
- Letting candidate settings choose their parent policy creates authority. Parent root/revision must come from reviewed host registration; candidate policy remains proposal data under previous immutable selection.
- Reading workflow bytes from the parent falsely attributes consumer workflow execution. Read the host-observed workflow revision from a separately validated canonical consumer workflow checkout and report its independent repository/ref/blob/hash.
- Executing candidate code during normalization crosses the trust boundary. Use Git object reads and JSON facts only; execute the independently pinned parent adapter.
- A shallow trusted checkout lacks approved policy ancestry. Preserve bounded history recovery and fail closed on unavailable objects.
- A forged/stale event or arbitrary workflow ref creates false provider evidence. Require exact event/repository/checkout/ref identities and verify the host workflow revision against the canonical default branch supplied by the trusted host’s complete candidate checkout.
- A local test is called provider authorization. Synthetic event fixtures remain local evidence; the existing public GitHub denial/repair pair stays separate, and external registration/live backend claims require their own evidence.
- Imported approval manifests or role labels grant authority. No local receipt, template or boolean can approve its own installation or mutation.

## Evidence and rollback

Reuse the existing strict-release/synthetic-trunk composed fixtures, one parent root/revision, real local bare remotes and Git commit/ref operations. Compare local policy eligibility with registered-event results, including wrong parent pin, wrong repository, stale head, missing ticket, missing/changed installed content, unsupported workflow identity and repair. Preserve public self-hosted regression coverage.

Revert the bounded source change. Do not install consumer workflows or modify main, default branch, branch protection, shared workspace or live host sessions while implementing this slice. #849 retirement and #1003/#1004 rollout acceptance remain separate.

## Proposed implementation shape

Extend the existing Python evaluator with a registered-host-event normalization mode, rather than create a second branch-policy engine. This mode reads fixed GitHub event/environment identities, accepts the parent root/revision only from the reviewed host invocation, validates actual consumer base/head and parent checkout separately, preserves shallow parent-history recovery, and reads actual default-workflow bytes from a separately validated canonical consumer workflow checkout. Direct synthetic evaluator calls retain their explicitly non-authorizing interface.

The canonical topology script delegates registered `pull_request_target` events to that mode before applying legacy local compatibility cases. Branch-role decisions for registered events come from the accepted effective-policy evaluator; current-main ancestry remains checked against the canonical workflow/main revision from that host checkout. Non-provider legacy compatibility must remain labeled and tracked for later retirement, not counted as migrated runtime proof.

A reviewed, inert consumer workflow example will show a protected host checkout of one exact parent SHA and a separate candidate data checkout. Parent pin installation remains an external operator/review decision; no candidate setting, template flag or local receipt authorizes it. Local event fixtures use real bare repositories and Git transport rewriting solely to avoid network/host mutation, and explicitly remain synthetic evidence.

A private consumer must not require a second unauthenticated fetch after `persist-credentials: false`. The observed accepted GitHub job already fetches `+refs/heads/*:refs/remotes/origin/*` for its candidate checkout. Shared consumers provide a separate authenticated canonical workflow checkout; the self-hosted public case already has an independently verified canonical base checkout. The adapter consumes that canonical checkout’s `origin/main` snapshot, requires its equality with the host workflow SHA, and rejects missing objects. Shared-consumer fixtures reproduce the full checkout through local Git transport before invoking the adapter.
