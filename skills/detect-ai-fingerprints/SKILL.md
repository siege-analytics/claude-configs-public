---
name: detect-ai-fingerprints
description: "Mechanical scanner for AI-fingerprint rules across the per-act rule files. Covers writing-prose:1-4, writing-code:2, writing-tests:3-4, writing-claims:2-3, writing-releases:2 in staged diffs, working-tree diffs, GitHub PR diffs, or commit/PR message bodies. Reports file:line violations and a 0/1 exit code. The remaining rules require [`code-review`](../code-review/SKILL.md) judgment and are not in scope."
disable-model-invocation: false
allowed-tools: Bash Read
argument-hint: "[--pr <n> | --working | --message <text> | --message-file <path>]"
---

# Detect AI Fingerprints

Mechanical pre-flight scan for the AI-fingerprint rules across the per-act rule files. Catches what a human reviewer reliably misses on a long diff: em-dashes, banned adverbs, structured rationale blocks in commit messages, bullets and headers in commit bodies, history references in code comments, countable / completeness claims missing the `Verified-by:` trailer, skip messages without actionable remediation, mocks instantiated without `spec=`. The structural rules (vacuous tests, cargo-culted patterns, speculative abstractions, asserting non-existent symbols, scope-of-fix, hypothetical code, doc-edit symmetry, silent error swallowing, untested exception handlers, conditional-import callsite hygiene, BREAKING-changelog determination) are not mechanically detectable and stay in `[`code-review`](../code-review/SKILL.md)` and (for `[`writing-code`](../_writing-code-rules.md)` writing-code:5) `[`commit`](../commit/SKILL.md)` step 4.

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
bash <this-skill-dir>/scan.sh --message-file /tmp/COMMIT_EDITMSG
```

Exit code is 0 when clean, 1 when any violation is found, 2 on usage error.

### Path filter

`--ignore <glob>` (repeatable) skips files matching the glob. The narrow legitimate use is scanning the scanner's own definition files, which contain the rule source, the regex, and the worked examples by design:

```bash
bash <this-skill-dir>/scan.sh --ignore 'skills/meta/detect-ai-fingerprints/*'
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

scanned: writing-prose:1-4 (stylistic), writing-code:2 (history references in code comments), writing-tests:3-4 (skip messages, mock-without-spec), writing-claims:2-3 (countable claims and completeness claims need Verified-by trailer), writing-releases:2 (skip-count trending). The rest require [`code-review`](../code-review/SKILL.md) judgment.
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
- **`[`writing-tests`](../_writing-tests-rules.md)` writing-tests:4** mock-without-spec sub-check: `MagicMock()` / `Mock()` without `spec=<RealClass>` or `spec_set=<RealClass>` or an explicit `# noqa: writing-tests:4-spec` rationale.
- **`[`writing-claims`](../_writing-claims-rules.md)` writing-claims:2** (countable claims) in commit/PR message bodies. Trigger phrases: "all N", "all X engines/connectors/call sites", "every (call site/engine/caller/connector)", "no remaining", "fully covers", "completes the X surface". When a trigger fires, the body must contain a `Verified-by: <command output excerpt>` trailer.
- **`[`writing-claims`](../_writing-claims-rules.md)` writing-claims:3** (completeness claims): extends the writing-claims:2 trigger set to unquantified phrases ("I have completed", "addressed all", "ready to ship", "loop closed"). Same `Verified-by:` trailer requirement.
- **`[`writing-releases`](../_writing-releases-rules.md)` writing-releases:2** (skip-count trending) in `--pr <n>` mode: counts new `pytest.skip(...)` / `@pytest.mark.skipif(...)` / `@pytest.mark.skip(...)` sites in the PR diff and requires a `New-skip: <count>; <reason>` trailer when the count increased.

## What the scanner does NOT cover

