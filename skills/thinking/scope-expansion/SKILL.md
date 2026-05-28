---
name: scope-expansion
description: "Post-epic/post-batch boundary audit. Fires after closing >=3 tickets in the same module to find sibling bugs the per-ticket pipeline missed. Analytical — read-only investigation producing a findings report."
disable-model-invocation: true
allowed-tools: Read Grep Glob
argument-hint: "[module-path-or-epic-ref]"
---

# Scope Expansion

After completing a batch of related work (epic, audit remediation, multi-ticket fix cycle), audit the module boundary for bugs the per-ticket pipeline structurally cannot see.

## Why This Exists

The per-ticket pipeline (think → investigate → implement → review) is thorough **within scope**. But its scope is defined by the ticket, not by the module. Three classes of bug survive per-ticket discipline:

1. **Sibling bugs:** The same pattern that was buggy in File A also exists in File B, which no ticket touched.
2. **Contract drift:** The tickets changed internal behavior but a public API, docstring, or test still encodes the old contract.
3. **Cross-cut violations:** The tickets each passed individually, but together they introduced an inconsistency (duplicate logic, incompatible assumptions, conflicting defaults).

Round 1 of the siege_utilities audit found 8 bugs in 6 files. Round 2 — triggered by this gap — found 13 more across 350 files. Every one of them was a sibling, contract drift, or cross-cut that no individual ticket would have surfaced.

## When This Skill Fires

**Mandatory trigger:** After closing >= 3 tickets in the same module or package within a single session or epic.

**Optional trigger:** After any epic completion, even if tickets span multiple modules.

**Does NOT replace:** Per-ticket investigation (investigate skill) or per-ticket self-review. This is an additional pass, not a substitute.

## Phase 1: Blast-Radius Map

List every file touched by the batch of tickets. For each file:

1. What functions/classes were modified?
2. What imports changed?
3. What tests were added or modified?

Then list every file that **imports from** a touched file (one hop out). These are the boundary files — they depend on contracts that may have changed.

```
### Blast-Radius Map
Touched files: [list with commit refs]
Boundary files (one-hop importers): [list]
Total scope: N touched + M boundary = P files to audit
```

## Phase 2: Sibling Grep

For each bug pattern that was fixed in the batch, grep the **full codebase** for the same pattern in untouched files. Specific queries:

1. **Same function shape:** If you fixed `foo()` in `module_a.py`, grep for `def foo(` across the repo.
2. **Same import path:** If a bug was caused by a wrong import, grep for other files using the same import.
3. **Same data shape assumption:** If a bug was wrong field access (`obj.x` when it should be `obj.y`), grep for other `.x` accesses on the same type.
4. **Same validation gap:** If a bug was missing validation, grep for other call sites that also lack it.

Each sibling hit is a candidate bug until verified otherwise.

```
### Sibling Grep Results
Pattern: [what was grepped]
Source fix: [file:line of the original fix]
Siblings found: [file:line list]
Verified as bug: [yes/no per sibling, with evidence]
```

## Phase 3: Contract Verification

For every public API (function, class, or module `__all__`) in a touched file:

1. **Docstring accuracy:** Does the docstring match the current implementation? Check return types, parameter descriptions, documented columns.
2. **Test coverage:** Does at least one test exercise the public API with a realistic input and verify the output shape?
3. **Cross-module consistency:** If two touched files define similar APIs, are their conventions consistent? (naming, error handling, return shapes)

```
### Contract Verification
| API | Docstring accurate? | Test exists? | Test verifies output shape? |
|-----|--------------------|--------------|-----------------------------|
| ... | ... | ... | ... |
```

## Phase 4: Findings Report

Produce a structured report:

```
### Scope Expansion Findings — [epic/batch ref]

**Scope:** N tickets, P files audited (N touched + M boundary)

#### Sibling Bugs (same pattern, different file)
| # | File:Line | Pattern Source | Severity | Description |
|---|-----------|---------------|----------|-------------|

#### Contract Drift (API/docstring/test mismatch)
| # | File:Line | What Drifted | Severity | Description |
|---|-----------|-------------|----------|-------------|

#### Cross-Cut Violations (inter-ticket inconsistency)
| # | Files | What Conflicts | Severity | Description |
|---|-------|---------------|----------|-------------|

#### False Positives Verified
| # | Claim | Why False | How Verified |
|---|-------|----------|-------------|

**Summary:** X findings (Y high, Z medium). N false positives caught by verification.
```

## Iron Laws

1. **File:line or it didn't happen.** Every finding must cite the exact location. "The module has issues" is not a finding.
2. **Verify before reporting.** Read the actual code at the cited line. Subagent claims have a ~30% false-positive rate on severity (measured empirically in this repo).
3. **Don't fix during audit.** This skill produces findings. Fixes are separate tickets with their own think gates per resolver rule #10.
4. **Sibling-grep is not optional.** Phase 2 is the reason this skill exists. If you skip it, you're doing a regular code review, not a scope expansion.
5. **Include the false-positive count.** The ratio of findings to false positives is a quality signal for the audit itself.
6. **"Design choice" is not a finding disposition.** If you encounter a pattern that looks wrong but you want to call it a design choice, you must state the invariant that makes it safe. If you cannot state the invariant, classify it as debt (file a ticket) or bug (promote to finding). "Debatable" is not a disposition — it is the Junior avoiding a verdict.
