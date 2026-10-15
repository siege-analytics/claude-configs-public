# Issue #962 F2/F3 Tier C self-review

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no (data/geospatial routing is regression-tested but not changed)
Working as: software engineer, tech lead
Roles: Peer reviewer = package/runtime correctness; Lead reviewer = epic closure and blast-radius review
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/962#issuecomment-6184498727
Goal source verification: GitHub issue read returned OPEN F2/F3 with installed-package closure criteria; latest coordinator claim is `issuecomment-6184547105`.
Plan reference: plans/issue-962-f2-f3-premortem.md
Pre-author-inventory: plans/issue-962-f2-f3-investigate.md#pre-author-inventory
Investigate-artifact: plans/issue-962-f2-f3-investigate.md
Pre-mortem-artifact: plans/issue-962-f2-f3-premortem.md
Hostile-review-artifact: plans/issue-962-f2-f3-hostile-review.md
Project-contribution: all advertised hook-bearing release layouts become independently executable consumer packages with readable, provenance-preserving capability instructions.

## Peer review

Shelf references: writing-code:1 (runtime correctness), writing-tests:1 (falsifiable installed behavior), writing-claims:8 (quantified evidence).

### Package/runtime mechanics shelf

Checked the engineering-principles/clean-architecture shelf for ownership and dependency direction. Runtime assembly is centralized in `install_hook_runtime`; layout-specific path derivation remains in the build layer, selector output remains data-only, and the hook owns installation-root resolution. No consumer must reconstruct a hidden mapping.

Evidence:

- From-scratch `rm -rf dist && python3.13 bin/build.py` completed.
- `python3.13 bin/_test/consumer_runtime_test.py` → `PASS (4 isolated layouts, prompt/path/push/parity/negative coverage)`.
- Each isolated manifest's 198 `known_by_source` entries is checked against a real packaged file and its packaged character/token cost.
- Actual hook output is parsed; every presented path is absolute, readable, and contained by an installation root whose path contains spaces.
- The exact Siege Utilities origin presents canonical provenance for the project rule and all three project skills; foreign host, shelf, and unknown fixtures remain fail-closed.

### Enforcement/security shelf

Checked the systems-architecture and security boundaries. The hook resolves `load_path` under its own installation root, rejects path escape via `relative_to(root)`, rejects unreadable selected files before emitting load instructions, and does not use payload cwd for capability paths. Selector route semantics and budgets are unchanged.

The valid Tier A push fixture creates a real clean Git repository, adds a scoped origin, commits README-only content with `Review-Tier: A` and `Self-Review:`, and invokes each copied package's actual `hooks/git/self-review.sh`; all four return 0. Before the fix, nested and flat returned 2 because the classifier was absent.

### Source/consumer parity shelf

- Language/framework: `python3 bin/language-scope.py --check` → 39 dispositions and 51 fixtures current across source plus all four current consumers.
- Data/geospatial: `python3 bin/data-scope.py --check` → 34 dispositions and 78 fixtures current across source plus all four current consumers.
- Historical evidence schemas remain unchanged; nested/flat are validated as current parity rather than fabricated exact-base attestations.

### Syntax and full suite

Syntax check: `python3 -m py_compile` on 6 changed Python files → all parse clean (exit 0); `bash -n` on 2 changed shell files → exit 0.

Full suite:

- Final build/freshness chunk: 15 commands passed, including build/check, full build, authority, kernel, risk metrics, progressive metrics, language/data scope, inventory, and lifecycle.
- Python: 18/18 modules passed on Python 3.13.13 (the prior 17 plus `consumer_runtime_test.py`).
- Hooks: 36/36 scenario suites passed with failure accumulation.
- Package/source validation: nested, flat, claude-code, craft-agent, and source all valid.
- Workflow policies: 2/2 passed.
- Flat layout, changed syntax, and `git diff --check` passed.

