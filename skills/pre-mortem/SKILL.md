---
name: pre-mortem
description: "Optional risk analysis for consequential or uncertain changes. Identify plausible failures from actual evidence and choose proportionate mitigations; use when requested or useful, not as a universal implementation gate."
user-invocable: true
allowed-tools: Read Grep Glob
---

# Pre-Mortem

Ask: if this change fails, what is the most plausible cause? Use this tool when consequences or uncertainty justify a separate risk discussion. Ordinary work does not require a pre-mortem artifact, classified risks, public posting or approval to start.

## Procedure

1. Inspect the relevant facts, consumers and failure history. Name a plausible trigger and consequence; do not invent a fixed number of risks.
2. Distinguish an unresolved risk from one already covered by the design, tests or operational controls. Cite the evidence that changes the decision.
3. Choose a proportionate response: improve the implementation, add a meaningful check, stage delivery, prepare rollback, or ask the owner to accept a material consequence outside existing authority.
4. Record useful conclusions in the existing task or review. Continue eligible work. The risk discussion does not create a whole-goal hold.

An identified defect is often a reason to implement its mitigation, not to prohibit implementation. An actual explicit owner hold or consequential operation requiring approval remains binding for that action. Do not manufacture such a hold from this optional exercise.

See [skill:think] for scope and authority and [skill:self-review] for publication review.
