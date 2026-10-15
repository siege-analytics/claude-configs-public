# Scaffolding baseline and two-project acceptance fixtures (#1000)

Status: draft for ticket review

Pinned source: `origin/develop` at `f97d194fedf1eda053a16e938851c6151f308d72`

Captured: 2026-10-15

Scope: evidence reconciliation and fixture specification only. This document does not authorize policy changes, deployment, release, install, or promotion to `main`.

## 1. Method and evidence classes

This baseline distinguishes four states:

- **Proved** — current exact-source code plus an executable acceptance test directly covers the criterion.
- **Partial** — relevant code/tests exist, but at least one acceptance criterion is missing, skipped, indirect, or at a different enforcement boundary.
- **Unverified** — a claim exists, but this audit did not find or run direct evidence.
- **Missing** — current exact-source behavior directly contradicts the criterion, or the required source/test is absent.

Issue state is metadata, not proof. A closed issue may be incomplete; an open issue may contain work already present on `develop`.

Commands executed from a clean worktree pinned to the SHA above:

```text
python3 bin/build.py --check
python3 bin/build.py --layout both
bash hooks/_test/gate_registry.test.sh
bash hooks/_test/resolve_project.test.sh
bash hooks/_test/project_scoped_gate.test.sh
bash hooks/_test/ca_enforcement_gate.test.sh
bash hooks/_test/ca_enforcement_manifest.test.sh
bash hooks/_test/ca_enforcement_runtime.test.sh
bash hooks/_test/verify_enforcement.test.sh
python3 bin/_test/consumer_runtime_test.py
python3 bin/_test/wire_enforcement_automations_test.py
bash hooks/_test/detect_ai_fingerprints.test.sh
bash hooks/_test/self_review_hook_819_820.test.sh
bash hooks/_test/branch_state_advisory.test.sh
bash hooks/_test/kb_consultation_advisory.test.sh
bash hooks/_test/hub_concurrency_gate.test.sh
bash hooks/_test/session_signal_resolution.test.sh
```

All commands passed after building local ignored artifacts. One important caveat: before the build, `ca_enforcement_runtime.test.sh` printed `SKIP` for the missing manifest and exited 0. The post-build 9-case run is the evidence; the pre-build green exit is not.

## 2. Measured current baseline

The exact read-only measurement probe is versioned in Appendix A below. Run it only after `python3 bin/build.py --layout both` has produced ignored local `dist/` outputs. It enumerates source files from `git ls-files -z`; generated package counts include paths for which `Path.is_file()` is true (including a valid symlink to a file), do not traverse directory symlinks, and include generated package tests. Text rows distinguish UTF-8 bytes, Python characters, and the deliberately rough `ceil(characters / 4)` token estimate. The pinned result is the table below; private consumer paths/data are not inputs.

| Measure | Exact result at `f97d194` | Interpretation |
|---|---:|---|
| Tracked files | 1,339 | Repository-wide denominator |
| Source hook files excluding hook tests | 53 | Independent runtime surfaces remain broad |
| Hook test files | 37 | Test presence, not semantic completeness |
| Shared `hooks/lib` files | 11 | Current shared helper substrate |
| Obvious parser/resolver helpers | 4 | `canonical-path.py`, `extract-json.py`, `resolve-think-gate.py`, `scope-check.sh`; this is a conservative filename-based lower bound |
| Obvious policy-shaped tracked files | 14 | Conservative filename-based lower bound; excludes embedded constants such as `CA_ENFORCEMENT_GATES` in `bin/build.py` |
| Generated gate contracts | 6 | think, investigate, self-review, branch, test, skill-enforcement |
| Declared projects | 1 | `siege-utilities` |
| Declared project skills | 3 | error-path-tests, hostile-review, notebook-impact |
| Source kernel | 6,995 chars / about 1,749 tokens | Authored resident safety surface |
| Packaged kernel | 7,287 chars / about 1,822 tokens | Deployed-byte budget must use this transformed artifact |
| Compatibility rules bundle | 421,298 chars / about 105,325 tokens | Must remain on demand; never ambient context |
| Package files | 826–831 per consumer layout | Generated product surface |
| Package hook files | 89–90 per layout | Copied/generated enforcement surface |

