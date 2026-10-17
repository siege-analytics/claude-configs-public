# #982 — Tier C workflow overlap decision and evidence

Base: exact `develop` cefa286ebda9dd81ad5307eb2a4e5c02517cb466. Integration: draft PR to `develop`; no promotion, merge, deployment, installation, or release. Parent #970, epic #962. Audit comments: 6148451579 and 6153066230 (the latter corrects the verifier's existence).

## Pre-mortem (before PR)

- **Tiger: an explicit billing slug is mistaken for a generic protected-check override.** Remove all generic merge commands/standing approvals/preauthorization; preserve slug strictly as diagnostic. The verifier always returns nonzero even on billing-looking evidence. Test a plausible complete billing response, wrong repo, missing approvals, forged/expired standing grants, out-of-scope paths and all incomplete/invalid check evidence. No authoritative electinfo host/repo policy is declared: never infer one from path names. Rollback: revert this isolated commit on develop if its diagnostic breaks consumers; *do not* roll back to generic bypass authorization.
- **Tiger: ambiguous multi-action prompts silently run the first ticket action.** Three mutually exclusive action routes; explicit action slugs participate in ambiguity; kernel-only on conflicts or budget overflow. Keep `ticketing` ID for create and every public action slug. Rollback the resolver and manifest together while leaving billing quarantine intact.
- **Tiger: prose weakens branch/release protections.** Declare the project topology before observed GitHub Flow behavior, ask before any develop creation/sync; correct main-only publication, keep exact-main deployment and release/review roles unchanged. Regression: branch policy, main-only publication, deployment source fixtures.
- **Tiger: generated artifacts lag final sources.** Stage final source/test paths first (inventory uses `git ls-files`); regenerate inventory, build, generated authority, lifecycle, and metrics in dependency order, then freshness checks. Do not track `dist/`.

## Exact source / identifier / consumer disposition

- `skills/{branch,develop-guard,commit,create-pr,merge}/SKILL.md`: separate branch topology, integration gate, ticketed commits, PR evidence, and merge/cleanup. Runtime routes `git-branch`, `git-commit`, `git-pr`, `git-merge`; local Git hooks/CI and `skills/RESOLVER.md` remain consumers. **Retain**; reconcile branch wording only.
- `skills/_writing-releases-rules.md`, `.github/workflows/build-and-publish.yml`, `.github/workflows/publish-consumption-tags.yml`, `bin/build.py`: release writing, validation and main-only publication, tag reconciliation, and exact-main deployment have different triggers. **Retain**; correct stale README/flat-layout description; do not edit deploy gates.
- `skills/{code-review,self-review,hostile-review,cross-review,pr-comments,coderabbit-response}/SKILL.md`: reviewer, author, adversarial, cross-provider, thread, and bot response roles are different. `projects/siege-utilities/skills/hostile-review/SKILL.md` belongs only to exact `github.com/siege-analytics/siege_utilities` overlay. **Retain** all.
- `skills/{ticket-guard,create-ticket,update-ticket,close-ticket,pre-work-check,evaluate-ticket,decision-to-ticket,ticket-decomposition}/SKILL.md` and `_ticket-lifecycle-rules.md`: destination, action, fitness, decision, decomposition and state changes are distinct. Runtime manifest `ticketing` remains creation alias; additive `ticketing-update` and `ticketing-close`, mutually exclusive, select action + guard. **Retain** slugs/commands and lifecycle rule.
- `skills/ci-billing-failure-merge/SKILL.md`, `scripts/ci/verify-billing-block.sh` (+ Python diagnostic): static compatibility slug, never an admin merge grant. **Quarantine as non-authorizing diagnostic** pending an independently reviewed exact project policy. Selector labels explicit selection diagnostic-only even in a plausible electinfo-named repo.

## Rollback and evidence

Unchanged kernel K3/K4/K5, credential/no-sensitive-file and destructive-action guards, branch protection, and exact-main deployment remain authoritative; no skills are deleted or automatically made ambient. PR remains draft until operator acceptance.

