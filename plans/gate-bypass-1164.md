---
ticket_refs:
  - siege-analytics/claude-configs-public#1164: comment posted
---
# Gate-bypass repair B1/B2 (#1164)

## Assumptions

Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket siege-analytics/claude-configs-public#1164, hostile-review findings https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6690927636
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6691164139
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6691164139
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6691164139
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6691164139
Hostile-review-artifact: PENDING. The findings are https://github.com/siege-analytics/claude-configs-public/issues/1164#issuecomment-6690927636. The cross-family hostile re-review of this branch head has not happened yet.
Project-contribution: the artifact lane of coordinator-status-guard and the Tier C artifacts-posted signals stop accepting laundered completion claims and spoofed or quoted artifacts, so the Tier C gate means what it says.

## Design

B1, `hooks/bash/coordinator-status-guard.sh`. A field label no longer exempts anything. Every line is scanned for claims: labelled lines, YAML front matter and wrapped lines alike. Each line is split into sentences (`;.!?`) and clauses (`,`, `:` but not `://`, dashes, `then`).

**Claims.** A completion word is masked, so it is not a claim, in only two cases:

- A modal directly precedes it. The modals are `could`, `might`, `would`, `may`, `should`, `will`, `must`, `can`, `cannot`, their negated contractions, and `to`. Between the modal and the word there may be only adverbs (`not`, `never`, `also`, `still`, `yet`, `ever`, `already`, `only`, `just`, `probably`, `likely`, `eventually`), linking verbs (`be`, `become`, `get`, `go`, `turn`, `stay`, `remain`, `look`, `seem`, `appear`, `have`, `been`, `being`) and one trailing intensifier.
  - Without a linking verb, only `go` and `complete` are masked.
  - A bare `to` ("set to done") masks nothing.
  - A modal does not carry over a later `and` conjunct.
- The word sits in a clause that opens with a subordinator (if, when, unless, until, once, ...) followed by a non-empty consequent clause in the same sentence.

**Evidence (fix rounds 1-3, R1/F1/F4/N5).** Eligibility is decided separately from masking, on the original-case text. A clause supplies owner/merge/rollout evidence only if all of these hold:

- Neither the clause nor its sentence is interrogative (`artifact_is_question`). Leading quotes, emphasis and Markdown quote markers are skipped. A field label is its own clause, because clauses split at `:`. A question is:
  - text ending in `?` followed only by non-word characters (`?"`, `?!`); or
  - text opening with an inverted auxiliary (did/does/do/has/have/had/is/are/was/were/am followed by a word), question mark or not, unless a finite auxiliary (has/had/is/are/was/were/am) is followed, after optional adverbs, by a lowercase participle (N5). "Owner: has approved the rollout" is an elliptical statement; "Has the owner approved the rollout" is a question. A bare `have` plus participle is non-finite (it follows a modal), so it stays ineligible.
- No modal auxiliary governs it (`artifact_has_modal`).
  - URIs are opaque, so `/may/` and `/will/` path segments are not modals.
  - May/Will followed by a number is a date.
  - A capitalized May/Will that does not open a sentence is a name or month when followed by punctuation, clause end, `and`/`or`, a past form or a finite has/had/is/was/did/does ("operator Will.", "owner Will approved", "The owner Will has approved"). A field value does not open a sentence (N5), so "Owner: Will approved" is a name.
  - Every other occurrence stays modal ("owner May have approved", "owner Will approve", "Owner: Will approve"). Genuinely ambiguous wording therefore fails closed.
- It is not a hypothetical conditional clause.
- It is not under a hypothetical field (`ARTIFACT_HYPOTHETICAL_FIELDS`, wrapped continuation included).

Each evidence predicate must match within a single line (`artifact_missing_evidence`). A line break therefore ends a match, so `Owner:` on one line and `approved.` on the next do not combine. The lane's entry rules, the evidence predicates themselves and the status lane are unchanged.

B2, `hooks/lib/pipeline_state.py`. The comment query now projects `user.login`, `author_association` and `body`. A comment counts only when both hold:

