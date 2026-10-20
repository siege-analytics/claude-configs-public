---
ticket_refs:
  - siege-analytics/claude-configs-public#994: file-backed commit messages
---

# Self-review: #994 narrow effective-message handling

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: siege-analytics/claude-configs-public#994 plus operator decision https://github.com/siege-analytics/claude-configs-public/issues/994#issuecomment-6296565616
Goal source verification: `evaluate-ticket.sh` reports that the old issue body lacks the current Context/Goal/Acceptance, think-note, and Assumptions structure; the operator decision and evidence-chain exemption below supply the approved execution contract.
Plan reference: plans/self-review-994-file-message.md#scope-and-design
Pre-author-inventory: plans/self-review-994-file-message.md#pre-author-inventory
Investigate-artifact: plans/self-review-994-file-message.md#pre-author-inventory
Pre-mortem-artifact: plans/self-review-994-file-message.md#pre-mortem-summary
Hostile-review-artifact: plans/hostile-review-994-file-message.md
Project-contribution: closes the direct explicit-message enforcement gap without reviving stale PR #998 or expanding into #1107 dispatch work.

### Ticket-fitness exemption

Reason: #994 predates the current ticket-body schema, but Dheeraj's later decision fixes the branch, supported forms, exclusions, tests, docs, push, and PR contract.
Evidence: `bash scripts/discipline/evaluate-ticket.sh siege-analytics/claude-configs-public#994` reports only missing structural sections; the approved scope is recorded at the operator decision URL above and reproduced below.
Falsification: this exemption fails if that comment does not authorize the stated scope, if the implementation broadens beyond the exact-head rework authorization, or if #994 was withdrawn before these commits.

### Scope and design

- Resolve direct literal `git commit` messages from `-m`/`--message`, repeated paragraphs, unambiguous long prefixes, clustered `-am`, quoted-delimiter heredocs (including tab-stripping `<<-`), `--trailer`, and bounded regular `-F`/`--file` sources.
- Consume value-taking commit options so their values cannot be reinterpreted as message flags.
- Apply CLI or configured cleanup plus Git's `-e`/`--edit` default-strip choice before ticket grammar, using the default `#` comment marker. Custom comment configuration remains #1112 work.
- Keep the fast literal prefilter, `ct_is_git_commit`, repository scope check, amend/no-edit behavior, and `read-only-command.py` ownership.
- Fail closed for direct messages that cannot be modeled and for missing, unreadable, non-regular, oversized, stdin, duplicate-file, and mixed sources.
- Keep aliases, wrappers, compound commands, editor mutation, tilde expansion, `-qF`, and dynamic dispatch in the follow-up scope named by the exact-head review.

### Pre-author inventory

Develop at `101f75439bd351bf0bba9b512b2cbdc14eb37c5c` scanned the command string after literal commit and scope detection. The baseline ticket suite passed 23/23; the read suite had the same four macOS `/proc/self/root` failures observed later. A new helper required Tier C policy, dependency-edge, build/package, release-note, and behavior-documentation coverage.

### Pre-mortem summary

Launch risks were: moving parsing above the fast skip; accepting incidental argv; losing shell quote/comment semantics; disagreeing with Git option or cleanup behavior; hanging on FIFO; drifting into #1107; and shipping an unclassified or unpackaged helper. Controls are ordering checks through the real hook, paired Git-shaped fixtures, direct-message fail-closed behavior, nonblocking bounded descriptor reads, and Tier C/package audits.

## Peer review

