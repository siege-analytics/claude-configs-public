# Lessons Learned — `claude-configs-public`

This file is the **Tier 1 ledger** of the rules pipeline. It captures recurring code-review findings, bot comments, and incident lessons as evidence. Entries get promoted to Tier 2 (`.claude/rules/<topic>.md`) by [skill:distill-lessons] when they meet the recurrence threshold, and from there to Tier 3 (the org-wide `_*-rules.md` in `claude-configs-public`) by human PR.

This is the dogfooding instance — `claude-configs-public` itself uses the pipeline it ships. Findings about the rules, the build, the workflow, and the skills themselves land here.

See [skill:lessons-learned] for the format spec and [skill:rules-audit] for the cross-tier hygiene pass.

## Audit metadata

- **Last audit:** 2026-05-12 (initialized — never run)
- **Audit cadence target:** quarterly (or on-demand via [skill:rules-audit])
- **Promotion threshold (default):** recurrence ≥ 3, or 1 production incident, or Critical-severity finding

---

## Entries
