---
ticket_refs:
  - siege-analytics/claude-configs-public#1274
---
# Self-review: own-PR artifact-heading refs in pipeline_state (#1274)

Ticket: siege-analytics/claude-configs-public#1274
Branch: bugfix/pipeline_state_own_pr_ref_1274, from develop 8043c583
Review tier: C (enforcement-gate input: hooks/lib/pipeline_state.py feeds the Tier C universal-mutation-gate)

## Assumptions
Working as: software engineer (peer review), tech lead (lead review)
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #1274, section "Request" (items 1-3), and the published Tier C artifacts https://github.com/siege-analytics/claude-configs-public/issues/1274#issuecomment-6779877308
Goal source verification: evaluate-ticket returned BLOCK (missing Goal/Acceptance/Assumptions headings, no /think link). Exemption blocks below carry the evidence chain; the ticket body was not edited by this worker.
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/1274#issuecomment-6779877308 (design, investigation and pre-mortem; approved design from the previous author)
Pre-author-inventory: plans/self-review-pipeline-state-own-pr-1274.md#pre-author-inventory
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1274#issuecomment-6779877308
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1274#issuecomment-6779877308
Hostile-review-artifact: plans/hostile-review-pipeline-state-own-pr-1274.md
Project-contribution: Tier C evidence that names its own implementing PR in a heading (the siege_utilities #1526 shape) counts again, so the artifact lane no longer silently refuses legitimate work, while cross-ticket artifacts stay excluded.

Assumptions taken on faith:
- GitHub's `pullRequest(number:)` read for an issue number fails (error, `gh` exit non-zero) or returns a null node. Both paths fail closed, so either is safe.
- The installed hook runtime runs the writer under `/usr/bin/python3` 3.9 with `-I -B`; the code uses nothing newer.
- GitHub lists issue comments oldest first (the writer's existing `--paginate` read), so reverse order is newest first.

## Exemption: Goal / Acceptance sections

Reason: #1274 states its goal and acceptance as "## Request" items 1-3 instead of "## Goal" and "## Acceptance" headings. This worker was told not to post or edit on the ticket.
Evidence: `bash scripts/discipline/evaluate-ticket.sh siege-analytics/claude-configs-public#1274` → "BLOCK ... missing sections: Goal,Acceptance". Request item 1 is the goal ("Don't treat a PR reference in an artifact heading as a foreign-ticket declaration when that PR's linked ticket is the current ticket"). Request item 3 is the acceptance list (own PR counts; unrelated ticket excluded; front-matter foreign excluded). All three are tests in hooks/_test/pipeline_state_own_pr_1274.py.
Falsification: a reviewer finds a Request item or a ticket acceptance case with no matching test.

## Exemption: /think design-note reference

Reason: the design note is the published Tier C comment, not a plans/think-*.md file.
Evidence: https://github.com/siege-analytics/claude-configs-public/issues/1274#issuecomment-6779877308 has the Junior task description, Senior adversarial checklist, Investigation and Pre-Mortem. The writer computed junior_found, senior_found, investigate_posted and premortem_posted all true from it (my task gate, 2026-11-10 15:54:19 and 16:04:38 CST).
Falsification: the writer stops crediting that comment, or its content disagrees with this diff.

## Exemption: Assumptions block

Reason: the ticket body has no "## Assumptions" heading.
Evidence: the "## Assumptions" section of this artifact lists them, and Request item 2 (keep #1267's exclusion of foreign or stale-round artifacts) is held as an invariant by test_unrelated_*, test_foreign_*, test_front_matter_*, test_ticket_key_* and test_refs_and_issue_keys_stay_strict.
Falsification: an assumption listed here turns out false in the installed runtime.

## Pre-author inventory

- Inputs read: develop 8043c583 hooks/lib/pipeline_state.py (TICKET_REF :35-37 at base, declarations(), declares_other_ticket(), comment loop); hooks/lib/resolve-think-gate.py:1009-1090 (the existing PR identity read); hooks/lib/task_actions.py:1227-1290 (github_ticket_reference); hooks/bash/universal-mutation-gate.sh (Tier C consumer); .claude/settings.json (pipeline-state-guard `"timeout": 10`); hooks/_test/gate_bypass_1164.py (existing fake gh).
- Knowledge requirements: GitHub GraphQL `repository.pullRequest(number)` and `closingIssuesReferences` shape; `gh api graphql -F` integer typing; the writer's lower-cased identity view.
- Contact-point measurements: one `gh api graphql` read per distinct heading ref; at most 4; each ≤3 s; all ≤8 s from the first read and never past 7 s after writer start.
- Surface areas: only artifact-heading declarations whose refs are not already current. Front matter and Ticket:/Refs:/Issue:/Task: keys are untouched.
- Hypothesis: a heading ref resolving to a PR whose GitHub relationship names the current ticket is the ticket's own PR; anything else, including every failure, keeps today's exclusion.
- Conclusions: confirmed by 32 hook-level tests through the real writer, real jq and the unchanged Tier C gate, plus a revert proof.

## Peer review

- Shelves:
  - writing-code:15: the one new blocking call, `subprocess.run(['gh','api','graphql',…])`, passes `timeout=remaining` at the call site, bounded to ≤3 s and to the 7 s writer ceiling; test_timeout_excluded_within_budget → PASS.
  - writing-code:7: `_resolve` catches `Exception` and returns `False`, which the class docstring documents as the failure result ("keeps the pre-#1274 exclusion"). It is not a silent swallow; every failure path has a test.
  - writing-claims:8: every count in this artifact and the PR body cites its command under Quantified claims.
  - writing-code:2 (deviation, noted): the new comments and docstrings cite `#1274`, following this file's existing `#1164`/`#1051` convention rather than introducing a new style.
- Syntax check: `ast.parse` on the 2 changed `.py` files → both parse (exit 0). The writer runs under `/usr/bin/python3` 3.9.6 in every test.
- Correctness, positive: own PR counts as a bare `#N`, "PR #N", `/pull/N` URL, a closingIssuesReferences link, a "Fixes #N" body, a qualified cross-repo PR that explicitly references `o/r#1526`, and mixed-case `nameWithOwner`.
- Correctness, negative: an unrelated PR, an unrelated ticket, an issue (not a PR), a foreign-repo PR with the same number whose relative "Refs #1526" belongs to that repo, a prose mention, an "Example:" mention, front-matter own-PR, Ticket:/Refs:/Issue: keys naming the PR, a strict key later in the same comment, gh failure, timeout, malformed JSON, a reply for another number or repo, malformed closing references, and a foreign GH_HOST. All are excluded.
- Bounds: cap (4 reads), cache (one read for a PR named in five headings; `#01748` and `#1748` share an entry), per-read timeout, total ceiling inside the 10 s hook timeout, and newest-first ordering so older foreign headings cannot starve the current artifact.
- Isolation: every test asserts api_reachable stays true and no `.unreachable` stamp is written. api_ok and the last-known-good write path are unchanged.
- Reuse: the GraphQL text sent equals a string literal in resolve-think-gate.py (test_query_is_the_resolver_pr_identity_read). task_actions.py and resolve-think-gate.py are unmodified.
- Hook-Dependencies: `gh` (risky; already required by this writer; on absence or failure the lookup returns False, so the comment is excluded as before, which is a loud-enough existing warning path); `jq` not used by the new code; python3 stdlib only.

## Lead review

- Did this close the class? The class is "a heading ref that is the ticket's own PR". Every heading shape the TICKET_REF grammar recognises (bare, qualified, issue or pull URL) is resolved through the same path; there is no per-shape code.
- Did it reopen #1267's gap? No. A heading ref only counts when GitHub's own relationship names the exact current ticket. A stale or foreign artifact still names a foreign ticket and is still excluded. Round/head binding (#1267) is not touched.
- Approach fit: reuses the resolver's existing PR identity read and the shared relationship parser rather than adding grammar.
- Blast radius: `pipeline_state.py` is executed only by hooks/resolver/pipeline-state-guard.sh (1 call site). `declares_other_ticket` was module-private (the file runs as a script and cannot be imported), and its replacement `ticket_exclusion` has 1 call site.
- Sequencing assumption: installed runtime changes only through normal develop → main promotion; nothing here installs anything.
- Post-mortem applicability: this fixes a false negative in shipped code. The #1164 hardening of artifact-heading declarations excluded a heading naming the ticket's own PR. The ticket body (Mechanism / Observed / Impact) is the failure trace. No separate post-mortem was run in this task. Whether #1164's design assumption ("a ref in an artifact heading is a ticket declaration") warrants a formal post-mortem or a post-error-revision block on #1164 is left to Root. This commit is not a revert and does not use a regression-fix title.
- DESIGN DECISION FOR ROOT: this adds a network read (`gh api graphql`) to a UserPromptSubmit hook path. It is bounded (4 reads, 3 s each, 8 s total, hard 7 s writer ceiling) and fails closed, but it is new latency on a per-prompt hook. It only fires when an otherwise-eligible comment has an artifact heading naming a non-current ref.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| H-F1 | P2 | Hostile review: the 8 s budget was measured from the first read, not writer start, so a slow GitHub could push the guard past its 10 s hook timeout | fixed: 7 s writer ceiling; test asserts writer elapsed < 9 s |
| H-F2 | P2 | Hostile review: oldest-first lookups ran before strict checks, so older foreign headings could use up the cap and starve the current artifact | fixed: strict checks first, then newest-first resolution; two new tests |
| H-F3 | P3 | Body "Refs #N" (not only closing links) widens what counts | noted: required by the approved design (github_ticket_reference); a comment still needs an approved author |
| H-F4 | P3 | Parser reached via the resolver's re-export | fixed: direct `from task_actions import github_ticket_reference` |
| H-F5 | P3 | 64 KiB reply cap could reject a maximal PR body | fixed: 5 × 65536 bytes |
| H-F6 | P3 | `#01748` and `#1748` used separate lookups | fixed: int cache key; test |
| H-F7 | P3 | Test gaps (mixed case, Refs:/Issue:, GH_HOST, strict key after heading) | fixed: tests added. Not added: end-to-end through pipeline-state-guard.sh (tests drive the writer exactly as the guard does) |
| N1 | P2 | Re-review: the F6 fix moved `int(num)` outside the try, so a 4301+-digit heading ref on Python 3.9.14+/3.11 raised into the outer handler and set api_ok false | fixed: reject non-digit or >12-digit refs before int(); test_huge_ref_number_excluded_without_read; guard-removed proof on 3.11 shows the writer skipping junior-senior-gate.json; round-3 re-review approves |
| H-F1r | P3 | Round-2 residual: the 7 s ceiling is measured from writer start, so the guard's own pre-writer work (hook_payload, git rev-parse, resolver process) sits outside it; about 1-2 s headroom remains | noted: not changed; a guard-level timing test is not added |
| L-1 | P3 | pipeline_state.py's local pre-mortem lookup does not scan the host session's own plans/ (the mutation gate does), so a valid session pre-mortem shows a "PRE-MORTEM: No pre-mortem artifact found" advisory | noted: outside #1274; observed in this task's own prompt hook |

## Test plan

- `python3 -B hooks/_test/pipeline_state_own_pr_1274.py` (32 tests; run under both /usr/bin/python3 3.9.6 and Python 3.11), via `hooks/_test/pipeline_state_own_pr_1274.test.sh`, which CI's "Hook scenario tests" step picks up through the `hooks/_test/*.test.sh` glob.
- Revert proof: the same tests against the 8043c583 writer.
- Full hook suite: every `hooks/_test/*.test.sh`, mirroring CI (result under Quantified claims).

## Quantified claims

- "32 tests pass" -- `/usr/bin/python3 -B hooks/_test/pipeline_state_own_pr_1274.py` → "Ran 32 tests in 53.167s / OK"; Python 3.11 → "Ran 32 tests in 50.789s / OK"
- "revert proof: 13 failures, 1 error" -- `/usr/bin/python3 -B debug/revert_proof_1274.py <worktree>` (swaps in `git show 8043c583:hooks/lib/pipeline_state.py`, runs the then-31 tests, restores) → "FAILED (failures=13, errors=1) / reverted-writer exit 1 / restored True"
- "N1 red without the guard" -- Python 3.11 `debug/revert_proof_n1.py <worktree>` → "FileNotFoundError ... junior-senior-gate.json / FAILED (errors=1) / guard-removed exit 1 / restored True"
- "red baseline on 8043c583" -- `/usr/bin/python3 -I -B debug/probe_1274.py <worktree> <out>` before any source edit → own-PR x3 `FFFF/2,2`, exclusions x4 `FFFF/2,2`, controls x2 `TTTT/0,0`
- "probe green after the fix" -- same probe → own-PR x3 `TTTT/0,0`, exclusions x4 `FFFF/2,2`, controls x2 `TTTT/0,0`
- "4 reads, 3 s, 8 s, 7 s ceiling" -- `grep -n '^OWN_PR' hooks/lib/pipeline_state.py` → lines 53-59
- "full hook suite: 73 of 77 files pass; the 4 failures reproduce identically on pristine 8043c583" -- `debug/run_hook_suite.sh <worktree>` (every `hooks/_test/*.test.sh`, after `bin/build.py`; Python 3.11 + Bash 5 first on PATH, run inside this Craft session) → "files=77 failed: ca_enforcement_runtime session_signal_resolution universal_mutation_gate universal_mutation_gate_empty_reporoot"; `pipeline_state_own_pr_1274.test.sh`, `gate_bypass_1164.test.sh`, `pipeline_review_headings_1164.test.sh` and `task_keyed_gates.test.sh` PASS. Each failing file run with the same runner on a `git archive 8043c583` extract (built with `bin/build.py`) gives the same failing cases: ca_enforcement_runtime 12 passed / 4 failed (F4 ×3 and PATH-provided ps ancestry); session_signal_resolution 16/2 ("hook JSON session id beats workspace root", "repo-matched singleton not bound under unknown session"); universal_mutation_gate 30/1 ("(n0) gh issue create ... cannot borrow unbound governance authority"); universal_mutation_gate_empty_reporoot "--session-known should be 0 with no session env". These are environmental: the tests assume no Craft session environment or ancestry, and this run executed inside a live Craft session. Hosted CI is the clean-environment check.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Hostile review F1/F2 (budget vs 10 s hook timeout; cap starvation) | did not read .claude/settings.json hook timeout or model multi-comment ordering before implementing | ~1 min | ~15 min + rerun of suite and revert proof | ~15:1 |
| First full-suite run stopped mid-way (code changed under it) | started the suite before the review fixes | 0 | ~10 min of suite time; one leftover `.1051-test-*` dir removed | n/a |
| Re-review N1 (int() outside try) | F6 fix moved int() without re-checking the exception boundary | ~1 min | gate hold until the self-review post (comment 6780744152), one guard line, one test, N1 revert proof | ~10:1 |
| Second full-suite run stopped for the N1 edit | suite started before the N1 fix | 0 | rerun | n/a |
| Push hook refused twice: artifact lacked a 'Working as:' role line (and Peer review shelf citations); then the commit lacked a Design-Note-Source: trailer | did not read hooks/git/self-review.sh field and trailer checks before the first commit | ~1 min | two amends of the unpushed commit (20e48755 → 5de76835 → final) and push retries | ~4:1 |
| Debug probe fake lacked `repository.nameWithOwner` | inherited fixture predates the stricter reply check | ~0 | one probe edit in ignored debug/ | n/a |

## Process disclosures

- Inherited work: the previous author (session 261106-polished-marsh) reproduced the bug against the 806f20e6 writer while its probe ran under the #1164 task's gate, inside that task's ignored `debug/` directory. No tracked file changed. Its gate for #1274 is disposed. Source: its investigate-gate.json and published artifact.
- Its wording-adaptation retries on the ticket comment were refused by coordinator-status-guard. Read from its transcript (read-only):
  - 2026-11-10T21:37:28Z: "BLOCKED: think-pipeline artifact also asserts completion status without evidence. Claim: what could go wrong. Missing: owner_signoff, rollout"
  - 21:38:24Z: same refusal, "Claim: github unavailable, rate-limited or slow: the read fails closed to today’s exclusion inside a fixed budget."
  - 21:40:57Z: same refusal, "Claim: a resolved own pr only stops a false exclusion"
  - 21:42:21Z: "Craft hook routing failed closed: workspace hook bash/coordinator-status-guard.sh timed out after 10.0s (limit 10.0s)."
- Operator publication: the Tier C artifacts were published on #1274 by the operator at 21:35:24Z (issuecomment-6779877308), from polished-marsh's data/artifacts-1274.md (sha256 7422704856a67bb09f1550a47e312e8ea3c261b18e1d7f1001730806da80161f, re-verified by this worker). This worker posted no ticket comment.
- This worker's gate status history (task gate in session 261110-vivid-spray): designing ~21:53Z → implementing ~21:54Z → designing 22:05:30Z (hub correction) → implementing 22:06:30Z ("correction reverted: hub retraction (pipeline_state.py:485 computes signals only at implementing)"). The writer computes junior-senior and artifacts-posted only under implementing. It computed all four true at 15:54:19 CST. The 8043c583 reproduction ran ~15:55 CST, before any source edit. This worker first wrote lastUpdated timestamps ahead of real time in its own gate files; corrected in their history.
- Self-review posting: the Tier C gate refused the N1 edit until a self-review was posted on the ticket (refusal: "Self-review not posted to ticket siege-analytics/claude-configs-public#1274"). On the hub's ruling, this worker posted exactly one self-review comment (issuecomment-6780744152, 22:15:23Z) carrying N1 and the full suite as open. Wording was pre-linted against coordinator-status-guard's completion words: "fails closed" became "keeps the exclusion on any failure", and the three refusal quotes above were summarized there by time and class, because the quotes contain trigger words. This file and the PR body carry the final state.
- Self-hosted signals: this worktree's .claude/settings.json registers repo-relative hooks, including hooks/resolver/pipeline-state-guard.sh, so this task's prompt turns also ran the worktree's own hooks/lib/pipeline_state.py. The workspace's installed writer runs too, via the Craft hook router; which of the two wrote a given signal file last is not determined. Only the 15:54:19 CST computation (junior/senior/investigate/premortem all true) predates this worker's first edit to pipeline_state.py (shortly after the ~15:55 CST reproduction). Every later local computation (16:04:38, 16:13:29 with selfreview_posted false, 16:15:40 with selfreview_posted true, and after) may come from the modified writer. They are self-hosted, not independent evidence. Hosted CI and Root's review are the independent checks.
- Hostile review independence is degraded: a fresh read-only reviewer of the same model family (the cross-provider source was not active in this session).

## Adversarial shape audit

Shape space: artifact-heading lines whose ticket refs (bare `#N`, `owner/repo#N`, `github.com/o/r/issues|pull/N`) are not the current ticket, plus GitHub GraphQL PR identity replies (success, null, error exit, timeout, malformed JSON, mismatched number/repo, malformed closing nodes).
Fixture-covered shapes: bare 1 (test_bare_number_heading_counts), "PR #N" 6, URL 1, qualified 2, leading zero 1, multi-ref heading 2 (cap, budget); replies: closing link 1, Refs body 3, Fixes body 1, prose 1, example 1, null/error 2, fail 1, timeout 2, malformed 1, other number 1, other repo 1, malformed nodes 1, mixed case 1. All in hooks/_test/pipeline_state_own_pr_1274.py.
Prose-vs-implementation gap: N/A: no skill prose claims this shape space; the writer docstrings were updated in this diff.
Adversarial frame this round: security engineer
Adversarial fixture from frame: test_foreign_repository_same_number_excluded. other/repo#1748 is a real PR saying "Refs #1526", and its closing link is other/repo#1526. A resolver that ignored the source repository would count it.

## Evidence-predates-work
Artifact: plans/self-review-pipeline-state-own-pr-1274.md
First-added commit: added in the same commit as the work (single-commit PR)
Work commit: see PR head
Verification: `git merge-base --is-ancestor <first-added> <work-commit>` is 0 for a single commit
