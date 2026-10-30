# Strict test evidence (#1063, historical #386)

## Investigation Fact Sheet

Goal source: operator continuation to repair remaining evidence validation and producers.
Prior knowledge: current task-gate recovery plan and independent review; test-guard history includes actual callback payload export, which must remain intact. No applicable solutions entry found in targeted source search. Knowledge loci: skills/_testing-frameworks-rules.md and skills/testing-frameworks/SKILL.md define the receipt contract; skills/commit/SKILL.md produces it; hooks/git/test-guard.sh enforces it.

Observed: test-guard suffix-compares source strings, so an empty source covers any changed file; it ignores result and freshness and embeds JSON path/source values in Python source. Producers are currently prose, not an executable receipt writer. Native terminal fallback is deliberately supported only when no host binding exists. Designing denial currently claims every task needs full C-tier artifacts, contrary to proportional effective-tier enforcement.

Impact chain: affected tests -> receipt -> scoped/native resolver -> test-guard at push/PR creation. A weak receipt can authorize untested source despite a valid owning task. Source matching, success and freshness must be checked together.

## Design

Use one packaged hook helper for strict validation and receipt production. Version 2 receipts carry exact repository-relative source paths, Git blob object IDs, a tested ancestor revision, canonical repo root, an executed argv and zero exit status. Producer snapshots source before/after the test command; changes during testing invalidate output. Validator compares exact touched paths against receipts, current committed blobs and current working content. Tests may run before commit: ancestor revision plus exact current blob proves content continuity; unrelated later commits do not invalidate unchanged tested source. Changed/deleted source requires a fresh successful receipt. JSON and paths cross subprocess boundaries as argv/stdin, never generated Python source.

Compatibility: a report-only helper command diagnoses legacy receipts without granting authority. Runtime gate remains strict; rerun tests via producer, no automatic promotion of old pass claims. Preserve scoped resolver and actual native stdin behavior. Preserve structured override policy separately.

## Pre-mortem

- Tiger: whitespace/quotes/newlines or suffix paths borrow coverage. Use NUL Git diff transport and exact canonical relative paths; test hostile filenames and false suffix/empty coverage.
- Tiger: stale/failed tests authorize changed source. Verify explicit success, tested revision ancestry, source blob, worktree content; producer refuses source mutation during tests.
- Tiger: evidence is silently upgraded. Reject old schemas with rerun guidance; report-only mode never used by enforcement.
- Tiger: integration hides native/payload separation. Retain actual INPUT export and test bound invalid identity separately from valid native receipt.
- Tiger: prose overstates tier requirements. Designing message reports the selected task's actual tier and proportional requirements.

Implementation may proceed: YES
Review-Tier: C
Independent review is required before promotion. This worktree does not deploy, publish or merge.

## Implementation/self-review receipt

Implemented one shared schema/producer/validator helper. Tests cover exact/empty/suffix/traversal source names, failures and malformed extra entries, content/revision staleness, precommit-to-commit continuity, deletion, real callback hostile filenames, legacy report-only behavior, source FIFO replacement, no clean-filter execution, and receipt links. Source hashing is raw and nofollow/bounded, intentionally rejecting filter-normalized checkout differences. Receipts remain trusted local assertions, not tamper-proof attestations or proof of test adequacy.

Focused evidence: 16 new contract cases passed; existing test-guard scenarios 8/8 passed; invalid-host/native boundary 2/2 passed; designing/effective-tier and proportional-artifact cases 2/2 passed. Risk dependency graph passed, including new Tier C helper and exact invocation snapshots. Full review-risk suite reached generated-freshness validation and stopped on stale skill inventory. Shared generated catalogs deliberately remain untouched for coordinator aggregation. Full integrated suite, package regeneration and independent exact-commit review remain required before promotion.

Independent-review handoff: root inspected initial implementation and requested all-entry shape/success validation, no-filter hashing and nonblocking regular source reads; these corrections are implemented with regressions. Final exact-commit review is pending. No deployment, publication or merge performed.
