# Self-review: task-scoped Git bootstrap (#1240)

## Problem and source

The Git mutation target model unconditionally resolved an existing repository toplevel. `git init` and explicit-destination `git clone` are how a scratch target becomes a repository. No live hook, task or business session is changed by this feature.

## Boundaries

Builtin init/clone now model their destination before the existing toplevel route. Init preserves ordinary project files when target metadata is absent; bare init and clone require empty destinations. Existing repository metadata (normal, bare or linked), symlink aliases, missing destination parents, implicit clone destinations, unknown flags, config/template/separate-metadata/helper overrides and unsafe transports stay unmodeled/denied. Local clone sources are read inputs, not destination writes. Directory sources require unambiguous `--no-local`: default local clones can hardlink objects and `--no-hardlinks` alone can retain borrowed alternates. A real borrowing-source fixture verifies independent target object inodes, no alternates and successful fsck/content reads after the original object source is moved away. Configured URL rewrites are resolved once with the fixed local-only `git ls-remote --get-url` query, then the effective source is validated. The candidate command stays unchanged so the URL is not rewritten a second time. Tests include safe HTTPS/SSH rewrites, helper rewrites denied without execution, and an actual rewritten local-source clone. Configured custom init templates are also rejected after a fixed local config query: a demonstrated objects-directory symlink caused real init to write outside its destination. The guard does not disable or modify that configuration; it reports the unmodeled alias predicate and the supported per-command empty `--template=` route. Only that exact empty template override is supported; actual init and clone positives prove it creates only their own destination, without outside alias writes. Existing Git operations keep their old ownership route.

Normal own-task selection and effective risk still run. A new repository without a listable tree retains conservative Tier C, even if the gate declares A. Required artifacts are prepared under the existing grant, not a new owner permission. A nested workspace gate can initially own its explicitly scoped fresh scratch; after repository creation, its actual repository identity changes. A stale enclosing-workspace repo_root cannot authorize a new index mutation; the same own task and companions must reflect the real new repository. Foreign sessions/tasks and wrong scopes remain denied.

## Meaningful verification

The focused suite uses actual temporary repositories, commits and bundles, native-shaped Craft session identity and real hook processes. Allowed commands actually run only after hook acceptance. It verifies regular init, `git -C` init, bare init, nonempty ordinary file preservation, saved-bundle/local-repository mirror clones, unchanged input content, wrong lifecycle/session/scope, effective risk, symlink/reinit/unknown-option/transport controls, and before/after nested task binding. The two native-shaped init/clone cases pass every configured Bash PreToolUse hook from settings-snippet before actual Git creation. No remote transport is executed.

Existing task-keyed, Git index risk, read-classification and Git operation-policy tests remain relevant regression checks. Normal generated refresh/check and protected exact-head CI remain separate. These tests do not prove live app delivery or deployment; installed hooks are untouched.

## Delivery and rollback

Own develop-based feature, normal review/commit/push/draft PR. Coordinate the disjoint copy/read-only-bundle source fix through normal reviewed integration; do not copy a moving candidate. Revert this feature commit to remove its bootstrap support; no live state migration or global configuration change is involved.

## Assumptions

Domain(s): software engineering. Geospatial cross-cut: no.
Goal source: issue #1240, existing owner repair task.
Goal source verification: PASS: ticket siege-analytics/claude-configs-public#1240 is fit for execution.
Plan reference: plans/think-git-bootstrap-1240.md.
Pre-author-inventory: existing `_git_toplevel`/Git action route, task selector and effective-risk logic inspected; concurrent cp/bundle owner confirmed disjoint source regions before edits.
Investigate-artifact: plans/think-git-bootstrap-1240.md and #1240 native failure evidence.
Pre-mortem-artifact: plans/pre-mortem-git-bootstrap-1240.md.
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1240#issuecomment-6756979232 — Root independent exact-source review at frozen runtime SHA256 3115e87373baaec628f0f7eaa9ba8365f5190b3087c928e3073d13fc0d68b1b7; source acceptance conditional on normal CI.
Project-contribution: makes assigned fresh repository work executable without requiring the repository to exist first, while preserving task and real risk constraints.

## Test plan and peer mechanics

Run `hooks/_test/git_bootstrap_targets.py`, existing task-keyed gates, Git-add risk and reader Git safety modules, then normal generated refresh/check. Both native-shaped bootstrap positives inspect semantic allow/block JSON across every configured Bash guard before actual Git creation. No remote network/helper is exercised. Protected exact-head hosted full CI is required and is not implied by focused tests.
Notebook API check: N/A (no notebook changes). Review-gate: N/A (no task review signal in this source worktree). Syntax and diff checks cover changed Python/shell source; schema/build/source-authority checks cover generated inputs.

