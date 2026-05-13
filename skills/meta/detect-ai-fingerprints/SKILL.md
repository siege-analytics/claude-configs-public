---
name: detect-ai-fingerprints
description: "Mechanical scanner for stylistic AI fingerprints (rules 1-6 of [rule:no-ai-fingerprints]) in staged diffs, working-tree diffs, GitHub PR diffs, or commit/PR message bodies. Reports file:line violations and a 0/1 exit code. Structural rules 7-11 require [skill:code-review] judgment and are not in scope."
disable-model-invocation: false
allowed-tools: Bash Read
argument-hint: "[--pr <n> | --working | --message <text> | --message-file <path>]"
---

# Detect AI Fingerprints

Mechanical pre-flight scan for the stylistic rules in `[rule:no-ai-fingerprints]`. Catches what a human reviewer reliably misses on a long diff: em-dashes, banned adverbs, structured rationale blocks in commit messages, bullets and headers in commit bodies, history references in code comments. Structural rules 7-11 (vacuous tests, cargo-culted patterns, speculative abstractions, asserting non-existent symbols, scope-of-fix) are not mechanically detectable and stay in `[skill:code-review]`.

## When to invoke

The scanner runs as a sub-routine of three callers:

1. `[skill:commit]` step 3 (pre-review gate): scan the staged diff and the proposed commit message before code-review starts. Block the commit on violations.
2. `[skill:code-review]` start: scan the diff under review (staged or PR). Surface violations as findings before the six-layer human review begins, so attention is not wasted on em-dash hunting.
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

Production gates (`[skill:commit]` step 3, `[skill:code-review]` start) do **not** pass `--ignore`. The flag is for ad-hoc inspection and for the bootstrap commit that lands changes to the scanner itself. Using it elsewhere is a smell: if you find yourself excluding paths to make the scanner shut up, the rules are firing for a reason.

## Output format

Each violation is a single line:

```
<file>:<line>:<rule-id>: <excerpt>
```

The `<rule-id>` names which rule fired and (where useful) the offending token in parentheses. Example output from a real run:

```
sample.py:2:rule-4-adverb(crucially):     """Say hello -- crucially, this function returns nothing notably useful."""
sample.py:2:rule-4-adverb(notably):     """Say hello -- crucially, this function returns nothing notably useful."""
COMMIT_EDITMSG:5:rule-5-header: ## Summary
COMMIT_EDITMSG:6:rule-5-bullet: - thing one

scanned with rules 1-6 of [rule:no-ai-fingerprints]; rules 7-11 require [skill:code-review] judgment.
violations: 4
```

The trailing reminder is not decoration. It exists so a clean scan does not get mistaken for a clean review.

## What the scanner covers

- **Rule 1 (em-dashes U+2014 and en-dashes U+2013)** anywhere in added lines or message bodies
- **Rule 2 (`Why:` / `How to apply:` structured blocks)** in commit/PR message bodies. Heuristic: line beginning with `Why:` or `## Why` or `**Why:**` etc.
- **Rule 4 (banned adverbs)**: `deliberately`, `intentionally`, `explicitly`, `fundamentally`, `essentially`, `crucially`, `notably`. Every match per line is reported.
- **Rule 5 (bullets and `##` headers)** in commit message bodies. Subject line is exempt; first blank line is skipped.
- **Rule 6 (history references)**: `PR #N`, `Sprint X`, `vN.N.N hardening`, `issue #N`, `TICKET-N` in lines that look like code comments (start with `#` or `//`).
- **Rule 13 (countable claims)** in commit/PR message bodies. Trigger phrases: "all N", "all X engines/connectors/call sites", "every (call site/engine/caller/connector)", "no remaining", "fully covers", "completes the X surface". When a trigger fires, the body must contain a `Verified-by: <command output excerpt>` trailer. Without the trailer, the claim line is reported.
- **Rule 15 (skip messages)** in `.py` files. Pattern: `pytest.skip(...)`, `pytest.xfail(...)`, `@pytest.mark.skipif(...)`, `self.skipTest(...)`, `unittest.skip(...)`. The skip message must contain at least one actionable verb (`install`, `set`, `configure`, `run`, `enable`, `start`, `provide`, `export`) plus an identifier-shaped token (env var, command name, file path, package name). Without both, the line is reported.

