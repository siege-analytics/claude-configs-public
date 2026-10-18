---
ticket_refs:
  - siege-analytics/claude-configs-public#1046: design, Fact Sheet, junior/senior, pre-mortem posted; self-review summarized in the draft PR
---

# Self-review: #1046 real-YAML frontmatter validation

## Assumptions

Goal source: #1046 (ticket body, the 2026-10-18 amendment, and the approved design note https://github.com/siege-analytics/claude-configs-public/issues/1046#issuecomment-6252134552)
Working as: software engineer, tech lead
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1046#issuecomment-6252824404 (the Fact Sheet, recorded on the ticket before authoring. It measures the data-shape contact (a full-key real-YAML sweep of all 198 build inputs) and the version-resolution contact (`python3` → /usr/bin 3.9.6 without PyYAML; Homebrew 3.14 with 6.0.3; CI setup-python 3.12 with no install step).)
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1046#issuecomment-6252824404
Pre-mortem-artifact: plans/pre-mortem-1046-frontmatter-validation.md
Hostile-review-artifact: plans/hostile-review-1046-frontmatter-validation.md
Project-contribution: Every packaged skill and always-on rule header is now provably parseable YAML with strict string metadata at inventory, build, deploy-build, and composed-package time. A missing parser fails closed. This removes the false-green class behind #1042/#1046 for every consumer layout, and the validator can be vendored for consumer bundle checks (D7).

Additional assumptions:
- **A1:** the Craft host parses skill frontmatter with a real YAML parser followed by schema validation. Supported, not proven, by `name: Required` on the two unparseable skills and by the quoted `analysis` control passing.
- **A2:** PyYAML (YAML 1.1) agrees with the host on every accepted file, because the lint rejects 1.1/1.2 divergences, anchors, aliases, tags, and merge keys. This is unprovable from source; host agreement is post-release evidence.
- **A3:** quoting changes syntax only. Verified by `committed_content_cases`: each header differs from v3.5.66 only by the added quotes, and the parsed value equals the original raw text.
- **A4:** every consumer layout is regenerated from source. All catalogs were produced by the repo's own generators, and the dist diff is limited to the 5 files plus size and timestamp metadata.

Ticket fitness: `bash scripts/discipline/evaluate-ticket.sh siege-analytics/claude-configs-public#1046` returns `PASS` (rc=0): sections Context, Goal, and Acceptance are present, the /think link is present, and the assumptions block is present. No exemption is claimed.

## Peer review

Shelf checks:
- **writing-code:** the validator fails closed on every error path. No exception is swallowed into a pass, PyYAML is never silently skipped, and failures name the file and reason.
- **writing-tests:** fixtures use the real parser, and the missing-dependency cases block the import in a subprocess rather than mocking the layer under test. A presence-only mutation is detected.
- **writing-claims:** every count below was observed in this work cycle on this branch, and installed proof is explicitly marked not performed.

Gate evidence on head `c15b56a`, with PyYAML 6.0.3 on CPython 3.12.12:
- `frontmatter_validation_test` → PASS
- `skill_inventory_test` → PASS
- `skill-inventory --check` → current
- `build.py` → exit 0
- `gate_contract_test` and `--check --probe` → PASS
- `effective_policy_test` and `validate` → PASS
- procedure, project, and package-selection tests → PASS (24 package-selection tests OK)
- selected-registration examples, independent and siege → exit 0
- `resident_delivery_test` → PASS
- `package_generation_test` → PASS
- `generated_source_authority_test` and `--check` → PASS
- `review_risk_test` → PASS
- `review_risk_policy.test.sh` → 12 passed
- The post-commit replay of `50c1e92` passed 30 of 34 CI validate-job steps; the one failing step, 09, is covered by the step 09 re-run above on `c15b56a`.
- `selected_registration_test` → 12 failures, identical at base `056b5337` (all "registration path contains symlink", from the macOS `/var` symlink). Pre-existing, not introduced here.

- **Validator** (`bin/frontmatter_validation.py`):
  - It uses only the standard library plus PyYAML, imported lazily. It has no repository path assumptions and exposes a CLI (`--kind`, `--check-dependency`).
  - Its loader is a `SafeLoader` subclass that rejects duplicate keys. Merge keys are skipped by the duplicate check, then rejected by the lint.
  - It requires a mapping. For skills, `name` and `description` are required, non-empty, non-whitespace `str`. For rules the block is optional, but a present block must be valid.
  - Delimiter handling is exact `---\n` … `\n---\n`. A BOM, CRLF, a near-miss delimiter, or an unterminated block is rejected.