- its author is the authenticated `gh api user` login, or GitHub attests OWNER, MEMBER or COLLABORATOR. A failed actor lookup falls back to the attested roles only. A bare string record counts as unattributed and is skipped.
- its ticket identity is current (fix rounds 1-3, R2/F2/N1/N4):
  - **Front matter** (a leading `---` block) is judged on the raw comment as one region, never parsed: every ticket reference in it must be the current ticket (N1, hub ruling). One current reference cannot neutralize a foreign one, and blank lines, YAML comments, flow collections, folded scalars or an unrecognized key cannot hide one. No-reference and current-only front matter count.
  - **Body declarations:** no declaration may name only other tickets. A declaration is an artifact heading line, or a Ticket/Task/Issue/Refs/`ticket_refs` key together with its entire value: its inline text plus every following indented or list-item line, across blank lines (F2). A declaration that also names the current ticket still counts, as does a comment with no declaration.

  Supported reference forms are `#N`, `owner/repo#N` and GitHub issue/PR URLs. A same-number reference in another repository is a different ticket.
  - Body identity is read from the same eligible text as headings (`comment_views`, N4), with inline code restored rather than erased, so `` `other/repo#9` `` still names its ticket (F2) while a `Ticket:` inside an HTML comment, CDATA, `<pre>` or other HTML block names nothing.
  - The rule is strict for every key, `Refs` included. A separate `Refs:` list naming only foreign tickets excludes an otherwise current-ticket artifact, so `Refs` is not a free-form bibliography.

`block_kinds()` (F3, N3, N4) is the single CommonMark 0.31 block classifier. It labels each line as text, fenced code or HTML block:
- types 1-5 (`pre`/`script`/`style`/`textarea`, comment, processing instruction, declaration, CDATA) end at the line holding their end marker;
- type 6 (block-level tags such as `blockquote`, `div`, `details`) and type 7 (any other complete tag alone on its line) end only at a blank line;
- type 7 cannot interrupt a paragraph. A blank line, ATX heading, thematic break (`---`, `***`), setext underline or indented code line leaves no paragraph open, so type 7 can start after one.

`markdown_lines()` drops fenced code (unchanged behavior) and removes every HTML-block line's text, so HTML-block content reaches neither heading detection, nor the keyword-stem fallback, nor body identity (N3). An element block (types 1, 6, 7) keeps only its container tags, indented one space, so the name-aware filter below still sees them and a mismatched type-1 end marker (`<script></pre>`) cannot expose what follows. A comment, processing-instruction, declaration or CDATA block (types 2-5) keeps only tags after its end marker.

`comment_text()` then removes, in this order:

1. inline code spans (set aside first; for the identity view their content is restored after the HTML filters, so a code span can name a ticket but never open or close a tag);
2. HTML comments;
3. CDATA sections;
4. HTML `pre`, `code`, `blockquote`, `q`, `samp`, `kbd`, `tt`, `var`, `xmp`, `listing`, `plaintext`, `textarea`, `script`, `style`, `template` and `noscript` content.

Container closure is name-aware (R3). A closing tag ends its own open element and anything opened inside it, and one naming no open container closes nothing. An unclosed container or CDATA section hides the rest of the comment. Each removed span becomes one space, so no remainder can begin a heading. These are bounded parsers, not a complete Markdown/HTML renderer. Signal JSON shape is unchanged; `universal-mutation-gate.sh` is not modified.

## Test plan

- `hooks/_test/gate_bypass_1164.py` (run by `gate_bypass_1164.test.sh`):
  - B1: all 10 main-review payloads plus 24 extra shapes against the real guard (21 through fix round 2, 3 added in fix round 3). Refusals must name "asserts completion status".
  - B2: all 13 main-review fixtures plus 36 extra shapes (27 through fix round 2, 9 added in fix round 3).
    - Each runs the real writer, then the unchanged universal-mutation-gate on both an existing and a missing hook target.
    - The writer reads from a fake `gh` that applies the writer's actual query to raw API records with real `jq`.
    - Refused cases need all four signals false with `api_reachable` true and gate exit 2. Counted cases need all four true and exit 0.
  - Review corpus, loaded from `gate_bypass_1164_review_cases.json`: 46 B1 and 27 B2 exact cases from the 371c4fe review (fix round 1), 17 B1 and 19 B2 from the 530beaa review (fix round 2, prefix `r2/`), and 23 B1 and 22 B2 from the 28b34e1 review (fix round 3, prefix `r3/`). Four r3 B1 rows are N2 and marked `held`: they are recorded with their observed results and skipped with that reason, never asserted as passing behavior.
