---
name: self-review
description: "Review the actual change against its goal before publication. Record proportionate validation and findings; obtain real independent review for high-risk changes without fictional rank stages or mandatory pre-mortem paperwork."
user-invocable: true
---

# Self Code-Review

Inspect the actual diff, verify it meets the requested outcome, and fix material defects before publishing. A review is an opportunity to make the change succeed. Do not require invented findings or treat a review handoff as delivery.

## Proportional review tiers

Use `python3 bin/review-risk.py --staged` where installed. The classifier establishes a minimum; a declaration may raise it, never lower it.

- **Tier A:** prose or generated evidence without runtime behavior. A short `Self-Review:` record and relevant syntax/reference/diff checks are sufficient.
- **Tier B:** standard code, skills and rules. Use one compact [review record](artifact-contract.md#artifact-format) with assumptions, actual validation and findings. Run relevant regression checks.
- **Tier C:** enforcement, authorization, credentials, destructive operations and release/deployment policy. Use the same compact record plus real independent review. Include meaningful negative tests, the affected component's regression suite, and staged runtime or rollback verification where applicable. Do not replace these with ceremonial job titles, universal full-repository test runs or unrelated canaries.

No tier universally requires a pre-mortem, Junior/Senior comments, separate investigation document or repeated public posting. Existing explicit project or operator approval requirements remain binding for their actual actions; do not invent them from an optional analysis exercise.

## Review procedure

1. Compare the change with the original request or task. Inspect affected callers, interfaces and failure behavior. Verify consequential assumptions against current source or runtime. Check the preparation evidence: the relevant documentation or source actually consulted, the facts established, and how they inform the change. A link list or assertion of effort alone is insufficient.
2. Run checks appropriate to the change. Record the command, actual result and limitations. Do not fabricate execution, backdate evidence, or infer deployed behavior from a build. Use [`detect-ai-fingerprints`](../detect-ai-fingerprints/SKILL.md) under its task-scoped acceptance contract.
3. Record substantive findings and resolve blockers. A finding-free review is valid when the inspected evidence supports it. Non-blocking debt may be tracked with a clear consequence and owner; do not turn every suggestion into a new prerequisite.
4. For Tier C, have an independent reviewer inspect the actual change and evidence. Link the real review and handle its findings. Independence means another reviewer, not the author assuming several titles. Review may happen while preparing publication; it is not a prerequisite to editing the fix being reviewed.
5. Publish through the project's normal branch and required-CI path. Existing authorization to deliver covers routine commits, pushes, PRs and merges within that path. Preserve protected branch requirements and real owner holds.

## Trailers and hook enforcement

Use these records where installed hooks require them:

```text
Review-Tier: A|B|C
Self-Review: <actual review and validation summary>
Self-Review-Source: <B/C compact record path or link>
Hostile-Review: <C actual independent review path or link>
```

`Hostile-Review` is a compatibility field name, not a requirement for hostility, a particular provider or an organizational rank. A useful rigorous reviewer helps produce a correct result. Do not fake a review, relax unresolved critical findings or claim a scanner is clean when it is not.

## Promotion and delivery

Review a promotion's cumulative diff, verify it contains the intended develop snapshot, inspect required CI, and merge under existing authority when ready. Already reviewed unchanged content does not need a second fictional hierarchy or a fresh operator GO. Conflict resolutions or new behavior need review proportionate to those changes.

A source review, merged PR and installed generation are separate observations. For a runtime repair, verify the requested behavior in the actual environment. For an unattended mission, verify working continuation and substantive outcomes beyond the initial dispatch. Preserve active external-job handles and actual action-specific holds.

## Recovery and records

Keep the review in the existing task, PR or repository; repeated copies are unnecessary. If evidence was produced after an edit, state that honestly and complete the needed verification before publication. Do not invent pre-work provenance or discard unfinished work to avoid its prerequisites. Historical larger artifacts remain useful evidence but their obsolete mandatory fields do not govern new work.