## Self-review / Tier C evidence (final local patch)

Pre-mortem-artifact: plans/issue-982-workflow-scope.md#pre-mortem-before-pr
Hostile-review-artifact: plans/issue-982-workflow-scope.md#peer-review

## Assumptions

The exact integration base remains cefa286ebda9dd81ad5307eb2a4e5c02517cb466. No authoritative project host/repo/path policy grants a protected-check bypass; this generic compatibility slug therefore has no positive authorization path. Generated `dist/` outputs are ignored consumer artifacts, not hand-maintained sources.

## Peer review

Independent pre-PR hostile review and latest ACCEPT are recorded below; concrete findings were fixed in this patch. The billing-only re-review is focused, not a claim that external CI ran.

## Lead review

Self-review inspected the protected-check boundary, selector ambiguity, preserved topology, release condition, and catalogs. The PR stays draft; operator/maintainer review is still outstanding and no merge is requested.

## Quantified claims

Counts below distinguish authored inventory and packaged consumer content; estimated tokens are approximations, not a measured model tokenizer count. Test counts name actually completed local commands, not CI results.

Computed by `bin/review-risk.py`: **Tier C** (manifest, CI verifier and workflow). Self-Review-Source: this file. Pre-mortem-artifact: section above. Hostile-Review: independent pre-PR review identified (1) mixed billing/test failure text misclassified as billing-only, (2) duplicate slug in overflow fixture, (3) overstated negative-test coverage; all fixed. Latest focused re-review found annotation title/raw_details hiding a test failure; fixed with negatives; latest independent billing re-review **ACCEPT**. No generic authorization remains; out-of-scope paths, grant provenance/expiry and operator approval are structurally unavailable without a project policy, not pretended to be dynamically verified here.

Self-review findings / disposition: selector explicitly tags billing compatibility as diagnostic-only; shell verifier always returns nonzero and never calls merge; null or incomplete branch protection, missing check runs, reviewer block, nonbilling or conflicting failure, pending check, negative/malformed duration, and changed SHA report gaps. Ticket actions use guard plus one action; explicit aliases add guard; multi-action route/explicit collisions become kernel-only; overflow remains kernel-only. Branch prose now defers to declared topology and requires approval for develop creation/sync. README now accurately says main push publishes; no release or deployment gates were relaxed. Rollback should revert the routing batch as a unit, never reinstate generic bypass.

Authored inventory before/after for one request each (estimated tokens are `ceil(characters/4)` per skill): create 28,701 chars/7,176t → 20,890/5,223 (−7,811/−1,953); update 28,701/7,176 → 14,245/3,562 (−14,456/−3,614); close 28,701/7,176 → 13,057/3,265 (−15,644/−3,911). Three-request mean saves 12,637 characters and ~3,159 estimated tokens (44%); **only** these routed tasks save content, not ambient kernel bytes. Newly supported update/close issue aliases had zero selected previously, so they are new selection, not a savings claim. Current consumer packages (`dist/claude-code` and `dist/craft-agent`) measure create 20,978/5,245, update 14,273/3,569, close 13,085/3,272 packaged chars/tokens; they include packaging overhead and are not interchangeable with authored-baseline figures.

Initial local verification (commit `e5b7fd5`): 15/15 supported-Python (3.13) suites; 36/36 hook suites in three bounded batches; two workflow fixtures (branch topology 10/10; main-only release PASS), billing focused 18 evidence negatives plus permanent non-authorizing entry point, ticket aliases/multi-action/overflow, flat-layout package check, exact-main deployment source test, packaged selector canaries, inventory/authority/lifecycle/metrics/kernel/review-risk/build freshness, `git diff --check`. Generated authority: 198 canonical sources, 804 snapshots, 2,900 mappings; lifecycle: 0 completed, 198 legacy; kernel: 6,995 chars/1,749t; max fixture injection: 7,774 chars. No `dist/` files tracked. The default macOS `python3` is 3.9 and fails existing modern type-syntax fixtures, hence the supported Python 3.13 run.

