## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: user request: "I sent you a PDF of DDIA to add to the shelf, it's also worth considering using it to revise existing skills/rules"
Goal source verification: N/A (operator request in session)
Plan reference: N/A (bounded shelf update)
Pre-author-inventory: DDIA shelf already existed at `skills/shelves/systems-architecture/data-intensive`; PDF located in session attachments; repo is public so PDF should not be committed.
Investigate-artifact: extracted PDF metadata/table of contents with `pdf-tool info` and frontmatter extraction; read existing shelf references and related `code-review` / `self-review` sections.
Pre-mortem-artifact: TRIVIAL (docs/skill update); main risk is copyright leakage from a full PDF or over-claiming DDIA coverage.
Hostile-review-artifact: WAIVED (small shelf/docs change)
Project-contribution: strengthens DDIA shelf routing and makes data-systems checks appear during ordinary code/self-review.

## Peer review

Syntax check: N/A (Markdown-only changes).

Copyright/source handling:
- The PDF is not committed.
- Added `references/source-ddia.md` documenting bibliographic details and non-redistribution policy.

Shelf coverage:
- Added `references/consistency-consensus.md` for DDIA chapters 8-9 concepts: partial failure, clocks, linearizability, serializability, quorums, fencing, and consensus.
- Added `references/data-integration-correctness.md` for chapter 12 concepts: systems of record, derived data, schema evolution, CDC/outbox, replay, timeliness, integrity, and privacy copy-sprawl.
- Updated `data-intensive/SKILL.md` from seven to nine domains and linked all new references.

Revision pass:
- `skills/code-review/SKILL.md` now checks transaction isolation, event/timestamp/partition ordering, and derived-data rebuild/reconciliation.
- `skills/self-review/SKILL.md` data-engineering standards now include source-of-truth, replay/backfill, schema compatibility, hot-key behavior, named consistency guarantee, lineage, and integrity checks.

Validation to run before push:
- `python3 bin/build.py --check`
- `python3 bin/sync-skill-references.py --check`
- targeted grep checks for new references and non-committed PDF

## Lead review

Approach-fit verdict: correct. The user asked to add the PDF to the shelf and consider revisions; the safe public-repo implementation is source citation plus original notes, not committing the copyrighted PDF.

Blast radius: shelf docs plus general review guidance. No runtime hooks changed.

Sequencing assumption: future deeper DDIA work can split individual chapters into more detailed references, but this patch closes the missing shelf-routing gap for chapters 8, 9, and 12.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P3 | Full PDF cannot be redistributed in the public repo. | noted; source note added instead |

## Quantified claims

- "Nine domains" -- `grep -n "Nine domains" skills/shelves/systems-architecture/data-intensive/SKILL.md` -> expected match after commit.
- "PDF is not committed" -- `git diff --name-only skills-upstream/develop..HEAD | grep -i '\\.pdf$'` -> expected no output after commit.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| N/A | No rework in this patch branch | N/A | N/A | N/A |

## Evidence-predates-work

Artifact: plans/self-review-ddia-shelf.md
First-added commit: 3332b1701d2235719931cb1326b90fe5343b89b0
Work commit: daeef86a18c60f502c12f72f1595d750519ff8a8
Verification: git merge-base --is-ancestor 3332b1701d2235719931cb1326b90fe5343b89b0 daeef86a18c60f502c12f72f1595d750519ff8a8; echo 0 -> 0