## Lead review and findings

Root's initial P1: local-directory clones could hardlink or borrow object aliases. Fixed by requiring unambiguous --no-local, proven with actual inodes/alternates and loss-of-source fsck/content checks.
Root's second P1: configured URL rewrites could turn a nominal HTTPS input into an unsafe helper. Fixed with local-only one-expansion resolution followed by effective-source validation; no second expansion or candidate execution by the classifier.
Additional author boundary probe: an actual private custom template objects symlink caused init to create info/pack outside target. Fixed by rejecting configured nonempty init.templateDir unless the invocation uses an exact empty template override; actual config/guard fixtures verify default denial and successful empty-template creation without outside writes.
Final independent disposition and exact commit/CI results remain separate receipts. No blocker is marked resolved merely because a patch exists.

## Adversarial shape audit

External shape: literal Git prefix/global options and builtin init/clone options/source/destination. Raw command is parsed without executing it; unknown flags/config/templates/helpers fail closed. Effective-source schema comes from Git's own local get-url operation; actual repository metadata and filesystem identities are checked with fixed read-only queries. Negative controls cover malformed/foreign/ambiguous/redirected inputs, existing metadata, symlinks and aliasing. The decisive positive checks execute real Git after actual guard acceptance, not a mirror of implementation strings.

## Quantified claims

Counts in final delivery are taken from the named test summaries and the configured guard enumeration; protected CI remains pending until observed. No claim of installed-runtime acceptance or no regressions outside the exercised suites.

## Final focused receipts

- `python3 hooks/_test/git_bootstrap_targets.py -v`: final exact-runtime amendment, eighteen tests pass; native-shaped init and clone each pass the actual sixteen configured Bash PreToolUse guards, then Git creates the repository. Global-template and env-template-only fixtures prove default denial and explicit empty-template repair without outside writes.
- Existing `task_keyed_gates.py`: eighty-eight pass; `git_add_risk.py`: ten pass; `reader_git_safety.py`: eighteen pass. These broader regressions preceded the final template-only amendment; affected bootstrap tests were rerun after that amendment rather than claiming the old runs used the final bytes.
- Root independently accepted frozen binary-query runtime SHA256 3115e87373baaec628f0f7eaa9ba8365f5190b3087c928e3073d13fc0d68b1b7 in issue comment 6756979232. The immutable-snapshot Claude peer review is still active; no verdict from it is claimed. Final-head PR review and hosted CI remain separate receipts.
- Normal canonical refresh/check passed, followed by a current final build/build-check/source-authority check after test-only additions. Protected exact-head full CI remains separate and is pending until the draft head is published. No full hosted-suite or installed canary success is claimed early.

Counts above come from the named unittest summaries and direct enumeration of settings-snippet Bash hooks, not prose-string tests. Local temporary Git creation and independence checks are the bounded canary; rollback is a normal feature revert. No live installation or state migration occurs.

## Template value amendment

A post-review actual private probe found that `templateDir=" "` is a real relative directory, not an empty template value. Git resolves it inside a nonempty init target and followed its objects symlink. A second actual probe showed text-mode CRLF normalization could erase a literal CR path as well. The config reader now reads binary output and removes only Git's one output newline, preserving whitespace path bytes; default use is denied and the exact empty per-command override remains the supported repair. The new real-config/guard/Git regression proves no outside writes and successful empty-template creation. This source amendment requires its own exact-source review and CI; the earlier runtime's CI cannot attest it.

The same text-mode CRLF normalization could misclassify an effective clone URL ending in CR: an actual rewritten local directory was mistaken for the regular bundle file whose name lacked CR, allowing default hardlinks. Both Git configuration-derived queries now read binary stdout, remove exactly one output LF and retain path bytes; URL validation then strictly decodes UTF-8 and rejects control line endings. Actual config fixtures cover raw space/tab/CR/LF templates and the directory-versus-file clone rewrite. All prior alias, transport and empty-template boundaries remain unchanged.

Frozen binary amendment validation: `/tmp/git1240-tests-final18-binary.log` records eighteen passes in 21.443 seconds; `bin/validate-local.py --mode refresh` completed successfully for the frozen source. The previous 4d9d199 hosted CI passed only the earlier runtime and does not attest this amendment.
