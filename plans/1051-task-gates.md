---
ticket_refs:
  - siege-analytics/claude-configs-public#1051
propagation: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252933479
---
# Task-keyed gates: design and investigation record

Design: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252889539
Fact Sheet: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252915590
Pre-mortem: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252933479

## Pre-author inventory
Verified base main 056b5337b08bb960fb7796b6bb00c971e22664f1; target develop dbe21c1968cb1c04ba6eeb780169ae37929cc7b1 has identical principal sources.

- Gate resolver: session / repo filename, project / local / workspace fallbacks; no task identity. Callers: think, investigate, review, skill-enforcement, pipeline-state, universal-mutation and git self-review guards. CRITICAL fanout.
- Bash payload: tool_input.command + cwd + runtime session identity. Canonical paths must account for cd, git -C, redirects and tool target paths; unknown shell constructs fail closed.
- Think signal: task/ticket, session/sessionId, repo_root, status. New fields: scope_paths, task_id. Canonical task directories, exact identity; legacy session file remains a read source only.
- Artifact signals: investigate, junior-senior, artifacts-posted, review; pipeline-state writes the middle two plus unreachable stamps. Writer must be session/task keyed and atomic.
- Hub payload: target sessionId; state cap/open_threads/last_activity. New structured task identity and parent/worker/traffic-cop relationships; never infer exemption from prose.
- Additional test evidence: git test-guard root singleton; commit/testing-frameworks guidance. Migrate alongside named gates.
- Knowledge loci: hooks/README.md; think/investigate/pre-mortem/self-review/cross-review/commit/testing-frameworks skill instructions.
- Test boundary: real hook subprocesses and resolver filesystem fixtures. Existing root-authorization fixtures require deliberate migration; no mocks of changed functions.

## Pre-mortem
Severity: classifier hidden execution and foreign-task fallback are launch-blocking until negative tests pass. Mitigations: bounded positive grammar, restricted non-evaluated Python AST; exact identities; canonical path-component containment; all mutation targets owned by one task; ties block with diagnostics; root legacy diagnostic-only; artifacts only beside selected task gate; atomic writers and serialized hub bookkeeping. No release or activation.

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: siege-analytics/claude-configs-public#1051
Goal source verification: PASS: ticket siege-analytics/claude-configs-public#1051 is fit for execution
Plan reference: approved design above
Pre-author-inventory: plans/1051-task-gates.md#pre-author-inventory
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252915590
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1051#issuecomment-6252933479
Hostile-review-artifact: plans/1051-hostile-review.md
Project-contribution: independent task enforcement without fleet-wide artifact coupling.

## Test plan
Implement every design case and acceptance negative, then run all hook suites, hook validator, source-authority checks, generated freshness/build, review-risk and independent hostile exact-SHA review. No live workspace canary; fixture-only canary and additive rollback.

## Peer review
Syntax check: every changed Python executable parsed using Python 3.10 grammar; every changed shell executable passed `bash -n` (exit 0). Runtime verification used Homebrew Python 3.14.6, not the system Python 3.9.

Test suite: all 37 `hooks/_test/*.test.sh` suites and 9 additional `bin/_test` suites passed. The task acceptance wrapper ran 28 real resolver/hook tests. Exact commands and executable digests are preserved in `plans/1051-verification.json`; raw logs remain clone-local under `.verification/1051/`.

Doc build: N/A (no docs/ changes); skill/reference synchronization, inventory, flat skill layout, kernel budget, ontology, normal build and freshness checks passed. Source hook settings and both generated runtime hook settings validated (45 registered paths; warnings only). No notebook changes.

Writer/reader review: task-specific artifacts, exact identities, canonical scopes, task-bound test evidence, atomic writers, and no root mutation authorization. Root singleton fixtures were migrated deliberately; their denial tests remain. Registration snapshots and helper graph were extended, with no removed edges or negative downgrade assertions; new enforcement helpers/policy are explicitly Tier C.

Scope: hooks and gate-directed skill guidance, not live workspace configuration. All edits are in the authorized fresh clone.

## Lead review
[software engineering] Approach fit: independent `(session, task)` directories avoid a shared task index and preserve legacy session reads without reviving root mutation authority. All action targets must select the same task; explicit binding disambiguates but cannot extend scope. Positive read classification precedes lookup; opaque inline execution and unresolved syntax fail closed.

[enforcement] The independent pre-commit hostile snapshot review found concrete path/execution/reservation issues, now fixed with regressions. Follow-up reviews and the final guard/identity snapshot found no further findings; see `plans/1051-hostile-review.md`. Final exact-SHA review is deliberately pending after draft PR creation, not claimed here.