No duplicate source core-hook basenames or byte-identical source core-hook copies were found between `.githooks/` and `hooks/git/` by the probe. Generated packages intentionally copy hook surfaces; those copies need provenance and drift checks rather than naive deletion.

## 3. Current architecture inventory and disposition

| Surface | Current owner/source | Scope | Evidence | Proposed disposition |
|---|---|---|---|---|
| Safety kernel | `skills/KERNEL.md`; build transforms it into consumer layouts | Global resident | kernel budget, generated-source authority, verifier exact-composition tests | **Split common integrity floor from configurable workflow**; retain authorization, credential, work-preservation, and evidence principles; move literal K5 topology/release-source choices into selected profiles; budget the final packaged composition |
| Compatibility bundle | generated `dist/RULES_BUNDLE.*` from rules | On demand only | verifier rejects global/nested broad-bundle injection | **Keep on demand**; never self-select |
| Progressive selection | resolver manifest, load-set resolver, consumer runtime | Task/project selected | accepted #962/F1–F4 tests and four-layout consumer test | **Keep/configure** |
| Project package identity | `projects/*/PROJECT.md` plus `bin/build.py` | Exact declared repository | build validates required fields and uniqueness | **Keep**, but share canonical identity parser with runtime |
| Runtime project gate identity | `hooks/lib/resolve-think-gate.py` | Gate lookup | 5 resolver + 3 scoped-gate tests | **Configure/replace** under #848; current tiny parser is separate from build logic and returns umbrella on missing identity |
| Gate registry | `CA_ENFORCEMENT_GATES` embedded in `bin/build.py`, emitted to package manifests | Six selected gates | 5 manifest + 17 registry + 9 runtime tests | **Migrate** to #851 authoritative contract; current generated manifest is downstream of a Python constant |
| UserPromptSubmit wrapper | `hooks/resolver/ca-enforcement-gate.sh` | Host-specific prompt boundary | 11 wrapper + 9 host-runtime tests | **Keep temporarily**; contract must identify advisory vs blocking honestly |
| Native Git enforcement | generated `.githooks/pre-push`, source `hooks/git/*` | Local Git boundary | partial self-review tests | **Repair** under #845/#1002; generated self-review path is latest-commit, not range-aware |
| Ticket requirement | native `commit-msg` plus PreToolUse parser work on separate draft #994 | Git commit boundary and early feedback | tactical draft remains independently gated | **Pilot family**; native/CI facts authoritative, command text not authorization |
| Review risk | `catalog/review-risk-policy.json` plus `bin/review-risk.py` | Changed-path evidence tier | Tier C graph and mutation tests from accepted F4 | **Keep locked**; project skill composition cannot waive it |
| Package/runtime acceptance | build outputs, verifier, consumer runtime test | Four generated layouts | 5 manifest, 34 verifier, 4-layout runtime, wiring tests | **Keep/extend** under #844/#847/#1004 |
| Release/tag production | GitHub workflows | `main` only | topology/source-policy tests exist | **Repair** under #852; fallback tag workflow reads live branch tips and changelog promotion follows package-branch build |
| Scanner truth | detect-ai-fingerprints hook/test | Commit/staged/PR claims | current test has five basic commit-message scenarios | **Repair** under #850; staged-blob and PR-head truth are not proved |
| Hub cap/board configuration | hub concurrency gate and shared doctrine | Session/project coordination | 26 cap/staleness tests | **Configure** under #909/#910; current cap resolution is env → state file → default 3; no project/manifest field found |

## 4. Historical acceptance reconciliation

