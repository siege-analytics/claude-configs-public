---
name: "CI Billing-Failure Merge Override"
description: "Authorizes admin-merge of PRs when all CI checks fail solely due to GitHub Actions org-level billing failure, provided the PR meets the substitute-review criteria. Two tiers: pre-authorized for non-runtime PRs (docs, read-only tooling); per-merge operator-approved (conditional tier) for runtime-adjacent paths like recon SQL. Workaround until billing is restored."
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
3. **At least one runtime validation outside of CI.** For SQL PRs: a dry-run against the actual target (Spark Connect / PostGIS / OpenSearch / etc.) producing the expected output shape. For docs PRs: markdown lint clean + visible-on-GitHub-render check.
4. **No reviewer block.** If a reviewer has requested changes, the changes are addressed and the reviewer hasn't re-blocked. Auto-passes if no review was requested.
5. **The agent has read and understood every line of the diff.** Not "the model glanced at it" -- the agent narrates the change in the merge-time report.

## Conditional authorization (requires per-merge operator approval)

Some PR scopes that the pre-authorization does NOT cover CAN be merged under this skill **on a per-merge basis** when the operator gives explicit, in-band approval for the specific PR. The conditional tier exists because some runtime-adjacent code (read-only recon SQL, git-sync'd configs) has a low blast radius but the skill cannot pre-authorize blanket bypass of CI for it.

**Conditional-scope PRs** (require operator approval per merge):
- `airflow/vendor/ee_pipelines/recon/**/*.sql` -- recon SQL files. These are read-only `SELECT`-only falsification queries run on-demand by the recon DAG. They are git-sync'd into the worker pod, not baked into the image, so a broken query breaks the recon DAG run but not the worker image build itself.
- `enterprise/rundeck/pipelines/recon/**/*.sql` -- equivalent recon SQL for the Rundeck side.
- Pre-staged PRs that were operator-reviewed at the design stage but not yet at the diff stage (e.g., PR drafts in `plans/pr-draft-*.md` that the operator green-lit conceptually before billing failed).

**Per-merge operator approval mechanism:**

1. Agent surfaces the PR to operator with: PR number, full diff summary, self-review artifact path, and explicit reference to this conditional tier.
2. Operator gives in-band approval ("merge it" / "yes" / specific PR-number approval) referencing the conditional tier (or implicitly by acknowledging the surfaced PR scope).
3. Agent merges using `--admin --merge` (per repo convention) AND records the operator's approving message verbatim in the merge commit body for the durable record (substring quoting is acceptable; full transcript not required).
4. All five Substitute-review criteria still must hold; the conditional tier does not waive any of them.

**Conditional tier does NOT cover** -- these stay out of scope:
- Worker-image-baked code (Dockerfile, Helm chart values consumed by the image build, Tekton pipeline definitions, base-image pins).
- Code that modifies Steve-owned catalogs (`fec_filings.*`, `fec_bulk.*`, `quicksilver.*`, `platinum.*`, `bullion.*`) -- Steve coordination required regardless of CI state.
- BSG-scoped fixes -- those auto-merge through their own pathway; billing failure adds a manual admin-merge step but doesn't change the BSG authorization itself.
- Anything that fails CI for a non-billing reason -- billing-induced failure is the ONLY override this skill authorizes.

## Merge mechanics

1. **Verify the trigger.** Use `gh api repos/{owner}/{repo}/commits/{sha}/check-runs` to confirm all failing checks finished in 1-3 seconds and have the billing annotation. If ANY check ran for longer, the failure may be a real defect -- do NOT use this override.
2. **Verify substitute-review criteria.** Walk through the 5 criteria above. Refuse the override if any fails.
3. **Determine tier.** If pre-authorized scope: proceed to step 5. If conditional scope: get operator approval per the mechanism above before proceeding.
4. **Choose merge mode.** Default to repo convention (look at recent merges on the target branch -- `git log --oneline --merges origin/develop -5`). Common conventions:
   - Repos using merge-commit history: `gh pr merge {NUMBER} --admin --merge`.
   - Repos using squash workflow: `gh pr merge {NUMBER} --admin --squash` with a comprehensive squash message.
5. **Run the merge.** Record the operator's approval message (for conditional-tier merges) in the merge commit body.
6. **Post-merge:**
   - Comment on the PR: "Admin-merged under `ci-billing-failure-merge` skill -- CI was blocked by GitHub Actions org-level billing failure; substitute-review criteria verified. [Tier: pre-authorized | conditional with operator approval from <timestamp>]"
   - Do NOT close any tracking tickets just from the merge; let normal close-on-keyword logic apply.

## Reporting back

Each time this skill is invoked, the agent reports to the operator:

- Which PR was merged + the merge-commit SHA.
- Tier used: pre-authorized OR conditional (with reference to the approval message for conditional).
- Trigger condition: confirmed (which checks, which annotation, duration).
- Substitute-review criteria: which were passed and what evidence supports each.
- Any deviations from defaults (squash vs merge-commit choice, etc.).

## Lifecycle

This skill is a **workaround**. When the operator confirms the GitHub Actions billing is restored, this skill should be retired (delete the directory or mark deprecated). Until then, it's the documented merge path for billing-blocked PRs.

Operator clears the billing issue via the organization's GitHub billing settings (e.g., `https://github.com/organizations/{org}/settings/billing`).
