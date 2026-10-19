---
ticket_refs:
  - siege-analytics/claude-configs-public#1046: comment posted (https://github.com/siege-analytics/claude-configs-public/issues/1046#issuecomment-6252860530)
---

## Pre-Mortem
Task: Shared real-YAML frontmatter validator (Approach C), wired into inventory and package generation, with the 5 malformed descriptions quoted
Ticket: siege-analytics/claude-configs-public#1046
Fact Sheet: https://github.com/siege-analytics/claude-configs-public/issues/1046#issuecomment-6252824404
Design note: https://github.com/siege-analytics/claude-configs-public/issues/1046#issuecomment-6252134552

### Tigers

#### Tiger 1: Validator fails open or CI goes red because PyYAML is absent
- **Scenario:** CI (`actions/setup-python` 3.12, no install step) or a local `python3` without PyYAML runs the validating gates. If the import error is swallowed, the false green persists. If it is unhandled, CI breaks with an opaque traceback.
- **Evidence:** `.github/workflows/build-and-publish.yml:21-24` has no dependency install. Local `/usr/bin/python3` 3.9.6 raises `ModuleNotFoundError: yaml` (Fact Sheet, N1).
- **Severity:** 70 (Mitigate-before-ship). Data integrity 80, user impact 70, reversibility 40, dependency chain 70, detection latency 90 if it fails open.
- **Urgency:** Launch-Blocking
- **Trigger condition:** `import yaml` fails in any validating path.
- **Mitigation:** a lazy import that raises a dedicated dependency error, which every caller turns into a non-zero exit with an explicit message. A test simulates the missing module in a subprocess and asserts the non-zero exit. A pinned requirement file plus a CI install step run before the first validating step.
- **Status:** Mitigated (in this PR's implementation and tests)

#### Tiger 2: The install/deploy path fails closed on hosts without PyYAML
- **Scenario:** after release, `bin/install.sh` or `bin/sync-workspace-hooks.sh` runs `python3 bin/build.py --deploy` on an interpreter without PyYAML. The install stops.
- **Evidence:** `bin/install.sh:139`, `bin/install.sh:311`, `bin/sync-workspace-hooks.sh:43`. This host's `python3` lacks PyYAML.
- **Severity:** 52 (Monitor-after-ship). Data integrity 10, user impact 70, reversibility 20, dependency chain 60, detection latency 10 (loud).
- **Urgency:** Fast-Follow
- **Trigger condition:** post-release install on an interpreter without PyYAML.
- **Mitigation:** an explicit fail-closed message naming the pinned requirement file and install command; a documentation note; flagged to the coordinator as a prerequisite for the installed-proof step. This is intended under D1, not a silent failure.
- **Status:** Accept-Risk (D1 mandates fail-closed; mitigated by a clear message and documentation)

#### Tiger 3: Staged selected builds lack the new module
- **Scenario:** `package_selection.build()` stages only `SCAFFOLD_FILES` and loads `compose-project.py` from the staged copy. If `compose-project.py`/`build.py` import the new validator by path, selected builds crash.
- **Evidence:** `bin/package_selection.py:31-37` and `:221-228`.
- **Severity:** 64 (Mitigate-before-ship)
- **Urgency:** Launch-Blocking
- **Trigger condition:** any `--selection` build or `package_selection_test`.
- **Mitigation:** add the module to `SCAFFOLD_FILES`; run `package_selection_test`, `selected_registration_test`, `package_generation_test`, and both `examples/selected-registration/run.py` cases.
- **Status:** Mitigated (in implementation)

#### Tiger 4: The compatibility lint false-positives on legitimate corpus
- **Scenario:** the lint flags dates, versions, or other legitimate plain scalars and breaks every build.
- **Evidence:** the Fact Sheet §9.3 census includes `metadata` dict×53 and `license`/`paths` strings. The base sweep with the same lint regex found 0 divergent scalars.
- **Severity:** 45 (Monitor-after-ship)
- **Urgency:** Fast-Follow
- **Trigger condition:** a plain scalar matching a divergent form in any packaged header.
- **Mitigation:** the lint applies only to PLAIN scalars matching YAML 1.1-only forms (bool words other than true/false; sexagesimal; leading-zero octal; `0b`; `_` digit separators). The corpus sweep with the shipped validator must show 0 failures in source and in every `dist` layout.
- **Status:** Mitigated

#### Tiger 5: Quoting changes a hand-parsed or generated value
- **Scenario:** a hand parser (`build._parse_yaml_frontmatter` uses `strip('"').strip("'")`; `skill-inventory._yaml_scalar`; `hooks/lib/split-frontmatter.py`) yields a different description after quoting, so generated catalogs and manifests drift.
- **Evidence:** `bin/build.py:281-285`, `bin/skill-inventory.py:53-78`. `_prospective-memory-rules.md` contains `"`.
- **Severity:** 48 (Monitor-after-ship)
- **Urgency:** Fast-Follow
- **Trigger condition:** a quote style that needs escapes.
- **Mitigation:** single quotes where the text has `"`. An equality proof across YAML and every hand parser. Diff of the regenerated outputs is restricted to the 5 files plus inventory hashes and sizes.
- **Status:** Mitigated

#### Tiger 6: Test-fragility (wrong mock layer)
- **Scenario:** tests stub the YAML layer, so they pass regardless of the validator.
- **Evidence:** pattern named in `skills/pre-mortem/SKILL.md` "Test-fragility Tiger".
- **Severity:** 50 (Monitor-after-ship)
- **Urgency:** Fast-Follow
- **Trigger condition:** tests that mock `yaml`.
- **Mitigation:** tests use real PyYAML. Only the missing-dependency test blocks the import, and it does so in a subprocess. A presence-only mutation check, with bytecode cleared, must break at least one test per class.
- **Status:** Mitigated

### Paper Tigers

#### Paper Tiger 1: Consumer runtime hooks break without PyYAML
- **Scenario:** shipped hooks import the validator at runtime.
- **Why it's handled:** no hook under `hooks/` imports `skill-inventory`, `build.py`, or the new module (grep in the Fact Sheet). Validation is build- and CI-time only.

#### Paper Tiger 2: Modules that import `build.py` crash at import time
- **Scenario:** `package-generation.py` → `compose-project.py` → `build.py` → the validator at import.
- **Why it's handled:** PyYAML is imported lazily inside the validation function (Fact Sheet §9.2).

### Elephants

#### Elephant 1: The hand-written frontmatter dialects remain
- **What it is:** `skill-inventory.frontmatter`, `build._parse_yaml_frontmatter`, and `hooks/lib/split-frontmatter.py` still diverge from real YAML for metadata extraction.
- **Why it's deferred:** D3 / #1048.
- **Cost of deferral:** the two value paths (real YAML for validation, hand parse for extraction) can disagree on exotic constructs. The validator gate bounds this by rejecting non-YAML.
- **Trigger for revisiting:** #1048.

#### Elephant 2: Host-parser agreement (A2/F6) is unprovable from source
- **What it is:** the Craft host parser is not available to CI.
- **Why it's deferred:** installed proof is post-release by design §5.8.
- **Cost of deferral:** a host-only divergence would surface only after release.
- **Trigger for revisiting:** the post-release native `skill_validate` result.

#### Elephant 3: `decomposition-guard.sh` fails open on missing PyYAML
- **What it is:** a sibling fail-open import.
- **Why it's deferred:** out of scope (design §2 sibling class, #1048).
- **Cost of deferral:** that guard is silently skipped on hosts without PyYAML.
- **Trigger for revisiting:** #1048.

### Launch-Blocking Assessment
- [x] No Launch-Blocking Tigers remain unmitigated (Tigers 1 and 3 are mitigated in the implementation plan and are verified by tests before the PR)
- [x] All Tiger mitigations are grounded in investigated facts
- [x] Elephants have deferral rationale and revisit triggers
- Implementation may proceed: YES
