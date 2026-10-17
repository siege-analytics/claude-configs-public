# Shape-space audit

This skill is the authoritative discipline for authoring or reviewing code that models an external shape space. It complements `self-review`'s adversarial shape audit subsection and `hostile-review`'s Category 10 (scanner-shape coverage) by defining the vocabulary those surfaces consume.

## When this skill applies

- The diff modifies external-shape-modeling code as defined by `[`writing-rules`](../_writing-rules-rules.md)` writing-rules:5. Concretely: scanners, parsers, linters, hooks that infer semantics from source syntax, config files, CLI arguments, API payloads, schemas, notebooks, or framework conventions. Not Python-specific, not scanner-specific.
- A rule's prose claims to cover "a class of code idioms" (e.g. `[`writing-code`](../_writing-code-rules.md)` writing-code:8's "optional-import patterns"). Class-membership prose triggers `[`writing-claims`](../_writing-claims-rules.md)` writing-claims:3, which itself triggers this discipline via `[`writing-rules`](../_writing-rules-rules.md)` writing-rules:8's enumeration requirement.
- A hostile review round targets scanner/parser/linter/hook code (per `hostile-review/SKILL.md` Category 10).

## Purpose

Ten rounds of alternating-provider hostile review on a Python AST scanner can converge on GREEN while missing dominant Python idioms. Provider alternation is not sufficient. Frame alternation IS. This skill formalizes the frame-alternation discipline and specifies the corpus-sampling protocol that makes the discipline mechanically checkable.

Empirical evidence: `siege-analytics/claude-configs-public#810` (R5-R10 scanner rewrites on `_extract_optional_imports`) all passed writing-code:5, writing-tests:1, writing-claims:8 individually while the shape space that writing-code:8's prose claimed to cover was never actually exercised. R11 (Scala/JVM-skeptic frame) surfaced 3 INVALIDATING + 4 MAJOR shape misses in one pass. See `plans/r11-scala-skeptic-review.md` and `plans/r11-meta-gap-analysis.md` for the full trace.

## The five rotation frames

Each frame is a lens for constructing adversarial inputs. The frames are ordered by "how orthogonal to author-frame each is" — a Python author is least like a Scala skeptic and most like a Python newcomer, so the strongest signal usually comes from frame 1.

**1. Scala / JVM skeptic.** Assumes Python is untyped, dynamically-dispatched, and every scanner claim is over-stated by default. Assumes AST-based Python static analysis is duct-tape over an untyped grammar and misses the shapes real Python code uses in production. Constructs adversarial inputs from JVM-boundary Python: `pyspark.sql.functions.udf`, `pandas_udf`, `py4j` callbacks, Spark driver scripts with N imports guarded by one `PYSPARK_AVAILABLE`. Typically finds: coverage over-claims, missing composition audits, out-of-scope claims that hide the dominant shape.

**2. PyPI top-100 CI operator.** Runs the scanner against real-world open-source packages the scanner claims to cover. Assumes fixture coverage does not imply real-world coverage. Constructs adversarial inputs by grepping real PyPI packages (numpy, pandas, scipy, matplotlib, requests, flask) for the target shape and running the scanner against those exact code snippets. Typically finds: fixture-frame traps — shapes the fixture set enumerated cleanly but real code uses differently (e.g. `try/except/else` for the availability flag, not `try/except` alone).

**3. Security engineer.** Asks about bypass surfaces and injection shapes. For a scanner meant to enforce X, constructs inputs that structurally look like X but semantically aren't (or vice versa). Typically finds: false negatives on obfuscated-but-legal shapes; false positives on look-alike literals (e.g. a regex literal inside a linter that matches its own pattern).

**4. Python newcomer.** Reads the SKILL.md prose without prior context and asks whether the enforcement actually does what the prose claims. Constructs inputs from the SKILL.md's own examples, then adjacent shapes a beginner would naturally try. Typically finds: prose-vs-implementation gaps — SKILL.md over-claims that the reviewer would take at face value.

**5. Linter author.** Focuses on AST edge cases: `AnnAssign` vs `Assign`, `Try` vs `TryStar`, `ImportFrom` with `alias.name == '*'`, decorator-annotated symbols, nested class/function bodies. Typically finds: shape gaps at Python-version boundaries or at grammar-edge constructs the scanner's author didn't have in their sample set.

## Rotation cadence

- No repeat frame within the last three hostile-review rounds on the same scanner/skill.
- Provider alternation is a SEPARATE axis; both are required. Rotating provider without rotating frame reproduces the R5-R10 failure mode (ten rounds, three providers, one implicit frame).
- The frame in force for a given round is declared explicitly in the hostile-review artifact's frontmatter or first section: `Frame: Scala/JVM skeptic` etc. Bounded pass reviewer cites which frame's counter-examples they constructed.

## Corpus sampling protocol

The frames define perspective. Corpus sampling defines the mechanical evidence.

**Sample size floor:** at least five distinct idioms per hostile-review round. Not five instances of the same idiom — five *shapes*.

**Sample source:** real-world code, not fixtures shipped with the scanner. For Python: PyPI top-100 packages; for TypeScript: DefinitelyTyped or npm top-100; for Rust: crates.io most-downloaded; for shell: coreutils or a distribution's `/etc/init.d`. Sample from artifacts the scanner would encounter in production.

**Sample selection:** favor shapes the SKILL.md claims to cover. If SKILL.md prose says "detects try/except optional-import patterns," the reviewer's sample MUST include the dominant real-world variants of that pattern (else-clause, positional flag, N-import with 1 flag, dotted-source with prefix flag) — not just the shape the shipped fixtures cover.

