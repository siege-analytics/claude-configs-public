---
ticket_refs:
  - siege-analytics/claude-configs-public#994: file-backed commit messages
---

# Self-review: #994 narrow effective-message handling

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: siege-analytics/claude-configs-public#994 plus operator decision https://github.com/siege-analytics/claude-configs-public/issues/994#issuecomment-6296565616
Goal source verification: `evaluate-ticket.sh` reports that the old issue body lacks the current Context/Goal/Acceptance, think-note, and Assumptions structure; the explicit operator decision and this evidence-chain exemption supply the approved execution contract.
Plan reference: plans/self-review-994-file-message.md#scope-and-design
Pre-author-inventory: plans/self-review-994-file-message.md#pre-author-inventory
Investigate-artifact: plans/self-review-994-file-message.md#pre-author-inventory
Pre-mortem-artifact: plans/self-review-994-file-message.md#pre-mortem-summary
Hostile-review-artifact: plans/hostile-review-994-file-message.md
Project-contribution: closes the explicit message-file enforcement gap without reviving stale PR #998 or expanding into #1107 dispatch work.

### Ticket-fitness exemption

Reason: #994 predates the repository's current ticket-body schema, but Dheeraj's later decision fixes the branch, supported forms, exclusions, tests, docs, push, and PR contract.
Evidence: `bash scripts/discipline/evaluate-ticket.sh siege-analytics/claude-configs-public#994` reports only the missing structural sections; the approved scope is recorded at the operator decision URL above and reproduced below.
Falsification: this exemption fails if that comment does not authorize the stated scope, if the implementation broadens beyond it, or if #994 was withdrawn before this commit.

### Scope and design

- Resolve effective messages only for direct literal `git commit` using `-m`, `-F <file>`, `--file <file>`, and `--file=<file>`.
- Keep the existing fast literal prefilter, `ct_is_git_commit`, repository scope check, amend/no-edit behavior, and `read-only-command.py` ownership.
- Deny recognized missing, unreadable, non-regular, oversized, stdin, duplicate-file, and mixed sources before ticket grammar.
- Keep aliases, wrappers, expansion, dynamic dispatch, and editor-generated messages out of scope under #1107.

### Pre-author inventory

Develop at `101f75439bd351bf0bba9b512b2cbdc14eb37c5c` scanned the command string after correct literal commit and scope detection. The baseline ticket suite passed 23/23; the read suite had the same four macOS `/proc/self/root` failures later observed after the change. A new helper required Tier C policy, dependency-edge, build/package, CHANGELOG, and behavior-documentation coverage.

### Pre-mortem summary

The launch risks were: moving parsing above the fast skip; accepting incidental argv; hanging on FIFO or disagreeing with Git file semantics; drifting into #1107; and shipping an unclassified/unpackaged helper. Controls are ordering assertions through the real hook, paired content fixtures, nonblocking descriptor reads with regular-file and size checks, a deliberately narrow tokenizer, and Tier C/package audits.

## Peer review

- **writing-code:** the helper runs only after the unchanged fast prefilter, literal detector, scope check, and amend skip. It accepts simple commands beginning with literal `git commit`; unquoted shell operators, substitutions, backslashes, and multiline input return unsupported, while quoted operator characters remain literal message/path data. File reads use `O_NONBLOCK`, descriptor `fstat`, regular-file and permission-bit enforcement, and a 1 MiB bound.
- **writing-tests:** the focused suite passes 64/64. Negative cases cover incidental author/pathspec text, both quoted-operator fail-open reproductions, paired quoted-semicolon message/path behavior, malformed quoting, every accepted source spelling, missing/unreadable/directory/FIFO/stdin/mixed sources, and all 15 requested read controls.
- **writing-claims:** every count below comes from command output or path enumeration; generated helper inclusion is byte-compared, not inferred.
- **writing-prose / writing-releases:** README and CHANGELOG describe only the approved forms and explicitly leave #1107 unresolved.
- **writing-rules:** the helper is Tier C, appears in the audited dependency inventory and edge/use digests, and `review_risk_test.py` passes.
- **hostile review:** exact-SHA regression review of `b37aaebc7b0026b0350bd1ae7f2fe489303eb9c2` returned NEEDS_REWORK for quoted-operator fallback. The follow-up fixes the S1 and passes local validation; no exact-head independent PASS is claimed before the required PR-head review. See `plans/hostile-review-994-file-message.md`.

## Test plan

