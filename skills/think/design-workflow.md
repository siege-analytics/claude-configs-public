# Design procedure

Use this when a change needs more explanation than the request and a short implementation note. It is a thinking aid, not a mandatory sequence of posted artifacts. Return to [Think](SKILL.md) for task scope and authority.

## Context

Read relevant task history and inspect the current target code. Establish what happens now, what should change, and what must remain true. Resolve factual discrepancies from evidence. Inspect affected callers and related failure patterns when they could change the solution.

## Approach

Choose an approach that meets the requested outcome with reasonable complexity. Explain real tradeoffs when they matter. Do not manufacture multiple proposals, exact call-site scoring or a user selection when existing requirements settle the method.

For a substantial interface or data change, describe inputs, outputs, compatibility, failure behavior and affected consumers. Keep the record proportional: an existing task, design note or PR is sufficient; repeated copies and public posting before every edit are not required.

## Questions and authority

Use existing instructions to settle routine methods. Ask the responsible owner only for material unresolved scope, consequences, priorities or authority. Preserve explicit sign-offs that the operator actually reserved. Hold the affected action, continue independent authorized work, and identify its real release condition. A self-authored concern does not create a new operator hold.

## Verification and delivery

Decide what observation would prove the requested behavior, and what would falsify it. Use relevant tests, review and deployment checks; include failure cases for consequential changes. Update affected documentation with the change. For operational work, inspect the actual runtime rather than treating a source diff as completion.

Optional [`investigate`](../investigate/SKILL.md) and [`pre-mortem`](../pre-mortem/SKILL.md) can help with unfamiliar systems or consequential uncertainty. Neither is a universal gate. Move directly into implementation once the approach and authority are clear, then follow [`self-review`](../self-review/SKILL.md) and the authorized delivery workflow.
