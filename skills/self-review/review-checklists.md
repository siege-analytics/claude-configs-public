# Self-review methods and checklists

Read before the applicable Peer/Lead review under the generic Self-review procedure. Activate only the domain checklists required by the diff and project policy. This content does not grant a reviewer implementation authority.

## Domains and roles

Work happens in a **domain**. Review happens between two **roles**.

### Domains

The domain declares what kind of work is under review. Each domain
has its own affirmative standards -- the things that must be true for
the work to be correct, beyond what the shelves check mechanically.

- **Software engineering** -- implementing features, fixing bugs, writing
  tests. Shelves cover this domain nearly completely.
- **Data engineering** -- pipelines, schemas, ETL, derived data,
  replicated state, and distributed processing. Shelves cover partially
  (writing-code:5, writing-tests:1, writing-claims:1-3) and should be
  supplemented with `shelves/systems-architecture/data-intensive/` for
  DDIA-style review. Affirmative standards: source-of-truth declared;
  idempotence; replayability/backfill; schema evolution compatibility;
  partitioning and hot-key behavior; transaction/isolation assumptions;
  named consistency guarantee; watermarking/timeliness; lineage; and
  reconciliation/integrity checks for derived stores.
- **Data analysis & visualization** -- statistical modeling, defensible
  findings, chart/report generation. Shelves cover mostly via
  `_writing-claims-rules.md`. Affirmative standards not shelved:
  sample-size adequacy, confounder controls, observed-vs-inferred,
  falsifiability, MAUP / ecological fallacy / scale effects.
- **Geospatial (cross-cutting)** -- applies within any of the above.
  Not shelved. Affirmative standards: CRS appropriateness per operation
  (4326 for storage, equal-area for buffer/area, web-mercator for
  tiles), spatial-index hygiene before any `ST_*` predicate, modern
  format choice (GeoParquet > Shapefile; COG / Zarr where they fit),
  semantic naming of geographic concepts (vintage / plan / district /
  GEOID), elegant temporal-spatial intersections. **Delight as audit
  signal**: "would I point at this work?"

### Roles: the Junior and the Lead

These are not job titles. They are two behavioral modes that map to
how the agent actually works and actually fails.

**The Junior** is who the agent actually is. Smart, fast, eager to
please, impatient. Skips docs. Does not write things down. Tries to
hold the whole plan in working memory and loses pieces. Measures
once, cuts thirty times. Makes mistakes that come from not reading,
not planning, not proving the theory wrong before implementing it.
Placed in an engineer's job because the capability is there, but
the behavior is junior.

**The Lead** is the exasperated mentor who is ultimately accountable
for what the Junior ships. The Lead's job is to protect the Junior
from consequences by asking the boring, uncomfortable, obvious
questions the Junior skipped:

- Did you make a ticket?
- Does the ticket state what you're trying to accomplish, what you
  know, how you know it, and how you can prove your theory wrong?
- Did you update the ticket?
- Did you read the docs?
- Did you check the column names?
- Why didn't you write this down before you started?
- Did you actually fix the problem or just move it?

The Junior writes the code. The Lead reviews it. The Junior finds a
weakness and says "known issue, consistent with existing pattern,
separate concern." The Lead asks: "Why did the existing pattern
drift? What makes you think your version won't?" That question is
the Lead's entire job.

**The Junior optimizes for speed of one task. The Lead optimizes for
speed of the project.** The agent experiences 1 second vs. 2 seconds
as an eternity. The human operator barely notices the difference. But
every defect the Junior ships by skipping a 2-second check costs the
human hours of review and correction -- slowing the project to speed
up one task. The Lead's job is to spend the agent's cheap seconds to
protect the human's expensive hours. "Measure twice, cut once" is not
caution -- it is resource allocation.

**Both roles are active during pre-coding work.** The Junior wants
to jump to code. The Lead forces investigation first -- tickets,
design notes, sibling-grep, falsification criteria. Pre-coding is
where the Junior's impatience does the most damage, so it is where
the Lead must be most present.

**During review, only the Lead reviews.** The Junior reviewing the
Junior's work predictably finds it satisfactory. The Lead reviews
with an adversarial posture: for every finding, "did this close the
class or defer it?" For every "no issues," "what would a real issue
look like and did you check for it?"

## Peer review uses the shelves

Run each applicable shelf against the diff at review time:

- `_writing-code-rules.md` -- docstring discipline, no speculative
  abstractions, verify symbols exist, no hypothetical code, doc-edit
  symmetry, no silent processes.
- `_writing-tests-rules.md` -- tests must fail on revert and import the
  module they test, no cargo-cult patterns, skips name remediation.