- `[`writing-code`](../_writing-code-rules.md)` writing-code:1 (multi-paragraph docstrings on internal helpers): requires distinguishing public from internal API, which the scanner cannot do mechanically without project-namespace and `__all__` detection.
- `[`writing-code`](../_writing-code-rules.md)` writing-code:3, :4, :5, :6, :7, :8; `[`writing-tests`](../_writing-tests-rules.md)` writing-tests:1, :2, :5; `[`writing-claims`](../_writing-claims-rules.md)` writing-claims:1; `[`writing-releases`](../_writing-releases-rules.md)` writing-releases:1: judgment-bound. These belong in `[`code-review`](../code-review/SKILL.md)` and (for `[`writing-code`](../_writing-code-rules.md)` writing-code:5) `[`commit`](../commit/SKILL.md)` step 4 (the affected-tests gate). See `_coverage.md` for the per-rule prevention-path noting what tooling would mechanize each judgment row.

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
$ bash skills/meta/detect-ai-fingerprints/scan.sh
clean. scanned: writing-prose:1-4 (stylistic), writing-code:2 (history references in code comments), writing-tests:3-4 (skip messages, mock-without-spec), writing-claims:2-3 (countable / completeness claims), writing-releases:2 (skip-count trending). The rest require [`code-review`](../code-review/SKILL.md) judgment.
$ echo $?
0
```

### Dirty staged diff blocking a commit

```
$ bash skills/meta/detect-ai-fingerprints/scan.sh
src/parser.py:42:writing-prose-3-adverb(deliberately):     # We deliberately drop NULLs here

scanned: writing-prose:1-4 (stylistic), writing-code:2 (history references in code comments), writing-tests:3-4 (skip messages, mock-without-spec), writing-claims:2-3 (countable / completeness claims), writing-releases:2 (skip-count trending). The rest require [`code-review`](../code-review/SKILL.md) judgment.
violations: 1
$ echo $?
1
```

The `[`commit`](../commit/SKILL.md)` pre-review gate checks the exit code; non-zero stops the commit until the violation is fixed.

### Scanning a PR before review

```
$ bash skills/meta/detect-ai-fingerprints/scan.sh --pr 43
src/transforms/silver.py:118:writing-prose-1-em-dash: # Cast to StringType — the FEC IDs need leading zeros
src/transforms/silver.py:118:writing-prose-3-adverb(explicitly):   ...
violations: 2
```

Reviewer addresses these before opening the six-layer human review.

## Implementation notes

The scanner is plain bash to keep dependencies minimal: no Python, no node, no jq. It uses `git diff` and `gh pr diff` for input, parses unified-diff hunk headers to track line numbers, and pipes through `grep -oE` for pattern matches. See `scan.sh` for the source; the file is small and reads top to bottom.

The diff parser handles only added lines (`+` prefix in unified diff), not removed or context lines, so existing-but-untouched fingerprints elsewhere in the file are not flagged. Rule violations are introduced by the diff under review or they are not introduced at all.

## Cross-references

- The per-act rule files `[`writing-prose`](../_writing-prose-rules.md)`, `[`writing-code`](../_writing-code-rules.md)`, `[`writing-tests`](../_writing-tests-rules.md)`, `[`writing-claims`](../_writing-claims-rules.md)`, `[`writing-releases`](../_writing-releases-rules.md)` are the rules this skill enforces. Mechanical coverage is enumerated in "What the scanner covers" above; everything else requires `[`code-review`](../code-review/SKILL.md)` judgment. See `_coverage.md` for the per-rule prevention-path that names what tooling would mechanize each judgment row.
- `[`commit`](../commit/SKILL.md)` calls this skill in step 3 (pre-review gate). A non-zero exit blocks the commit.
- `[`code-review`](../code-review/SKILL.md)` calls this skill at the start of the review pass. Findings prefix the six-layer review.

## Attribution

Defers to `[`output`](../_output-rules.md)`. No AI / agent attribution in scanner output, in commits that follow it, or anywhere else.