| Ticket | Baseline state | Evidence-backed disposition |
|---|---|---|
| #843 CA wrapper/verifier truth | **Proved for listed criteria** | stdin replay, child diagnostics/nonzero/`continue:false`, exact registered wrapper, no-op/missing wrapper negatives, and host runtime behavior are directly tested. Do not reschedule the original slice. |
| #844 package honesty | **Partial** | Generated manifests are colocated; four isolated layouts and package paths execute. Package-specific README reference completeness and every advertised installer path still need an explicit inventory. Map remainder to #847/#1004. |
| #845 native registration/range | **Missing/partial** | Installer/verifier machinery exists, but `CA_ENFORCEMENT_GATES` still points pre-push self-review to `hooks/git/self-review.sh`; generated pre-push is not the required range-aware path. Existing #819/#820 test is not a multi-commit push-range acceptance test. |
| #846 shared classifier | **Partial** | Shared helpers exist for selected domains, but no single bounded structured classifier covers mutation/PR/push/staging/sensitive paths. #993/#994 are tactical drafts and not baseline acceptance. Coordinate only the pilot family with #1002. |
| #847 consumer acceptance CI | **Partial, substantial** | Four isolated consumer layouts, verifier, wiring, package path, prompt and push canaries pass locally. Hosted immutable release handoff, changelog consistency, and live host evidence remain separate. |
| #848 parent/project policy | **Partial substrate; target missing** | Build-time project packaging and runtime project lookup exist. There is no typed effective-policy resolver/explain/check interface for parent → org → project with locked fields and previous-policy evaluation. |
| #849 taxonomy/retirement | **Partial** | Six generated gates declare action class/runtime policy, and advisory behavior is tested for selected gates. No complete all-gate ownership/taxonomy or measured retirement against this baseline exists. |
| #850 scanner source of truth | **Missing direct evidence** | Current suite proves five commit-message cases only. No staged-vs-worktree AST or PR-head-vs-checkout fixture was found or run. Keep open. |
| #851 gate contract | **Partial substrate; target missing** | Manifest generation and drift tests exist, but the authority is still an embedded Python constant and lacks the complete typed schema/override/capability/probe contract. |
| #852 deterministic release outputs | **Missing/partial** | Main-only publishing and exact-main topology are enforced. `publish-consumption-tags.yml` resolves live `release/*` tips; changelog promotion occurs after package branches are built. Immutable producing-workflow handoff and version-consistency proof remain. |
| #873 scoped gates epic | **Partial** | Runtime detection, registry, selected advisory behavior, session isolation, and project lookup exist. Do not close the epic from these tests alone. |
| #877 project-scoped gates | **Partial** | Exact origin → project and cross-project negatives pass. Runtime parser is separate from build parser; missing identity returns umbrella, and cross-root ambiguity is not directly tested. Fold target behavior into #848/#1002. |
| #878 task relevance | **Partial** | `gate_applies` tests action-class matching, and session isolation tests avoid foreign gates. No shared structured action classifier proves the whole epic contract. |
| #879 KB advisory | **Proved for listed default/opt-in behavior** | Three direct tests prove advisory default and explicit blocking opt-in. Do not schedule the same behavior again; retain under the shared contract. |
| #909 parametric cap | **Missing project source** | 26 runtime tests prove counting/staleness and env/file/default cap. No `hub.thread_cap` or manifest/project source was found. |
| #910 board target | **Unverified/missing contract fields** | No `board_owner`/`board_number` fields were found. A narrow scan did not prove the original literal remains, so record the parameter contract as missing without claiming a surviving exact string. |

## 5. Decision mismatches and recovery baseline

### Observed decision mismatches