- **Gates:**
  - `skill-inventory.make_item` validates with a strict file read. It also refuses any header where hand-parsed and YAML `name`/`description` differ, which keeps the catalog truthful and stays inside the #1048 boundary.
  - `build.py` has a new Phase 3b before any layout write. It covers `--check`, the full build, and `--deploy`.
  - `compose-project.package()` validates composed and selected packages.
  - `install.sh` and `sync-workspace-hooks.sh` preflight `--check-dependency` before any build or mutation.
- **Registries:**
  - `package_selection.SCAFFOLD_FILES`, `selected_registration.CORE_FILES`, and the package-generation trusted-tool list now include the validator. Staged scaffolds import it.
  - The review-risk policy now classifies `bin/frontmatter_validation.py` and `requirements-validation.txt` as Tier C. They are blocking enforcement dependencies under the #962 F4 rule, and before this change they computed Tier B. Both are added to `AUTHORITY_DEPENDENCY_FLOOR`, and `review_risk_test` plus `review_risk_policy.test.sh` (12/12) pass.
  - CI installs `requirements-validation.txt` with `--require-hashes` in the validate and publish jobs.
- **Python 3.9:** annotations are deferred, and there is no 3.10+ syntax. Unit and committed-content cases pass on 3.9.6, 3.12.12, and 3.14.6 with PyYAML 6.0.3.

## Lead review

- **Does this solve the ticket?** The two direct skills and the three rule headers now parse, and the presence-only false green is replaced by a real parse at every packaging gate. The ticket's installed-proof acceptance criterion (native `skill_validate` on installed bytes plus a fresh-session invocation) is **not** satisfied by this PR. It is post-release only.
- **Class, not instance:** a full-key sweep of the source corpus (198 headers) and of every generated layout (796 files) shows 0 failures. Validation runs in every packaging path rather than only at the 5 known files.
- **Scope held:** hand-parser consolidation stays in #1048. `KERNEL.md`/`RULES.md`/`_coverage.md` support-file validation was escalated to the coordinator rather than expanded unilaterally. `decomposition-guard.sh` failing open remains a known sibling.

## Findings

See `plans/hostile-review-1046-frontmatter-validation.md`. Five findings were fixed; finding 4 (support files) and finding 5 (deploy transforms) are deferred with evidence, and finding 7 (pin enforcement) is accepted.

## Quantified claims

- Source headers validated by `build.py --check` Phase 3b: **198** (157 skills, 37 rules, 3 project skills, 1 project rule). Verified by `.venv-1046/bin/python -B bin/build.py --check`, which reports "198 skill/rule header(s) validated".
- Generated corpus: **796** skill and rule files across flat, nested, craft-agent, and claude-code, with **0** validator failures. Verified by the dist sweep over a fresh `--dist` build of the working tree.
- Counts are unchanged: **77 direct / 83 nested** SKILL.md in each of the 4 layouts, at both base (`056b5337`) and head. Verified by the same sweep's base-versus-head count report.
- Generated output diff between base and head builds: **0 added, 0 removed, 38 changed**. That is 20 copies of the 5 quoted files, 5 `resolver-manifest.json` character-count updates, 4 `CHANGELOG.md` copies, and 9 timestamp-only metadata files (RULES_BUNDLE ×2, package.json ×2, enforcement-manifest ×3, build-info ×2). Verified by a file-digest comparison.
- Catalog truth: `frontmatter_name` and `description` are identical to base for all **198** inventory items. Only sizes, hashes, and heuristic evidence moved. Verified by a field-level comparison against `git show 056b5337:catalog/skills-inventory.json`.
- Mutation check (presence-only validator, bytecode cleared before mutate and before revert):
  - It detects 2/2 verbatim skill headers, 3/3 verbatim rule headers, and every bool, list, dict, int, unterminated, duplicate-key, tab, and `yes` fixture. The #1042 negatives (0/2) stay caught under presence-only, as expected.
  - Both test files fail under each mutation and pass after the byte-exact restore, and the worktree diff stat is identical before and after.
