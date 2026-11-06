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

**Evidence (fix round 1, R1).** Eligibility is decided separately from masking. A clause supplies owner/merge/rollout evidence only if all of these hold:

- it is not in a question, meaning a sentence that ends with `?` or opens with did/does/do/has/have/had/is/are/was/were/am;
- it contains no modal word anywhere;
- it is not a hypothetical conditional clause;
- it is not under a hypothetical field (`ARTIFACT_HYPOTHETICAL_FIELDS`, wrapped continuation included).

Each evidence predicate must match within a single line (`artifact_missing_evidence`). A line break therefore ends a match, so `Owner:` on one line and `approved.` on the next do not combine. The lane's entry rules, the evidence predicates themselves and the status lane are unchanged.

B2, `hooks/lib/pipeline_state.py`. The comment query now projects `user.login`, `author_association` and `body`. A comment counts only when both hold:

- its author is the authenticated `gh api user` login, or GitHub attests OWNER, MEMBER or COLLABORATOR. A failed actor lookup falls back to the attested roles only. A bare string record counts as unattributed and is skipped.
- no ticket declaration names only other tickets (fix round 1, R2). A declaration is one of:
  - an artifact heading line;
  - a Ticket/Task/Issue/Refs/`ticket_refs` key together with its entire value: its inline text plus every following indented or list-item line. This covers YAML `ticket_refs:` lists and wrapped `Ticket:` values.

  Supported reference forms are `#N`, `owner/repo#N` and GitHub issue/PR URLs. A same-number reference in another repository is a different ticket. A declaration that also names the current ticket still counts, as does a comment with no declaration.

`comment_text()` keeps the fence filter, then removes, in this order:

1. inline code spans;
2. HTML comments;
3. CDATA sections;
4. HTML `pre`, `code`, `blockquote`, `q`, `samp`, `kbd`, `tt`, `var`, `xmp`, `listing`, `plaintext`, `textarea`, `script`, `style`, `template` and `noscript` content.

Container closure is name-aware (R3). A closing tag ends its own open element and anything opened inside it, and one naming no open container closes nothing. An unclosed container or CDATA section hides the rest of the comment. Each removed span becomes one space, so no remainder can begin a heading. These are bounded parsers, not a complete Markdown/HTML renderer. Signal JSON shape is unchanged; `universal-mutation-gate.sh` is not modified.

## Test plan

- `hooks/_test/gate_bypass_1164.py` (run by `gate_bypass_1164.test.sh`):
  - B1: all 10 main-review payloads plus 18 extra shapes against the real guard. Refusals must name "asserts completion status".
  - B2: all 13 main-review fixtures plus 21 extra shapes.
    - Each runs the real writer, then the unchanged universal-mutation-gate on both an existing and a missing hook target.
    - The writer reads from a fake `gh` that applies the writer's actual query to raw API records with real `jq`.
    - Refused cases need all four signals false with `api_reachable` true and gate exit 2. Counted cases need all four true and exit 0.
  - Review corpus (fix round 1): 46 B1 and 27 B2 exact cases from the 371c4fe review, loaded from `gate_bypass_1164_review_cases.json`.
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
- `evidence_split_owner` and `evidence_split_role` (approval wrapped across lines) went from 0 at both develop and 371c4fe to 2. This is a deliberate consequence of per-line evidence, which the review listed as inherited and non-blocking.

## Findings

Hostile re-review of the fix-round-1 head is PENDING with the original cross-family reviewer.
