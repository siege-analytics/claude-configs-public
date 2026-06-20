---
name: "CI Billing-Failure Merge Override"
description: "Authorizes admin-merge of PRs when all CI checks fail solely due to GitHub Actions org-level billing failure, provided the PR meets the substitute-review criteria. Three tiers: pre-authorized for non-runtime PRs (docs, read-only tooling); per-merge operator-approved (conditional tier) for runtime-adjacent paths like recon SQL and silver_canonical; standing delegation for time-bounded blanket approval of a work-package."
alwaysAllow:
  - "Bash"
---

# CI Billing-Failure Merge Override

## Trigger condition

A PR has all required CI checks reporting `failure` AND each failing check's annotation reads:

> The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings.

Diagnostic signal: every failing job completes in 1-3 seconds (the runner refused to start, didn't run any code).

## Authorization (pre-authorized scope)

When the trigger condition holds AND all substitute-review criteria below are satisfied AND the PR scope is in the pre-authorized list, **admin-merge is pre-authorized** -- agent can use `gh pr merge --admin --merge` (or `--squash` per repo convention) without re-requesting operator approval per PR.

The pre-authorized scope covers PRs whose changes don't auto-execute on merge and have low blast radius:
- Pure docs / markdown / RST.
- SQL files that are tooling (run-on-demand), read-only (`SELECT`-only, no DDL/DML), and NOT in the runtime-adjacent paths covered by the Conditional tier below.
- Configs / YAML that aren't loaded by a running service on merge.

## Substitute-review criteria (ALL must hold for both tiers)

The PR must satisfy ALL of these -- CI's billing-induced absence is not a free pass. These apply equally to the pre-authorized tier and the conditional tier below:

1. **Non-runtime scope OR conditional-tier coverage.** Either the PR matches the pre-authorized scope above, or it matches the conditional-tier scope below with explicit operator approval. DOES NOT QUALIFY (out of scope entirely): pipeline transformation code (gold/silver MV definitions), DAG files baked into worker images, Tekton task definitions, Dockerfile changes, Helm chart changes that the running worker consumes.
2. **Self-review artifact present.** The PR (or one of its commits) references a self-review artifact, OR the PR description includes Assumptions / Peer review / Lead review sections per the `self-review` skill. The artifact-existence floor is non-negotiable.
3. **At least one runtime validation outside of CI.** For SQL PRs: a dry-run against the actual target (Spark Connect / PostGIS / OpenSearch / etc.) producing the expected output shape. For docs PRs: markdown lint clean + visible-on-GitHub-render check. For YAML rule/template PRs (silver_canonical): validate YAML syntax + dry-run of affected schedule against the target engine confirming the output schema matches expectations.
4. **No reviewer block.** If a reviewer has requested changes, the changes are addressed and the reviewer hasn't re-blocked. Auto-passes if no review was requested.
5. **The agent has read and understood every line of the diff.** Not "the model glanced at it" -- the agent narrates the change in the merge-time report.

## Conditional authorization (requires per-merge operator approval)

Some PR scopes that the pre-authorization does NOT cover CAN be merged under this skill **on a per-merge basis** when the operator gives explicit, in-band approval for the specific PR. The conditional tier exists because some runtime-adjacent code (read-only recon SQL, git-sync'd configs) has a low blast radius but the skill cannot pre-authorize blanket bypass of CI for it.

**Conditional-scope PRs** (require operator approval per merge, unless an active standing delegation covers them per the section below):
- `airflow/vendor/ee_pipelines/recon/**/*.sql` -- recon SQL files. These are read-only `SELECT`-only falsification queries run on-demand by the recon DAG. They are git-sync'd into the worker pod, not baked into the image, so a broken query breaks the recon DAG run but not the worker image build itself.
- `enterprise/rundeck/pipelines/recon/**/*.sql` -- equivalent recon SQL for the Rundeck side.
- `airflow/vendor/ee_pipelines/silver_canonical/**/*.{sql,yaml,yml,md}` -- silver canonicalization layer declarative files only: YAML rules under `rules/<schedule>/<cycle>.yaml`, SQL templates per schedule, tests, README. Per design at electinfo/enterprise#2168. Same rationale as recon SQL: read-only data normalization, git-sync'd into worker pod, NOT baked into worker image. A broken canonical query breaks the daily DAG run but not the worker image build. **Excludes** Python files (`*.py`) in this subtree -- Python changes to `rule_loader` or other runtime code are out of scope and require full CI or per-merge operator approval with explicit Python-specific runtime validation (import + dry-run of affected schedule).

**Per-merge operator approval mechanism:**

1. Agent surfaces the PR to operator with: PR number, full diff summary, self-review artifact path, and explicit reference to this conditional tier.
2. Operator gives in-band approval ("merge it" / "yes" / specific PR-number approval) referencing the conditional tier (or implicitly by acknowledging the surfaced PR scope).
3. Agent merges using `--admin --merge` (per repo convention) AND records the operator's approving message verbatim in the merge commit body for the durable record (substring quoting is acceptable; full transcript not required).
4. All five Substitute-review criteria still must hold; the conditional tier does not waive any of them.

## Standing delegation (time-bounded blanket approval)

The operator can grant a **standing delegation** for a specific work-package (a sprint, a phase, or a feature branch tree). During an active standing delegation, conditional-scope merges WITHIN the delegation's scope DO NOT require per-merge approval ceremony for the duration of the delegation. This pattern reduces per-PR friction when the operator has already approved an architectural direction and wants the implementation sequence to move without re-asking on each PR.

**Standing delegation requirements (all still apply):**

1. All five Substitute-review criteria from the section above. Standing delegation does NOT waive any of them.
2. Self-review artifact per merge per the `self-review` skill, predating the work commit.
3. Hostile review per the `hostile-review` skill with fix-in-same-PR. If hostile review surfaces a defect, fix it in the same PR before merging; do NOT file a follow-up ticket.
4. Runtime validation outside CI per substitute-review criterion 3.
5. The merge commit body must **cite the standing-delegation source** (chat timestamp + workspace memory entry path) so future readers can audit the delegation chain without consulting chat history.

**Time-bounding:** a standing delegation expires when the operator says it does, or implicitly at the work-package's acceptance gate (e.g., a Phase 1 standing delegation expires when Phase 1 acceptance criteria pass). After expiry, conditional-scope merges in that scope return to per-merge operator approval.

**Discovery and required schema:** workspace-specific active standing delegations live in workspace-local memory entries (e.g., `project_<work_package>_standing_merge_approval.md`), not in this public skill. The skill documents the mechanism; the memory documents the active instances. The memory entry MUST contain all of the following fields -- an entry missing any field is not a valid delegation:

- **Operator grant:** verbatim quote of the operator's approving message (not paraphrased)
- **Grant source:** chat session ID + timestamp where the operator gave approval
- **Scope:** exact file paths or glob patterns covered (must be a subset of the conditional-scope list above)
- **Work-package:** ticket/epic/branch tree the delegation covers
- **Expiry:** explicit condition or date when the delegation ends
- **Created by:** session ID that created the memory entry (must differ from any session that later invokes the delegation -- an agent cannot both grant and consume a delegation)

**Conditional tier does NOT cover** -- these stay out of scope regardless of delegation:
- Worker-image-baked code (Dockerfile, Helm chart values consumed by the image build, Tekton pipeline definitions, base-image pins).
- Code that modifies Steve-owned catalogs (`fec_filings.*`, `fec_bulk.*`, `quicksilver.*`, `platinum.*`, `bullion.*`) -- Steve coordination required regardless of CI state.
- BSG-scoped fixes -- those auto-merge through their own pathway; billing failure adds a manual admin-merge step but doesn't change the BSG authorization itself.
- Anything that fails CI for a non-billing reason -- billing-induced failure is the ONLY override this skill authorizes.

## Merge mechanics

1. **Verify the trigger (automated).** Run the verification script:
   ```bash
   bash scripts/ci/verify-billing-block.sh <owner> <repo> <PR#>
   ```
   The script queries `gh api repos/{owner}/{repo}/commits/{sha}/check-runs`, confirms ALL failing checks completed in 1-3 seconds, and checks each annotation for the billing failure string. It exits 0 (pass) or 1 (fail) and prints the evidence. If ANY check ran for longer or has a different failure annotation, the script rejects the override. Do NOT bypass the script with a manual check -- the script IS the trigger gate.
2. **Verify substitute-review criteria.** Walk through the 5 criteria above. Refuse the override if any fails.
3. **Determine tier.** If pre-authorized scope: proceed to step 5. If conditional scope: get operator approval per the mechanism above (OR confirm an active standing delegation covers the PR per the Standing-delegation section).
4. **Choose merge mode.** Default to repo convention (look at recent merges on the target branch -- `git log --oneline --merges origin/develop -5`). Common conventions:
   - Repos using merge-commit history: `gh pr merge {NUMBER} --admin --merge`.
   - Repos using squash workflow: `gh pr merge {NUMBER} --admin --squash` with a comprehensive squash message.
5. **Run the merge.** Record the operator's approval message (for conditional-tier merges) OR the standing-delegation source (chat timestamp + memory entry path) in the merge commit body.
6. **Post-merge:**
   - Comment on the PR: "Admin-merged under `ci-billing-failure-merge` skill -- CI was blocked by GitHub Actions org-level billing failure; substitute-review criteria verified. [Tier: pre-authorized | conditional with operator approval from <timestamp> | conditional under standing delegation <source>]"
   - Do NOT close any tracking tickets just from the merge; let normal close-on-keyword logic apply.

## Reporting back

Each time this skill is invoked, the agent reports to the operator:

- Which PR was merged + the merge-commit SHA.
- Tier used: pre-authorized OR conditional (with reference to the approval message for conditional, or the standing-delegation source if applicable).
- Trigger condition: confirmed (which checks, which annotation, duration).
- Substitute-review criteria: which were passed and what evidence supports each.
- Any deviations from defaults (squash vs merge-commit choice, etc.).

## Lifecycle

GitHub Actions org-level billing is not coming back any time soon, which is why this skill was created. This is the documented merge path for billing-blocked PRs for the foreseeable future.

If the operator ever restores billing, this skill should be retired (delete the directory or mark deprecated). Operator clears the billing issue via the organization's GitHub billing settings (e.g., `https://github.com/organizations/{org}/settings/billing`).