## What the scanner does NOT cover

- Rule 3 (multi-paragraph docstrings on internal helpers): requires distinguishing public from internal API, which the scanner cannot do mechanically.
- Rules 7-12, 14, 16, 17, 18 (structural): require judgment about test fidelity, cargo-culted patterns, speculative abstractions, symbol existence, scope-of-fix, dependency reachability, public-surface diffs, mock fidelity, doc-edit symmetry, and silent error swallowing. These belong in `[skill:code-review]` and (for rule 12) `[skill:commit]` step 4 (the affected-tests gate).

A clean scan does not mean clean code. It means the mechanical checks passed. The judgment checks still need a reviewer.

## False positives

The scanner is literal by design. Some legitimate uses will trip rules:

- **Rule 4 in test fixtures or rule files that quote the banned words.** The new-rule file `_no-ai-fingerprints-rules.md` itself lists the words in rule 4; the scanner will report it. Acceptable because the rule file is the one place those words have to appear.
- **Rule 4 in this scanner's own regex source** (`scan.sh`'s `ADVERBS_RE` constant). Same reason as above: the regex defines the rule, so the words have to be in the file.
- **Rule 4 and rule 1 in this skill's worked examples below.** Quoted scanner output and example violations include the banned content by design.
- **Rule 6 in references that point at history on purpose.** A migration note that says "see PR #1234 for the original schema" is technically a history reference. If the reference is load-bearing for the code's behaviour, replace it with the behaviour itself; if it is not, delete it.

There is no override flag in the scanner. Address the violation or accept that it will be reported on every scan.

## Worked examples

### Clean staged diff

```
$ bash skills/meta/detect-ai-fingerprints/scan.sh
clean (rules 1-6); rules 7-11 still require [skill:code-review] judgment.
$ echo $?
0
```

### Dirty staged diff blocking a commit

```
$ bash skills/meta/detect-ai-fingerprints/scan.sh
src/parser.py:42:rule-4-adverb(deliberately):     # We deliberately drop NULLs here

scanned with rules 1-6 of [rule:no-ai-fingerprints]; rules 7-11 require [skill:code-review] judgment.
violations: 1
$ echo $?
1
```

The `[skill:commit]` pre-review gate checks the exit code; non-zero stops the commit until the violation is fixed.

### Scanning a PR before review

```
$ bash skills/meta/detect-ai-fingerprints/scan.sh --pr 43
src/transforms/silver.py:118:rule-1-em-dash: # Cast to StringType — the FEC IDs need leading zeros
src/transforms/silver.py:118:rule-4-adverb(explicitly):   ...
violations: 2
```

Reviewer addresses these before opening the six-layer human review.

## Implementation notes

The scanner is plain bash to keep dependencies minimal: no Python, no node, no jq. It uses `git diff` and `gh pr diff` for input, parses unified-diff hunk headers to track line numbers, and pipes through `grep -oE` for pattern matches. See `scan.sh` for the source; the file is small and reads top to bottom.

The diff parser handles only added lines (`+` prefix in unified diff), not removed or context lines, so existing-but-untouched fingerprints elsewhere in the file are not flagged. Rule violations are introduced by the diff under review or they are not introduced at all.

## Cross-references

- `[rule:no-ai-fingerprints]` is the rule this skill enforces. Rules 1-6 are mechanically scanned; rules 7-11 are not.
- `[skill:commit]` calls this skill in step 3 (pre-review gate). A non-zero exit blocks the commit.
- `[skill:code-review]` calls this skill at the start of the review pass. Findings prefix the six-layer review.

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in scanner output, in commits that follow it, or anywhere else.
