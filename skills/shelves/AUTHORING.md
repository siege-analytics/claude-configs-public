# Authoring a new shelf entry

How to add a book entry to the DBrain book-skill library. Captures the
conventions used by existing entries (clean-code, drive-motivation,
geocomputation-with-r, etc.) so future absorptions don't need to
reverse-engineer the pattern.

## Where it lives

```
skills/shelves/<shelf>/<book-slug>/SKILL.md
```

Optional supplementary files in the same directory:
- `references/` -- deeper distilled material from the book (chapter notes,
  pattern catalogs, etc.). Optional; populate later if useful.

If the book introduces a new shelf, also create:
- `skills/shelves/<shelf>/SKILL.md` -- the shelf router with trigger
  table + book list + disambiguation.
- Update `skills/shelves/SKILL.md` -- the top-level meta-router; add the
  new shelf to the trigger table + bump the shelf count in the
  description.

## Frontmatter

Required fields:

```yaml
---
name: <book-slug>
description: '<trigger-phrase-rich description. Use when the user mentions
  "phrase 1", "phrase 2"... Also trigger when [situation]. Pairs with
  <other-skill>. For [adjacent topic] see <other-skill>.>'
license: <license string; CC-BY-NC, MIT, "Free PDF from authors", etc.>
metadata:
  source: '<canonical URL or attribution. e.g. r.geocompx.org -- full
    free online edition of Geocomputation with R (authors). CRC Press
    also publishes paid print edition.>'
  coverage: '<FULL or PARTIAL. If PARTIAL, name exactly what is and
    is not absorbed. Verified DATE via WebFetch.>'
---
```

**Honesty conventions:**

- **`coverage: PARTIAL`** when the absorbed material is a companion site,
  a course-without-book, or selected chapters rather than the full book.
  Coverage gaps are flagged in the metadata + reiterated in the body's
  "Source + license" section.
- **`Verified DATE via WebFetch`** in metadata.coverage when the source
  URL was checked. Required for any "free / online / inline / canonical"
  claim per writing-claims:5 (verify before recommending external
  resources).
- **License must reflect the actual source.** CC-BY-NC for most free-with-
  attribution; CC-BY-NC-ND for the Lovelace / Pebesma-Bivand R books;
  MIT for code-repo-based course materials; "Free PDF from authors"
  for author-distributed PDFs without explicit license declaration.

## Body sections

Mirror existing entries (clean-code, drive-motivation as canonical
references). Required sections:

1. **Title heading** -- `# <Book name> Framework` (or similar).
2. **Intro paragraph** -- 2-4 sentences naming what the book is and when
   to load it.
3. **Core Principle** -- bold the central claim of the book. 1-2 paragraphs.
4. **Scoring** -- 10-point rubric tied to the book's framework. Required
   format: "Goal: 10/10. When evaluating X, rate 0-10 on Y." Then
   define what 9-10 / 7-8 / 5-6 / 3-4 / 1-2 look like.
5. **Framework sections** -- 3-7 numbered sections distilling the book's
   load-bearing concepts. Each section: core concept + why it works +
   key insights + anti-patterns where applicable.
6. **When this skill does NOT apply** -- boundary conditions; cross-
   references to adjacent skills that handle the out-of-scope cases.
7. **Companions** -- list of related skills + how this composes with
   them.
8. **Source + license** -- explicit URL, author attribution, license
   string, verification date. For partial coverage, name what was
   absorbed vs what waits for procurement.
9. **See also** -- optional. References to other skills, the originating
   recommendations doc, etc.

Existing entries vary in depth (drive-motivation is ~338 lines;
pragmatic-programmer is leaner). Match depth to the book's content; do
not pad.

## Router updates

When adding a book to an existing shelf:

```markdown
# In skills/shelves/<shelf>/SKILL.md:

## Trigger table

| Task signal | Book to read |
|---|---|
| ... existing entries ... |
| <new task signal phrase> | [skill:<book-slug>] |

## Books in this shelf

- ... existing entries ...
- [skill:<book-slug>] -- <author>. <book title>. <one-line summary>. <source note>.

## Disambiguation

- **<this book> vs <similar existing book>:** <one-sentence distinction>
```

