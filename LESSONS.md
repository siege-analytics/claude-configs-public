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

## 2026-05-12 — Concurrent build-and-publish runs race when main+tag pushed back-to-back

- **Source:** Run [25768243378](https://github.com/siege-analytics/claude-configs-public/actions/runs/25768243378) failed during v1.2.1 release with `cannot lock ref 'refs/heads/release/nested': is at f03c3b07 but expected 0702ccbe`. Issue [#38](https://github.com/siege-analytics/claude-configs-public/issues/38); PR [#39](https://github.com/siege-analytics/claude-configs-public/pull/39).
- **Rule (draft):** Any GitHub Actions workflow job that force-pushes to a shared branch must declare a concurrency group with `cancel-in-progress: false`, so back-to-back triggers queue rather than race.
- **Why:** Pushing main and immediately pushing the version tag is the standard release sequence (see any CHANGELOG-stamp commit). Two workflow runs trigger ~2 seconds apart; both force-push to `release/nested` + `release/flat`; the loser fails with the lock-ref error. The losing run is the tag-push, so the `vX.Y.Z-nested` / `vX.Y.Z-flat` fan-out tags don't get created and downstream consumers can't pin.
- **Recurrence:** 1
- **Promoted:** `.github/workflows/build-and-publish.yml` on 2026-05-12 by PR #39 (Tier 3 directly — single-repo workflow fix, doesn't need to traverse Tier 2)

## 2026-05-12 — Agents take side-effecting actions without first investigating actual state

- **Source:** Reviewer flag from Dheeraj at session 260502-pure-vista; resulted in `[rule:verify-before-execute]` in v1.2.0 and the Design-line tightening in v1.2.1. Issues [#34](https://github.com/siege-analytics/claude-configs-public/issues/34), [#36](https://github.com/siege-analytics/claude-configs-public/issues/36); PRs [#35](https://github.com/siege-analytics/claude-configs-public/pull/35), [#37](https://github.com/siege-analytics/claude-configs-public/pull/37).
- **Rule (draft):** Before any side-effecting action (Write, Edit, side-effecting Bash, commit, push, delete, deploy), emit a visible Verify-before-execute block grounded in same-turn evidence and (for non-trivial actions) a same-conversation think reference.
- **Why:** Recurring observation across multiple sessions — agents infer state from prior context, stale memory, or conversation summaries instead of observing the current state, then take actions that have to be reverted. Invisible discipline (private "checks") doesn't fire reliably; visible discipline is auditable.
- **Recurrence:** 1
- **Promotion-requested:** Dheeraj (explicit reviewer flag — promoted to Tier 3 on day of capture, bypassing the recurrence threshold)
- **Promoted:** `skills/_verify-before-execute-rules.md` (Tier 3 directly, since this repo is the org-rules repo) on 2026-05-12 by manual PRs #35 and #37 — pre-dates the formal `[skill:distill-lessons]` workflow; documented here for the audit trail
