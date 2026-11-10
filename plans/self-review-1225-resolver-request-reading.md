---
ticket_refs:
  - siege-analytics/claude-configs-public#1225: comment posted (design note, investigation, pre-mortem, junior/senior)
---

# Self-review: resolver reads the operator's actual request (#1225)

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket siege-analytics/claude-configs-public#1225 (Goal, Design and Acceptance criteria), filed after the cross-family review of PR #1216 found shared matcher limits; brief from the Siege Claude Hub, 2026-11-10.
Goal source verification: #1225 has Context, Goal, Design, Assumptions, Acceptance criteria and Falsification sections, and its "## Design" section is in the issue body.
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/1225#issuecomment-6770747746
Pre-author-inventory: plans/self-review-1225-resolver-request-reading.md#pre-author-inventory
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1225#issuecomment-6770747746
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1225#issuecomment-6770747746
Hostile-review-artifact: local hostile reviews, rounds 1-5 all CHANGES-REQUESTED (findings H1-H5, R1-R7, T1-T5, Q1-Q8 fixed; round-5 residuals V1-V3 open, quoted verbatim in "Open residuals" below and in the PR body); per the hub's ruling the PR is opened as a draft and Root rules at review.
Project-contribution: verb routes read the operator's actual request, prohibitions bind to their own sentence, quote variants are normalized once, and quoted prose is data for the ask-questions protocol routes without costing any technology route a guard.

## Pre-author inventory

