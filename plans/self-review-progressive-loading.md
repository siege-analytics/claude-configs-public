# Self-review: deterministic progressive skill loading

## Assumptions

Domain(s): software engineering, runtime policy routing
Geospatial cross-cut: no
Goal source: user-approved Skill Library Simplification Plan, progressive-loading PR.
Goal source verification: compact candidate kernel merged to `develop` at `53a7eb3eb36078dc99ad49baf6721453d5fc97b6`; current resolver hook injects selected prose from a 46,316-character root resolver on every prompt while the generated rules bundle remains 424,988 characters.
Plan reference: approved `skill-library-simplification.md`, Phase 3 / proposed PR 5.
Pre-author-inventory: `hooks/resolver/inject-resolver.sh`, root and skill resolver documents, project manifests, inventory tiers, kernel budget, build/install paths, resolver hook fixtures.
Investigate-artifact: this document plus the inspected resolver/hook/build surfaces.
Pre-mortem-artifact: Risks below.
Hostile-review-artifact: required before implementation commit.
Project-contribution: make the compact kernel the invariant context and select only task/project capabilities with deterministic reasons instead of ambiently treating the entire library as active.

## Pre-implementation comprehension

Current behavior: the resolver hook ignores prompt JSON, injects static instructions plus live sections from root `RESOLVER.md`, and tells the agent to scan the full resolver. Skill selection is human prose matching. Project routing is convention-only. Shelves appear in resolver prose. Unknown tasks can lead to broad manual loading.

Intended behavior: a compact machine-readable manifest and deterministic selector receive prompt, changed/referenced paths, and working repository identity; return an ordered load set with a reason for every item. The kernel is always included. Project overlays load only for a matching manifest repository. Shelves cannot select themselves and load only through an active skill's declared references. Unknown or ambiguous routing is visible and never falls back to loading everything.

Steps:
1. define a compact manifest schema with exact slugs, signals, project scope, priority, and explicit references;
2. generate/validate it against inventory and project manifests;
3. implement deterministic selection and human-readable diagnostics;
4. replace broad resolver-hook instructions with kernel plus the selector result;
5. preserve an explicit opt-out/canary switch and fail closed to kernel-only with a warning if selection fails;
6. add fixtures for generic, coding, Git, project, shelf, deterministic-order, unknown, and ambiguous inputs;
7. measure before/after injected characters and selected item counts.

Success criteria: irrelevant domain skills are absent from a generic task; relevant task/project skills resolve; reference shelves never auto-load; identical inputs produce identical ordered results; unknown and ambiguity states are explicit; project overlays never cross repo boundaries; kernel is always present; runtime injection is materially below the former resolver/rules surface; existing enforcement and all regression suites pass.

## Risks

1. Natural-language routing can overmatch. Use explicit normalized signals with deterministic priority and visible ambiguity; do not infer from embeddings.
2. Undermatching could omit a safety procedure. Kernel and mechanical hooks remain; high-risk routes receive explicit signals and negative fixtures.
3. Project detection can leak overlays across repositories. Match normalized remote identity and declared project manifest; ambiguous/no remote means no overlay.
4. Shelves can become ambient context through broad keywords. Mark them non-selectable and require an active non-shelf route to reference them.
5. Hook input shape can vary across runtimes. Parse defensively, test known shapes, and emit kernel-only warning rather than broad-loading on parse failure.
6. Immediate cutover could create false blocking. Provide a canary environment flag that emits old-vs-new diagnostics without loading old prose; preserve rollback by reverting one PR.
7. The root resolver contains engagement-specific policy. Do not silently delete it; stop injecting it globally and retain it as a compatibility/reference artifact until consumer migration is verified.

## Senior adversarial checklist

Reject nondeterministic ordering, substring overmatch, hidden load-all fallback, shelf self-selection, cross-project leakage, unvalidated slugs, path traversal, malformed hook JSON, prompt injection into diagnostics, failure-open broad loading, missing kernel, and claims that merely generating a manifest proves runtime use.

## Peer review

Pending implementation and hostile review.

## Lead review

A deterministic selector plus kernel-only failure mode is the correct next boundary. The runtime cutover must be proven through the actual injection hook and its fixtures, not only by catalog generation.

## Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| P1 | P1 | Current hook injects resolver prose but does not compute a load set. | pending implementation |
| P2 | P1 | Project routing is convention-only. | bind selection to project manifest identity |
| P3 | P1 | Shelf routes are visible in global resolver prose. | prohibit shelf self-selection |
| P4 | P2 | Root resolver is 46,316 characters and full rules bundle is 424,988 characters. | measure actual post-cutover injection |

## Quantified claims

Baseline files: root resolver 46,316 characters, skill resolver 17,802 characters, kernel 6,944 characters, generated rules bundle 424,988 characters. The implementation will record exact manifest size, per-fixture load counts, and hook injection size.

## Rework ledger

No rework yet.

## Evidence-predates-work

Artifact: `plans/self-review-progressive-loading.md`
First-added commit: this planning commit
Work commit: subsequent implementation commit
Verification: this commit must be an ancestor of implementation.