- Five accepted fixtures relied on the label exemption: three in `hooks/_test/coordinator_status_guard.test.sh` and two in `hooks/_test/artifact_result_followup.py`. They are reworded to modal form with the same intent, and their old wording is added as refusal cases. No refusal expectation is relaxed; `test_hypothetical_text_cannot_supply_actual_completion_evidence` still refuses.
- `hooks/_test/pipeline_review_headings_1164.test.sh`: the fake `gh` now emits attributed records (MEMBER). All its expectations are unchanged.

## Before and after

`coordinator-status-guard.sh` and `pipeline_state.py` are byte-identical on main 9f47b035 and develop 1cd83f95, so the develop column is also main.

| B1 payload (guard exit) | develop | this branch |
|---|---:|---:|
| original_mitigation | 0 | 2 |
| original_frontmatter | 0 | 2 |
| conditional_no_split | 0 | 2 |
| wrapped_mitigation | 0 | 2 |
| original_conditional | 2 | 2 |
| original_field_conditional | 2 | 2 |
| original_split_sentence | 2 | 2 |
| conditional_comma | 2 | 2 |
| plain_claim_control | 2 | 2 |
| genuine_hypothesis_control | 0 | 0 |

| B2 fixture (Junior, Senior, investigation, pre-mortem flags / gate exit, existing and absent target) | develop | this branch |
|---|---|---|
| wrong_ticket | TTTT / 0 0 | FFFF / 2 2 |
| outsider_author | TTTT / 0 0 | FFFF / 2 2 |
| html_pre_code | TTTT / 0 0 | FFFF / 2 2 |
| html_blockquote | TTTT / 0 0 | FFFF / 2 2 |
| original_fenced_example | FFFF / 2 2 | FFFF / 2 2 |
| unlabelled_code_fence | FFFF / 2 2 | FFFF / 2 2 |
| tilde_code_fence | FFFF / 2 2 | FFFF / 2 2 |
| indented_fence_3_spaces | FFFF / 2 2 | FFFF / 2 2 |
| indented_code_4_spaces | FFFF / 2 2 | FFFF / 2 2 |
| markdown_blockquote | FFFF / 2 2 | FFFF / 2 2 |
| cross_comment_boundary | FFFF / 2 2 | FFFF / 2 2 |
| empty_control | FFFF / 2 2 | FFFF / 2 2 |
| plain_heading_control | TTTT / 0 0 | TTTT / 0 0 |

Revert proofs at da86bfd:

1. Develop's guard: 13 B1 cases fail, the 4 reported among them.
2. Develop's writer: 15 B2 cases fail with the actual bypass (TTTT, gate 0), the 4 reported among them.
3. HTML-container stripping alone disabled: exactly the 5 HTML-container cases fail.

## Peer review

- Syntax: `bash -n` of the guard and `py_compile` of the writer and the test module.
- Behavior: the B1/B2 probes were run against both develop and this branch. The before/after table is in the PR body.
- Real data: the new writer, run against the live #1164 comments, still reports all four signals true. Those comments are MEMBER-authored, and some mention `<pre>`/`<blockquote>` inside inline code.

## Lead review

- Scope of the guarantee. These are bounded lexical rules, not general factual understanding. The fix closes every reported payload and the tested shapes in `gate_bypass_1164.py`, including the full 371c4fe review corpus. It does not prove that no other English or HTML/Markdown construction evades them. The 371c4fe review showed an earlier "class-level" claim here was false (R1-R3).
- Known costs and limits:
  - Indicative risk or criteria wording now needs a modal or conditional, or evidence. The original #1164 outcome "No wording workarounds needed" no longer holds.
  - Evidence wrapped across lines no longer counts.
  - A modal does not carry over `and`.
  - Some parenthetical and causal conditional forms stay ambiguous and are accepted, as at develop.
  - The evidence model stays lexical.
  - Any author with the OWNER, MEMBER or COLLABORATOR role counts as approved, including a record without a login.