## The P6 anti-pattern: context-free grep is not shape evidence

**Named pattern.** A grep that finds a token can only prove the token exists somewhere. It does NOT prove the token exists in the block-type, grammar-context, or control-flow position that gives the token its meaning. Shape evidence requires either:

- an AST- or control-flow-aware check that walks to the position where the token is load-bearing, OR
- an executable fixture that would fail if the check were absent.

Context-free grep is discovery, not verification.

**Recurrence:** R11-meta's own first-pass framing over-generalized from a grep. Twelve `Category: local-only` matches across R5-R10 self-reviews were reported as "invented-token bypass," but the token was legitimate in one block-type (`Trivial-against-state`) and invalid in another (`Trivial-investigation`). The context-free grep found the token; the shape audit distinguishes valid-in-block-A from invalid-in-block-B. Without the shape audit, the first-pass diagnosis blamed the wrong scope, and PR A (`siege-analytics/claude-configs-public#814`) had to correct the diagnosis mid-implementation. See `plans/self-review-pr-a.md` for the recurrence trace.

**Applied to scanner code:** a coverage claim in SKILL.md prose like "catches try/except optional-import patterns" is a class-membership claim (subject to `[`writing-claims`](../_writing-claims-rules.md)` writing-claims:3). The claim is not backed by a grep for "try/except ImportError" in the scanner source — that only proves the string exists. The claim is backed by an AST-walking check in the scanner that dispatches on `ast.Try` nodes AND a fixture that would regress if the check were removed. The same standard applies at review time: reviewer's coverage-status claim in the writing-code:8 shape table must cite the AST-walking function AND the fixture, not a grep line-count.

**Applied to review artifacts:** a hostile-review finding that says "grep for X returns N hits" is discovery, not evidence. The finding becomes evidence when the grep's hits are classified by enclosing block/grammar position AND the reviewer names which of those positions is load-bearing for the claim under review.

## Corpus-sampling recipe (concrete)

For a hostile review round on Python scanner code claiming to cover a class of import idioms:

1. Pick the frame in rotation (see cadence above). Declare it in the artifact.
2. Identify the five dominant real-world variants of the target idiom by grepping top-N PyPI packages. For "optional-import patterns," this yields at minimum: `try/except ImportError` with module-scope flag; `try/except/else FLAG = True`; `try/except ImportError` with `AnnAssign` flag; multi-import with single flag; dotted-source `import a.b.c as d` with prefix flag.
3. For each variant, construct a minimal fixture and run the scanner. Record the actual behavior (matched / silently-dropped / warned).
4. If any variant is silently dropped and SKILL.md's prose claims to cover it, that is a class-membership over-claim per `[`writing-claims`](../_writing-claims-rules.md)` writing-claims:3. File as a review finding, cite the P6 anti-pattern if the coverage claim's original backing was a grep rather than a fixture.
5. Cross-reference every finding with the writing-code:8 shape-space coverage table (per `[`writing-rules`](../_writing-rules-rules.md)` writing-rules:8). Missing row = table gap; row present but marked `covered` when fixture fails = false coverage claim.

## Composition with other rules and skills

- **`[`writing-rules`](../_writing-rules-rules.md)` writing-rules:8** requires this enumeration for any rule whose prose claims to cover a class of code idioms. This skill provides the discipline; the rule provides the enforcement.
- **`[`writing-rules`](../_writing-rules-rules.md)` writing-rules:5** defines external-shape-modeling as never-trivial. This skill's applicability aligns with that definition.
- **`[`writing-claims`](../_writing-claims-rules.md)` writing-claims:3** governs class-membership prose. Unquantified coverage claims like "detects X patterns" are class-membership claims and must be backed by the enumeration this skill produces.
- **`self-review/SKILL.md`** — `## Adversarial shape audit` subsection consumes this skill's rotation frames and corpus-sampling protocol at authoring time.
- **`hostile-review/SKILL.md`** — Category 10 (10a corpus audit, 10b detector composition, 10c prose-vs-impl) consumes this skill at review time.
- **`[`authoring-against-state`](../_authoring-against-state-rules.md)` authoring-against-state:6** — the step-2 knowledge-requirements enumeration IS the shape-space enumeration this skill formalizes. Shape-space audit at write time is authoring-against-state's step 2 applied to external-shape-modeling code.

## Canonical fix work-item

When a shape-space audit surfaces uncovered shapes in a scanner that ships as-is, the audit result is not the fix — a work-item ticket is. `siege-analytics/claude-configs-public#827` (PR D: repair R11 Python scanner shape-space gaps) is the canonical example of a shape-space-audit-driven fix ticket. Its acceptance criteria bake in this skill's discipline: failing-then-passing fixtures per named shape, external-idiom evidence from real code, no context-free-grep-only coverage claims.

## Attribution

Named pattern P6 ("context-free grep is not shape evidence") originated in the R11-meta remediation consensus between coordinator session `260525-long-swan` and reviewer session `260905-clever-quasar` (Siege Skills Revision) on 2026-09-07 during the PR B/C sequencing thread. Recorded here as the canonical named-pattern reference; also referenced from `writing-code:8`'s shape-space coverage table preamble and from `siege-analytics/claude-configs-public#827`'s acceptance criteria.

Defers to `[`output`](../_output-rules.md)`. No AI / agent attribution.
