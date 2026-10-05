---
name: detect-ai-fingerprints
description: "Mechanical scanner for AI-fingerprint rules across the per-act rule files. Covers writing-prose:1-4, writing-code:2/4/7/8/9/15, writing-tests:3/5, writing-claims:2, writing-releases:3, plus rule-citation Rule-executed evidence, in staged diffs, working-tree diffs, GitHub PR diffs, or commit/PR message bodies. Reports file:line violations and a 0/1 exit code. Remaining rules require [`code-review`](../code-review/SKILL.md) judgment and are not in scope."
allowed-tools: Bash Read
---

# Detect AI Fingerprints

Mechanical pre-flight scan for the AI-fingerprint rules across the per-act rule files. Catches what a human reviewer reliably misses on a long diff:

**Prose-side (scan.sh regex):** em-dashes and broader typographic Unicode, banned adverbs, structured `Why:` / `How to apply:` rationale blocks in commit messages, bullets and `##` headers in commit bodies, history references in code comments, countable claims missing the `Verified-by:` trailer, rule citations missing the `Rule-executed:` evidence trailer, skip messages without actionable remediation.

**Code-side (scan_ast.py AST scanner):** Django ORM kwarg validation against same-file models (writing-code:4), silent exception swallowing (writing-code:7), optional-import callsite guards (writing-code:8), silently-dropped defaulted parameters (writing-code:9), unbounded blocking I/O without timeout (writing-code:15), untested named exception handlers cross-file (writing-tests:5), deprecation messages missing removal anchor + keyword (writing-releases:3). Includes 10 dedicated test files with ~140 fixtures total.

The remaining structural rules — vacuous tests (writing-tests:1), cargo-culted patterns (writing-tests:2), speculative abstractions (writing-code:3), asserting non-existent symbols (writing-code:4-broader), scope-of-fix (writing-claims:1), hypothetical code (writing-code:5), doc-edit symmetry (writing-code:6), unquantified completeness claims (writing-claims:3), BREAKING-changelog determination (writing-releases:1), skip-count trending (writing-releases:2), mock-without-spec (writing-tests:4) — remain judgment-bound and stay in `[`code-review`](../code-review/SKILL.md)` and (for `[`writing-code`](../_writing-code-rules.md)` writing-code:5) `[`commit`](../commit/SKILL.md)` step 4 (the affected-tests gate).

## When to invoke

The scanner runs as a sub-routine of three callers:

1. `[`commit`](../commit/SKILL.md)` step 3 (pre-review gate): scan the staged diff and the proposed commit message before code-review starts. Block the commit on violations.
2. `[`code-review`](../code-review/SKILL.md)` start: scan the diff under review (staged or PR). Surface violations as findings before the six-layer human review begins, so attention is not wasted on em-dash hunting.
3. Direct invocation as `/detect-ai-fingerprints` for ad-hoc use (PR triage, post-merge spot checks, scanning your own draft before committing).

## Invocation

The scanner lives at `<this-skill-dir>/scan.sh`.

```bash
# Scan staged diff (default)
bash <this-skill-dir>/scan.sh

# Scan working-tree diff (uncommitted, unstaged changes)
bash <this-skill-dir>/scan.sh --working

# Scan a GitHub PR diff
bash <this-skill-dir>/scan.sh --pr 43

# Scan a commit/PR message body from text
bash <this-skill-dir>/scan.sh --message "fix: bad

This commit changes line 48 -- crucially the leading zeros are preserved."

# Scan a message body from a file
bash <this-skill-dir>/scan.sh --message-file /tmp/message-body.txt

# Scan a full commit message from a file; line 1 subject is exempt
bash <this-skill-dir>/scan.sh --commit-message-file /tmp/COMMIT_EDITMSG
```

Exit code is 0 when clean, 1 when any violation is found, 2 on usage error.

### Path filter

`--ignore <glob>` (repeatable) skips files matching the glob. The narrow legitimate use is scanning the scanner's own definition files, which contain the rule source, the regex, and the worked examples by design:

```bash
bash <this-skill-dir>/scan.sh --ignore 'skills/detect-ai-fingerprints/*'
```

Production gates (`[`commit`](../commit/SKILL.md)` step 3, `[`code-review`](../code-review/SKILL.md)` start) do **not** pass `--ignore`. The flag is for ad-hoc inspection and for the bootstrap commit that lands changes to the scanner itself. Using it elsewhere is a smell: if you find yourself excluding paths to make the scanner shut up, the rules are firing for a reason.

## Output format

Each violation is a single line:

```
<file>:<line>:<rule-id>: <excerpt>
```

The `<rule-id>` names which rule fired and (where useful) the offending token in parentheses. Example output from a real run:

