# Lessons Learned — `<repo-name>`

This file is the **Tier 1 ledger** of the rules pipeline. It captures recurring code-review findings, bot comments, and incident lessons as evidence. Entries get promoted to Tier 2 (`.claude/rules/<topic>.md`) by [`distill-lessons`](../../distill-lessons/SKILL.md) when they meet the recurrence threshold, and from there to Tier 3 (the org-wide `_*-rules.md` in `claude-configs-public`) by human PR.

See [`lessons-learned`](../../lessons-learned/SKILL.md) for the format spec and [`rules-audit`](../../rules-audit/SKILL.md) for the cross-tier hygiene pass.

## Audit metadata

- **Last audit:** YYYY-MM-DD (initialized — never run)
- **Audit cadence target:** quarterly (or on-demand via [`rules-audit`](../../rules-audit/SKILL.md))
- **Promotion threshold (default):** recurrence ≥ 3, or 1 production incident, or Critical-severity finding

---

## Entries

<!--
Append new entries below this line. Most-recent first.

Format:

## YYYY-MM-DD — <one-line title in rule form>

- **Source:** <link or reference> (`<source type>: <url-or-id>`)
- **Rule (draft):** <imperative one-liner — "do X" / "don't do X">
- **Why:** <one or two sentences — the underlying invariant or incident>
- **Recurrence:** 1

Bump recurrence in place when the same pattern reappears; do not duplicate.
Mark **Promoted:** when [`distill-lessons`](../../distill-lessons/SKILL.md) moves the entry to Tier 2.
-->

(no entries yet)