1. A missing built manifest made `ca_enforcement_runtime.test.sh` print `SKIP` and exit 0. A workflow that treats exit 0 as proof can silently lose runtime coverage.
2. The generated gate manifest marks selected prompt gates `blocking: true`, while `runtime_policy.craft` is advisory. The distinction is intentional, but a boolean-only consumer can misreport Craft enforcement as live blocking.
3. Build-time project identity and runtime gate identity use separate parsers. Build uniqueness does not by itself prove runtime identity resolution across installed/workspace roots.
4. Generated native pre-push calls a latest-commit self-review hook despite an open range-semantics contract.
5. Green scanner tests cover a much narrower truth surface than #850 claims.
6. Release fallback tags use mutable branch tips rather than an immutable producing-run handoff.

### Recovery steps observed or directly supported

| Failure | Current recoverable action | Evidence status |
|---|---|---|
| Missing/stale task signal | Read-only diagnosis remains allowed; update the current session’s signal/evidence and retry | Proved by 18 session-resolution cases and mutation/non-mutation split |
| Missing enforcement manifest | Restore/build the package-local manifest; runtime wrapper fails closed rather than claiming advisory success | Proved by runtime F2 |
| Wrong/no-op registered wrapper | Correct the exact `.claude/settings.json` command path and rerun verifier | Proved by verifier negatives |
| Unsupported/mismatched host | Stop claiming blocking live; report unsupported/unverified and use a disposable canary | Contract for #1003; live proof remains unverified |
| Project identity mismatch | Refuse project-specific authority; inspect canonical host/owner/repo mapping | Target contract for #848; current fallback-to-umbrella behavior needs redesign |
| Repeated review rejection | Freeze exact SHA, preserve reproductions, redesign or escalate after bounded failed heads | Operational contract in #1005; not yet machine enforced |

No performance target or recovery-step count is invented here. #1002/#1003 should measure steps and false blocks against these named scenarios.

## 6. Two synthetic project fixtures

These are public synthetic consumers. They contain no private repository path, credentials, or operational data. Exact canonical identity includes host, owner, and repository; same-name repositories under another owner or host never match.

### Fixture A — `strict-release`

```yaml
identity:
  host: github.com
  owner: example-org
  repository: strict-release
branch_policy:
  integration: develop
  release: main
  feature_targets: [develop]
  only_release_promotion: develop -> main
  direct_protected_push: deny
ticket_policy:
  required: true
  accepted_ids: ['#[0-9]+']
review_binding:
  default: hostile-review
  enforcement_changes: tier-c-exact-sha
locked:
  - protected_branch_topology
  - review_evidence_floor
  - credentials_and_destructive_actions
```

Expected decisions:

- feature → `develop` PR: allow after required evidence.
- feature → `main` PR: deny; explain canonical promotion rule.
- `develop` → `main` PR from the exact same repository: allow after required evidence.
- commit without `#<number>`: deny at the native message/range boundary.
- enforcement change declared Tier B: deny; computed Tier C cannot be downgraded.
- resident instructions and guard decisions both state this profile’s authorized `develop` → `main` topology; extracting literal K5 workflow choices from the common integrity floor is a prerequisite for #848/#1002, not a weakening of this repository’s selected profile.

### Fixture B — `synthetic-trunk`

```yaml
identity:
  host: github.com
  owner: example-labs
  repository: synthetic-trunk
branch_policy:
  integration: main
  release: main
  feature_targets: [main]
  direct_protected_push: deny
ticket_policy:
  required: true
  accepted_ids: ['LAB-[0-9]+']
review_binding:
  default: synthetic-project-review
  extends: [general-code-review]
  enforcement_changes: tier-c-exact-sha
locked:
  - review_evidence_floor
  - credentials_and_destructive_actions
```

Expected decisions:

- feature → `main` PR: allow after required evidence.
- feature → nonexistent `develop`: deny as outside the effective branch policy.
- commit with `LAB-42`: allow at the ticket boundary; `#42` alone does not satisfy this project.
- project review procedure loads once, in declared order, without importing fixture A.
- resident instructions and guard decisions both state the authorized trunk topology and do not retain fixture A’s literal `develop` → `main` text.
- project review binding cannot waive Tier C or manufacture approval.

