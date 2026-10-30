# Actors can edit existing GitHub artifact text without unrelated task gates (#1144)

Pre-mortem-artifact: plans/remote-metadata-task-scope.md
Hostile-review-artifact: plans/remote-metadata-task-scope.md

## Context

Actual installed 3.5.81 gh pr edit --repo owner/repo --body-file calls treat remote slugs and read inputs as filesystem writes, select an unrelated workspace task and classify the entire checkout as C. Status/publication guards also inspect quoted body prose as operations. Evidence: issue https://github.com/siege-analytics/claude-configs-public/issues/1144 and /private/tmp/remote-metadata-routing-repro.json; no remote command ran in that reproduction.

## Goal

Dheeraj directed that actors can edit their existing comments and PR text. Permit these ordinary existing-artifact text edits without a task gate, while keeping real source mutations and state/topology operations guarded.

Design: plans/remote-metadata-task-scope.md

## Acceptance

A literal existing-artifact body/title/edit-last command passes the complete registered hook stack from an unrelated cwd with no task gate. Body files are read inputs. Unreadable inputs deny clearly; unproven companions, filesystem writes, state/base/merge and unsupported API payloads do not inherit the exception. Registration verifies classifier bytes before loading it. Revert the typed metadata route; the gate-free text-edit tests go red because they again resolve unrelated filesystem/task authority.

## Assumptions

User authorized routine existing-artifact text maintenance without another task gate. Highest risk: an ambiguous command or unsafe companion inherits the exception and escapes mutation controls. Strict field/operation parsing, independent companion proof and mixed-write negatives bound that risk. Body inputs must be readable regular files; unknown API payloads are not exempt. Classifier bytes must be verified before the unbound router imports them. Installation remains exact-main with private backup and actual host acceptance; no direct source patch to a live workspace.

Operator requires existing PR/issue body/title and edit-last comment edits without task-gate ceremony. GitHub authorship cannot distinguish actors sharing one account. The exception is action-based, not an authorship or read-only claim.

Plan: strictly parse literal gh PR/issue text edits and API PATCH body/title fields using existing shell tokens. Optional explicit remote slug/URL and body files are inputs, never filesystem mutation targets. Numeric/branch selectors and the normal current-branch PR default remain supported without --repo ceremony. API --input JSON is outside the initial typed subset; literal raw fields are supported. Pure text maintenance returns metadata_only and bypasses task/status/destructive ceremony. Mixed commands preserve every actual filesystem target; state/topology/reviewer/label/base/new comments remain guarded. Unreadable or nonregular body inputs fail clearly. Router enrollment/receipt verification remains mandatory; pinned action classifier permits the same typed maintenance when task identity is pending. No network authorship check, new gate schema or remote execution.

Validate actual hooks for gate-free body/title/edit-last/API text success with status vocabulary; unreadable body diagnostics; mixed writes/scope; state/merge/delete/reviewer/base/new-comment negatives; router unbound typed edit positive and state/mixed denial. No settings/deployment/remote mutation. VERSION stays coordinator-owned. Do not commit/push until independent review.

## Implementation and verification handoff

Source is ready for independent review, not committed/pushed. No VERSION edit, remote operation, live apply or settings mutation. Literal content-only parsing uses the existing shell lexer; all actual filesystem companion targets remain. A lead review found a new mixed-reader bypass (`metadata; gh pr view --web`): fixed by independently proving each nonmetadata reader via the released classifier; unproven companions contribute cwd as a gated mutation target. Quoted command examples in text exposed an actual fix-shape false trigger: only the same typed pure metadata lane bypasses that publication check.

Validation: five new real-hook Gates methods PASS26.161s (text surfaces, mixed/unknown scopes, released companion proof, PR API state agreement, unreadable input); complete router31 PASS16.023s including full16-hook registered Bash stack with command prose, appended-write deny and unbound typed metadata/pin tamper controls. Existing destructive32 and fix-shape4 pass. Coordinator45 also passed after the narrow PR API state addition. Hook/syntax/whitespace checks pass. No actual GitHub mutation was executed by fixtures.

Dependency audit: three new actual inline import edges to task_actions (coordinator-status, destructive, fix-shape); no removed edges. Coordinator now has two extractor uses (command and cwd). Site digest8dc43dd7ee0970d7e5d2e32cd77a457a81968130195f0896712afaf075d3d1d8 and assignment-use digest852b9fe50e7b0aa14ca233efe2ff7d42e416c09ae48938b6f237ec2c334aa9d2. Exact edge/site/use assertions and each new-import removal negative pass; existing negative checks remain. Runtime enforcement/helper sources and the explicitly protected router/audit tests retain C. The shared task-keyed test module retains its existing B floor; this mixed change is C overall. No floor was lowered. Router pins installed task_actions bytes and installer compares those bytes with immutable reviewed source before activation.

