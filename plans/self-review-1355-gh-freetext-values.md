---
ticket_refs:
  - siege-analytics/claude-configs-public#1355: tests first; pre-implementation artifacts and design review to be posted before any runtime edit
  - siege-analytics/claude-configs-public#1347: shared parser (PR #1356), merged into this branch before the runtime edit
---
# Self-review: gh free-text option values are not local mutation targets

Task: siege-analytics/claude-configs-public#1355
Review-Tier: C for the runtime change in `hooks/lib/task_actions.py` (enforcement code). The first commit is tests only (Tier B).

## Assumptions

Goal source: #1355
Working as: software engineer (enforcement hooks)

### Sources consulted

- #1355 body and both owner comments (issuecomment-6845871452, issuecomment-6846801619).
- `hooks/lib/task_actions.py` at develop `2a7c2ba4`: generic branch `:2244-2252`, cwd fallback `:2416-2426`, `github_metadata_target` `:1712`, tokenizer substitution rejection.
- PR #1356 head `47c45145`: `_gh_without_repo_selectors`, its tests and review records.
- Upstream cli/cli v2.104.0 flag definitions for `issue close|reopen`, `pr close|reopen|merge`, `release create`; `pkg/cmdutil/flags.go` (`NilBoolFlag` NoOptDefVal); spf13/pflag `parseLongArg` / `parseSingleShortArg`.

## Test stage (tests only)

`hooks/_test/explicit_target_operands.py`, new section "gh free-text option values (#1355)":

- Positive: every row of the issue table (including `--comment=` and `-tfix/x`) and other pflag spellings are not path targets from a non-repo cwd, the own-session data scope and a clone; an owned clone passes; an unowned cwd refuses and names only the cwd; a text value naming an owned path cannot authorize an unowned cwd.
- Negative: path flags (`--body-file`, `-F`, `--notes-file`), release asset positionals, download destinations (`-D/--dir`, `-O`), unknown flags, unmodelled subcommands and executables, `--` handling, the pinned merge-queue refusal, and command substitution / tilde / glob errors.
- Red on unfixed develop `2a7c2ba4` (scratch runner from the session data dir, venv python 3.11.11): 108 failing subtests, all in positive assertions; every negative test passes.

These are action-classification checks only: they call `action()` and the source gate. No real close, merge or release ran.

The runtime change, review verdicts and full-suite results are recorded when they exist.
