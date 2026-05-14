---
description: Entry point for the always-on rule set. One line per rule file; one link to the coverage matrix. Read this when looking for the relevant rule, not the individual files.
---

# Rules

The always-on rule set is split by act. Each act has its own file; the files are siblings, not children of an umbrella file. Find the rule by asking "what am I doing right now?" and reading the file that matches.

For mapping failure modes to rules (the inverse question: "is this failure mode covered?"), see `_coverage.md`.

## Per-act rule files

| File | What it covers | When it applies |
|---|---|---|
| `_writing-prose-rules.md` | AI-typographic Unicode characters (rule 1; covers em/en dashes, arrows, curly quotes, ellipsis, middle dot, bullet, NBSP), structured rationale blocks (rule 2), banned adverbs (rule 3), commit-message body shape (rule 4). Four prose-style rules. | Any natural-language output: chat to operator, commit-message body, PR description, agent-to-agent messages, comments-as-prose. |
| `_writing-code-rules.md` | Docstring brevity (rule 1), no history references in code comments (rule 2), no speculative abstractions (rule 3), verify symbol exists (rule 4), no hypothetical code (rule 5), doc-edit symmetry (rule 6), silent error swallowing (rule 7), conditional-import callsite hygiene (rule 8), no silently-dropped parameters (rule 9), capability declarations match implementations (rule 10), no silent processes (rule 11). Eleven code-act rules. | Writing production code (any `.py` file outside `tests/`), plus the comments and docstrings that live in those files. |
| `_writing-tests-rules.md` | Tests fail on revert + import the module (rule 1), no cargo-cult patterns (rule 2), skip messages name remediation (rule 3), mock fidelity with real exceptions, real-shape fixtures, `spec=` on `MagicMock` (rule 4), every `except` block exercised by a test that forces it (rule 5). Five test-act rules. | Writing tests or test fixtures. |
| `_writing-claims-rules.md` | Grep before declaring fix complete (rule 1), countable claims need same-turn evidence (rule 2), confidence calibration on unquantified completeness claims (rule 3). Three claim-act rules. | Stating facts in commit bodies, PR bodies, agent-to-agent messages, chat to the operator. Verify-before-claiming (this file) is the temporal sibling of verify-before-touching-code (in `_writing-code-rules.md`). |
| `_writing-releases-rules.md` | BREAKING in CHANGELOG when public surface changes incompatibly (rule 1), skip-count must not silently trend upward (rule 2), deprecation messages name a removal target (rule 3). Three release-act rules. | Cutting releases, merging PRs that affect the public surface or the test-suite skip count, or adding a deprecation warning. |

## Meta-rule files (cross-cut all acts)

| File | What it covers |
|---|---|
| `_verify-before-execute-rules.md` | Same-turn evidence requirement for any side-effecting action and for factual claims. Parent of the claim-grounding rules. |
| `_definition-of-done-rules.md` | Five hard criteria (code-reviewed, edge cases, tests, ticket update, ticket exists) before declaring work done. |
| `_environment-preflight-rules.md` | One-time-per-repo inventory of interpreters, services, credentials, CI parity. Companion to `[rule:writing-code]` writing-code:2. |
| `_output-rules.md` | Output formatting and attribution policy (no AI / agent attribution in any user-visible artifact). |
| `_principles-rules.md`, `_python-rules.md`, `_jvm-rules.md`, `_rust-rules.md`, `_typescript-rules.md`, `_data-trust-rules.md`, `_siege-utilities-rules.md` | Language and domain rules; orthogonal to the per-act split. |

## Coverage matrix

`_coverage.md` maps each known failure mode (from the originating siege_utilities arcs and subsequent retrospectives) to the rule that covers it and the enforcement mechanism. Format is TOML; one entry per failure mode; fields are `rule_id`, `enforcement` (`scanner | hook | code-review | operator-honor`), `tooling_status` (`mechanical | judgment | gap`), `originating_arc`.

Read the matrix when:

- Asking "is this failure mode covered?" before assuming it is.
- Auditing which rules are honor-system vs mechanical.
- Surfacing tooling gaps for follow-up.

## How rules get promoted into this set

Three-tier pipeline. Findings start as Tier-1 entries in a consumer repo's `LESSONS.md`, get distilled into Tier-2 project rules at `<repo>/.claude/rules/<topic>.md`, and become Tier-3 rules in this directory only via human PR with cited evidence from at least two Tier-2 projects (or a language/framework justification from one). See `CONTRIBUTING.md` for the Tier-3 PR requirements. The `[skill:lessons-learned]`, `[skill:distill-lessons]`, and `[skill:rules-audit]` skills implement the pipeline.

## Identifier scheme

Each rule is identified by `<file-stem>:<n>` where `<file-stem>` is the rule file name without the leading underscore or `-rules.md` suffix. Examples: `writing-prose:1` (no em-dashes), `writing-claims:3` (countable claims), `writing-releases:2` (skip-count trending).

This scheme replaces the v1.x flat numbering (rules 1-20). The v2.0.0 `CHANGELOG.md` carries the one-time migration table mapping old numbers to new identifiers. Historical references in commits, LESSONS entries, and code comments using the old numbers still resolve through that table.

## Migration from v1.6.x

Files renamed:

- `_no-ai-fingerprints-rules.md` -> the five per-act files above (`_writing-*-rules.md`).

Resolver consumers using the `_*-rules.md` glob pick up the new files automatically. Consumers that hard-coded the old filename need to update once. See `CHANGELOG.md` v2.0.0 entry for details.

This file is loaded by the resolver alongside the rule files; agents see it on every session.
