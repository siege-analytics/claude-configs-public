---
name: ticket-guard
description: "Use an existing durable destination for useful task tracking. Missing tracker configuration does not universally block authorized work."
allowed-tools: Bash Read
---

# Ticket Guard

Keep material decisions and outcomes somewhere the operator and future workers can find them: the existing issue, PR, project document or repository note. Reuse the project's established tracker when available. Do not require a new issue, board placement or workspace tracker setup for every authorized task.

If a project policy requires issue tracking, satisfy that requirement within the existing grant. If its tracker is unavailable, continue independent work and preserve a useful local record for later reconciliation. Ask the operator only when selecting or changing the organizational tracking system is a material decision that existing context does not settle.

A reachable tracker is not proof that a task is progressing, and a missing tracker is not a whole-goal hold. Use [`pre-work-check`](../pre-work-check/SKILL.md) for actual dependencies and authority and [`self-review`](../self-review/SKILL.md) for useful validation and delivery records.