- `bash -n` on changed shell and `ast.parse` on changed Python: pass.
- `bash hooks/_test/ticket_required.test.sh`: 64/64 pass.
- `bash hooks/_test/commit_detector.test.sh`: 24/24 pass.
- All 44 `hooks/_test/*.test.sh`: 43 scripts pass; `read_allowlist.test.sh` exactly reproduces its untouched baseline, 298 pass / 4 macOS `/proc/self/root` failures.
- Applicable bin suites: 12 pass, including review-risk, package generation/selection, selected generation/registration, settings drift, and inventory.
- `bin/build.py --check`: pass; source and four generated helper copies are byte-identical.
- `validate-hooks.py` on source, Claude Code package, and Craft Agent package: all valid with pre-existing unreferenced-hook warnings.

## Lead review

In software engineering: **scope fit holds in author-side evidence** because only the four authorized explicit source forms are resolved and unsupported dispatch retains legacy handling.

In software engineering: **fail-closed behavior holds in the regression suite** because recognized indeterminate file conditions and the exact quoted-operator/incidental-argv reproductions block before ticket matching.

In software engineering: **read isolation holds** because ordering is unchanged and all 15 Finding #7 controls pass through the real hook.

In software engineering: **package and policy integrity hold** because build/check, three validators, helper byte parity, and Tier C dependency mutation tests pass.

Approach-fit verdict: fit pending exact PR-head review. A single-purpose parser has less blast radius than expanding the shared detector or reimplementing shell parsing in Bash. Runtime blast radius is one registered hook and one helper. The sequencing invariant is that the helper remains below literal commit detection and repository scope approval.

### Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| HR-1 | P2 | Mode `000` fixture was unreliable as root. | fixed with descriptor mode check |
| HR-2 | P2 | Attached `-F` lacked a deny pair. | fixed with `-Fno-ticket.txt` fixture |
| HR-3 | P3 | Unsupported editor/dynamic shapes retain command scanning. | noted; deliberately outside #994 |
| XR-1 | P1 | Quoted `;` lost provenance, returned unsupported, and let incidental argv satisfy ticket grammar. | fixed in follow-up with raw quote-aware operator screening and exact regressions |

No known P1 remains in author-side evidence. Independent disposition of the follow-up is pending the required exact PR-head review.

### Canary and rollback

Canary: the real hook ran against a temporary in-scope repository with cwd-relative paths, spaces, quoted operator characters, malformed quoting, ticketed/ticketless content, permission denial, directory, and FIFO sources; the focused suite passed 64/64.

Rollback: before deployment or merge, revert the #994 commits in reverse order. There is no migration or external state; reverting both restores legacy command scanning and removes the helper registration.

## Quantified claims

- "64 focused scenarios": `bash hooks/_test/ticket_required.test.sh` -> `ALL PASS: 64 scenarios passed.`
- "24 detector scenarios": `bash hooks/_test/commit_detector.test.sh` -> `Results: 24 passed, 0 failed`.
- "44 hook scripts" — `find hooks/_test -maxdepth 1 -type f -name '*.test.sh'` -> 44; final sweep produced 43 passes plus one exact 298/4 baseline.
- "12 applicable bin suites" — six package/runtime suites plus review-risk, protected-policy, settings-drift, skill-inventory, selected-generation (13 tests OK), and selected-registration (14 tests OK).
- "three hook trees" — source validator: 45 paths; Claude Code: 40; Craft Agent: 45; each ended `All hooks valid.`
- "four generated copies" — `dist/*/hooks/lib/commit-message-source.py` enumerated four paths; each matched source bytes.
- "b37 verdict is NEEDS_REWORK": exact-SHA regression review reproduced both quoted-`;` fail-opens; `plans/hostile-review-994-file-message.md` records the evidence and withdrawn static PASS.

## Rework ledger

| Trigger | Root skip | Resolution |
|---|---|---|
| Tier C audit found edge/count drift | first inventory edit omitted discovered graph data | pinned edge, counts, and recomputed digests |
| Selected suites failed under macOS path/system Python | environment not normalized | reran with `/private/tmp` and Homebrew Python; no code change |
| First commit attempt lacked Tier C trailers | native commit contract was inspected too late | produced durable review evidence and validated trailer parsing |
| Hostile review found two pre-commit test gaps | root and attached-form assumptions | fixed code/fixtures and reran full validation |
| Exact-SHA review found quoted-operator fail-open | token-level operator check ran after shlex erased quote provenance | moved operator screening before shlex, added six regressions including malformed quoting, reran full validation |

## Evidence-predates-work

Artifact: plans/self-review-994-file-message.md
First-added commit: `b37aaebc7b0026b0350bd1ae7f2fe489303eb9c2`
Work commit: pending follow-up commit at artifact correction time
Verification: the artifact existed before the follow-up and is corrected atomically with the S1 fix before any push, PR, merge, release, or deployment.