Contact points checked on origin/develop b2c4fcf8 (contains #1216 merge c9f7ac8d) before authoring:

- `bin/resolve-load-set.py`:
  - `select` lowercases and turns "?" and newlines into ";".
  - `route_matches` splits clauses on ";" only, and only for routes with verbs.
  - A verb-route clause starting with "don't" or "do not" is skipped.
  - There is no quote handling.
  - Explicit `[skill:x]` and `/x` tokens are removed from route text before matching.
- 15 routes have verbs, including duckdb-spatial (`all_terms` continuation) and scala-on-spark / unity-catalog-insert (`context_terms`). Project routes have no verbs.
- The manifest has no key schema validator; `route_matches` is the single entry point for top-level and project routes.
- Regression corpora:
  - `bin/_test/resolve_load_set_test.py`;
  - `catalog/language-scope-fixtures.json` (51) via `bin/language-scope.py`;
  - `catalog/data-scope-fixtures.json` (78) via `bin/data-scope.py`;
  - progressive-loading, consumer-runtime and package tests.
- The ask-questions manifest carried two per-route U+2019 escapes and five quote-prefixed exclusions as #1225 workarounds.

## Design

Round 5. Rounds 1-4 were rejected by local hostile review:
- round 1 made every sentence its own clause (cross-sentence recall loss, quadratic scan);
- round 2 dropped "don't" sentences and stripped quotes in every route, losing guards named inside a "don't" sentence or a quotation;
- round 3 skipped a leading "don't" sentence only for the prefix check, so its prohibited verb still authorized a route ("Don't edit the SQL. Leave it as is." loaded sql), and dropped every "don't" sentence on ask-questions, so a bare "Don't ask questions." no longer suppressed it;
- round 4 dropped any "don't" sentence containing a qualifier word anywhere, so "at once" as a time word, total prohibitions naming a manner, and a sentence also carrying the request were mishandled; an unlisted elision ('Cos) opened a quotation.

Current design:
- `normalize_quotes` (all routes): apostrophe-like and quotation-like code points to ASCII, applied to the prompt first. The set covers U+2018/2019/201A/201B/2032/02BC/00B4/FF07 and U+201C/201D/201E/201F/2033/FF02/00AB/00BB.
- `split_sentences`: one linear pass over whitespace-separated words. A word ending in "." or "!" ends a sentence unless it is a known abbreviation or dotted initials.
- `without_prohibitions(clause, qualifiers)`: drops sentences that open with "don't"/"do not" and keeps the rest verbatim.
  - Technology verb routes (no qualifiers): only the leading run is dropped. Develop skipped any clause starting with "don't", so judging the remainder with develop's logic can only add loads, and a dropped sentence contributes neither verbs nor terms.
  - ask-questions verb route (`prohibition_qualifiers`): a prohibition is dropped only when `manner_prohibition` matches the whole sentence ("don't ask|send [me] [all your] questions|them <qualifier>") and the next sentence is an imperative ask ("Ask ...", "Please ask ...", "Interview ..."). Every other prohibition, including bare and total ones, stays and is excluded as on develop.
  - The sentence split is cached per clause (every verb route reads the same clauses), and both new keys are validated in `validate_manifest`.
  - The read-only/docs signal is still judged on the whole clause.
- `prose_request` (both ask-questions routes): `strip_quoted` removes quoted spans. A quotation opens at the start of the text, after whitespace or after an opening bracket. A single quote opens only before a letter that does not start a common elision ('em, 'til, 'cause, ...) and closes only at a word boundary.
- The how-to rewrite is unchanged from develop.
- Manifest: remove the seven ask-questions workaround entries; add `prose_request` to both routes and `prohibition_qualifiers` to the verb route.

Deliberate narrowing of the ticket's Design: the ticket asks for quoted-span stripping in every route. Round 2 showed that global stripping drops develop-guard (`Implement the "release" step`), unity-catalog (`query = "INSERT ..."`), rust and siege_utilities project skills; it is therefore opt-in per route. Disclosed in the PR for Root's ruling.

## Test plan

- `bin/_test/resolve_load_set_test.py` (#1225 block):
  - ask-questions positives: "Don't ask questions as a group. Ask your questions one at a time." (pinned as a #1225 miss before), "It's late. ...", the e.g. case, a mid-clause qualified prohibition, an elision-plus-possessive prompt, "Ask me questions one at a time. Don't ask them all at once.", and a curly form.
  - ask-questions negatives: single-, double-, curly-, low-9- and bracket-quoted prose, curly and modifier-letter "Don't ask" forms, "Please don't ask questions as a group. ...", "Don't ask questions one at a time. Just do it.", and two bare prohibitions followed by a narrative mention of asking.
  - Curly and ASCII forms behave identically on three prompts.
  - Technology/project routes pinned to develop's selections on all six round-1 and all eight round-2 reproducers (cross-sentence pairs, guards inside "don't" sentences, assignment and call string literals, quoted step names, PR titles, siege_utilities quoted test names, abbreviations).
  - Intended gain pinned: "Don't worry about tests. Fix the spark bug that writes to a delta table." loads databricks and unity-catalog.
  - Retained develop behavior pinned: a clause of prohibitions alone ("Don't forget saveAsTable.", "Don't fix the pyspark job ..."), a prohibited verb followed by a non-request ("Don't edit the SQL. Leave it as is.", "Don't run or modify the pyspark job. Just summarize what it does.") and a read-only first sentence ("Don't write to the catalog. ...") load nothing; the read-only signal stays clause-scoped by design.
  - Unit cases: `split_sentences`, `without_prohibitions` (leading-only and qualified modes), `strip_quoted` (contraction inside quotes, possessive, decade, elision, bracketed quote) and `normalize_quotes`.
  - Latency: 126k-character prose, a 51k-character "a. a. ..." prompt and a 210k-character quote-opener prompt resolve within the hook's 5 second timeout.
- Red-before/green-after: the test fails on develop's resolver and on single-helper reverts, including both rejected earlier designs; the restore passes (counts in the PR body from the same-cycle run).
- Develop-vs-PR probe on 59 prompts (all round-1 to round-4 reproducers): within that corpus, 0 losses on any route other than the intended quoted-prose negative; 6 differences: three manner-prohibition ask-questions positives, the quoted "Proofread" negative, the leading-"don't" technology gain, and the disclosed inherited gain Q5. The round-5 hostile review found losses outside the corpus (residual V1 below), so "0 losses" holds only for the probe corpus.
- Red-before/green-after: 22 single-change variants (develop's resolver, the rejected round-2, round-3 and round-4 designs, and each helper and validator) all turn the test red; the restore passes.
- The 41 PR #1216 reviewer prompts reach 41/41 (develop 40/41); eight extra acceptance cases reach 8/8.
- The language-scope (51) and data-scope (78) corpora route unchanged; no fixture edits.
- Full hook and bin suites; the pre-push self-review hook on push.

## Peer review

- writing-code: the resolver source stays ASCII (non-ASCII code points written as `chr(...)`). The new helpers are pure functions with no I/O; the sentence scan and quote strip are linear.
- writing-tests: every behavior change has a positive and a negative case; each helper and both rejected designs have a revert proof; no fixture rewrites.
- Generated artifacts are regenerated with the repo tools; progressive metrics with core.abbrev=7 for the #1258 short-SHA dependence.

## Lead review

- Class, not instance: the sentence rule is in the shared matcher for all 15 verb routes; quote handling is a shared helper behind a route flag, so another protocol route can opt in without code changes.
- Intended routing shifts:
  - ask-questions: a "don't" sentence forbidding a manner of asking ("as a group", "at once") no longer hides the request; quoted prose such as "Proofread: 'We ask questions'" no longer loads it; a bare "Don't ask questions." still suppresses it.
  - technology verb routes: a leading "don't" sentence no longer hides the request in the next sentence (gain only; the dropped sentence contributes nothing).
  - curly and other quote variants now behave exactly like ASCII in every route, including the read-only and prefix checks; this can drop a load develop made only because it misread a curly-apostrophe (U+2019) "don't write".

  None shifted any existing fixture.
- Blast radius: `bin/resolve-load-set.py` (shared resolver), the two ask-questions manifest routes, and their tests.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| D1 | P2 | First quote-strip draft removed the SQL string in `spark.sql("INSERT ...")` | superseded: quotes are stripped only on the ask-questions routes; covered by tests |
| D2 | P2 | Round-1 sentence split broke the how-to plus patch join | superseded: ";" clauses kept, how-to rewrite unchanged from develop; the join is covered by a test |
| L1 | P3 | Term routing stays lexical | noted; semantic routing is out of scope per the ticket |
| H1 | P1 | Round 1: every sentence its own clause lost six cross-sentence routes | fixed: ";" clauses kept; pinned; revert proof |
| H2 | P1 | Round 1: quadratic splitter (86 s at 158k chars) vs 5 s hook timeout | fixed: linear scan; latency bound in tests; revert proof |
| H3 | P3 | Round 1: missing abbreviations | fixed |
| H4 | P3 | Round 1: quotes inside a call stripped | superseded by R2/R3 |
| H5 | P3 | Round 1: missing quote variants | fixed; U+2039/203A, backtick and CJK brackets left as-is |
| R1 | P1 | Round 2: dropping a "don't" sentence lost guards named in it ("Don't forget to saveAsTable") | fixed: technology routes keep the sentence; only the prefix check skips it; pinned; revert proof |
| R2 | P1 | Round 2: `query = "INSERT ..."` stripped as prose | fixed: no quote stripping on technology routes; pinned |
| R3 | P1 | Round 2: global quote stripping lost develop-guard, rust and siege_utilities project skills | fixed: `prose_request` opt-in on ask-questions only; pinned; revert proof |
| R4 | P3 | Round 2: '90s paired with a later possessive; a stray inch mark swallowed a request | fixed for technology routes (no stripping); single-quote opener now requires a letter; a stray double quote can still hide part of an ask-questions request (noted) |
| R5 | P3 | Round 2: bracketed quotation `("ask me questions ...")` loaded ask-questions | fixed: a quotation may open after an opening bracket; pinned |
| R6 | P3 | Round 2: a test pinned a read-only clause loading nothing as if desired | relabeled as retained develop behavior; the read-only signal stays clause-scoped by design |
| R7 | P3 | Round 2: self-review inaccuracies (D2 text, "18 identical" count) | fixed in this revision |
| T1 | P1 | Round 3: a leading "don't" sentence's verb still authorized technology routes ("Don't edit the SQL. Leave it as is." loaded sql) | fixed: leading prohibitions are removed from the clause before every check; pinned; revert proof |
| T2 | P1 | Round 3: dropping every "don't" sentence on ask-questions let a bare "Don't ask questions." be followed by a narrative mention that loaded the skill | fixed: only qualified prohibitions ("as a group", "at once", ...) are dropped; bare ones exclude as on develop; pinned; revert proof |
| T3 | P3 | Round 3: elisions ('em, 'til) opened a quotation that ran to a later possessive | fixed: common elisions never open a quotation; pinned; revert proof |
| T4 | P3 | Round 3: CHANGELOG "only gain" claim omitted the quote-normalization loss | fixed: stated next to the claim |
| T5 | P3 | Round 3: "a don't sentence contributes nothing" was false for the explicit route | fixed: the qualifier rule is stated for the verb route only |
| Q1 | P1 | Round 4: "at once" as a time word ("Don't ask questions, at once start coding.") dropped a bare prohibition | fixed: the manner prohibition must be the whole sentence; pinned; revert proof |
| Q2 | P1 | Round 4: total prohibitions naming a manner ("upfront or at all", "together with the code", "at once. Just start.") loaded ask-questions | fixed: whole-sentence match plus a following imperative ask; pinned; revert proofs |
| Q3 | P1 | Round 4: "Do not send questions together, ask one question at a time." lost the load develop made | fixed: the sentence is no longer a whole-sentence manner prohibition, so it is kept; pinned as a positive |
| Q4 | P1 | Round 4: unlisted elision 'Cos opened a quotation closed by a later possessive | fixed: 'cos/'coz/'cuz added; a possessive-closer heuristic was tried and rejected because it broke the #1056 negative "Translate 'ask me questions' into French"; other unlisted elisions remain a residual |
| Q5 | P3 | Round 4: "Don't edit the SQL. I'll fix the SQL myself later." gains coding and sql | residual, disclosed: develop selects them for the second sentence alone |
| Q6 | P3 | Round 4: 4x develop latency on prohibition-heavy clauses | the sentence split is cached per clause; develop itself exceeds 5 s on 200k characters of ";" |
| Q7 | P3 | Round 4: new keys not validated | fixed: validated, with negative tests and a revert proof |
| Q8 | P3 | Round 4: docs overclaimed "only gain" | fixed: CHANGELOG states the probe evidence and the inherited gain |

## Open residuals (round-5 local hostile review, verbatim)

VERDICT: CHANGES-REQUESTED

V1 (Blocking): "Claim (a) is refuted: the PR still loses ask-questions loads that develop makes when an opening apostrophe pairs with a plural possessive later in the prompt. This is the same failure as round-4 finding 4. Adding 'cos, 'coz and 'cuz to a fixed list only covers those words. Any leading apostrophe followed by a letter that is not on the list, with a possessive like "users'" later, still hides the request."
- "'Specially since you're new, ask me questions one at a time about the users' table." develop ["ask-questions"], PR []
- "'Fraid I'm new here, so ask me questions one at a time about the users' table." develop ["ask-questions"], PR []
- "'Nother thing: ask me questions one at a time about the customers' schema." develop ["ask-questions"], PR []
- "Rename the 'Users table, then ask me questions one at a time about the admins' permissions." (a quote never closed, likely a typo) develop ["ask-questions"], PR []
- Reviewer's suggested direction: "The fix needs to be structural: for example, a single-quote span should not cross a sentence or clause boundary, or a closing quote that is only a plural possessive should not close a span opened far earlier." (Author note: a possessive-closer heuristic was tried in round 5 and broke the #1056 negative "Translate 'ask me questions' into French"; the sentence/clause-boundary variant is untested.)

V2 (Non-blocking): "Claim (b), and so (e), understates the gains on ask-questions. Each prompt below says not to ask the operator, or to ask only when blocked, and now gains ask-questions. Develop already loads the second sentence alone, so this is the same inherited class as the disclosed SQL case."
- "Don't ask me questions upfront. Ask questions of the codebase instead, not me, and just build it." develop [], PR ["ask-questions"]
- "Don't ask questions upfront. Ask questions only if you are truly blocked." develop [], PR ["ask-questions"]
- "Don't ask me questions at once. Ask questions to Priya instead, I'm unavailable." develop [], PR ["ask-questions"]
- "Don't ask questions at once. Ask questions never." develop [], PR ["ask-questions"]
- "Don't edit the SQL. Never edit production SQL." develop [], PR ["coding","sql"]. Develop also selects these for "Never edit production SQL." alone.

V3 (Non-blocking): "Claim (c) is broader than what the code does. Each of these is a manner-only prohibition followed by an ask, and each returns [] on both develop and the PR. There is no regression, but the claim and the CHANGELOG wording overstate what loads."
- "Don't ask questions as a group. Ask them one at a time." The next sentence has no "question(s)" word.
- "Don't ask questions at once, ask them one at a time." The comma form is not a whole-sentence match.
- "Don't ask me 20 questions at once. Ask them one at a time."

What the round-5 review found to hold: all four round-4 reproducers fixed; intended positives load; quoted modes behave as on develop; resolver test, data-scope (78) and language-scope (51) pass; latency within 1.6 s on 200k-character adversarial prompts; manifest validation in place.

## Quantified claims

- "15 routes have verbs" -- `jq '.routes[] | select(.verbs)'` over the manifest -> 15 rows
- "41/41" and "8/8" -- probe over the 41 reviewer prompts and eight extra cases at the PR head
- "51" and "78" fixtures -- `bin/language-scope.py --check` and `bin/data-scope.py --check` output
- "59 prompts, 0 unintended losses within the corpus, 6 differences" -- develop-vs-PR probe output (the corpus is not exhaustive; see V1)
- "22 variants" -- revert-proof run output (22 RED lines, then RESTORED exit=0)

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| data-scope catalog-insert went unknown after the first quote-strip draft | code string literals not considered as a quote context | seconds | one regex boundary | low |
| hostile review round 1 (H1/H2) | only corpora and ticket prompts measured, not develop-vs-PR cross-sentence prompts or long-prompt latency | minutes | one redesign round | high |
| hostile review round 2 (R1-R3) | treated the ticket's "every route" as a requirement without checking what quotes and "don't" sentences carry for technology and project routes | minutes (a develop-vs-PR superset probe) | one redesign round | high |
| hostile review round 3 (T1-T2) | probed only for losses, not for harmful gains, and treated a bare prohibition and a manner prohibition as the same lexical shape | minutes (probing gains on prohibited requests) | one redesign round | high |
| hostile review round 4 (Q1-Q4) | matched a qualifier word anywhere instead of the sentence's whole shape | minutes (adversarial qualifier placement) | one redesign round | high |