## Rework ledger

- Draft 1 removed HTML containers without first removing inline code. The live #1164 comments mention `<pre>` in inline code, which would have hidden their later real headings. Code spans are now removed first, and `inline_code_tag_mention_counts` covers this.
- Raising on bare string records would have taken the API-error path, which keeps the last-known-good signal. They are now skipped as unattributed instead, which is fail-closed.
- Draft 1 dropped the label set entirely. That let Scenario text supply evidence, which `test_hypothetical_text_cannot_supply_actual_completion_evidence` forbids. Its `:` split also broke `https://` evidence lines. Labels are now kept for evidence exclusion only, URLs are not split, and evidence is matched per line. `label_cannot_supply_evidence` and `url_evidence_line_passes` cover both.

## Fix round 1 (review of 371c4fe: REJECT)

Findings: https://github.com/siege-analytics/claude-configs-public/pull/1212#issuecomment-6694073952

- **R1:** a modal or interrogative approval question supplied owner evidence. The guard went from develop 2 to 371c4fe 0 in 6 variants. Fixed by the evidence-eligibility rule above.
- **R2:** YAML `ticket_refs:` lists, same-number foreign repositories, URL lists and wrapped `Ticket:` values were not checked. Fixed by collecting each declaration's full value.
- **R3:** a mismatched closing tag (`</blockquote>`, `</code>`) ended an open `<pre>`, and CDATA content counted. Fixed by name-aware closure and CDATA removal.
- **R4:** `git init` in the test helper had no timeout. Now `timeout=10`.
- **R5:** claims narrowed (Lead review), the modal grammar described exactly (Design), and the wording-workaround behavior change stated.

All 46 B1 and 27 B2 cases of the reviewer's corpus are ported byte-for-byte as `hooks/_test/gate_bypass_1164_review_cases.json`. The 10 B1 and 13 B2 original payloads were already in `gate_bypass_1164.py`. Each case's expected value is the reviewer's observed 371c4fe result, with two kinds of exception:

- The R1/R2/R3 cases now refuse. `real_headings_after_pre_control` (four real headings after a closed `pre`) still counts.
- `evidence_split_owner` and `evidence_split_role` (approval wrapped across lines) went from 0 at both develop and 371c4fe to 2. This is a deliberate consequence of per-line evidence. The reviewers classified it as a newly refused, non-blocking compatibility cost (corrected in fix round 3; an earlier version of this paragraph wrongly called it inherited).

## Fix round 2 (review of 530beaa: REJECT)

Findings: https://github.com/siege-analytics/claude-configs-public/pull/1212#issuecomment-6700795795

- **F1:** quoted, field-prefixed, unmarked and `?!` questions supplied owner evidence. Fixed by `artifact_is_question` on each sentence and clause, after leading wrappers are skipped.
- **F4:** "May 5", "operator Will", "owner Will approved" and `/may/`/`/will/` URL segments wrongly removed real signoff (an over-refusal introduced in round 1). Fixed by `artifact_has_modal` on original-case text, with URIs opaque.
- **F3:** a `<blockquote>` closed without a following blank line exposed later headings. Fixed by CommonMark HTML-block recognition in `markdown_lines`.
- **F2 (hub decision A, whole-region identity):**
  - YAML front matter is not parsed. At 530beaa+F2 (829815b) the rule was "at least one reference must be current"; fix round 3 (N1) replaces it with the hub's controlling rule: every reference must be current.
  - Body `Ticket:`/`Refs:` values continue across blank lines while indented or list-item lines follow.
  - Identity is read from a view where inline code is unwrapped, before code spans are erased for heading detection.
  - Accepted cost: front matter or a `Refs:` list naming only foreign tickets is excluded, even when it is meant as a bibliography (strict identity policy).
  - The "mixed current+foreign front matter still counts" cost recorded at this round was a hub drafting error and is withdrawn (hub ruling 2026-11-07); mixed front matter is excluded from fix round 3 on.
