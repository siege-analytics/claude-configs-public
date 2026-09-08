# Hostile review: scanner and hook audit gaps after PR D

Issue: siege-analytics/claude-configs-public#837

## Review stance

Read the diff as a reviewer looking for regressions in enforcement routing, scanner coverage claims, and hook bypasses.

## Findings checked

### 1. Quoted command text can still affect PR routing

Risk: quote stripping only at trigger detection would let `--base main` inside a PR body or title override the actual CLI base.

Result: fixed. The hook now parses base/head/source/target/bypass flags from the same quote-stripped command surface. Regression `(af2)` covers a `gh pr create` command with quoted body text containing `--base main` and a real `--base develop` flag.

Residual risk: branch names wrapped in quotes are not parsed by the existing regex. That was already true for several paths and is not expanded here.

### 2. Body-only message scans skip line 1

Risk: PR body scanners and ad-hoc message scans miss first-line `Why:` blocks, banned words, countable claims, and rule citations.

Result: fixed. Body-only modes scan from line 1. Full commit-message mode is separate, and the commit hook uses it to keep subject exemption.

Residual risk: callers that were passing a full commit message through `--message-file` now get line 1 scanned. The repository hook was updated; external ad-hoc callers should use `--commit-message-file` for full commit messages.

### 3. writing-code:8 try/except/else safe region

Risk: the #827 else-flag support paired the optional import but did not mark the try body safe, causing setup calls inside the import-success try body to fire as unguarded.

Result: fixed. `visit_Try` now classifies a Try as tracked if a tracked flag assignment appears in the try body or else body, then skips only the try body range. The new `(z6b)` fixture covers try-body setup plus a guarded public call.

Residual risk: deferred shapes in the writing-code:8 shape table remain deferred: annotated flag assignment, star import pollution, nested try, conditional imports inside the try body, and cross-block shadowing.

### 4. Docs can route reviewers wrong

Risk: code-review pointed at a missing scanner path and stale coverage claims, causing reviewers to skip live scanner surfaces or expect nonexistent ones.

Result: fixed. The code-review command points to `skills/detect-ai-fingerprints/scan.sh`. Coverage rows now align with scanner output: writing-code:8 and writing-tests:5 are mechanical; writing-tests:4 mock-without-spec, writing-claims:3, and writing-releases:2 are judgment rows with prevention paths.

Residual risk: no new prose consistency test was added because the existing test surface validates references and build layout, not natural-language coverage matrices.

### 5. Scanner self-validation found empty config array bug

Risk: on Bash 3.2, a changed Python file with no scanner config could emit `config_arg[@]: unbound variable` and skip AST scanning.

Result: fixed with a conditional invocation path, plus a temp-git fixture in `test_scan_sh_exit_code.sh`. The documented scanner-self `--ignore` path also now skips ignored added lines before regex work, so ignored scanner fixtures are not processed before emission is suppressed.

## Shelf-readiness and routing

- Shelf references in `skills/code-review/SKILL.md` were checked against `bin/build.py` slug rules. The `shelves--<slug>` form is valid for nested shelf skills.
- No shelf router files needed edits.
- The changed code-review scanner path now resolves to an existing file in source layout.

## Verdict

No blocker found after the targeted validation suite. The only noted residual risks are existing scope limits or external caller migration to the new full-message flag.