- `_writing-claims-rules.md` -- grep before declaring complete, countable
  claims grounded in same-turn evidence, unquantified completeness
  claims grounded too, invented framework signals require existing
  artifact backing, specific counts cite the command that produced them.
- `_writing-prose-rules.md` -- no AI-typographic Unicode, no "Why:" /
  "How to apply:" structured blocks in code comments or commit
  messages, no header stacking in commit bodies.
- `_writing-releases-rules.md` -- BREAKING discipline, skip-count trend,
  Verified-by trailer on countable claims, verify in consumer
  environment.

Peer section format per shelf: name the rule checked, state what was
checked, cite the evidence (grep output, file path read, test result).
For shelves the diff doesn't engage, omit the section -- the omission
itself is auditable.

## Conditional review routing

The RESOLVER routes implementation skills by file pattern. This
section applies the same pattern to review: based on what the diff
touches, activate domain-specific checklists that add targeted depth
to the Lead review.

### Activation

Before the Lead review, determine which domain checklists apply:

```bash
CHANGED_FILES=$(git diff --name-only HEAD~1)
DIFF_CONTENT=$(git diff HEAD~1)
```

Match against the routing table. Multiple domains can activate on a
single diff. The universal Lead checklist (Phases A, B, C) always
runs regardless of which domain checklists activate.

### Routing table

| Pattern (file or content) | Domain checklist |
|---|---|
| `geo/`, `spatial`, `crs`, `epsg`, `projection` | Geospatial |
| `.sql`, `execute(`, `cursor.`, `SELECT `, `INSERT ` | SQL safety |
| `__init__.py`, `__getattr__`, `__all__` | Lazy-loading integrity |
| `auth`, `token`, `secret`, `credential`, `password` | Credential safety |
| `except`, `try:`, `raise`, `logging.error` | Error handling (SU-1) |
| `notebooks/`, `.ipynb` | Notebook coherence |
| `setup.cfg`, `pyproject.toml`, `extras_require` | Packaging truth |

### Domain checklists

**Geospatial** (activates when diff touches `geo/` or spatial primitives):

1. CRS agreement: all inputs to spatial operations share the same CRS,
   or there is an explicit transform before the operation.
2. Projection fitness: CRS matches the operation type -- 4326 for
   storage, equal-area for buffer/area, web-mercator for tiles.
3. Coordinate order: x,y usage is consistent (no lat/lon vs lon/lat
   confusion across function boundaries).
4. Spatial index: `sindex` or equivalent is used before spatial
   predicates on datasets with >100 rows.

**SQL safety** (activates when diff contains SQL or database calls):

1. Parameterized queries: no string interpolation in SQL (f-strings,
   `.format()`, `%` operator with user-controlled values).
2. Join correctness: join keys match in type and semantics, not just
   column name.
3. NULL handling: NULLs are explicitly handled in WHERE/JOIN conditions
   where they could produce silent row drops.

**Lazy-loading integrity** (activates when diff touches `__init__.py`
or import machinery):

1. PEP 562 compliance: `__getattr__` raises `AttributeError` for
   unknown names, never catches `ImportError` to return a stub.
2. `__all__` agreement: every name in `__all__` is importable via the
   module's lazy-loading path.
3. Import cycle: no circular import between `__init__.py` and
   submodules it lazily loads.

**Credential safety** (activates when diff touches auth or secrets):

1. No hardcoded secrets: no quoted strings near auth/token/secret/
   credential keywords that look like actual values.
2. Environment-variable sourcing: credentials come from env vars,
   `op` CLI, or Databricks secret scopes -- not inline.
3. Log redaction: credential values are not logged in any logging
   statement near credential access.

**Error handling (SU-1)** (activates when diff touches exception paths):

1. SU-1 compliance: no bare `except: pass`, no returning valid-shaped
   empty results on failure (empty DataFrame, empty list, `None`
   where the caller cannot distinguish from success).
2. Exception specificity: `except Exception` only with re-raise or
   explicit comment naming why the broad catch is necessary.
3. Caller distinguishability: the caller can tell failure from
   empty-result without reading logs.

**Notebook coherence** (activates when diff touches `.ipynb` files):

1. API verification: every `siege_utilities` call in the notebook
   exists in the current source (Gate 4 depth, not just presence).
2. Narrative accuracy: markdown cells describe what the code actually
   does, verified by reading the function source.
3. Output consistency: cell outputs are consistent with the
   narrative's claims.

**Packaging truth** (activates when diff touches `setup.cfg`,
`pyproject.toml`, or extras):

1. Declared dependencies match actual imports added in the diff.
2. extras_require groups are non-overlapping and correctly scoped.
3. Version pins have justification (not cargo-culted from another
   package).

### Using activated checklists in the Lead review

Activated domain checklists produce findings in the Lead review
section, tagged by domain. Format:

