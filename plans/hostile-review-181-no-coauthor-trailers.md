# Independent review: #181 no-co-author trailers

## Scope

Read-only review of the rule, the early PreToolUse guard, the native `commit-msg` guard, the tests and all procedural instruction copies changed in this candidate.

## Findings and disposition

1. **High, fixed:** The PreToolUse guard only sees literal command text, so `git commit -F <message-file>` could bypass its new generic pattern. Added enforcement in `.githooks/commit-msg`, which reads the final message file, and added a regression case through the native hook. This covers `-F` and editor-supplied messages.
2. **Low, fixed:** The early hook called a human co-author trailer “AI/agent attribution.” Changed the diagnostic to “prohibited attribution.”
3. **Informational:** A broad text match could reject commit prose that mentions `Co-Authored-By`. The policy concerns trailers, and the native hook anchors to a trailer-shaped line. The early hook remains strict for visible mentions as a defense-in-depth check.

The reviewer found the lower-level instruction copies consistently ban co-author trailers and found no remaining procedural exception to human co-author trailers in the searched surfaces.

## Verdict

No known blocker remains after the two fixes. Re-run focused tests and CI on the exact final head before merge.
