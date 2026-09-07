## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: user request: "Try to rewrite the skills or policies on GitHub to allow for self-reviewed PR's in linear promotion."
Goal source verification: N/A (operator request in session, no ticket)
Plan reference: N/A (small policy-only follow-up)
Pre-author-inventory: observed branch protection cannot be changed by repo content; repo-controlled surfaces are `.github/workflows/pr-base-guard.yml`, `skills/develop-guard/SKILL.md`, and `skills/self-review/SKILL.md`.
Investigate-artifact: grep/read pass over PR/base/self-review policy surfaces in this branch
Pre-mortem-artifact: TRIVIAL (policy/docs/test change; risk is claiming branch protection bypass that repo content cannot provide)
Hostile-review-artifact: WAIVED (small policy patch)
Project-contribution: makes self-reviewed `promote/*` branches an explicit, CI-auditable linear-promotion vehicle without bypassing develop.

## Peer review

Syntax check: N/A (no Python source changes).

Policy surfaces checked:
- `.github/workflows/pr-base-guard.yml` now distinguishes canonical `develop` promotion from `promote/*` promotion branches and requires `Self-Review-Source:` in promote PR bodies.
- `skills/develop-guard/SKILL.md` now states `promote/*` is valid only for already-developed content with final-tree equivalence and self-review evidence.
- `skills/self-review/SKILL.md` now defines the self-reviewed linear promotion contract.

Validation run:
- `python3 bin/build.py --check` -> pass
- `python3 bin/sync-skill-references.py --check` -> pass
- `bash hooks/_test/pr_base_guard.test.sh` -> 35 scenarios passed
- `bash .github/workflows/_test_pr_base_guard_policy.sh` -> 6 scenarios passed

## Lead review

Approach-fit verdict: suitable. The change does not pretend repo content can disable GitHub branch protection. It instead makes the repo-owned policy layer accept `promote/*` main PRs when they carry durable self-review evidence.

Blast radius: main-targeted PR guard behavior. Feature branches to `main` remain blocked; `develop` direct promotion remains allowed; `promote/*` without self-review evidence is now blocked by CI.

Sequencing assumption: future conflict-resolved promotion branches include `Self-Review-Source:` in the PR body and are based on content already merged into `develop`.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P3 | Repository branch protection review requirements cannot be changed from this repo content. | noted |

## Quantified claims

- "35 scenarios passed" -- `bash hooks/_test/pr_base_guard.test.sh` -> `ALL PASS: 35 scenarios passed.`
- "6 scenarios passed" -- `bash .github/workflows/_test_pr_base_guard_policy.sh` -> `pr-base-guard workflow policy: 6 passed, 0 failed`

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| N/A | No rework in this patch branch | N/A | N/A | N/A |

## Evidence-predates-work

Artifact: plans/self-review-self-reviewed-linear-promotion.md
First-added commit: 12f3714442a410019dbc272bd71d8947cb518b50
Work commit: 2dd4b9797c2062ee4f4317264cbfcfe35a45fd11
Verification: git merge-base --is-ancestor 12f3714442a410019dbc272bd71d8947cb518b50 2dd4b9797c2062ee4f4317264cbfcfe35a45fd11; echo 0 -> 0