When creating a new shelf:

1. Write `skills/shelves/<shelf>/SKILL.md` with frontmatter `name:
   shelf-<shelf>`, description, trigger table, book list, disambiguation,
   when-to-use / when-not-to-use, always-on companions, origin.
2. Update `skills/shelves/SKILL.md` top-level router:
   - Bump shelf count in description.
   - Add row to the Shelves trigger table referencing `[skill:shelf-<new>]`.

## Self-review (per `[skill:self-review]`)

Every shelf absorption is a substantive PR that requires the standard
self-review artifact in `<session>/plans/review-shelf-<book-slug>.md`
with the trailer pair on the commit:

```
Self-Review: <one-line summary>
Self-Review-Source: <absolute path to the review artifact>
```

The review's Lead section should declare the role-tagged affirmative
standards specific to absorption work:
- **As tech lead:** scope of the absorption (full book / companion /
  course); blast radius (which shelves are affected); reversibility.
- **As <domain expert if relevant>:** is the distillation accurate to
  the source? Does it preserve the canonical framework names? Does it
  honestly flag what's omitted?

For verification, ASCII-only is required across the new entry + router
updates. Validate before commit:

```bash
perl -ne 'print "$ARGV:$.: $_" if /[\x{2014}\x{2013}\x{2192}\x{2018}\x{2019}\x{201C}\x{201D}\x{2026}\x{2022}\x{00B7}\x{00A0}]/' \
  skills/shelves/<shelf>/<book-slug>/SKILL.md \
  skills/shelves/<shelf>/SKILL.md \
  skills/shelves/SKILL.md
```

If any line returns, replace em-dashes with `--`, curly quotes with
straight, etc.

## PR conventions

- One book per PR when feasible. Multi-book PRs (e.g. two complementary
  books that establish a new shelf together) are acceptable when the
  bundling is justified.
- Title: `feat(shelves/<shelf>): <action -- title>` matching existing
  PR title patterns.
- Body: name the gap the entry closes, the coverage state (FULL / PARTIAL
  with explicit caveats), the verification done, the test plan, and the
  origin (which session / recommendations doc / ticket).
- Self-review trailers on the commit per the self-review hook.

## Verification before recommending a book

Per writing-claims:5 (verify before recommending an external resource):
when proposing a book for shelf absorption, verify the source claims
before assertion. For "free at URL X" claims, WebFetch the URL and
confirm full content is readable inline (not just a landing page). For
"canonical reference for Y" claims, ground in the field's actual
consensus (a Wikipedia / well-known-textbook-list cross-check is the
minimum bar).

Bad-example catalog (session 260502-vital-channel, 2026-05-17):
- "lethain.com hosts An Elegant Puzzle freely" -- WebFetch showed
  promotional landing page only; book is paid. Recommendation retracted.
- "py.geocompx.org hosts Geocomputation with Python freely" -- WebFetch
  showed landing page; full chapters not yet online; R version at
  r.geocompx.org was the canonical free reference. Recommendation
  re-pointed.

The verification cost is small (one WebFetch); the cost of an
incorrect recommendation is a downstream consumer trying to read a
book that doesn't exist where you said it did.

## Procurement tracking

Books that the operator does not yet have access to (paid / library /
not-yet-procured) should be added to a procurement-queue issue rather
than absorbed against guesses. See claude-configs-public#111 for the
pattern. When a procured PDF arrives, this AUTHORING guide is the
starting point.

## See also

- `skills/shelves/SKILL.md` -- the meta-router; the top-level entry point
  for any shelf navigation.
- `skills/distill-lessons/SKILL.md` -- DIFFERENT skill (promotes Tier-1
  lessons to Tier-2 rules); not used for book absorption.
- `skills/self-review/SKILL.md` -- required for every shelf absorption PR.
- `_writing-claims-rules.md` -- writing-claims:5 grounds the verify-
  before-recommending discipline that gates book proposals.
- Example entries with strong frontmatter / coverage-caveat hygiene:
  `team/staff-engineer/SKILL.md` (PARTIAL coverage),
  `geospatial/geocomputation-with-r/SKILL.md` (FULL coverage with
  verification date).
