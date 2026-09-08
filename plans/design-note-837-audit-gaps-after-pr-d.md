# Design note: scanner and hook audit gaps after PR D

Issue: siege-analytics/claude-configs-public#837

## Goal

Repair four concrete audit gaps found after the PR D scanner work:

1. `pr-base-guard` must not read `--base`, `--head`, or bypass labels from quoted body text.
2. `detect-ai-fingerprints` body-only message scans must inspect the first body line.
3. `writing-code:8` must keep optional-import try bodies safe when the success flag is assigned in `else`.
4. Review and coverage docs must route reviewers to the real scanner path and current scanner coverage.

Two small scanner invocation repairs are included because validation found `scan.sh --working` on a changed Python file emitted `config_arg[@]: unbound variable` when no scanner config existed, and the documented scanner-self `--ignore` still processed ignored diff lines before suppressing emission. Both defects are in the same scanner path; the empty-config case has a focused fixture.

## Pre-author inventory

Inputs read before changes:

- `AGENTS.md` and `CLAUDE.md` workspace rules.
- `skills/detect-ai-fingerprints/SKILL.md` scanner contract.
- `skills/detect-ai-fingerprints/scan.sh` and `scan_ast.py` on main and develop.
- `hooks/git/pr-base-guard.sh` and `hooks/git/detect-ai-fingerprints.sh`.
- Existing fixtures under `skills/detect-ai-fingerprints/test_*.sh` and `hooks/_test/pr_base_guard.test.sh`.
- Recent PR D artifacts and commit messages for #827, #835, and #836.

Open questions resolved:

- The shelf skill references in `skills/code-review/SKILL.md` use `shelves--<slug>` because `bin/build.py` names nested shelf skills that way. No routing change is needed there.
- The broken review-routing path is the scanner command path, not the shelf slug format.
- `--message` and `--message-file` are documented as body-only inputs. The commit hook passes full commit messages, so the scanner needs a separate full-message mode to keep subject-line exemption.

## Failing-first evidence

Before repairs, new fixtures or probes showed:

- `hooks/_test/pr_base_guard.test.sh`: quoted PR body text containing `--base main` caused a real `--base develop` command to block as main-targeting.
- `skills/detect-ai-fingerprints/test_rule_citations.sh`: a body-only file whose first line is `Why:` passed clean because `scan_message_stdin` skipped line 1 as a subject.
- `skills/detect-ai-fingerprints/test_writing_code_8.sh`: try-body setup under a try/except/else availability flag fired `writing-code-8` on the setup call.
- `bash skills/detect-ai-fingerprints/scan.sh --working`: changed Python files with no `.claude/scanner-config.toml` produced an empty-array `set -u` error.

## Implementation

- `hooks/git/pr-base-guard.sh` now parses base, head, source-branch, target-branch, and bypass label flags from `COMMAND_UNQUOTED`, the same quote-stripped command surface used for trigger detection.
- `scan.sh` now treats `--message` and `--message-file` as body-only input and scans line 1. A new `--commit-message-file` mode scans full commit messages while skipping the subject and conventional blank separator.
- `hooks/git/detect-ai-fingerprints.sh` calls `--commit-message-file` so push and PR hooks keep commit-subject exemption.
- `scan_ast.py` treats a Try node as an optional-import safe region when a tracked flag is assigned in either the try body or the else body, while still only skipping the try body range.
- `skills/code-review/SKILL.md`, `skills/_coverage.md`, and `skills/detect-ai-fingerprints/SKILL.md` now match the current scanner implementation.
- `scan.sh` avoids empty-array expansion for `config_arg` under Bash 3.2.
- `scan.sh --ignore` now skips ignored added lines before regex processing instead of only suppressing emitted violations.

## Bounded exclusions

- No new docs consistency test was added. Existing `bin/sync-skill-references.py --check` validates reference slugs and `bin/build.py --check` validates the build surface, but there is no small existing test that can prove prose coverage paragraphs match scanner output without building a brittle text mirror.
- Deferred optional-import shapes in the writing-code:8 shape table stay deferred.
- No main branch changes and no direct pushes to protected branches.
