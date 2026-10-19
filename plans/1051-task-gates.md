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

[runtime identity] The observed hook-process identity failure (live evidence pending from the worker) and incorrect target-repo metadata are separately addressed. The four identity tests run both real hook entrypoints, with Craft session vars absent except the directory-override case. Different-origin scope rejection reports the rejected path and both repo/origin values. Correct TARGET metadata works even from workspace CWD with explicit mutation paths.

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
