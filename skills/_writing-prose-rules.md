---
description: Always-on. Stylistic discipline for natural-language output -- chat, comments-as-prose, commit subject and body, PR descriptions, agent-to-agent messages. Four rules covering the prose-style fingerprints; rule 1 covers the broader AI-typographic Unicode character class (dashes, arrows, curly quotes, ellipsis, middle dot, bullet, NBSP). Code-comment specifics (history references) live in `_writing-code-rules.md`; docstring discipline lives in `_writing-code-rules.md` because docstrings are code.
---

# Writing Prose

These four rules apply whenever the agent generates natural-language prose: chat to the operator, commit-message bodies, PR descriptions, agent-to-agent messages, code comments that are predominantly explanatory rather than load-bearing. They are the stylistic fingerprints whose cumulative effect is "this reads like AI output."

For code-comment-specific rules (no PR/sprint/issue references in code comments) see `[`writing-code`](_writing-code-rules.md)` writing-code:2. For docstring discipline (default to no docstring or one-liner; multi-paragraph reserved for public API) see `[`writing-code`](_writing-code-rules.md)` writing-code:1. Both are code-authoring acts and live with the code-writing rules.

## The four prose rules

**writing-prose:1. No AI-typographic Unicode characters.** Editors, word-processors, and language-model output insert a recognisable family of typographic Unicode characters that read as AI-generated when they appear in prose. Use the ASCII equivalent or rephrase. The banned characters:

- **Dashes (the historical kernel):** em-dash U+2014, en-dash U+2013. Use `--`, a comma, or a period.
- **Arrows:** U+2192 right, U+2190 left, U+21D2 right-double, U+21D0 left-double. Use `->`, `<-`, `=>`, `<=` or rephrase the prose.
- **Curly quotes:** U+2018 left-single, U+2019 right-single, U+201C left-double, U+201D right-double. Use straight `'` and `"`.
- **Ellipsis:** U+2026. Use three dots `...` or rephrase.
- **Middle dot:** U+00B7. Use a comma or list separator appropriate to context.
- **Bullet:** U+2022. Use ASCII `-` or `*` for list markers; the rendered output is identical in Markdown.
- **Non-breaking space:** U+00A0. Use a regular space.

The rule body intentionally references the banned characters by Unicode codepoint only and does not display the literal glyphs; this lets the scanner run cleanly against the rule files themselves without a special-case exemption.

**Path-based whitelist for U+00A0:** legitimate inside `templates/` (HTML email and report templates where the non-breaking space prevents undesired wrapping in rendered output) and `i18n/` (string tables for languages where the non-breaking space is grammatically required). The scanner skips files matching those path globs. Other characters in the list have no path-based whitelist; the meta and marketing carve-outs already in place for the existing dash check extend to the broader char class.

This rule extends what was previously a dashes-only rule. Consumers grepping LESSONS or PR bodies for "no em-dashes" should know the rule is the same identifier (writing-prose:1), the kernel still includes em-dashes and en-dashes, and the new char-class additions are the same discipline applied to a broader set of typographic Unicode that produces the same AI-generated reading. See `CHANGELOG.md` v2.2.0 for the rename callout.

**writing-prose:2. No "Why:" or "How to apply:" structured blocks in code comments or commit messages.** If the rationale is non-obvious, write one sentence inline. If it is obvious, write nothing. This rule does not apply to memory ledgers, skill files, or rule files where structured rationale is the documented format.

**writing-prose:3. Strip self-justifying adverbs.** Do not write "deliberately," "intentionally," "explicitly," "fundamentally," "essentially," "crucially," or "notably." If a reader could disagree with the design, the diff and the test cover it; the comment does not need to argue.

**writing-prose:4. Commit messages: subject line + plain-prose body, as long as the explanation genuinely needs and no longer.** No bulleted "what this PR does" lists. No structural headers (`## Summary`, `## Why`, `## Test plan`) in the commit body. No self-justifying adverbs (writing-prose:3 applies). No narrating the diff ("This commit changes line 48 to use StringType"). Length is determined by what the why genuinely requires: a typo fix is one line, a non-obvious rewrite may be three paragraphs. Padding to look thorough is a tell; truncating to look terse is a different tell. PR bodies may have a short summary and a test plan; the commit body is prose only. See `[`commit`](git-workflow/commit/SKILL.md)` Body section for the commit-message-specific format.

## Override

These rules are mandatory. There is no `[prose-skip]` override. The rule-2 carve-out for memory ledgers, skill files, and rule files where structured rationale is the documented format is in the rule, not an override.

## Cross-references

- `[`writing-code`](_writing-code-rules.md)` writing-code:1 (docstring discipline) and writing-code:2 (no history references in code comments) are the code-act sibling rules; they apply when the prose lives in a code file.
- `[`commit`](git-workflow/commit/SKILL.md)` implements writing-prose:4 directly and enforces the artifact-specific format (subject line conventions, ticket-reference footer).
- `[`detect-ai-fingerprints`](meta/detect-ai-fingerprints/SKILL.md)` mechanically scans writing-prose:1, :2, :3, :4 on staged diffs and commit message bodies.

## Migration note (v2.0.x only)

This file is derived from rules 1, 2, 4, 5 of the deprecated `_no-ai-fingerprints-rules.md`. Old rules 3 and 6 moved to `_writing-code-rules.md` because they apply specifically to code-authoring acts (docstrings, code comments). See `CHANGELOG.md` for the v2.0.0 migration table mapping old rule numbers to new `<file-stem>:<n>` identifiers. This migration note is retained for one release cycle (v2.0.x) and removed in v2.1.0.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in prose, code, commits, PRs, or comments.
