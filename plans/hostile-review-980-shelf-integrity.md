# Hostile review — #980 shelf integrity

Independent read-only review at base 022fb81: `sessions/261013-brave-torrent/data/hostile-review-980.md`. Verdict: **CHANGES_REQUIRED**, four findings. It did not execute suites (reviewer permission mode read-only), so author-side execution is recorded in the self-review. Independent focused re-review: `sessions/261013-polished-leaf/data/re-review-980.md` found three residual semantic gaps; all accepted and patched author-side, not yet independently re-accepted.

## Findings and disposition

1. **HIGH angle-wrapped and reference-style Markdown links escaped path scan:** accepted. `check-shelf-paths.py` now normalizes angle destinations, resolves used reference definitions, and includes negative fixtures for inline and definition forms. Explicit upstream URLs remain exempt.
2. **MEDIUM orphan count trusted prose basename:** accepted. Orphans now require a resolved same-book supplemental path (including recursively nested references); a bare `orphan.md` mention and nested orphan fail fixtures. Four tracked one-byte placeholders are retained with explicit reasons, not treated as substantive links.
3. **MEDIUM owner evidence could be anti-consultation/archive prose:** accepted. Each of 12 owned records now carries a verbatim positive consultation directive from the same Markdown section as its path-specific evidence. Negative/archive-only prose and section-remote claims fail; `skills/code-review/SKILL.md` etc. retain real contextual directions. 71 other records stay quarantined.
4. **LOW explicit negated/unvendored citation false positive:** accepted. Fenced code examples and `Do not read ...` clauses are skipped; a second actionable target on the same semicolon-delimited line still fails. Unavailable historical citations require explicit qualification.

Residual scope: this is a targeted Markdown `.md` path integrity check, not a universal Markdown parser or dynamic file-reference analyzer. Five resolver scenarios and three actual injection outputs matched the exact base byte-for-byte (bounded canary, not all prompts). No resolver or publish-job mutation.

## Follow-up re-review dispositions

1. Bare backtick `references/orphan.md` no longer justifies a nonempty orphan unless an affirmative reading directive accompanies it; passive one-page marketing template citation migrated to a Markdown link. New bare-backtick and nested orphan fixtures fail as expected.
2. Owner section is now checked for contradictory non-consultation prose, not only the two cataloged evidence lines. Added same-section `not for reading` fixture.
3. Negation is scoped to sentence/semicolon/conjunction segments. `Do not read old but read missing` fails on the second target; fenced and explicitly negative examples still pass.

## Coordinator follow-up on head 2ab38e5

- CI failed due stale inventory before authority generation. Regeneration now occurs after source/test/artifact edits, then dependent authority and progressive metrics; this was a real defect in the first head and is disclosed in the self-review.
- CommonMark inline destinations now handle balanced nested parentheses and escaped punctuation (including parentheses). Added failing missing-target and passing existing-target fixtures for both forms. Reference-style links remain covered.
- Negation boundaries now include comma/colon/dash; 4-backtick and tilde fences only close with a matching marker and at least the opening length. Added adversarial fixtures so an affirmative target after punctuation still fails.
- Ownership evidence strips frontmatter, HTML comments and correctly matched fenced examples; anti-consultation includes do-not-open/reference/follow and related language across the section. An unrelated `read logs` directive cannot justify a path-specific shelf entry. Negative fixtures cover all of these.
- `skills/RESOLVER.md` now calls shelf rows a navigation index rather than ambient routes, and `AUTHORING.md` states precise guard scope: actionable Markdown local `.md` links/backticks and `references/**/*.md`; HTML/non-Markdown/assets/dynamic paths are not covered.

## Review of head 761386b

- Valid inline CommonMark labels with nested brackets (`[the [chapter]]`) or escaped brackets (`[the \\[chapter\\]]`) bypassed the previous opener regex. The scanner now balances/escapes link labels before reading destinations; missing-target and existing-target fixtures cover both forms.
- Negation boundaries also split on spaced `--` and unspaced em dash, with negative fixtures confirming an affirmative second target still fails.
- Quarantine reasons now require at least 20 non-whitespace characters; short vague reasons fail a fixture while all existing 71 remain valid.
- Separate measurement: `skills/RESOLVER.md` grew by **232 bytes** from the exact develop base. This is documentation size, not actual hook injection; the three injected-output comparisons remain byte-identical.

These are author-run regressions; independent reviewers could not execute fixtures in their read-only sessions. No blanket independent ACCEPT of the new head is asserted.
