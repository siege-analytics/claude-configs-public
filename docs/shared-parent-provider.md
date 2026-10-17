# Shared-parent provider events

The registered event adapter is `scripts/ci/protected-policy-range.py --host-event`. It calls the existing effective-policy evaluator. It does not create a second branch policy or authorize its own host registration.

Four identities remain distinct:

| Identity | Trusted source | Validation |
|---|---|---|
| Parent policy repository and revision | Reviewed host checkout and explicit invocation | Repository identity, exact HEAD, selected-policy ancestry, entrypoint/validator/policy/contract/selection blobs |
| Canonical consumer and base | Host event | Exact repository and immutable base |
| Candidate source and head | Host event plus candidate data checkout | Supported same-repository mapping, exact HEAD, base and canonical-main ancestry |
| Executed consumer workflow | Host workflow ref/revision plus separate canonical workflow checkout | Canonical consumer repository, default-main ref/revision, exact workflow checkout HEAD, origin/main and workflow Git blob/hash |

The same-repository candidate mapping is the bounded supported case; forks fail closed. Shared-parent mode requires an explicit parent repository/revision and a separate canonical workflow checkout. The existing self-hosted public registration uses its independently checked-out exact protected base as both parent and canonical consumer object store; it never equates that base with the executed default-workflow revision.

The preparation example is [shared-parent-workflow.yml](../examples/provider/shared-parent-workflow.yml). Replace its parent revision placeholders with one exact accepted SHA and independently review the resulting workflow before installing it at `.github/workflows/pr-base-guard.yml` on a consumer's default `main`. The example checks out the pinned parent, candidate data and actual consumer workflow separately with credentials removed after checkout. Complete checkout history supplies canonical `origin/main`; the adapter does not require a later anonymous consumer fetch, which would fail for private repositories. Missing workflow objects or inconsistent refs fail closed.

The example expects the consumer's composed content at `.pilot/` and validates the complete committed tree against trusted recomposition. Configure another supported receipt path explicitly in reviewed host code if needed. Candidate config, edited guidance, an `approved` flag or a self-written receipt cannot select parent authority. Workflow installation and required-check configuration are separate operator actions; the example is not installed by a build.

`eligible` means the exact operation is eligible for a protected host check. Local calls, including simulated GitHub environment variables, cannot establish provider execution or authorization. Error/denied receipts retain `authorization: none`. Read-only diagnosis and a repaired replacement head remain available.

Registered host events use approved project branch-role policy before retained legacy local compatibility checks. The strict public profile keeps its develop/main denials; the approved synthetic trunk profile can target main directly. Non-provider compatibility, native branch capability, live Craft/backend behavior and legacy retirement remain separately tracked under #849/#1003. No unit fixture changes their live severity.
