# #1051 pre-commit hostile review evidence

Scope: bounded independent reviews of source snapshots before the implementation commit. This is **not** final exact-SHA acceptance. The coordinator must arrange the independent exact-SHA review after the draft PR is available.

## Initial findings and resolution

- **Opaque inline execution could escape declared targets.** Fixed: non-read inline execution is rejected when targets cannot be bounded. Regression: `test_hostile_review_opaque_and_nested_targets`.
- **Nested relative paths could escape task scope.** Fixed: canonicalize nested/option operands as mutation targets. Same regression; symlink, prefix and compound-target cases remain separately covered.
- **Identical no-ID spawns could reuse one reservation.** Fixed: unique PreToolUse reservations; no-ID PostToolUse matches a pending request signature and task, preventing double counts. Regressions: `test_same_arguments_without_request_id_cannot_reuse_reservation`, `test_fallback_reservations_reconcile_without_double_counting`.
- **Missing session identity could lend authority.** Fixed: mutation resolution requires a known runtime session. UUID-only payloads cannot select a wrong session directory; explicit diagnostics explain hook-host identity requirements.

## Follow-up reviews

The follow-up classification/administration snapshot reported: “No concrete bypass or normal-input bug found in the supplied snapshot.” It explicitly did not verify native test evidence or claim exact-SHA acceptance.

A focused identity/target-repo review reported: “No findings. The requested session-identity and repository-binding cases appear covered; I found no reproducible bypass or invocation regression in the reviewed changes.”

The final bounded source review covered `resolve-think-gate.py`, the real investigate/pipeline/think guards, the universal mutation gate, and the final acceptance tests, including the hook-host environment and removal of dummy missing-file fallbacks. Its result was: **“No findings.”**

## Evidence boundaries

Corrected runtime evidence (independent round one): this Craft hook process **has `CRAFT_SESSION_DIR` and no `CRAFT_SESSION_ID`**. Its payload session_id is an SDK UUID and its real Claude transcript path does not contain a Craft /sessions/<id>/ segment. The observed mechanism is the old resolver adopting the SDK UUID as the known identity and rejecting Craft-stamped companions, not an absent CRAFT_SESSION_DIR. Default tests now use that realistic context for every real hook; missing-host-identity is only a deliberate negative, and conflicting identity is only a deliberate override case. A resolver invocation in an agent shell is not hook-host evidence.

All executable changes remain clone-local. No live install, activation, deployment, release or shared-branch merge was performed. Final exact-SHA review remains pending and must not be inferred from this pre-commit record.

## Catalog dependency-chain follow-up review

The complete generated diff for progressive-loading metrics and language/data fixture costs was independently reviewed before the follow-up commit. Result: “No findings. The diff changes only measured character/token counts and generated rules-bundle size; it does not alter source selections, expected states, budgets, limits, or assertions.”

This review is limited to that supplied generated diff; it does not claim CI execution or final exact-SHA approval. The implementation executables were not changed. Full validate-job replay is separately recorded after completion.

Reviewed generated-diff SHA-256: 248d940bcc1847ed847497db4ca339221583349bf225e176c678b16cc9c64564

## Independent round-one FAIL supersedes snapshot reviews

The coordinator's independent review of the substantive implementation at `cbbb975` found six functional merge blockers: self-gate lifecycle lockout; real-header hub liveness/task accounting; repo-wide Git ownership; unsafe reader forms; investigation regressions; and terminal gate ownership. Its seventh blocker was historical red CI, subsequently green at `c9cbbecc`, but new code must obtain new hosted green. None of the earlier snapshot “No findings” statements constitutes acceptance of these failures. The complete reviewer evidence is retained by the coordinator/reviewer.

Mandatory upstream integration: merged `6685879e` into the feature branch, retained both changelog contributions, regenerated every conflicted catalog using the merged generators (no hand-merged values), and ran the review-risk snapshot suite successfully. Required validation dependency PyYAML 6.0.3 was reused from the existing installation under Python 3.12; no product installation or activation. Full post-fix validation and exact-head review remain pending.

## Round-one blocker repair snapshot

B1: narrow own-session signal/plans/data lifecycle exception plus real-hook bootstrap-to-cleanup E2E. B2: actual JSONL header liveness and tool-prompt/sole-active-gate task accounting; witnessed spokes and uniquely task-identified history only. B3: Git mutations require the toplevel owner and explicit output targets. B4: pure branch/tag/remote lists and bounded tree options, with glob/option execution/output negatives. B5: bounded diagnostics are distinct from pure reads; designing allows these standard checks but not arbitrary scripts, clones or source-fixing/output/plugin flags. B6: terminal canonical gates are excluded and suppress stale legacy copies.