```
sample.py:2:writing-prose-3-adverb(crucially):     """Say hello -- crucially, this function returns nothing notably useful."""
sample.py:2:writing-prose-3-adverb(notably):     """Say hello -- crucially, this function returns nothing notably useful."""
COMMIT_EDITMSG:5:writing-prose-4-header: ## Summary
COMMIT_EDITMSG:6:writing-prose-4-bullet: - thing one

scanned: writing-prose:1-4 (stylistic; broader Unicode class), writing-code:2 (history references in code comments), writing-code:4 (Django ORM kwarg validation, same-file models; AST), writing-code:7 (silent error swallowing; AST), writing-code:8 (optional-import callsite guards; AST), writing-code:9 (silently-dropped parameters; AST scoped visitor), writing-code:15 (unbounded blocking I/O; AST, incl. Popen chains, Session/Client instance methods, invalid literal timeouts), writing-tests:3 (skip messages must be actionable), writing-tests:5 (untested named exception handlers, cross-file; AST), writing-claims:2 (countable claims need Verified-by trailer), rule citations in messages require Rule-executed evidence (#282), writing-releases:3 (deprecation messages need version+removal-keyword anchors; AST). Not mechanized (judgment-bound): writing-code:1/3/5/6, writing-tests:1/2/4, writing-claims:1/3, writing-releases:1/2.
violations: 4
```

The trailing reminder is not decoration. It exists so a clean scan does not get mistaken for a clean review.

## What the scanner covers