## PR #990 review response (follow-up)

Independent A review ACCEPT; Claude review CHANGES_REQUIRED at `e5b7fd5`. Addressed F1: removed noun-like `open issue`, `new issue`, `resolve issue` and related broad route terms; `list open issues`, `are there any open issues`, `what is the new issue about` remain kernel-only, while `resolve issue handling in this python module` selects coding+python only. Explicit close/create/update slugs and clear action phrases still route to guard+action. F2: treat null optional GitHub output/annotation fields as empty, recognize only the canonical billing sentence with known `Error:` or `GitHub Actions:` prefix (not arbitrary suffix), keep mixed billing/test-failure text rejected and CLI always GAP/STOP/exit 1. Added a prefixed-null realistic positive evidence shape and two new negatives (20 evidence negatives at `1324552`). Follow-up F2b uses the exact documented two-sentence GitHub message (billing reason plus Billing & plans instruction), with only three declared exact display prefixes (`""`, `"Error: "`, `"GitHub Actions: "`). Bare and prefixed full messages are positive evidence shapes; partial reason and mixed appended failures are rejected (**22** evidence negatives). The CLI still always GAP/STOP/exits 1. F3: corrected remaining `CONTRIBUTING.md` tag claims, removed a stray skill separator, and replaced the Siege Utilities `--admin` hint with non-authorizing escalation. Latest independent follow-up re-review **ACCEPT** on the attached corrected files, with the explicit caveat that resolver implementation, test execution and generated freshness were not independently inspected in that pass; local full matrix/freshness evidence below covers execution, and the coordinator's Claude re-review of the new SHA remains pending.

Follow-up local verification at `1324552` (before F2b): 15/15 Python 3.13 suites, 36/36 hook suites (three bounded batches), branch topology 10/10, main-only release fixture PASS, billing 20 evidence negatives plus always-non-authorizing CLI, flat package and Claude Code/Craft Agent selector canaries (`list open issues` kernel-only, `close issue` guard+close), inventory/authority/lifecycle/progressive metrics/kernel/review-risk/build freshness and `git diff --check` PASS.

The F2b patch also corrects `.github/workflows/build-and-publish.yml`'s stale comment claiming a real tag push and a release-notes commit; no workflow trigger or executable step changed. Independent focused F2b hostile re-review: **ACCEPT** for the full-message matcher, declared prefixes, partial/mixed negatives, and permanent CLI rc1 (not a substitute for the coordinator's full Claude re-review on the next SHA). Final local post-F2b matrix: Python 3.13 15/15, hooks 36/36 in three batches, branch topology 10/10, main-only release fixture PASS, billing 22 evidence negatives and realistic bare/prefixed positives with CLI GAP/STOP, flat package and both consumer selector canaries PASS, inventory/authority/lifecycle/progressive metrics/kernel/review-risk/build freshness PASS, and `git diff --check` PASS.

**Explicit action overhead (R3):** for an explicit action slug without route terms, the old resolver at exact base selected the action alone. The new resolver adds `ticket-guard` (6,434 authored chars / 1,609 estimated tokens) for each: create 14,456/3,614 → 20,890/5,223; update 7,811/1,953 → 14,245/3,562; close 6,623/1,656 → 13,057/3,265. Packaged after for each is 20,978/5,245, 14,273/3,569, 13,085/3,272. This is an intentional safety cost, not savings; routed create/update/close savings above apply to natural-language routes, not explicit slugs.

Remaining risk: no authoritative project-specific admin-merge policy exists, so billing-blocked PRs cannot use this compatibility skill to bypass checks. A future project capability must provide exact host/repo/path policy, complete required-check and reviewer accounting, PR/head-specific operator approval and hostile negatives before any override exists. CI on the draft PR may be blocked by external billing; no local result substitutes for required checks.