The expanded 37-test acceptance suite passed under realistic defaults. The original reviewer fixtures were replayed against the repair and a clone-local archived baseline; lifecycle, unsafe reader and terminal-overlap reproductions now have the requested outcomes. A different-family bounded source review of the six repair surfaces returned “No findings.” Follow-up edge negatives cover explicit Git outputs, glob-injected options, directory masquerading as gate JSON, and mixed scaffold/recursive cleanup. These are source snapshot reviews/test evidence only, not final exact-SHA acceptance. Full merged validate replay and hosted green are pending at this checkpoint.

Nonblocking follow-ups to disclose on the PR: N1 compatibility transcript fallback anchoring/SDK mapping; N3 self-service role labels/non-spoofability; N4 cwd-dependent automatic pipeline companions; N5 unresolved audit locations; N6 duplicate local path-tool registration; N7 explicit tied-scope binding limitation; N8 review HEAD check's cwd; N9 content-matched shared pre-mortem. N2 is corrected here and in operator guidance/test defaults, not deferred.

The focused pure-reader follow-up identified three additional concrete forms: printf percent-n assignment, combined printf variable assignment, and combined date clock-setting switches. All are now rejected with real-hook negatives, while ordinary printf/date queries pass. Its Git-status cache-refresh observation is retained as a trust-boundary note: normal query/cache behavior remains permitted, not a source mutation or reason to block investigation.

The first merged replay stopped in unchanged selected-registration fixtures because macOS /var temporary paths contain an ancestor symlink. The harness now resolves its external temporary root to the canonical /private/var path (without weakening the symlink guard). All 14 unchanged registration tests then passed. The first replay is explicitly superseded; final validation restarts from step zero with the final reader snapshot. No partial earlier step is counted toward final-source proof.

Final B1/B6 source follow-up: canonical retirement is per task, not a global migration switch. Durable exclusive atomic claims prevent stale legacy revival after actual gate deletion; unrelated legacy tasks, including artifact-only pipeline migration, remain live. Reserved markers are denial-only, full-session/full-task keyed, and outside the lifecycle exemption. Final marker symlinks/nonregular inputs are rejected without blocking reads. The focused independent follow-up read the resolver, pipeline writer and acceptance tests and returned “No findings.” Preflight acceptance was 37/37; subsequent marker-symlink and legacy-writer targets passed, plus 18/18 session-signal scenarios. Full frozen-source replay remains pending; this is not exact-head acceptance.

## Final compatibility-fixture alignment before fresh replay

The complete merged replay passed steps0-29 and all37 realistic acceptance tests, but one pre-existing #926 shell fixture expected Git checkout in an intentionally non-Git workspace to pass the gate. B3 correctly rejects unresolvable Git ownership. The fixture now uses a valid filesystem mutation for EVERY original own-session/artifact/shared-root/cross-session/unknown-session assertion, and adds an explicit unresolved-Git-owner denial with its diagnostic. The targeted suite passes; no runtime enforcement, assertion floor or threshold was relaxed. The trace remains superseded and the final complete31-step replay restarts from zero after this fixture-only change.

The #1054 frontmatter fixture intentionally exports cached plus nonignored untracked files. Private .verification scratch initially entered that fresh inventory. A clone-local .git/info/exclude entry now excludes ONLY this untracked scratch (no tracked source), respecting the fixture's existing --exclude-standard mechanism. Step28 passed unchanged after the environment correction. The initial missing info-directory setup/retry trace is retained. All temporary roots remain canonical and external; no test/guard change was needed for scratch isolation.

## Final complete local validation checkpoint

The fresh replay passed all31 merged validate-job shell steps, all37 hook suites and37 acceptance tests, with zero resumes/skips and unchanged904 frozen inputs. The #926 compatibility suite now passes every original isolation/artifact check with a valid filesystem mutation and explicitly rejects unresolved Git ownership. [Full workflow evidence](1051-full-validate.json) and [current source digests](1051-verification.json) supersede historical selections. No risk snapshot, assertion floor or threshold was relaxed.

This closes the local validation work, **not independent exact-head acceptance**. B7 still requires hosted green on the normally pushed repair SHA. The coordinator must arrange the final exact-head hostile review; readiness/merge are not authorized here. No live rollout or activation was performed.