[operations] Administrative load, not communication, is bounded. Only metadata-labelled hubs face spawn admission limits; all messaging is nonblocking, stewards exempt, unknown roles audit/fail open. Existing #896/#898/#915 messaging state remains advisory only. Declared adoption counts at the next spawn check; arbitrary adoption has no intercepted host-tool boundary and is not claimed as enforced.

[runtime identity, corrected after independent review] Observed Craft hooks have CRAFT_SESSION_DIR, no CRAFT_SESSION_ID, an SDK UUID payload id and a Claude-project UUID transcript path. The old UUID-as-known-id precedence was the mechanism; missing CRAFT_SESSION_DIR was not evidenced. Real-hook defaults now reproduce the observed environment. Only deliberate missing-identity negatives remove the host directory variable. Different-origin scope rejection separately reports both repositories/origins; correct TARGET metadata works from workspace CWD with explicit mutation paths.

Blast radius: shared gate resolver and its registered callers, Bash/write target enforcement, hub spawn admission, source/generated settings and writer documentation. No live rollout. Sequencing: merge by normal promotion only after independent exact-SHA review; rebase/force-push and activation are not part of this task.

## Quantified claims
- “37 hook suites + 9 additional suites”: enumerate `hooks/_test/*.test.sh` and the nine explicit Python suites, run each subprocess, persist return codes → `plans/1051-verification.json` has 46 zero-exit entries.
- “28 acceptance tests”: `PATH=/opt/homebrew/bin:$PATH python3 hooks/_test/task_keyed_gates.py` (also run by its shell wrapper) → `Ran 28 tests`, `OK`.
- “13 validation checks”: the verification JSON `checks` array → 13 zero-exit entries (freshness, source/runtime settings, source authority, inventory, risk metrics, policy/probes and layout).
- “45 registered paths”: `python3 bin/validate-hooks.py` → all hooks valid, warnings only; registration drift fixture separately confirms 45 triples over 30 tool-event hooks.

## Canary and rollback
Fixture-only canary: task A designing cannot block B implementing; changing A's status leaves B's result unchanged. Missing/wrong artifacts and stale root copies remain blocked; classified readers remain available without gates. Concurrent writers retain separate task files, and hub communication remains available at administrative cap. These are actual hook subprocesses, not deployment canaries.

Rollback boundary: no installed workspace was changed. For an eventual rollout, a normal revert of the implementation plus rebuild from source restores the previous package; do not hand-edit generated files or restore root artifacts as an authorization bypass. This rollback was not performed on a live workspace.

