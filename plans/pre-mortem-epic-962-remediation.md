# Pre-mortem: epic #962 release-blocking remediation

Target: `develop`; issues #983–#987 and coordination finding from #972.

## Failure modes considered

1. **Kernel override still injects arbitrary content.** Mitigation: byte-identity and 80k source-bound checks before any output; missing/tampered paths emit one blocking JSON object. Negative fixtures cover missing, tampered, and identical packaged copies.
2. **Root CLAUDE.md or AGENTS.md hides broad policy through pasted bytes or aliases.** Mitigation: preserve operator files but accept only direct verified-kernel symlinks or exact kernel bytes (`AGENTS.md` may also be absent/empty). Mixed, pasted-bundle, and indirect-alias fixtures must fail.
3. **Project capability crosses host/repository scope.** Mitigation: explicit project kinds require membership in the exact matched project; bracket/slash foreign-host forms are rejected. Project `always` shelves fail validation.
4. **Risk classifier loses unusual path bytes.** Mitigation: NUL-delimited Git output with surrogateescape; tab/newline/non-ASCII hook paths remain Tier C. Kernel, enforcement settings, resolver, and lifecycle governance have explicit Tier C floors.
5. **Approval replay authorizes a different lifecycle gap.** Mitigation: approvals enumerate the exact current gap set; mismatch fails. Two-step fixture changes the gap set under an unchanged approval.
6. **Fresh deployment silently lacks selector runtime.** Mitigation: deploy selector and self-contained manifest with hooks; fresh temporary workspace must route Python.
7. **Explicit union overwhelms task context.** Mitigation: code-owned limits of 12 items, 80,000 characters, and 20,000 estimated tokens; overflow rejects the entire selection visibly and kernel-only.
8. **Coordination alias loses cadence semantics.** Mitigation: canonical rule restores post-handoff, post-wait, pre-decision, and status/latest-reply checks; focused fixture pins phrases.
9. **Generated evidence drifts after source/runtime edits.** Mitigation: regenerate inventory, authority, package, and progressive metrics; run freshness checks and full hook suite before push.

## Rollback

Revert the remediation merge commit on `develop`. No `main` promotion, publish, deploy, or workspace install is part of this change.