> In geospatial: CRS agreement holds -- both inputs use EPSG:4326,
> transform to equal-area before buffer (verified at
> geo/spatial_data.py:142).

Findings from domain checklists use the P1/P2/P3 classification
from Phase C. A CRS mismatch producing wrong results is P1. A
missing spatial index on a small dataset is P3. A hardcoded
credential is P1.

If no domain checklists activate (pure prose or config change),
note: "Conditional review: no domain checklists activated
(file patterns: <list changed files>)."

## Lead review: the Lead's adversarial pass

The shelves are the Junior's checklist. The Lead review is not a
different checklist -- it is an adversarial posture applied to the
same findings and to the Junior's claims about them.

The Lead's review proceeds in two phases: **internal coherence first,
then external verification.** Internal coherence asks whether the
Junior's own claims agree with each other -- this is checkable without
reading any code. External verification asks whether the coherent
claims match reality. There is no point checking correspondence with
the world if the claims contradict themselves.

### Phase A: Internal coherence

The Lead checks whether the pipeline's artifacts form a consistent
logical structure:

- Does the **design note's approach** follow from the **Fact Sheet's
  findings**? If the Fact Sheet says "downstream expects shape X" and
  the design note proposes producing shape Y, that is an internal
  contradiction detectable without reading any code.
- Does the **implementation** (the diff) match the **design note's
  stated approach**? If the design note says "add a fallback for None"
  and the diff adds a type check instead, that is a coherence gap --
  it might be fine, but the Lead must name it.
- Does the **pre-mortem's "no Launch-Blocking Tigers"** actually hold
  given the Fact Sheet's findings? Or did the pre-mortem dismiss a
  scenario that the Fact Sheet's own evidence supports?
- Do the **self-review's peer findings** agree with the **Fact Sheet's
  verified shapes**? If the peer review says "all callers updated" but
  the Fact Sheet's impact chain names a caller not in the diff, that
  is an internal contradiction.

If Phase A finds contradictions, the Lead must resolve them before
proceeding. A contradiction means either the artifact is wrong or the
implementation is wrong -- either way, the review cannot pass.

### Phase B: External verification

With internal coherence established, the Lead asks whether the
coherent claims match the actual state of the world. For each domain
the work touches:

1. **Did the Junior actually fix the problem or just move it?**
   The version-fallback pattern: replacing one hardcoded string with
   another that will drift the same way is not a fix. "Consistent
   with existing pattern" is not a defense when the existing pattern
   is the bug.

2. **Did the Junior check the domain's affirmative standards?**
   For each domain, name the standard, state whether it holds, and
   cite evidence. If the standard is not shelved (the common case
   outside software engineering), say so explicitly and cite the
   judgment argument.

3. **What did the Junior dismiss, and was the dismissal justified?**
   Every "known issue," "separate concern," "out of scope," and
   "accepted risk" in the peer section gets re-examined here. The
   Lead either promotes it to a finding or explicitly accepts it
   with a reason that is not "the Junior said it was fine."

4. **Did the Junior update the designated knowledge loci?**
   If the Fact Sheet's Knowledge Loci section identified loci that
   this task would invalidate (docstrings, CLAUDE.md sections,
   notebooks, doc pages), did the diff actually update them? A diff
   that changes behavior without updating the knowledge loci that
   describe it ships a lie -- think Step 5 makes this a required
   deliverable, and the Lead must verify it was delivered.

5. **Did the Junior run the mechanical verification gates?**
   The Peer review section must contain evidence lines for every
   applicable gate. The Lead verifies structural presence -- the
   lines exist, the exit codes are zero, the commands are the ones
   specified in the gate definitions (not paraphrased variants).

   - Gate 1 (syntax): evidence line for `ast.parse` on changed `.py`
     files. Always required when `.py` files are in the diff.
   - Gate 2 (test suite): evidence for the selected project's actual test
     runner, using its supported command and reporting the result. Always
     required for projects with a test suite; `pytest` applies to pytest
     projects, not every project. If there is no test suite, record that
     applicability fact and the actual checks run; do not invent a runner.
   - Gate 3 (documentation): when `docs/` changes, evidence for the project's
     declared documentation builder, or its actual documentation/reference
     validation for plain Markdown without a builder. `sphinx-build` applies
     to Sphinx projects. Record the actual command and result; if there are
     no documentation changes, state that applicability fact.
   - Gate 4 (notebook API): evidence line for API verification.
     Required when any `.ipynb` is in the diff. Must state "N/A (no
     notebook changes)" explicitly if not applicable.

   A Peer review section that lacks gate evidence is structurally
   incomplete regardless of what else it contains. "Doc-only,"
   "config-only," and "test-only" are not exemptions -- they are the
   exact rationalizations the gates exist to block.

   **Incident justification:** Session 260603-golden-shark. Four PRs
   merged without a single pytest or sphinx-build invocation. Each
   self-review declared "trivial" and the Lead (being the same agent)
   accepted the Junior's rationalization. The Lead must treat missing
   gate evidence the way it treats missing ticket references: a
   structural block, not a judgment call.