- **`[`writing-prose`](../_writing-prose-rules.md)` writing-prose:1** (em-dashes U+2014 and en-dashes U+2013) anywhere in added lines or message bodies.
- **`[`writing-prose`](../_writing-prose-rules.md)` writing-prose:2** (`Why:` / `How to apply:` structured blocks) in commit/PR message bodies. Heuristic: line beginning with `Why:` or `## Why` or `**Why:**` etc.
- **`[`writing-prose`](../_writing-prose-rules.md)` writing-prose:3** (banned adverbs): `deliberately`, `intentionally`, `explicitly`, `fundamentally`, `essentially`, `crucially`, `notably`. Every match per line is reported.
- **`[`writing-prose`](../_writing-prose-rules.md)` writing-prose:4** (bullets and `##` headers in commit-message bodies). Subject line is exempt; first blank line is skipped.
- **`[`writing-code`](../_writing-code-rules.md)` writing-code:2** (history references in code comments): `PR #N`, `Sprint X`, `vN.N.N hardening`, `issue #N`, `TICKET-N` in lines that look like code comments (start with `#` or `//`).
- **`[`writing-tests`](../_writing-tests-rules.md)` writing-tests:3** (skip messages in `.py` files): pattern `pytest.skip(...)`, `pytest.xfail(...)`, `@pytest.mark.skipif(...)`, `self.skipTest(...)`, `unittest.skip(...)`. The skip message must contain at least one actionable verb (`install`, `set`, `configure`, `run`, `enable`, `start`, `provide`, `export`) plus an identifier-shaped token (env var, command name, file path, package name). Without both, the line is reported.
- **`[`writing-claims`](../_writing-claims-rules.md)` writing-claims:2** (countable claims) in commit/PR message bodies. Trigger phrases: "all N", "all X engines/connectors/call sites", "every (call site/engine/caller/connector)", "no remaining", "fully covers", "completes the X surface". When a trigger fires, the body must contain a `Verified-by: <command output excerpt>` trailer.
- **Rule-citation execution guard** (#282) in commit/PR message bodies: citing a numbered rule ID such as `writing-code:19` or `writing-claims:2` requires a matching `Rule-executed: <rule-id> <artifact>` trailer. Citation is not compliance; the artifact pointer is the claim.
- **`[`writing-code`](../_writing-code-rules.md)` writing-code:4 -- Django ORM kwarg validation** (v1, same-file models). For each `<Model>.objects.<method>(...)` call where `<Model>` is a class defined IN THE SAME FILE with at least one `<X>Field(...)` attribute, the scanner verifies each direct kwarg key (and each key inside a `defaults={...}` or `create_defaults={...}` dict literal for `get_or_create` / `update_or_create`) maps to a declared field. Lookups like `field__gte` decompose to `field` before matching. Reports `writing-code-4-django-orm-kwarg(unknown-field)`. **Scope limitation:** cross-file model resolution is not in v1 -- calls referencing models imported from other modules are silently skipped.
- **`[`writing-code`](../_writing-code-rules.md)` writing-code:7 -- silent error swallowing** (AST scanner). Detects Pass / Return None / Return False / Continue / logging-call-plus-terminator / scaffold-plus-terminator (constant-value assign + terminator) inside `except` handlers. Carve-outs: `# noqa: writing-code-7 <category>` with a category keyword (cleanup, best-effort, atexit, signal, handler, ...); `Optional[T]`-return + docstring documenting `None` as failure; ImportError + availability-flag idiom (writing-code:8 territory).
- **`[`writing-code`](../_writing-code-rules.md)` writing-code:8 -- optional-import callsite hygiene** (AST scanner). Detects `try/except ImportError` optional-import patterns and flags every callsite of the imported name not guarded by the availability flag. Recognizes `if not FLAG: <raise/return>` early-return guards, `if FLAG: <body>` positive guards, private-helper docstrings with a caller-contract phrase, and the try-body itself (where the flag can't be false).
- **`[`writing-code`](../_writing-code-rules.md)` writing-code:9 -- silently-dropped parameters** (AST scanner). Function parameters with non-None defaults that are never Load-referenced in the function's own scope, not documented in the docstring, and not decorator-consumed. Scoped visitor (no nested-scope shadowing); `**locals()` escape hatch.
- **`[`writing-code`](../_writing-code-rules.md)` writing-code:15 -- unbounded blocking I/O** (AST scanner). Subprocess / requests / httpx / urllib / socket / sqlite3 calls without a `timeout=` kwarg. Handles aliased imports, bare-name from-imports, `Popen(...).communicate/wait` chains, `Popen(...).stdout.read()` pipe reads, `Session()/Client()/AsyncClient().<verb>` instance methods, and invalid literal timeouts (`timeout=0`, `timeout=False`, `timeout=()`, invalid tuple shapes). `timeout=None` requires an audit-signal comment.
- **`[`writing-tests`](../_writing-tests-rules.md)` writing-tests:5 -- untested named exception handlers** (AST scanner, cross-file). Every `except <Class>:` in a production file requires a matching `pytest.raises(<Class>)` / `assertRaises(<Class>)` / `raises(<Class>)` in the sibling test file (namespaced-layout aware). Recognizes `Optional[<Class>]` / `Union[<A>, <B>]` argument shapes, `except* <Class>:` (PEP 654 exception groups), and short-name matches for dotted exception classes. Carve-outs: `# noqa: writing-tests-5 <category>` with a controlled-vocabulary category keyword; test-path exemption for source files.
- **`[`writing-releases`](../_writing-releases-rules.md)` writing-releases:3 -- deprecation message format** (AST scanner). `DeprecationWarning(...)`, `PendingDeprecationWarning(...)`, and `warnings.warn(..., DeprecationWarning)` messages must contain BOTH a version-or-date anchor (`vN.N.N` or `YYYY-MM-DD`) AND a removal-commitment keyword (`remove`, `removed`, `dropped`, `slated for`, `target`, `EOL`). Handles implicit string-literal concatenation.

## What the scanner does NOT cover

- `[`writing-code`](../_writing-code-rules.md)` writing-code:1 (multi-paragraph docstrings on internal helpers): requires distinguishing public from internal API, which the scanner cannot do mechanically without project-namespace and `__all__` detection.
- `[`writing-code`](../_writing-code-rules.md)` writing-code:3, :5, :6; `[`writing-tests`](../_writing-tests-rules.md)` writing-tests:1, :2, :4; `[`writing-claims`](../_writing-claims-rules.md)` writing-claims:1, :3; `[`writing-releases`](../_writing-releases-rules.md)` writing-releases:1, :2: judgment-bound. writing-tests:4 (mock-without-spec), writing-releases:2 (skip-count trending), and writing-claims:3 (unquantified completeness claims) are candidates for mechanization but not currently implemented. These belong in `[`code-review`](../code-review/SKILL.md)` and (for `[`writing-code`](../_writing-code-rules.md)` writing-code:5) `[`commit`](../commit/SKILL.md)` step 4 (the affected-tests gate). See `_coverage.md` for the per-rule prevention-path noting what tooling would mechanize each judgment row.

A clean scan does not mean clean code. It means the mechanical checks passed. The judgment checks still need a reviewer.

## False positives

The scanner is literal by design. Some legitimate uses will trip rules:

- **writing-prose:3 in test fixtures or rule files that quote the banned words.** `_writing-prose-rules.md` itself lists the words in writing-prose:3; the scanner will report it. Acceptable because the rule file is the one place those words have to appear.
- **writing-prose:3 in this scanner's own regex source** (`scan.sh`'s `ADVERBS_RE` constant). Same reason: the regex defines the rule, so the words have to be in the file.
- **writing-prose:3 and writing-prose:1 in this skill's worked examples below.** Quoted scanner output and example violations include the banned content by design.
- **writing-prose:3 in `_coverage.md`** (the description field for the self-justifying-adverbs failure-mode entry quotes the banned words). Same documented-false-positive class.
- **writing-code:2 in references that point at history on purpose.** A migration note that says "see PR #1234 for the original schema" is technically a history reference. If the reference is load-bearing for the code's behaviour, replace it with the behaviour itself; if it is not, delete it.

There is no override flag in the scanner. Address the violation or accept that it will be reported on every scan.

## Worked examples

### Clean staged diff

```
$ bash skills/detect-ai-fingerprints/scan.sh
clean. scanned: writing-prose:1-4 (stylistic; broader Unicode class), writing-code:2 (history references in code comments), writing-code:4 (Django ORM kwarg validation, same-file models; AST), writing-code:7 (silent error swallowing; AST), writing-code:8 (optional-import callsite guards; AST), writing-code:9 (silently-dropped parameters; AST scoped visitor), writing-code:15 (unbounded blocking I/O; AST), writing-tests:3 (skip messages must be actionable), writing-tests:5 (untested named exception handlers, cross-file; AST), writing-claims:2 (countable claims need Verified-by trailer), rule citations in messages require Rule-executed evidence (#282), writing-releases:3 (deprecation messages need version+removal-keyword anchors; AST). Not mechanized (judgment-bound): writing-code:1/3/5/6, writing-tests:1/2/4, writing-claims:1/3, writing-releases:1/2.
$ echo $?
0
```

### Dirty staged diff blocking a commit

```
$ bash skills/detect-ai-fingerprints/scan.sh
src/parser.py:42:writing-prose-3-adverb(deliberately):     # We deliberately drop NULLs here

scanned: writing-prose:1-4 (stylistic; broader Unicode class), writing-code:2 (history references in code comments), writing-code:4 (Django ORM kwarg validation, same-file models; AST), writing-code:7 (silent error swallowing; AST), writing-code:8 (optional-import callsite guards; AST), writing-code:9 (silently-dropped parameters; AST scoped visitor), writing-code:15 (unbounded blocking I/O; AST), writing-tests:3 (skip messages must be actionable), writing-tests:5 (untested named exception handlers, cross-file; AST), writing-claims:2 (countable claims need Verified-by trailer), rule citations in messages require Rule-executed evidence (#282), writing-releases:3 (deprecation messages need version+removal-keyword anchors; AST). Not mechanized (judgment-bound): writing-code:1/3/5/6, writing-tests:1/2/4, writing-claims:1/3, writing-releases:1/2.
violations: 1
$ echo $?
1
```

The `[`commit`](../commit/SKILL.md)` pre-review gate checks the exit code; non-zero stops the commit until the violation is fixed.

### Scanning a PR before review

```
$ bash skills/detect-ai-fingerprints/scan.sh --pr 43
src/transforms/silver.py:118:writing-prose-1-em-dash: # Cast to StringType -- the FEC IDs need leading zeros
src/transforms/silver.py:118:writing-prose-3-adverb(explicitly):   ...
violations: 2
```

Reviewer addresses these before opening the six-layer human review.

## Implementation notes

The scanner has two layers: `scan.sh` (bash + `grep -oE`) parses unified diffs and message bodies for the prose-side rules; `scan_ast.py` (Python AST) is invoked by `scan.sh` on any changed `.py` files for the code-side rules. Prose/regex checks are added-line and message-body scoped (they read the diff hunks only). AST checks scan the full post-state file for each changed `.py`, so pre-existing violations in a touched file surface alongside newly-added ones. See `scan.sh` and `scan_ast.py` for the sources; both are readable top to bottom.

The diff parser handles only added lines (`+` prefix in unified diff), not removed or context lines, so existing-but-untouched fingerprints elsewhere in the file are not flagged. Rule violations are introduced by the diff under review or they are not introduced at all.

## Cross-references

- The per-act rule files `[`writing-prose`](../_writing-prose-rules.md)`, `[`writing-code`](../_writing-code-rules.md)`, `[`writing-tests`](../_writing-tests-rules.md)`, `[`writing-claims`](../_writing-claims-rules.md)`, `[`writing-releases`](../_writing-releases-rules.md)` are the rules this skill enforces. Mechanical coverage is enumerated in "What the scanner covers" above; everything else requires `[`code-review`](../code-review/SKILL.md)` judgment. See `_coverage.md` for the per-rule prevention-path that names what tooling would mechanize each judgment row.
- `[`commit`](../commit/SKILL.md)` calls this skill in step 3 (pre-review gate). A non-zero exit blocks the commit.
- `[`code-review`](../code-review/SKILL.md)` calls this skill at the start of the review pass. Findings prefix the six-layer review.

## Attribution

Defers to `[`output`](../_output-rules.md)`. No AI / agent attribution in scanner output, in commits that follow it, or anywhere else.
