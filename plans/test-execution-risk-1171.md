# Task-scoped pytest execution risk (#1171)

Goal source: siege-analytics/claude-configs-public#1171. Parent authorized fixing local task gates; this slice treats test execution as execution, never a pure read or a source edit. Baseline c4d2f8a.

## Design and investigated premises

The current action classifier keeps repository cwd as the target for pytest. Ownership resolution correctly requires the task to own that directory. The risk classifier then enumerates every tracked file under the root, so an unchanged workflow forces Tier C. The existing bounded pytest argv grammar is separate from investigation: pytest is not certified as a reader.

Keep ownership unchanged. In task_tier, recognize a sole literal pytest or python3 -m pytest invocation, optionally after one fixed cd PATH && prefix, with the existing bounded no-write-option flags. Unknown plugins/config/commands/expansion/compositions retain conservative classification. The selected task must own the target Git root and be implementing; its ordinary evidence requirements still apply.

For that execution risk view, choose the newest comparable merge-base of HEAD against fixed local remote-tracking refs/remotes/origin/main and refs/remotes/origin/develop. No task or environment chooses the base. Missing or incomparable bases and failed Git queries retain Tier C. Classify the committed delta from that base plus staged, working-tree and untracked paths and explicit test selectors; raise the result to at least B for code execution. Preserve the declared-tier maximum and normal C classification for actual high-risk changes. Native Git configuration and local ref freshness retain their existing trust; this is not a transactional execution sandbox.

Alternative: require every ordinary pytest invocation to use the exact test receipt producer. Rejected as the only repair because it leaves the common reported command broken and adds a wrapper requirement. An arbitrary producer test argv is not newly classified as safe; producer support requires the same bounded actual test grammar and may remain conservative.

## Risks and falsification

- A source modification could be omitted from the risk set. Verify branch commits, staged changes, unstaged changes, untracked high-risk files and deleted high-risk files. Any unavailable listing fails to C.
- A test option could change execution or output policy. Reject narrowing for plugins/config/override/output options, opaque interpreter invocations, globs and mixed commands.
- Another task could donate preparation. Actual hook controls must retain cross-task/session/binding and designing denials.
- A stale/ambiguous baseline could pretend no changes. Only fixed fixed local remote-tracking names participate; missing refs or incomparable common ancestors fail conservatively.

## Validation plan

Red-first real hook: root pytest with ordinary B preparation and an unchanged workflow fails C before correction. Green: no-selector pytest, python3 -m pytest and fixed cd form use B; real C changes and declared C retain C. Unsupported shapes, unavailable base and classifier failures remain conservative. Run focused existing task gate/risk checks, config validator and native content-bound test producer before feature publication. Protected combined exact-head CI and Root review precede any merge/install.

## Investigation and validation record

The red-first root pytest hook call failed at Tier C solely because the unchanged workflow existed; no success artifact or gate was invented. The eleven focused checks passed in 19.884 seconds after one fixture setup correction: global ignore rules had omitted its baseline test file, so its disposable baseline now stages fixture files. Actual failures and corrections are retained in the session log; this was a test harness correction, not a production change.

The local protected-ref names are a risk heuristic under the existing trusted-checkout Git metadata assumption. They are mutable and may be stale or misdirected; this code does not attest server provenance, freshness, all imported dependencies or ignored files. No reference grants task authority. Task/session ownership, implementing lifecycle, B preparation, declared-tier maximum and commit-time staged-file enforcement remain separate. Missing/incomparable baselines and unavailable changed-path queries produce Tier C even if no high-risk source currently exists.

The opaque test-evidence producer retains its prior conservative classification. This slice repairs the ordinary direct pytest command without requiring a new wrapper. Independent review accepted the bounded design after requiring this precise local-ref qualification; final hash-bound review and protected combined CI remain pending. No installed behavior or full-suite success is claimed.

Pre-mortem-artifact: plans/test-execution-risk-1171.md#risks-and-falsification
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1171

## Source and scanner review

The staged scan completed with 41 findings: three plan wording findings corrected, plus 38 AST findings. It remains nonclean. The prior c4d2f8a review in plans/self-review-github-project-1161.md covers the unchanged resolver exception/denial sites, mapped by enclosing function rather than shifted line number. Those internal handled-error sites use CLI/decision tests rather than the scanner's required pytest.raises spelling; this is not a claim that each historical exception branch was raised.

The new helper contributes two findings at its UnknownShape handler: writing-code-7 and writing-tests-5. Returning None declines risk narrowing and retains the normal conservative classifier; it does not allow an action. A direct malformed-command control verifies that return. The actual hook controls exercise task/command boundaries and unavailable baseline/listing denials. The scanner convention mismatch does not justify suppressing a real runtime failure. Raw first scan: /tmp/test-execution-1171-scan.log. Final corrected scan is recorded separately.

Four existing risk/lifecycle regression methods passed in 8.636 seconds. Source hook validator, generated-source authority and risk metrics checks passed unchanged. Native content-bound receipt and protected full CI remain pending; no full-suite or live claim is made.

## Assumptions

The task author owns the target checkout and its Git metadata. Review-tier calculation is a risk heuristic; existing authorization, task/session ownership, actual owner holds and commit-time review remain authoritative for their own operations.

## Peer review

Independent source review accepted the resolver after qualifying the local-ref trust boundary. The new handled parse error was accepted as declining risk narrowing. Final raw scan/row binding is retained in /tmp/test-execution-1171-scan-findings.json; no exhaustive historical exception-path test claim is made.

## Lead review

Root approved the ordinary direct pytest lane and the fixed local remote-tracking risk baseline without a network fetch or new authority mechanism. Opaque execution, unsupported options and mixed commands retain conservative treatment. No installed permissions or owner holds changed.

## Quantified claims

Verified-by: actual focused execution_risk.py run (11 passed in 19.884 seconds), four existing risk regression methods (8.636 seconds), source hook validator and generated freshness checks. The corrected selected scan has 38 AST findings and no lexical findings, with its raw hash and per-row enclosing-function mapping stored in the evidence JSON. Native receipt and protected CI are separate pending evidence.
