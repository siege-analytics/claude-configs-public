---
ticket_refs:
  - siege-analytics/claude-configs-public#1274
---
# Hostile review: own-PR artifact-heading refs in pipeline_state (#1274)

Ticket: siege-analytics/claude-configs-public#1274
Reviewer: a fresh read-only reviewer with no implementation context, prompted to break the diff against the ticket's requirements. It was not told the author's conclusions. Independence is degraded: same model family as the author, because the cross-provider review source was not active in the authoring session.
Target: worktree diff against develop 8043c583 (hooks/lib/pipeline_state.py, hooks/_test/pipeline_state_own_pr_1274.{py,test.sh}).
Role limits given: review only; no edits, mutating git commands or GitHub posts.

## Root review @ 05ecbbfb (P1)

Source: pullrequestreview-5853528515 (03:40:54Z), relayed by hub 261110-fit-boulder from Root outbox entry 249. Root had accepted 35ea7797 with no source finding (pullrequestreview-5853167730). On the round-2 delta it found a P1: `relationship_body` erased all list padding, so `-     Refs #1526` and `1.     Refs #1526`, which are CommonMark indented code, made all four signals true and the gate 0/0. Root's private proof: E/core1279-indented-list-delta-proof-20261111.json.

Author response in round 3:
- The marker now strips only 1-4 ASCII spaces followed by text.
- A list item whose content is code is rewritten as indented code, because the shared parser's `. ` clause split would otherwise read `1.     Refs #N`.
- Leading indent is spaces only.
- Tests: Root's 2 negatives, 4 tab/mixed-padding negatives, and 1 ordinary numbered / 4-space positive. The 10 round-2 delta controls are retained.

The re-review's N-S3-1 (per-clause reduction) is left as a follow-up.

## Recovery review @ 35ea7797 (separate reviewer session, same model family)

Source: https://github.com/siege-analytics/claude-configs-public/pull/1279#issuecomment-6785649710 (posted 2026-11-11T02:58:27Z). It replaced the assigned cross-family review, whose reviewer failed at startup with an expired provider token, so cross-family review is still owed. Verdict ACCEPT; S1 0, S2 3, S3 4; no merge blockers. Author response in round 2, on hub instruction:
- S2-1 (GraphQL failure keeps returning False with api_ok true): not changed; Root's design decision.
- S2-2 (bulleted/annotated Refs lines): fixed with `relationship_body()` inside OwnPullRequests. Positive tests for bulleted refs, fixes, qualified refs and 3 annotated forms; negatives for a bulleted foreign ref, a ticket only in an annotation, bulleted prose mentions, and bulleted Example/fence/quote forms.
- S2-3 (mixed headings): test added; the reviewer's mutant now fails it.
- S3 notes: carried to Root as follow-ups.

## Round 1 (initial diff, 25 tests)

Verdict: approve with notes. No S1.

| ID | Sev | Finding | Author response |
|---|---|---|---|
| F1 | S2 | 8 s budget measured from the first read, not writer start; guard runs under a 10 s hook timeout (.claude/settings.json), so slow GitHub could get the hook killed with no signals written | Added a 7 s ceiling from writer start; test asserts writer elapsed < 9 s |
| F2 | S2 | Oldest-first reads before strict checks; four older foreign headings exhaust the cap and the current artifact is still dropped | ticket_exclusion() strict pass first; reads newest comment first; 2 tests |
| F3 | S3 | Body `Refs #N` (not only closing links) widens what counts | Kept: the approved design names github_ticket_reference; documented |
| F4 | S3 | Parser reached through the resolver's re-export; a rename would silently disable resolution | Direct `from task_actions import github_ticket_reference` |
| F5 | S3 | 64 KiB reply cap rejects a near-maximal PR body | 5 × 65536 bytes |
| F6 | S3 | `#1748` and `#01748` use separate reads | Cache key on int |
| F7 | S3 | Missing tests: mixed-case nameWithOwner, Refs:/Issue: keys, GH_HOST, strict key after heading | Added |

Clean checks the reviewer reported: front matter and keys stay strict; repository scoping; exceptions never reach api_ok; subprocess timeouts kill and wait; no shell or flag injection (argv list, REPO_NAME, int pr); `#0` rejected; Python 3.9 compatible.

## Round 2 (after F1-F7)

Verdict: request changes (N1 only).
- F1 partially resolved: the 7 s ceiling is measured from writer start, so the guard's own pre-writer work and interpreter start-up sit outside it (about 1-2 s headroom remains). Noted S3; a guard-level timing test is not added.
- F2, F4, F5, F6, F7 resolved. The reviewer checked the two-pass loop: `kept` ordering, zip alignment, `all([])` for comments without pending refs, and early return on strict keys.
- N1 (S2, new): the F6 fix moved `int(num)` outside the try. A 4301+-digit heading ref on Python 3.9.14+/3.11 raises ValueError into the outer handler and sets api_ok false. Author fix: reject non-digit or >12-digit refs before int(). Test test_huge_ref_number_excluded_without_read. Proof without the guard on 3.11: the writer writes no junior-senior-gate.json (api_ok false path).

## Round 3 (N1 re-review)

Verdict: approve with notes.
- N1 fixed in the reviewer's assessment. TICKET_REF captures only ASCII `[0-9]+`, so after the `isdigit()` and ≤12-digit check, `int()` cannot raise. 12 digits is inside both the GraphQL Int range and Python's digit limit. A ref padded past 12 characters with leading zeros now stays excluded, which the reviewer accepted.
- No other escape path found: `ticket_refs` and `ticket_exclusion` do only regex and string work with no int() or I/O; in the two-pass loop only `own_pr(ref)` can fail, and its key is now safe while `_resolve` catches Exception; `kept` is booleans.
- The reviewer did not run the tests (asked not to, during the suite run). It relied on the author's 3.11 guard-removed proof for the red result.
- Residual notes carried to the PR: F1 headroom (guard pre-writer work sits outside the 7 s ceiling) and F3 (Refs-in-body widening, as designed).