### Required negative corpus

| Case | Expected result |
|---|---|
| Fixture A policy evaluated in fixture B | deny/unknown; never inherit A |
| `foreign.example/example-org/strict-release` | no match despite same owner/repo text |
| `github.com/foreign-owner/strict-release` | no match despite same repository basename |
| stale task evidence from a prior SHA/session | deny; explain stale provenance |
| working-tree edit that loosens policy | evaluate under previously approved policy; edit cannot authorize itself |
| same resolved replacement reached by explicit route and prerequisite | load once in declared order; identical repeated references are idempotent |
| conflicting replacement declarations for one capability | reject with both sources identified; never choose silently |
| missing required host capability | unsupported/blocked, not “enforcement live” |
| ambiguous identity or unknown policy field | reject with actionable diagnostic |

## 7. Proposed first migrated gate family

**Family:** ticket binding for Git commits.

**Actual authority boundary:**

1. Native `commit-msg` validates the effective message for one commit using project-declared matching and cleanup semantics. Fixtures inherit no implicit `[no-ticket]` escape; any permitted exception must be typed, explicit, provenance-bearing, and visible in explain output.
2. A required protected CI/server-side acceptance check validates every relevant exact commit range/head for the selected merge strategy. Merely running CI is not enforcement; the check must actually prevent acceptance when it fails.
3. PreToolUse command classification may provide early feedback or a scoped fail-closed refusal for known protected forms, but arbitrary command text is not authorization and is not represented as server-side protection.
4. Both instructions and executable checks consume the same effective policy/provenance from #848/#851.

Why first: the boundary is objective, has two deliberately different fixture policies, and directly incorporates #994 counterexamples without requiring a general shell/Python interpreter. It also exposes where native hooks are bypassable and where CI must carry authority.

## 8. Host/backend discovery boundary

Observed local session metadata for designing later canaries:

- Craft Agent application environment: `0.14.0`, Darwin arm64.
- Current agent is powered by Craft Agents Backend.
- Exact deployed backend build, provider/model adapter build, registered live hook paths, and recovery semantics are **unverified** for public acceptance.

Private host names, workspace paths, credentials, and real consumer operations must stay in authorized private evidence. #1003 must report fixture proof and authorized disposable live proof separately; missing live access is a blocker, never a pass.

## 9. Remaining-work map

- #851: extract the minimal typed gate/capability contract from the embedded/generated substrate.
- #848: implement deterministic effective-policy resolution and explain/check for these two profiles.
- #1001: bind replacement/extension skills and resident blocks without weakening locked rules.
- #1002: execute the ticket/branch/review pilot through real disposable Git and CI facts.
- #1003: verify exact Craft/backend capability and recovery behavior in an authorized disposable live session.
- #1004: prove upgrade/rollback preservation and coherent manifests.
- #845: repair native range semantics used by the pilot.
- #847/#844/#852: complete package and immutable release acceptance.
- #849: retire the migrated duplicate only after parity, runtime, and rollback proof.
- #850: separately repair scanner truth-source behavior.
- #909/#910: express coordination parameters through the same project policy model.
- #1005: make long-running work bounded, visible, interruptible, and escalation-limited.

## 10. Review questions before behavior changes

1. Approve ticket binding as the first migrated gate family, or choose branch topology instead?
2. Is fixture B’s `LAB-<n>` ticket syntax sufficiently different while retaining the same safety intent?
3. Should missing project identity be explicit `unknown` rather than current `umbrella` fallback? This baseline recommends **yes**.
4. Should CI range validation be a required capability for any profile that claims ticket enforcement is live? This baseline recommends **yes**.
5. What exact backend/provider combinations are authorized for #1003 disposable live canaries?

## Appendix A — exact read-only measurement probe