## NEW-1 scoped re-review repair preflight

The independent re-review of936978a verified B1-B7 fixed and found NEW-1: the lexer rejected all unquoted glob characters before reader/diagnostic classification. The authorized delta is only that repair, R3 disclosure, the #926 worktree positive, and required moved-develop integration. R1/R2/R4-R7 and N1/N3-N9 remain follow-ups, not repaired here.

Develop moved to4d6fbd2 (#1059); additive merge8538f42 preserves the #1046 BREAKING entry and existing Unreleased task-gate notes. The lexer now preserves positions of unquoted glob characters. Reader/diagnostic arguments require a literal non-option prefix, or quoting; raw leading patterns remain denied with “prefix ./ or quote the pattern”. Thus the reported raw leading examples use ./ or quoted equivalents in positive cases and remain explicit negatives in raw form. A fixed grep-family --include= pattern stays attached to its known option and cannot inject a separate option; globbed option keys are rejected. Mutation operands, redirections and cd still require explicit concrete paths; no diagnostic/source-edit option allowances changed.

Pre-mortem: (1) injected option filenames: preserve leading-glob/key-glob negatives next to --pre=evil; (2) hidden mutation-option-key glob: reject any unquoted mutation expansion before equals-value extraction; (3) lost quote provenance: record only unquoted positions, retain existing quoted positives; (4) worktree scope regression: add a non-Git-CWD positive with a gate scoped to git-C's real worktree, without relaxing unresolved-Git denial.

Focused real-hook matrices pass in hostDIR-only/SDKUUID/ordinary-transcript context, both no-gate and implementing, through universal and investigate entrypoints. The initial focused negative exposed an equals-key gap; it was fixed before this checkpoint and its failed trace retained. The requested #926 positive and all existing assertions pass. Full regeneration/fresh validate replay/new hosted proof remain pending;936978a's green is historical, not proof of this delta. R3 is explicit in Unreleased and will be explicit in the final PR body.

### Superseding FINAL v2 contract and focused proof

The hub's08:31Z FINAL v2 supersedes v1 command-class, shape/terminator and fixture requirements. No v1 push occurred. Glob expansion is certified only for bounded pure-reader option grammars and pytest selection paths; mixed commands (sort/find/tree and similar) retain explicit concrete paths even with safe-looking prefixes or --. Genuine -- permits leading glob operands for pure readers; option values equal to -- do not terminate options. Bounded flags/value grammars distinguish these cases. Literal non-dash prefixes remain required before the terminator, with the forbidden leading characters from v2; a fixed attached grep --include=pattern remains safe. Existing unquoted brace/parameter/command/incomplete-escape/escaped-newline UnknownShape denials are retained.

Correction: an initial self-review concern about backslash-newline was not a demonstrated current bug: direct inspection showed the lexer already rejects it. No newline normalization was introduced. Dedicated regressions retain that denial. The partial v1 replay (.verification/1051/full-ci-round3,30/31 completed) is superseded by the mandatory v2 source change, not counted as final proof; traces remain.

Focused v2 positives/negatives pass through real universal/investigate hooks with no gate and implementing, in temp directories containing literal -o,--output=pwn,-delete and --pre=evil sentinel files. Cases cover the complete requested matrix, genuine --, -- consumed as an option value, mixed command classes, mutation globs and existing unsafe-reader forms. The #926 non-Git-CWD/owned-worktree positive and all original fixture assertions pass.

#1057 corpus availability: issue body fetched from GitHub, comments empty, no attachment/corpus file and no1057/45-of71 provenance-bearing fixture found in this authorized repo. The issue contains examples only. The exact45/71 corpus is not reachable here; no full corpus replay or corpus-wide mutation result is asserted. Existing real-hook mutation negatives and v2 injection cases are exercised instead;1057 remains open.

Fresh full v2 replay, frozen hashes and exact-head hosted proof remain pending at this preflight checkpoint. No R1/R2/R4-R7 or N1/N3-N9 implementation, install or activation is included.

V2 pre-freeze bounded source review of only the glob diff returned **No findings**. This is not independent exact-head acceptance. The expanded real-hook v2 matrix also passes with PATH explicitly selecting macOS system Python3.9 for hook subprocesses.

Final v2 vocabulary tightening: do not add generic --help/--version allowances to the NEW glob grammar; Git --help can launch a man/browser helper. Added both-state real-hook git diff/log --help-with-glob negatives. No ordinary non-glob reader behavior changed. Final focused matrix passes on Python3.12 and explicit system-Python3.9 subprocess PATH; final bounded option-vocabulary/terminator review returned **No findings** (not independent exact-head acceptance). The earlier v2 run at17/31 is retained/superseded and cannot count as final proof. Final replay must start from zero after required develop-promotion integration.

### Final v2 full-replay checkpoint

The final frozen v2 replay (.verification/1051/full-ci-round3-v2-final) passed all31 applicable merged validate shell steps from zero, all37 real-hook suites and39 acceptance tests. All904 frozen runtime/test/skill inputs remained unchanged; no resumed/skipped steps or superseded partial results count. Risk-policy snapshots/thresholds/negative floors and clean-home/canonical-temp/symlink protections were preserved. The proof recorder first refused an incomplete final-loop result, then recorded only the actual all-zero completion. Develop was re-fetched and remains the integrated4d6fbd2 at this checkpoint.

The stopped v1 test scratch was preserved intact under private superseded-fixtures, not deleted or broadly excluded; the untracked export boundary was verified clean before final replay. Pinned dependency setup remained an offline already-satisfied reuse, not installation or a policy waiver. FINAL v2 scope remains NEW-1, R3 disclosure,926 positive and additive upstream integration only. Exact-head hosted success and independent acceptance remain pending; do not treat this local checkpoint as either.

## Released-main additive integration addendum

The09:50Z hub addendum authorizes an additional normal update after merging origin/main exactly f5c63baecfffa65b04508beb13d8b16312d215f8 instead of waiting for develop promotion. Additive merge67170d8 contains that pinned main and develop4d6fbd2. Runtime/test/skill inputs remain byte-identical to the prior904-input full v2 proof. No FINAL v2 behavior or deferred R1/R2/R4-R7/N1/N3-N9 changed.

Pinned main's actual changelog blob still used Unreleased, with no3.5.67 heading. To implement the required placement, only its heading was relabelled3.5.67; the entire following upstream body is byte-for-byte preserved. Four1051 notes, including R3, now occupy a fresh Unreleased above it. The private preservation receipt hashes that complete upstream body. No released note wording was edited.

The actual local compatibility topology entrypoint passes on this ancestry; that local path is NOT protected-host authorization. Prior hosted run39231071049 passed validate and skipped publish, but its separate exact-head topology failed on the pre-main ancestry. That is historical runtime evidence, not proof for the new integration. Fresh full merged replay,13 final-head checks and new hosted green are required before handoff. No force/shared-branch mutation/install/activation is authorized.

### Released-main integration: final complete local proof

The fresh .verification/1051/full-ci-round4-main replay passed all31 applicable merged validate shell steps from zero,37/37 hook suites and39/39 acceptance tests. All904 frozen runtime/test/skill inputs stayed unchanged. The final proof guard also verified actual pinned-main ancestry and RAW BYTE equality of the entire upstream body below3.5.67 against main's original Unreleased body. No partial/historical run counts toward this integration proof. Risk snapshots/thresholds/negative floors and canonical-temp/clean-home/symlink assertions remain unchanged.

Evidence finalization only follows this complete run. New exact-head hosted validator/topology success and independent acceptance remain pending at this immutable pre-push checkpoint; prior hosted validate success is historical and did not override its failed pre-main topology check. No FINAL v2/source-policy behavior changed in this integration.

## FINAL v3: NEW-2 fd/null redirects and source-changelog correction

Independent review of b14a94cd verified NEW-1 (114 probes, zero unexpected), B1-B7 and no newly admitted corpus mutation, but failed NEW-2. This blocker was present from the initial implementation and missed by earlier reviews: stderr duplication tokenized as separate > and &, adjacent fd digits leaked into argv, and the literal null sink became an unowned file target. No independent PASS was issued.

FINAL v3 supersedes the CHANGELOG-only authorization: combine NEW-2 and the source-header correction in ONE normal update; do not implement #1063 glob families or R1/R2/R4-R7/N1/N3-N9. Restore source CHANGELOG to pinned f5c63bae plus only five1051 notes (including R3 and NEW-2) under its existing Unreleased. Next version remains3.5.20; no source version promotion. Earlier3.5.67-heading preservation claims are historical/superseded, not this final layout.

NEW-2 pre-mortem/self-review checkpoint (after initial prototype, before freezing/generation): likely failure modes are quoted/escaped digits mistaken for IO_NUMBER; &> split as background; fd words or expanded targets treated as descriptors; later null/dup redirects erasing earlier outside paths; literal null aliases/symlinks borrowing exemption; and unchanged mutation commands escaping authority merely because stderr is redirected. Mitigations: wholly-unquoted adjacent ASCII digits only, longest bounded redirect tokens, digit-or-dash descriptor checks, cumulative concrete file targets, exact literal null sink only, existing mutation and glob policies retained. Unquoted tilde redirect targets are also nonconcrete and denied. No command under test is executed by classification hooks.

Three new real-hook methods cover no-gate/designing/implementing/done-awaiting-pr/disposed reads and pytest, authorized Git/touch mutations, scoped file outputs, outside output/order/expansion/symlink negatives and quoted/escaped fd lexing. Pre-fix run produced89 failed assertions (retained). Python3.12 focused3/3 passed; actual macOS Python3.9 hook subprocesses3/3 passed. A longer5-method system run timed out after120 seconds with the last method incomplete; it is not counted as full proof, and its own leftover fixture was preserved intact in private traces before bounded reruns. Bounded isolated source review returned No findings; not independent exact-head acceptance. Fresh full31-step replay and new exact-head hosted Validate/topology green remain required.

Release-note limitation remains escalated: exact main-plus-additions source has the upstream BREAKING/Added notes under Unreleased, so unchanged promote-unreleased/release-notes scripts emit the entire block, not only1051 notes. No upstream notes or release tooling are removed/rewritten to fabricate that condition. Await hub ruling; no push until the conflict is resolved.

### FINAL v3.1 precision before freeze

The prior combined generation command timed out after120 seconds during ordered generation; NO full replay directory/process was created. Generation is restarted sequentially after staging the v3.1 source. Completed v3 corpus classification remains historical:253 log entries/234 unique commands, b14 allowed54 and v3 allowed74;20 newly allowed, zero previously allowed denied, all new admissions classified as reads/approved diagnostics containing redirects. Nothing executed. This differs from the reviewer's earlier249/230 log snapshot and is not the absent curated45/71 set. The same frozen234-command subset will be rerun on v3.1.

V3.1 keeps the exact whole-token /dev/null exemption (quoted or unquoted); no prefix/substring/canonical alias/device exemption. Add >| and N>| operators. Fixtures cover >/dev/null.txt, /dev/nullx, /dev/null/../tmp/x, /dev//null, /dev/fd/3, /dev/stdout, /dev/stderr, /dev/tty, high-fd duplication and file openings at prefix/mid-command positions. Opening a file remains gated even when a later duplicate redirects to that fd. Opaque exec remains denied. No runtime wiring/settings change.

V3.1 actual system-Python focused3/3 passed in101.765s with the full required no-gate/implementing vocabulary and representative designing/terminal read/diagnostic forms. Additional150-second interrupted expanded-cross-product trace/fixture is retained, not counted. Every requested operator/device/opening case remains; only redundant repetition across non-required states was bounded. The final workflow still executes all42 acceptance methods and37 wrapper suites.

### FINAL v3.1 complete local proof checkpoint

Fresh .verification/1051/full-ci-round6-new2 passed31/31 workflow shell steps from zero,37/37 hook wrappers and42/42 acceptance tests (acceptance219.679s). All904 frozen inputs remained unchanged; no resumes/skips/mixed-source proof. Strict seal verified pinned-main ancestry, identical source version headers, five-note additions-only CHANGELOG with exact upstream remainder, canonical external temps, pinned offline dependency receipt and matching source hash on the frozen raw-corpus replay.

Stabilized v3.1 raw-corpus snapshot253 entries/234 unique: baseline b14 allowed54, candidate74,20 newly admitted (all classified read/approved diagnostic and containing redirects),zero formerly allowed denied. Nothing executed. Programmatic audit and bounded source No findings are not independent exact-new-head acceptance. Curated45/71 fixture remains absent; raw corpus limitations (truncation/original cwd unknown) retained.

No new commit or push at this checkpoint: unchanged release-note tooling emits137 lines (upstream BREAKING/Added plus five1051 notes), contradicting the only1051-output condition while mandatory source equality/additions-only holds. Hub ruling requested; no workaround/deletion/tool change or false note-output claim. Evidence-only finalization follows this complete proof; exact-new-head hosted Validate/topology and independent hostile acceptance remain future requirements.