Limits: strict API PATCH accepts raw body/title fields on existing issues/pulls or existing comment-body endpoint; --input JSON, unknown/duplicate fields/methods and missing API target are not exempt. CLI title/body/body-file, numeric or branch selector, current-branch PR default, edit-last comment and optional explicit owner/repo/URL are supported. This is action-based artifact maintenance, not proof of actor authorship. Shared account identity cannot establish session ownership. Full suite, final catalogs/scan, source commit/CI and live delivery remain coordinator work after independent review.

## Peer review

Root reviewed the action boundary and found the unsafe companion exception; implementation now requires independent proof for reader companions. Root also requested normal implicit-repository CLI forms, PR API state agreement and a complete registered-stack fixture. Independent repair reviewer approved the bounded source, separately reran companion controls and unbound/full16-hook router controls, and found no blocker. This approval does not replace protected CI or Craft host acceptance. Craft configs hub will receive exact committed source pins for its separate bounded review. No review result is implied by this candidate plan.

## Lead review

Affirmative standards: existing-artifact content maintenance is a typed mutation surface, independent of task implementation authority. Unknown shell/API forms do not inherit that exception. Source identity and receipt integrity precede loading the classifier. Mixed filesystem effects preserve ownership checks. Tests cover rejection paths and the complete registered Bash stack; actual SDK delivery remains final installation acceptance, not fixture certification.

## Quantified claims

Before this candidate commit: five new Gates methods, router31, coordinator45, destructive32 and fix-shape4 passed as recorded above. Independent review reran companion controls and two router controls. No full Linux CI, main promotion, installed artifact count or live SDK pass is claimed yet. The code never executed a proposed GitHub command during tests.

## Test plan

Run the actual source-bound producer against the combined branch, including router, metadata/transport, scanner and complete task-keyed suites. Refresh generated artifacts in order, run protected final-head CI, obtain bounded Craft hub review, promote through develop into main, back up and normally install exact main. Verify live existing-text maintenance and original GA task isolation with implementing A/designing B/unscoped controls, plus ordinary terminal Claude isolation. Preserve user gates, source files and unmanaged settings/skills.

## Evidence-predates-work

Artifact: plans/remote-metadata-task-scope.md
First-added commit: 54cf3c2a09c596f5995fe7bd157bbbe999c138a4
Work commit: 5acfff3506355eac09fe5268d49d7a395a76ef12
Verification: git merge-base --is-ancestor 54cf3c2a09c596f5995fe7bd157bbbe999c138a4 5acfff3506355eac09fe5268d49d7a395a76ef12 returned0. The initial plan was written before implementation in the agent trace and first committed with the source, not as an earlier separate planning commit.

## Rework ledger

- Lead review found the unsafe reader companion exception; fixed and reran both-order positive/negative controls before commit. Time ratio was not measured.
- Native commit rejected missing required review headings; completed the record and retried normally. No hook bypass.
- The integration merge message lacked a ticket reference; added #1144 and committed normally. No hook bypass or rewritten source ancestry.

## Findings

| ID | Priority | Description | Resolution |
| --- | --- | --- | --- |
| M1 | P1 | Unproven reader companions could inherit metadata exemption. | fixed; each companion independently proven or gated |
| M2 | P1 | Quoted command examples triggered publication guards. | fixed; complete registered stack tested |
| M3 | P3 | Strict API support excludes --input and unknown fields. | noted; no exemption or equivalence claim for unsupported forms |

Goal source verification: bash scripts/discipline/evaluate-ticket.sh plans/remote-metadata-task-scope.md → PASS: ticket plans/remote-metadata-task-scope.md is fit for execution.
Domain: software engineering. Geospatial cross-cut: no. Implementation author: task_gate_review. Lead: Codex. Independent bounded reviewer: repair_review. Craft reviewer: Siege Claude Hub (design author, limitation declared).
Pre-author-inventory: NONE (existing action boundary repair; no new skill/rule family).
Syntax check: ast.parse on all7 changed .py files and bash -n on all5 changed .sh files relative60cb513 → all parse, exit0.
Measured root router command: env PATH=/opt/homebrew/bin:/usr/bin:/bin TMPDIR=/private/tmp python3 -B bin/_test/craft_hook_router_test.py → Ran31 tests, OK (/private/tmp/metadata-root-router.log). Other source-author focused counts above are author-reported; the combined actual producer is retained separately as the final seven-source receipt before push.

Final combined source-bound producer at5acfff3: router31 + transport9 + scanner27 + task-keyed77 =144 Python tests passed; review_risk_test: PASS. Hub26, session-signal18, spawn14, coordinator45, destructive32 and fix-shape4 =139 shell scenarios passed. Actual command is preserved in test-gate.json and /private/tmp/metadata-combined-producer.log; it invoked each named suite directly through hooks/lib/test-evidence.py record with all7 changed production Python sources. Ordered bin/validate-local.py --mode refresh passed (/private/tmp/metadata-final-refresh.log). The only generated delta adds two discovered router-test references to skills-inventory.json. No production source changes follow this producer.