- **writing-code:** the helper runs only after the unchanged fast prefilter, literal detector, scope check, and amend skip. Non-direct dispatch returns to legacy handling; direct literal commits either produce a modeled default-comment-cleaned message or fail closed.
- **writing-tests:** the focused suite passes 116/116. It includes every B1/B2 deny reproduction, both N1 reviewer variants, heredoc-boundary pairs, `-e`/`--edit` default cleanup, long forms and `-am`, source failures, and all 15 requested read controls.
- **writing-claims:** counts below come from command output or path enumeration. Generated helper inclusion and metrics currency are tested, not inferred.
- **writing-prose / writing-releases:** README and CHANGELOG state the modeled forms, regular-file cap, known large-multiline false-denial limit, default-comment cleanup, FU-A/#1112 limit, fail-closed boundary, and deferred dispatch/editor-mutation scope.
- **writing-rules:** the helper is Tier C, appears in the audited dependency inventory and edge/use digests, and review-risk tests plus regenerated metrics checks pass.
- **hostile review:** exact-head review rejected `b37aaebc7b0026b0350bd1ae7f2fe489303eb9c2`, `a857c0ef63dd305f050192051a0339c4596737d9`, and `3c9f2188f9ec0b7f44120a81f75132636845097a`. This rework records and addresses the remaining N1 first-terminator blocker, but claims no exact-head PASS before the hub-requested rerun. See `plans/hostile-review-994-file-message.md`.

## Test plan

- `bash -n` on changed shell and `ast.parse` on changed Python: pass.
- `bash hooks/_test/ticket_required.test.sh`: 116/116 pass.
- `bash hooks/_test/commit_detector.test.sh`: 24/24 pass.
- All 44 `hooks/_test/*.test.sh`: 43 scripts pass; `read_allowlist.test.sh` reproduces the untouched baseline, 298 pass / 4 macOS `/proc/self/root` failures.
- Twelve applicable bin suites pass, including review-risk, metrics, package generation/selection, selected generation/registration, settings drift, and inventory.
- `bin/build.py --check`: pass; source and four generated helper copies are byte-identical.
- `validate-hooks.py` on source, Claude Code package, and Craft Agent package: all valid with pre-existing unreferenced-hook warnings.
- Hosted Linux hook scenarios remain a required CI result after the reworked head is pushed.

## Lead review

In software engineering: **scope fit holds in author-side evidence** because the expanded model implements only direct explicit-message forms required by the exact-head review; non-direct dispatch stays deferred.

In software engineering: **fail-closed behavior holds in the regression suite** because every listed incidental-argv, unmodeled direct message, cleanup, comment, and source-error shape denies.

In software engineering: **modeled fidelity holds with stated limits** because Bash comments, option values, trailers, default-`#` cleanup (including edit-default strip), and the first quoted heredoc terminator affect the evaluated message as tested. Custom comment configuration and parse18 semantics remain #1112 work.

In software engineering: **read isolation holds** because hook ordering is unchanged and all 15 Finding #7 controls pass.

In software engineering: **package and policy integrity hold** because build/check, validators, byte parity, Tier C dependency tests, and regenerated metrics pass.

Approach-fit verdict: fit pending exact PR-head review. Runtime blast radius is one registered hook and one helper. The sequencing invariant is that the helper remains below literal commit detection and repository scope approval.

### Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| HR-1 | P2 | Mode `000` fixture was unreliable as root. | fixed with descriptor mode check |
| HR-2 | P2 | Attached `-F` lacked a deny pair. | fixed with `-Fno-ticket.txt` fixture |
| XR-1 | P1 | Quoted `;` lost provenance and fell back to incidental argv. | fixed in `a857c0e` with raw quote-aware operator screening |
| XR-2 | P1 | Other quoted shell characters and unhandled message spellings still fell back to argv. | fixed locally with direct-message fail-closed modeling, literal heredoc, long prefixes, and `-am` |
| XR-3 | P1 | Bash comments, option values, trailers, and cleanup produced messages different from Git. | fixed locally with comment stripping, option consumption, trailer application, and CLI/configured cleanup |
| XR-4 | P1 | Review-risk metrics were stale, so Linux hook CI did not run. | regenerated canonical metrics; local check passes |
| XR-5 | P1 | PR head did not contain canonical main. | normal main-to-feature merge created as CI required; no rebase or force push |
| XR-6 | P1 | Heredoc regex skipped Bash's first terminator and counted a later ticket footer that Git omitted. | replaced regex body matching with first-terminator line scanning; added six boundary fixtures |
| HR-3 | P3 | Unsupported dispatch, editor mutation, and large-message cases remain. | recorded as directed follow-up scope; no broader claim |
| HR-4 | P3 | Custom comment cleanup and parse18 semantics need later work. | FU-A and T9 remain tracked in #1112; unchanged here |

