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

B1, `hooks/bash/coordinator-status-guard.sh`. A field label no longer exempts anything. Every line is scanned for claims: labelled lines, YAML front matter and wrapped lines alike. The label set (`ARTIFACT_HYPOTHETICAL_FIELDS`) and its indented-continuation state are kept for one purpose only. Text under a hypothetical field still cannot *supply* evidence, so a label can only make the check stricter. Each line is split into sentences (`;.!?`) and clauses (`,`, `:` but not `://`, dashes, `then`), and evidence is matched per line. A completion word is hypothetical in only two cases:

- a modal governs it, directly for `go`/`complete` or through linking verbs ("could be green", "should not be merged", "to be done"). A bare `to` ("set to done") does not hedge.
- it sits in a clause that opens with a subordinator (if, when, unless, until, once, ...) and is followed by a non-empty consequent clause in the same sentence.

Masked words supply neither claims nor evidence. The lane's entry rules, the evidence predicates and the status lane are unchanged.

B2, `hooks/lib/pipeline_state.py`. The comment query now projects `user.login`, `author_association` and `body`. A comment counts only when both hold:

- its author is the authenticated `gh api user` login, or GitHub attests OWNER, MEMBER or COLLABORATOR. A failed actor lookup falls back to the attested roles only. A bare string record counts as unattributed and is skipped.
- no Ticket/Task/Issue/Refs declaration line and no artifact heading names only other tickets. Supported forms are `#N`, `owner/repo#N` and GitHub issue/PR URLs. A same-number reference in another repository is a different ticket.

`comment_text()` keeps the fence filter, then removes inline code spans, HTML comments and nesting-aware HTML `pre`, `code`, `blockquote`, `q`, `samp`, `kbd`, `tt`, `var`, `xmp`, `listing`, `plaintext`, `textarea`, `script`, `style`, `template` and `noscript` content. An unclosed container hides the rest of the comment. Each removed span becomes one space, so no remainder can begin a heading. Signal JSON shape is unchanged; `universal-mutation-gate.sh` is not modified.

## Test plan

- `hooks/_test/gate_bypass_1164.py` (run by `gate_bypass_1164.test.sh`):
  - B1: all 10 review-harness payloads plus 15 extra shapes against the real guard. Refusals must name "asserts completion status".
  - B2: all 13 review-harness fixtures plus 18 extra shapes. Each runs the real writer, with a fake `gh` that projects raw API records exactly as the writer's query does, followed by the unchanged universal-mutation-gate on both an existing and a missing hook target. Refused cases need all four signals false with `api_reachable` true and gate exit 2; counted cases need all four true and exit 0.
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

- The fix is class-level: no label, front matter, wrapping or comma placement can exempt factual completion wording. Unattributed, outsider and other-ticket comments never count. Code and quotation containers never count.
- Known costs and limits are recorded in the PR: indicative risk wording now needs a modal or conditional, a modal does not carry over `and`, inline-only ticket declarations are checked (not YAML lists), and the evidence model stays lexical.

## Rework ledger

- Draft 1 removed HTML containers without first removing inline code. The live #1164 comments mention `<pre>` in inline code, which would have hidden their later real headings. Code spans are now removed first, and `inline_code_tag_mention_counts` covers this.
- Raising on bare string records would have taken the API-error path, which keeps the last-known-good signal. They are now skipped as unattributed instead, which is fail-closed.
- Draft 1 dropped the label set entirely. That let Scenario text supply evidence, which `test_hypothetical_text_cannot_supply_actual_completion_evidence` forbids. Its `:` split also broke `https://` evidence lines. Labels are now kept for evidence exclusion only, URLs are not split, and evidence is matched per line. `label_cannot_supply_evidence` and `url_evidence_line_passes` cover both.

## Findings

Hostile re-review of this head is PENDING with the original cross-family reviewer.
