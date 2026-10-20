---
ticket_refs:
  - siege-analytics/claude-configs-public#1087: classifier and legacy safelist admit git remote/tag/config writes, date, printf -v, --ext-diff, option-word globs
---

# Self-review: #1087 close the classifier holes found by #1055's fixtures

## Assumptions

Pre-author-inventory: on develop 9391930, with no task gate, the gate allowed `git remote -v add|set-url`, `git tag v1.0`, `git tag --list -a x`, `git config --list --add`, `date 10182300`, `printf -vNAME`, `printf -v PATH /tmp/x; ls`, `git log --ext-diff` and `rg foo --pre*=evil`. Each was observed with the gate harness.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1087
Pre-mortem-artifact: plans/pre-mortem-1087-classifier-holes.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1055
Project-contribution: closes no-gate write and execute paths in every consumer workspace, including the remote-URL rewrite and the PATH reassignment.

- The hostile review is #1055's adversarial fixture suite (`hooks/_test/task_keyed_gates.py`, from three hostile-review rounds on #1055). Running it against the released classifier is what found these holes.
- `printf` leaves the plain verbs and is checked explicitly.

## Peer review

- **writing-code:**
  - `git_ok` handles remote, tag and config writes, and rejects `--ext-diff`/`--help` for every subcommand.
  - `unsafe()` vetoes the same forms.
  - `date_sets` and `printf_unsafe` are new.
  - The expansion scanner now flags a glob inside a word that starts with `-`.
- **writing-tests:** `read_allowlist` passes 231/231 here and fails 18 cases on develop.
- **Gate evidence:**
  - every hook suite passes, 38/38 after `bin/build.py`;
  - review_risk_test PASS;
  - metrics and generated-source-authority current.
- **Replay:** 2,845 commands, in both states: 0 verdict changes.

## Lead review

- **Solves #1087:** yes. Every listed command blocks with no gate.
- **Out of scope:** #1055's stricter glob policy for plain readers. `ls *.md` and `grep -n foo *.py` stay reads, matching the NEW-1 finding on #1055.

## Quantified claims

- New must-block cases: 18, and all fail on develop.
- New allow cases: 16.
- Replay verdict changes: 0.