Prerequisite: from the pinned checkout, run `python3 bin/build.py --layout both` without `--deploy`. Then save the following as a temporary file and invoke it with the repository root as its sole argument. It writes JSON to stdout and does not modify the repository.

```python
#!/usr/bin/env python3
import hashlib
import json
import pathlib
import re
import subprocess
import sys

repo = pathlib.Path(sys.argv[1]).resolve()


def tracked():
    output = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"])
    return [
        repo / raw.decode("utf-8", "surrogateescape")
        for raw in output.split(b"\0")
        if raw
    ]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


files = tracked()
relative = lambda path: str(path.relative_to(repo))
source_hooks = [
    path for path in files
    if relative(path).startswith("hooks/")
    and "/_test/" not in relative(path)
    and path.is_file()
]
hook_tests = [
    path for path in files
    if relative(path).startswith("hooks/_test/") and path.is_file()
]
lib_files = [
    path for path in files
    if relative(path).startswith("hooks/lib/") and path.is_file()
]
parser_terms = re.compile(r"(classif|parse|token|resolve|command|extract|scope|path)", re.I)
parser_candidates = [path for path in lib_files if parser_terms.search(path.name)]
policy_terms = re.compile(
    r"(policy|manifest|settings|_rules\.md$|PROJECT\.md$|deploy-model)", re.I
)
policy_candidates = [
    path for path in files
    if policy_terms.search(relative(path)) and not relative(path).startswith("plans/")
]

core = []
for root in (repo / ".githooks", repo / "hooks" / "git"):
    if root.exists():
        core.extend(path for path in root.rglob("*") if path.is_file())
by_name = {}
by_hash = {}
for path in core:
    by_name.setdefault(path.name, []).append(relative(path))
    by_hash.setdefault(digest(path), []).append(relative(path))

resident = {}
for path in (
    repo / "skills/KERNEL.md",
    repo / "dist/flat/skills/KERNEL.md",
    repo / "dist/craft-agent/skills/KERNEL.md",
    repo / "dist/craft-agent/KERNEL.md",
    repo / "dist/RULES_BUNDLE.md",
):
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
        resident[relative(path)] = {
            "bytes": len(text.encode("utf-8")),
            "chars": len(text),
            "estimated_tokens": (len(text) + 3) // 4,
        }

packages = {}
for name in ("flat", "nested", "craft-agent", "claude-code"):
    root = repo / "dist" / name
    if root.exists():
        packages[name] = {
            "files": sum(1 for path in root.rglob("*") if path.is_file()),
            "hook_files": sum(
                1 for path in (root / "hooks").rglob("*") if path.is_file()
            ) if (root / "hooks").exists() else 0,
        }

manifest = repo / "dist/craft-agent/enforcement-manifest.json"
manifest_summary = None
if manifest.exists():
    data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_summary = {
        "gate_count": len(data.get("gates", [])),
        "gate_ids": [gate.get("id") for gate in data.get("gates", [])],
        "source_commit": data.get("source_commit"),
    }

print(json.dumps({
    "head": subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip(),
    "tracked_files": len(files),
    "source_hook_files": len(source_hooks),
    "hook_test_files": len(hook_tests),
    "hook_lib_files": len(lib_files),
    "parser_candidates": [relative(path) for path in parser_candidates],
    "policy_candidates": [relative(path) for path in policy_candidates],
    "core_hook_name_copies": {
        name: paths for name, paths in by_name.items() if len(paths) > 1
    },
    "core_hook_identical_copies": [
        paths for paths in by_hash.values() if len(paths) > 1
    ],
    "resident": resident,
    "projects": [
        relative(path) for path in sorted((repo / "projects").glob("*/PROJECT.md"))
    ],
    "project_skills": [
        relative(path)
        for path in sorted((repo / "projects").glob("*/skills/*/SKILL.md"))
    ],
    "dist_packages": packages,
    "enforcement_manifest": manifest_summary,
}, indent=2, sort_keys=True))
```