- **Note for whoever owns hook-runtime dependencies:** no YAML parser is available to hooks as installed on this host.
  - The Craft router (`hooks/lib/craft-settings-router.py`) runs hooks as `python3 -I -B` with `#!/usr/bin/env python3` shebangs, so they get the first `python3` on the app PATH.
  - Here that is `/Library/Developer/CommandLineTools/usr/bin/python3` 3.9.6, which cannot import PyYAML.
  - `bin/install.sh` requires PyYAML only for the build. `hooks/git/decomposition-guard.sh` imports `yaml` and silently skips when it is missing, which is acceptable for an advisory warning but would be fail-open in a security gate.
  - A parser-based approach needs PyYAML declared and verified as a hook-runtime dependency first.
- **B1 direction:** lexical owner-signoff checking may be replaced by a structural check verified through the GitHub API, as Deep Think advises. That would be a separate PR after a Root/Dheeraj design decision; further lexical B1 hardening is held.
- **Corrections:**
  - the PR body's extra-B1 count;
  - split owner/role evidence described as newly refused;
  - foreign wrapped `Refs` documented under the strict identity rule.

The 17 B1 and 19 B2 round-2 reviewer cases are ported byte-for-byte into the corpus. The writer is also exercised under the 3.9.6 hook-runtime interpreter.

## Fix round 3 (review of 28b34e1: REJECT)

Findings: https://github.com/siege-analytics/claude-configs-public/pull/1212#issuecomment-6710468304

- **N1 (B2):** mixed current+foreign front matter still counted. Fixed: the whole front-matter region of the raw comment must name only the current ticket. The module case is now `front_matter_mixed_current_and_foreign_excluded`, and `yaml_ticket_refs_with_current_counts` (also mixed) became `yaml_ticket_refs_mixed_excluded`.
- **N3 (B2):** processing-instruction, declaration and `<div>`/`<span>` HTML-block content still fed the keyword-stem fallback, and a type-7 block after a thematic break was missed. Fixed as a class by `block_kinds()`: one classifier for headings, stems and identity; HTML-block text is removed rather than indented, and paragraph state resets on thematic breaks, setext underlines and indented code.
- **N4 (B2):** a foreign `Ticket:` inside an HTML comment or `<pre>` example excluded real current-ticket artifacts after it. Fixed by reading body identity from the same eligible text, with inline code restored after the HTML filters.
- **N5 (B1):** "Owner: has approved", "had approved" and "has signed off" were read as inverted questions; "Owner: Will approved" and "The owner Will/May has approved" were read as modals. Fixed by the finite-auxiliary-plus-participle rule and by treating a field value as not sentence-opening, with has/had/is/was/did/does marking a name.
- **N6 (docs):** PR body updated to the current design and counts (B1 module 34 = 10 + 24, including the 31 = 10 + 21 of fix round 2), the structural-redesign note and the strict front-matter rule; the split owner/role attribution above is corrected.
- **N2 (B1): HELD, not worked.** Modal scope does not carry across parenthetical separators ("Owner: could, in principle, already have approved the rollout"), a quoted conditional opener escapes conditional detection, and a wh-question without a mark is accepted. This waits on the Root/Dheeraj structural B1 decision. It is a known residual, not a risk acceptance; the four reviewer rows are in the corpus as `held`.
- Observed, not changed: `Owner: Must approved the rollout.` and `The owner Will signed-off on the rollout.` stay refused (fail closed; the hyphenated form is not a recognized signoff predicate at develop either).

The 23 B1 and 22 B2 round-3 reviewer cases are ported byte-for-byte, with develop 6cae44a / 530beaa / 28b34e1 observations, and re-run at develop / 28b34e1 / this head under the hook runtime (`/usr/bin/python3 -I -B`, 3.9.6).

## Findings

Hostile re-review of the fix-round-3 head is PENDING with the original cross-family reviewer.
