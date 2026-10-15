# Self-review: effective ticket commit messages (#994)

## Assumptions

Domain(s): software engineering, governance enforcement, shell/Git safety
Geospatial cross-cut: no
Working as: software engineer, tech lead
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/994
Goal source verification: issue #994 requires validation of the effective Git commit message, correct `-m`/`-F`/stdin/amend/template/`-c`/`-C` semantics, hostile path and quoting tests, native hook alignment, and elimination of unrelated argv ticket bypasses.
Pre-author-inventory: `plans/investigate-994.md`
Investigate-artifact: `plans/investigate-994.md`
Pre-mortem-artifact: `plans/pre-mortem-994.md`
Hostile-review-artifact: `plans/hostile-review-994.md`
Project-contribution: replace incidental command-string matching with one bounded effective-message contract shared by pre-tool and native Git enforcement.

## Pre-implementation comprehension

The original hook grepped all of `tool_input.command`. It therefore rejected ticketed message files and accepted ticket-like text in unrelated options or pathspecs. Git itself has multiple message sources and editor/cleanup stages, so correctness requires resolving only deterministic sources and failing closed when shell, editor, repository configuration, or unsupported Git options can still alter the result.

## Pre-author inventory

- `hooks/git/ticket-required.sh` contained all ticket grammar inline and skipped amend/no-edit unconditionally.
- `.githooks/commit-msg` had a narrower duplicate grammar and receives its file before final cleanup.
- `hooks/lib/` had no shared effective-message parser; existing security guards use `shlex` only for much narrower command shapes.
- `hooks/_test/ticket_required.test.sh` had 23 command-string scenarios and no file, cwd, stdin, repository-state, option-order, or incidental-argv negatives.

## Peer review

Independent Git-semantics and security reviews found and drove fixes for unsupported global-option bypass, newline chains, cleanup removal, heredoc context, shell comments, pathname expansion, `CDPATH`, mixed overrides, bounded reads, and descriptor-pinned path traversal. Each finding is recorded with its resolution in `plans/hostile-review-994.md`.

## Lead review

The shared parser is large because it defines a security boundary, but it remains narrower than a shell: no evaluation, explicit supported Git forms, exact message-source precedence, and visible fail-closed errors for uncertain forms. The native hook uses the same ticket grammar and conservatively validates only cleanup-stable content. Repository confinement and bounded reads are enforced at the file-descriptor boundary rather than by string checks alone.

## Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| R1 | P1 | Initial helper treated unsupported Git global options as unrelated commands. | fail closed when `commit` follows an unsupported global option |
| R2 | P1 | Shell comments/newlines/expansion could diverge from parsed argv. | quote-aware comments and newline/path-expansion rejection; chains/wrappers/groups block |
| R3 | P1 | Cleanup could remove a reference accepted before or during native hook execution. | inspect configured cleanup pre-tool; validate cleanup-stable native content |
| R4 | P1 | Resolve/stat/read sequence left path replacement concerns. | canonical in-repo target plus pinned no-follow descriptor traversal |
| R5 | P2 | Input caps were applied after full reads. | bounded JSON, message-file, native-file, and revision reads |
| R6 | P2 | Native ticket syntax drifted from pre-tool syntax. | one shared validator and positive/negative native fixtures |

## Test plan

- Syntax: Bash `-n`, Python 3.13 compile, and `git diff --check`.
- Focused: all scenarios in `ticket_required.test.sh` and `review_risk_policy.test.sh`.
- Packaging: full build, both consumer hook validators, and byte-identical shared helper in both packages.
- Full suite: the complete serial `build-and-publish.yml` validation command set plus every `hooks/_test/*.test.sh` file.
- Hosted: draft PR checks must pass before any merge decision.

## Quantified claims

- Focused ticket matrix: 82 scenarios before evidence-only additions; final rerun records the current exact count.
- Native commit/risk matrix: 19 passing scenarios.
- Full hook suite: 36 of 36 files pass after a fresh build.
- Full serial CI matrix: all listed build, generated-authority, loading, risk, install, policy, lifecycle, and hook steps pass.
- Shared runtime: one parser is copied byte-identically into both `dist/claude-code/hooks/lib/` and `dist/craft-agent/hooks/lib/`.

## Rollback

Revert the single issue #994 commit. The prior command-string behavior returns immediately; no migration, deployment, release, or external state change is required. Existing native hooks remain source-controlled and protected checks still gate merge.
