# Self-review: sync main fixes back into develop (#673, #729)

## Assumptions

Goal source: operator instruction in Craft Agent session 260905-clever-quasar to get work through develop to main, plus CI failure on PR #753 from `python3 bin/validate-hooks.py` settings drift.
Working as: tech lead for repo promotion and hook governance.
Pre-author-inventory: compared `skills-upstream/main..skills-upstream/develop`, attempted main-to-develop merge in clean worktree, inspected conflict files, checked CI log for PR #753, and ran `python3 bin/validate-hooks.py` before and after settings synchronization.
Investigation-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Project-contribution: repairs the develop-first invariant so accepted main-only fixes and hook settings consistency can flow through develop before promotion to main.

## Peer review

Shelf checks: session-coordination:4, writing-claims:2, definition-of-done:1, writing-prose:1.

Gate evidence:

- Ticket propagation case-folding now folds only governed artifact directory components, preserving case-sensitive parent directories.
- Survey-context diff discovery now includes a root-to-HEAD fallback for first-push and isolated fixture repositories.
- Raw path artifact fallback now applies only when the raw target does not exist, preserving the outward-symlink control while keeping upper-case artifact spellings governed.
- `hooks/_test/survey_context.test.sh` fixture commits now use `--no-verify` so unrelated commit hooks cannot make the hook-under-test silently skip in CI.
- `bash hooks/_test/survey_context.test.sh` passed with 6 scenarios.
- `bash hooks/_test/ticket_propagation_guard.test.sh` passed with 53 scenarios after case-insensitive existing-component canonicalization.
- NotebookEdit guard fixture passed after adding the explicit `tool_input.notebook_path` support signal to `hooks/write/ticket-propagation-guard.sh`.
- Local merge conflict resolution validation passed before first push: `python3 bin/build.py --check`; `python3 bin/sync-skill-references.py --check`; `bash hooks/_test/session_signal_resolution.test.sh` -> 6 passed; `bash hooks/_test/universal_mutation_gate.test.sh` -> 18 passed; `bash hooks/_test/investigate_gate_schema.test.sh` -> 5 passed.
- CI failure on PR #753 identified `python3 bin/validate-hooks.py` settings drift between `.claude/settings.json` and `hooks/settings-snippet.json`.
- After synchronization, `python3 bin/validate-hooks.py` reported: `All hooks valid.` Warnings were limited to unreferenced hooks.

Review findings:

- `CHANGELOG.md` conflict was resolved by preserving develop's current Unreleased content and adding explicit bullets for main-only fixes plus hook settings drift.
- `hooks/_test/investigate_gate_schema.test.sh` add/add conflict was content-identical; executable mode was preserved.
- Hook settings synchronization introduces no new hook scripts; it aligns existing settings and snippet entries so CI can verify the repository's documented hook wiring.

## Trivial-investigation declaration

Category: merge synchronization and configuration drift repair.
Cannot produce error: the branch brings already-main fixes back into develop and aligns hook configuration files validated by `bin/validate-hooks.py`; no hook runtime logic is newly invented here.
Evidence: targeted hook tests, build/reference checks, and validate-hooks output passed after edits.
Falsification: failing validate-hooks output, conflict markers, non-executable test mode, or a missing main-only fix in develop would falsify this declaration.