Doc build: N/A (README changed, no `docs/` files changed).
Notebook API check: N/A (no notebooks changed).
Review-gate: N/A (no signal file).

## Lead review

**Software-engineering affirmative standard:** The change closes the defect class, not just one archive. All four supported package roots receive the same required runtime dependency cohort; manifests are parameterized by layout and validated against final bytes. The installer validates transferred runtimes and manual sync documentation copies all four required directories.

**Approach-fit verdict:** Accept. A separate runtime `load_path` is additive and preserves `source_path` as canonical identity. Absolute hook paths are necessary because consumer cwd is unrelated; metrics normalize only the variable root for reproducibility and do not alter runtime instructions.

**Blast radius:** Build/package assembly, resolver JSON output, prompt-hook text, installer validation, README sync recipe, current scope parity, CI. No route table, project allowlist, shelf policy, budget, release workflow authorization, deployed workspace, main, or release branch is changed.

**Sequencing assumption:** A package build must complete before runtime manifests are measured, and CI must build before running the isolated consumer test. Both are explicit in `bin/build.py` and workflow order.

**Rollback:** Revert the implementation commit. Generated `dist/` is ignored and can be rebuilt; there is no installed, deployed, published, released, or external mutable state to undo.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| SR-1 | P1 | Absolute emitted paths initially made tracked injection metrics depend on checkout-root length, risking CI freshness failure. | fixed: normalize only the root prefix in the metrics generator; targeted hostile re-review ACCEPT |
| SR-2 | P2 | First isolated-test run compared `/var` with macOS-resolved `/private/var`. | fixed: containment compares resolved paths |
| SR-3 | P2 | Initial package selector subprocess inherited source checkout cwd and install path had no spaces. | fixed: run from clean consumer repo; install under `installed packages/` |
| SR-4 | P3 | System `/usr/bin/python3` is 3.9 and cannot execute existing PEP 604 annotations in some tests. | environment only: final suite used project-compatible Python 3.13; CI uses 3.12 |

No unresolved P1 or P2 findings.

## Quantified claims

- "four isolated layouts" — `python3.13 bin/_test/consumer_runtime_test.py` → `PASS (4 isolated layouts, prompt/path/push/parity/negative coverage)`.
- "18/18 Python modules" — loop over `bin/_test/*_test.py` → `PASS: 18/18 Python test modules`.
- "36/36 hook suites" — failure-accumulating loop over `hooks/_test/*.test.sh` → `Hook suites: 36/36 passed`.
- "51 language fixtures" — `python3 bin/language-scope.py --check` → `language scope: 39 dispositions, 51 source/consumer fixtures current`.
- "78 data fixtures" — `python3 bin/data-scope.py --check` → `data scope: 34 dispositions, 78 source/Claude/Craft fixtures current`.
- "max injection 8,530" — `python3 bin/progressive-loading-metrics.py --check` → `progressive loading: current (max injection 8530 chars)`.
- "198 sources / 804 snapshots / 2,904 mappings" — `python3 bin/generated-source-authority.py --check` → `generated source authority: current (198 sources, 804 artifact snapshots, 2904 generated file mappings)`.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---:|---:|---:|
| macOS `/var` containment assertion failed | test compared lexical rather than resolved paths | <1 min | <2 min | 2x |
| progressive metrics stale | absolute path output changed measured size | <1 min | <2 min | 2x |
| independent review exposed machine-specific metric risk | first metric refresh measured local checkout prefix | ~5 min review | ~4 min fix/test | <1x |
| local all-Python loop stopped on Python 3.9 | interpreter version not checked before loop | ~1 min | ~2 min rerun | 2x |

## Evidence-predates-work

Artifact: plans/issue-962-f2-f3-self-review.md
First-added commit: evidence-only parent commit created before the implementation commit
Work commit: subsequent Tier C implementation commit
Verification: the final PR branch history keeps the evidence commit as the direct ancestor of the implementation commit; exact SHAs are reported in the PR and epic evidence comment.