## Evidence-predates-work
Artifact: plans/1051-task-gates.md
First-added commit: 1e581bc3ae62622f33fa4cfc7047c51079f5a777
Pre-work HEAD: 1e581bc3ae62622f33fa4cfc7047c51079f5a777 (this artifact's original record was committed before runtime edits).
Work commit: the implementation commit carrying this final revision; its exact SHA is reported on the draft PR and to the coordinator after creation. No future SHA is fabricated here.
Verification: `git log -1 --diff-filter=A --follow --format=%H -- plans/1051-task-gates.md` returns the first-added commit above; the implementation commit has it as an ancestor.

## Rework ledger
| Trigger | Root cause / correction | Verification |
|---|---|---|
| Ticket fitness initially blocked | Missing literal Design line; coordinator corrected body | PASS; no exemption |
| Old root/unknown-command fixtures failed | Old expectations authorized removed root state or unsafe shell shapes | Migrated explicit contract assertions; all suites pass |
| Pipeline shell/Python quoting failed | Large embedded Python was brittle | Extracted standalone helper; writer tests pass |
| Hostile snapshot findings | Opaque execution, nested paths, duplicate reservations, unresolved identity | Fixed with negative regressions and re-reviewed |
| Registration/risk snapshots failed | New registrations and helper edges intentionally changed source authority | Extended audited graph/counts; all mutation/downgrade negatives retained |
| Documented example failed | Example session stamp did not match fixture runtime | Runtime aligned with documented stamp; findings negatives retained |
| New test initially in wrong fixture class | Pipeline test placed under hub fixture | Moved to gate fixture; PASS |
| No-ID completion double count | Unique admission lacked matching completion key | Signature+task reconciliation regression passes |
| Binding requirements changed during work | Hook identity and target repo metadata required real-host-like tests | All seven required cases and real-entrypoint variants pass |
| Transient provider disconnects | Work interrupted before commit, not an implementation failure | Resumed from clone; full rebuild and all suites re-run |

No commits were amended or deployed during these cycles. Check/rework durations were not measured; no cost ratio is asserted.

## Hosted CI inventory follow-up

Hosted run 39176581026 rejected the initial implementation head's inventory at the generated-source-authority check. Local reproduction after that commit also fails under Python 3.14.6, so this is not interpreter-sensitive output. Regeneration with the existing Python 3.12.12 runtime and Python 3.14.6 produced byte-identical JSON.

**Cause:** the inventory generator discovers evidence inputs with `git ls-files`. The initial regeneration and local freshness checks ran before the new test/writer files were staged, so those untracked files were absent from reference/test-evidence scanning. Once committed, the clean CI checkout included them and expected extra evidence-list entries. This was a verification-order error, not a source-authority check to weaken.

**Correction:** regenerate using Python 3.12 after all source files are tracked; preserve the added reference/test-evidence entries. Re-run the generator, authority, build and policy checks against that file set, then repeat freshness checks after the additive commit and observe hosted CI on its new SHA. No runtime implementation or workflow checks are relaxed. The original verification JSON remains the original implementation snapshot; follow-up logs are clone-local under `.verification/1051/ci-followup/`.

**Focused review:** only generated evidence and this diagnosis change. Existing source hashes are unchanged. Generator tests and post-commit freshness are the relevant regression checks; independent exact-SHA review still applies to the new PR head. No installation, deployment or activation is involved.

Follow-up verification: all 46 prior suites and 13 validators passed with Python 3.12.12. The first local follow-up runner scheduled validators concurrently with rebuilding suites, causing a transient missing-kernel read; a completed rebuild followed by sequential validators (the CI ordering) passed. The 28-test acceptance wrapper also passed. No executable source changed.

## Full catalog dependency-chain correction

Hosted run 39187794281 passed the repaired inventory/authority step but then rejected stale progressive-loading metrics. The prior local follow-up ran a hand-picked validator subset, not the full validate job; that subset omitted progressive-loading, language-scope and data-scope freshness. Updated gate-writing skills change selected-content costs and the generated rules-bundle size, so dependent measurement catalogs must be refreshed even though their routing definitions are unchanged.

Correction: use Python 3.12.12 to regenerate inventory and ontology, build, refresh progressive-loading metrics and language/data measurements, refresh risk metrics, rebuild packaged catalogs, then regenerate source authority and kernel budget. All generators were run; only the progressive-loading metrics and language/data fixture measurements changed. No route, budget, expected state, safety predicate or executable source was edited.

The full validate job's 30 shell steps are now replayed directly from the committed workflow, sequentially and with PR lifecycle context. Checkout/setup are supplied locally; the uses-only first-main-promotion provenance step is not applicable to this PR, and the publish job is never executed. Long composition fixtures are monitored in bounded chunks; a tool-call time limit interrupted the first chunk after three completed-successful commands, so replay resumes after those proven successes rather than claiming the incomplete step passed.

The final replay results, step script hashes and logs are retained under `.verification/1051/full-ci/`. Final successful step count and post-commit freshness are recorded after execution, before hosted confirmation. This follow-up is additive and the PR remains draft pending green hosted validation and exact-SHA re-review.

Replay environment correction: placing test temporary homes under the checkout caused the clean-home package diagnostics test to report a source-path leak. The unmodified test passed once standard temporary fixtures were placed outside the source tree, matching CI's separation; no production home or workspace was activated. The original failed harness log is retained separately.

Full replay result: all 30 applicable validate-job shell steps passed under Python 3.12.12, including all 37 hook scenario suites and the 28-test task acceptance wrapper. `plans/1051-full-validate.json` records the workflow hash, ordered step names/script hashes and zero exit statuses. All source/executable files and policy thresholds are unchanged by this follow-up. Hosted approval must still be observed on the new commit.

## Hostile-review repair pre-mortem and merge integration

Round-one review found lifecycle bootstrap, task ownership and realistic-header gaps that snapshot reviews missed. Before fixes: risk one is allowing another session's artifacts through an overbroad self-management exemption; risk two is treating executable diagnostics as pure reads; risk three is lending nested ownership to repo-wide Git; risk four is treating concluded historical children as active administrative load. Regressions must invoke real hooks with only `CRAFT_SESSION_DIR`, an SDK UUID payload and real-shaped Claude transcript paths; include sibling-session/symlink/compound negatives, terminal task overlap and real JSONL session headers. Diagnostic execution is not a sandbox and must have an explicit bounded policy.

Merged upstream #1054 at `6685879e` additively before blocker code edits. Both changelog contributions were retained. Conflicted catalogs were regenerated with merged generators; review-risk independent snapshots passed without hash changes at this merge stage. Existing pre-fix full-suite evidence does not imply post-merge/post-fix acceptance.

Repair checkpoint: 37 realistic acceptance tests and the reviewer's original comparison fixtures passed for B1-B6. Actual default identity is host CRAFT_SESSION_DIR only, SDK UUID and a real-shaped Claude transcript. Diagnostics intentionally permit standard tests/cache/metadata activity and are not called pure reads; explicit source-edit/output/plugin options and arbitrary scripts/clones remain gated. The standalone spawn prompt line CCP_TASK_ID=<full-task-id>, or a sole active canonical sender task, is hook-visible; agent-shell exports are not. A disposable clone-local no-pip validation environment references the already-installed pinned parser and pip via symlinks. Offline dry-run is already-satisfied, so no dependency/product installation or managed-Python override is needed. Full post-fix merged validation remains to be recorded.

Additional self-review negatives cover printf variable-assignment forms and combined date setter flags. The first full replay exposed a local harness-path error: default macOS /var temporary fixtures violate the existing no-symlink registration contract. Canonical external temporary roots preserve both the clean-home/no-source-path and no-symlink predicates. The unchanged 14-test registration suite passes with that environment; final full replay restarts at step zero after source stabilization. No tests/assertions/thresholds were disabled.

Post-cleanup B6 correction: a stale legacy copy could revive after the canonical terminal JSON was actually removed. A global namespace switch was rejected during self-review because it would disable unrelated legacy tasks. The shipped repair uses exclusive atomic denial-only claims keyed by full session/task SHA256 under reserved tasks/.canonical. Claims are recorded from canonical lookup and before own lifecycle modification/deletion; they carry no status and cannot grant authority. Actual deletion, mixed canonical/legacy scopes and artifact-only legacy pipeline migration are covered. Symlink/FIFO claim targets fail closed without being opened. The terminal signal fixture retains exact exit-2 denial but now requires Unscoped mutation, since terminal records are not owners. A preliminary 37-test run passed; final loader/symlink and legacy-writer additions then passed targeted runs, and the unchanged signal suite has 18/18 passes. The next full workflow run will execute all 37 acceptance tests again from this frozen source.

## Final compatibility-fixture alignment before fresh replay

The complete merged replay passed steps0-29 and all37 realistic acceptance tests, but one pre-existing #926 shell fixture expected Git checkout in an intentionally non-Git workspace to pass the gate. B3 correctly rejects unresolvable Git ownership. The fixture now uses a valid filesystem mutation for EVERY original own-session/artifact/shared-root/cross-session/unknown-session assertion, and adds an explicit unresolved-Git-owner denial with its diagnostic. The targeted suite passes; no runtime enforcement, assertion floor or threshold was relaxed. The trace remains superseded and the final complete31-step replay restarts from zero after this fixture-only change.

The #1054 frontmatter fixture intentionally exports cached plus nonignored untracked files. Private .verification scratch initially entered that fresh inventory. A clone-local .git/info/exclude entry now excludes ONLY this untracked scratch (no tracked source), respecting the fixture's existing --exclude-standard mechanism. Step28 passed unchanged after the environment correction. The initial missing info-directory setup/retry trace is retained. All temporary roots remain canonical and external; no test/guard change was needed for scratch isolation.

## Final complete local validation checkpoint

All **31 applicable merged validate-job shell steps passed** in a fresh replay from zero, without resumes or skips. All **37 hook suites and37 realistic acceptance tests passed**. All904 frozen runtime/test/skill inputs stayed unchanged; the recorder also verified the exact staged input tree and every hook-loop PASS. Full commands/output hashes, superseded attempts and fixture semantics are recorded in [full workflow proof](1051-full-validate.json); current executable hashes supersede the old baseline in [verification](1051-verification.json).

Risk snapshots, negative floors and thresholds remain unchanged. Source inputs were staged before regeneration. Python3.12 reused the already-installed pinned parser without download/install or managed-environment override. No live installation, activation, deployment, release, shared-branch merge or rollback occurred. Normal feature-branch commit/push follow this checkpoint. Hosted exact-head green and independent exact-SHA acceptance are **not asserted by this pre-push checkpoint**; subsequent PR checks/checkpoint comments carry that evidence. The PR stays draft and session needs-review.

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