No known P1 remains in author-side evidence. Independent disposition is pending the required exact PR-head review and hosted CI.

### Canary and rollback

Canary: the real hook ran in temporary in-scope repositories with cwd-relative paths, spaces, first-terminator and tab-stripping heredocs, edit-default cleanup, long forms, clusters, trailers, permission denial, directory, and FIFO sources; the focused suite passed 116/116.

Rollback: before deployment or merge, revert the #994 behavior commits in reverse order. The topology merge can remain if canonical ancestry is still required. There is no migration or external state.

## Quantified claims

- "116 focused scenarios": `bash hooks/_test/ticket_required.test.sh` -> `ALL PASS: 116 scenarios passed.`
- "24 detector scenarios": `bash hooks/_test/commit_detector.test.sh` -> `Results: 24 passed, 0 failed`.
- "44 hook scripts": `find hooks/_test -maxdepth 1 -type f -name '*.test.sh'` -> 44; final sweep produced 43 passes plus one exact 298/4 baseline.
- "12 applicable bin suites": six package/runtime suites plus review-risk, protected-policy, settings-drift, skill-inventory, selected-generation, and selected-registration.
- "three hook trees": source validator 45 paths, Claude Code 40, Craft Agent 45; each ended `All hooks valid.`
- "four generated copies": `dist/*/hooks/lib/commit-message-source.py` enumerated four paths; each matched source bytes.
- "metrics delta": canonical regeneration changed only `policy_characters` from 4193 to 4215 and `--check` then passed.
- "real-Git blocker matrix": reviewer rows F1-F7 and G1-G8 all report `pr_correct=true`; all 15 read controls report hook exit 0. Directed follow-ups G9, G10, and G12 remain false denials.
- "review verdicts": `plans/hostile-review-994-file-message.md` preserves NEEDS_REWORK at b37 and REJECT at a857 and 3c9; no new-head PASS is claimed.

## Rework ledger

| Trigger | Root skip | Resolution |
|---|---|---|
| Tier C audit found edge/count drift | first inventory edit omitted discovered graph data | pinned edge, counts, and recomputed digests |
| Selected suites failed under macOS path/system Python | environment not normalized | reran with `/private/tmp` and Homebrew Python; no code change |
| First commit attempt lacked Tier C trailers | native commit contract was inspected too late | produced durable review evidence and validated trailer parsing |
| Hostile review found two pre-commit test gaps | root and attached-form assumptions | fixed code/fixtures and reran full validation |
| b37 review found quoted-semicolon fail-open | operator check ran after shlex erased quote provenance | moved operator screening before shlex and added exact regressions |
| a857 review found broader direct-message fallback and fidelity gaps | parser treated unmodeled direct forms like out-of-scope dispatch and skipped Git option/cleanup semantics | direct forms now fail closed; option, comment, trailer, cleanup, heredoc, and spelling fixtures added |
| 3c9 review found heredoc terminator backtracking and recommended FU-B | regex skipped an earlier Bash terminator; edit flags did not change the default cleanup to strip | first terminator plus exact closure enforced; eight heredoc-boundary and two edit-cleanup fixtures added |
| Hosted validation stopped before Linux hooks | generated metrics were not refreshed after policy edit | ran canonical metrics generator and check |
| Pre-commit review questioned scissors comment cleanup and repeated cleanup ordering | static claim conflicted with observed helper behavior | real Git confirmed scissors preserves pre-cut comments and the last cleanup option wins; added three differential regressions |
| Topology CI rejected missing main ancestry | develop and feature did not contain the current main promotion commit | merged current main normally into the feature branch as authorized |

## Evidence-predates-work

Artifact: plans/self-review-994-file-message.md
First-added commit: `b37aaebc7b0026b0350bd1ae7f2fe489303eb9c2`
Work commits: the #994 implementation, follow-up, topology merge, and exact-head rework commits are preserved in branch history.
Verification: this artifact existed before each follow-up and is corrected in new commits before each push; no amend, rebase, reset, or force push followed the operator's correction.