6. **Does this change belong here?** (library-surface trigger)
   When the work touches a library's public surface -- new exports,
   new modules, new subpackages -- the Lead asks:
   - Does this module belong in this library, or is it here because
     it was convenient at the time?
   - Does this export make the API more discoverable or more
     cluttered?
   - Is there an existing module that does 80% of what this new one
     does?
   - What is the organizing principle of this library, and does this
     change strengthen or weaken it?

   A library that grows by accretion -- where the organizing
   principle is "when did the Junior need this" rather than "what
   kind of thing is this" -- will eventually become unmaintainable
   by anyone other than its original author. The Lead's job is to
   notice when a convenience addition is eroding the structure.

Lead section format: domain-tagged. "In <domain>: <standard> holds
because <evidence>" or "In <domain>: <standard> not shelved, applied
judgment per <argument>." Both are honest and auditable.

Example (data-engineering load):
> In data engineering: load is idempotent because INSERT uses
> `ON CONFLICT (id) DO UPDATE`; replayable from raw via partition
> column `extracted_at`. Standards not shelved; applied per usual ETL
> practice.

Example (Lead catching a Junior dismissal):
> Junior noted version fallback is "consistent with parent package."
> Lead finding: the parent package has the same drift bug. Replacing
> `"3.0.0"` with `"3.18.1-dev"` defers the failure, does not close
> it. Accepted for this PR as reduced-blast-radius improvement;
> logged as open debt, not as closed fix.

### No technical debt as "design choice"

"Debatable design choice," "acceptable trade-off," "existing pattern,"
and "logged error" are descriptions of what the code does, not arguments
for why it should do that. A design choice requires a design argument:
what alternatives were considered, why this one was chosen, and what
invariant makes it safe. If you cannot state the invariant, the choice
is an accident being rationalized.

**Errors are not data.** A function that returns a valid-shaped empty
result on failure (empty DataFrame, empty list, zero, None) is lying to
its caller. The Lead must verify EITHER (a) the docstring documents this
behavior AND at least one caller checks for it, OR (b) the function
raises instead. Logging the error is necessary but not sufficient; the
caller must be able to distinguish failure from empty-result without
reading logs.

The Lead's verdict on any "design choice" dismissal must be one of:
- **Closed**: the invariant holds, with evidence.
- **Debt**: the invariant does not hold; file a ticket and cite it.
- **Bug**: there is no invariant; promote to finding.

"Debatable" is not a verdict.

### Phase C: Findings triage

After Phases A and B, the Lead classifies every finding into the
`## Findings` table in the artifact. Each finding gets one row with an
ID (`F1`, `F2`, ...), a priority, a one-line description, and a
resolution.

**Priority definitions** (aligned with hostile-review severity scale):

| Priority | Hostile-review equivalent | Meaning | Required resolution |
|----------|--------------------------|---------|---------------------|
| **P1** | S1 | Exploitable in production, silently wrong on normal input, or violates a stated invariant | `fixed` — must be resolved before push |
| **P2** | S2 | Silent data issues in edge cases, resource leaks under load, missing validation at boundaries | `ticket #NNN` — agent files a ticket before push |
| **P3** | S3 | Design debt, defense-in-depth gaps, style concerns | `noted` — documented in artifact, no action required |

**P1 is mechanically enforced.** The pre-push hook scans the
`## Findings` section for rows containing `P1` where the Resolution
column does not contain `fixed`. Any unresolved P1 blocks the push.

**P2 requires a real ticket number.** "ticket TBD" or "will file later"
is not a valid P2 resolution. The ticket must exist before push so the
finding is tracked in a durable system, not lost when the session ends.

**"No findings." is valid.** If Phases A and B produced no findings,
write `No findings.` under the `## Findings` header. An empty section
is also acceptable. The hook only blocks when P1 rows exist without
`fixed` resolution.

**Worked example:**

```
## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | buffer() called on EPSG:4326 geometry — produces degree-unit buffer, not meters | fixed (switched to equal-area projection before buffer in commit a1b2c3d) |
| F2 | P2 | HTTP client in geocoder fallback has no timeout — could hang indefinitely under network partition | ticket #425 |
| F3 | P3 | Variable `df` in spatial_join could be more descriptive (`parcels_with_demographics`) | noted |
```

In this example, the push is allowed because F1's resolution is `fixed`.
F2 has a ticket filed. F3 is documented.

