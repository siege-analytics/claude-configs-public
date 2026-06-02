---
name: post-error-revision
description: "MANDATORY when a failure contradicts a documented Assumption. Walk failure -> commit -> PR -> ticket; append a five-field Post-error revision block (Triggered by / Observed / Falsified assumption / Revised model / Implication) to the originating ticket; preserve-and-annotate the original Assumption; THEN draft the fix or revert PR with a Refs: + Post-error-revision: trailer pair. Implements writing-rules:6. Canonical implementations: scripts/discipline/check-post-error-revision.sh (block-structure validator), hooks/git/post-error-revision-required.sh (trailer requirement on revert / regression-fix)."
disable-model-invocation: true
user-invocable: true
---

# Post-error revision

writing-rules:5 ships the substrate (Trivial-change declarations with Cannot-produce-error claims and Falsification observables). writing-rules:6 ships the back-edge: when one of those observables surfaces -- or any other documented Assumption is contradicted by empirical evidence -- the originating ticket gets a structured revision so engineering knowledge compounds instead of being re-discovered.

This skill is the prose layer. `scripts/discipline/check-post-error-revision.sh` is the enforcement layer. `hooks/git/post-error-revision-required.sh` wires the script to the commit / PR-open path. They stay in sync.

## When to invoke

The trigger fires when **a durably-documented Assumption is contradicted by empirical evidence**. Six concrete trigger shapes:

| Trigger | What it looks like | Where the revision goes |
|---|---|---|
| Runtime failure (any deployed env) | Page, customer report, bad data, exception in dev/staging/prod logs, failed smoke test on a preview deploy, repro on a developer's local end-to-end stack | Originating ticket of the failed-Assumption work |
| CI regression | Test that wasn't catching the regression now catches it; OR new test fails against pre-fix code | Originating ticket of the introducing work |
| Post-merge code-review finding | Reviewer of a later PR identifies a contradiction with an earlier PR's stated invariants | The earlier PR's originating ticket |
| Revert PR | Any revert is itself evidence the original change was wrong | The originating ticket of the reverted change |
| Trivial-change Falsification surface | The observable named in a Trivial-change block's Falsification field surfaces | A new ticket filed retroactively, citing the failed block as Goal source |
| Cross-ticket contradiction | A new ticket's investigation falsifies an Assumption documented on a closed ticket | The closed ticket gets the revision; the new ticket cross-links it |

**Not a trigger -- but only when BOTH conditions hold:** (a) the failure is in the agent's own iteration cycle (write -> test -> fail -> fix, pre-commit), AND (b) no durably-documented contract is being contradicted anywhere. "Durably documented" includes hook contracts in `hooks/**`, SKILL.md prose, rule files (`_*-rules.md`), ticket Assumptions blocks, self-review artifacts, Trivial-change blocks, and source-code docstrings on the function being touched.

A push hook blocking the commit IS a trigger -- the hook's SKILL.md contract is the documented belief being contradicted, even though the agent is in their own loop. Same for: CI lint blocking on a violated rule, type checker rejecting against a docstring, downstream consumer flagging an undocumented schema change.

The first version of this rule (claude-configs-public#168) had a more generous carve-out. Three real-time triggers were missed during its own dogfood (#169, #178, #181) because "I'm in my own fix loop" was treated as sufficient. Tightened in #184.

## Procedure

### Step 0 -- Pre-fix pause (the gate)

The first action when ANY failure fires is **not the fix**. It is one sentence:

> "What did I believe that this evidence contradicts?"

If the answer names a durable artifact (skill / rule / ticket / hook / docstring / Trivial-change block), proceed to Step 1 -- the Post-error revision block comes before the fix.

If the answer is "nothing durable -- I formed this belief minutes ago," the carve-out applies. Note that out loud or in chat as an explicit no-op ("in-loop, no documented contract; continuing fix"), and proceed to fix.

The pause itself is the discipline; the documentation steps (1-5 below) only kick in when the pause finds a durable contract. Skipping the pause is the writing-rules:6 failure mode that #184 was filed to correct.

### 1. Identify the originating ticket

Walk the chain: failure -> commit -> PR -> ticket. The commit message's `Refs:` / `Fixes:` / `Part-of:` trailer names the originating ticket (or one of them).

If the chain breaks -- no commit, no PR, no ticket (the failed work used a Trivial-change escape) -- **file the missing ticket FIRST**. Goal source: quote-and-link the failed Trivial-change block. The new ticket's first content is the Post-error revision documenting why the Trivial-change was wrong.

If multiple tickets contributed (the failed belief was documented across two related tickets), each gets a Post-error revision block, and the blocks cross-link.

### 2. Re-read the originating ticket's Assumptions block

Find the specific belief the failure contradicts. Quote it verbatim -- the Falsified-assumption field cites the source, not a paraphrase.

If the originating ticket has no Assumptions block at all, the *absence* is itself the falsified belief: the implicit Assumption that no Assumptions were needed.

### 3. Append the Post-error revision block

Append (do NOT replace existing content) a `## Post-error revision` section to the ticket body. Five required fields:

```
## Post-error revision

Triggered by: <PR # / commit SHA / incident link / failed Trivial-change block path>
Observed: <empirical evidence -- log line, test output, user report,
          production incident link, surfaced Falsification observable.
          Must include a writing-rules:4 evidence-token: fenced code,
          file path, git command output, stat/count, or URL.>
Falsified assumption: <quote the specific Assumption from the original
                      ticket / self-review artifact this evidence
                      contradicts. If no Assumption was documented,
                      state the implicit one being falsified.>
Revised model: <what the system actually does, in falsifiable terms --
               the corrected version of the Assumption>
Implication: <what changes -- file paths edited, docs updated,
             Assumptions on future tickets, Trivial-change category
             to remove>
```

The `Observed:` field carries the same writing-rules:4 evidence-token requirement as the Trivial-change block's `Evidence:` field. Free-text assertions ("it broke") do not satisfy this -- paste a log line, a test output, a stat, a URL.

### 4. Update the Assumptions block

The original wrong Assumption is **NOT deleted**. Preserve it with a `(superseded by Post-error revision YYYY-MM-DD)` annotation, and add the revised Assumption alongside. The original-wrong + revised-correct pair documents the learning explicitly. Deleting the original loses the audit trail and lets the same Assumption silently re-form.

Example:

```
## Assumptions
- ~~No dynamic-dispatch patterns in the codebase~~ (superseded by
  Post-error revision 2026-05-22)
- services/dispatcher.py:142 dispatches via getattr from a config key;
  renaming any config-referenced method requires updating both the
  config and the method. (revised 2026-05-22)
```

### 4.5. Update the designated knowledge locus

The ticket's Assumptions block (Step 4) is one place the correction lives. But knowledge about this entity may also live in other locations -- a module docstring, a CLAUDE.md section, a doc page, a wiki article, a notebook. These are the **designated knowledge loci** for the entity.

If an Investigation Fact Sheet exists for the code area this error touches, its "Knowledge Loci" section identifies where canonical knowledge lives. Route the correction to each locus that described the falsified behavior:

- **Module docstring** describes the old behavior → update the docstring with the revised model.
- **CLAUDE.md / README** describes the old convention → update the section.
- **Notebook** demonstrates the old behavior → update or file a ticket for the notebook.
- **Doc page / wiki** describes the old interface → update the page.
- **Prior Fact Sheet** records the falsified assumption → add a pointer to this post-error revision in the Fact Sheet's Prior Knowledge section.

If no Fact Sheet exists (the original work skipped investigation), note which loci you identified and updated in the `Implication:` field of the Post-error revision block. The next investigation for this code area will pick these up via Phase 0's post-error-revision and knowledge-locus reads.

### 5. Draft the fix or revert PR

Reference the Post-error revision in the commit body:

```
fix(<scope>): <terse description of corrected behavior>

<body explaining the fix>

Refs: <repo>#<originating-ticket> Post-error revision dated YYYY-MM-DD
Post-error-revision: <link to the ticket's Post-error revision block>
```

The `Refs:` + `Post-error-revision:` pair is what the hook `post-error-revision-required.sh` enforces. Without both trailers, the push is blocked on any commit whose message contains `revert` or `fix(...): regression`.

## Worked example: a `private-rename` Trivial-change Falsification

**Setup.** An agent ships a `private-rename` Trivial-change for `_fetch_inner -> _fetch_pages` in `services/api.py`. The Trivial-change block (per writing-rules:5) names:

```
## Trivial-change declaration
Category: private-rename
Cannot produce error: Renaming `_fetch_inner` to `_fetch_pages`; private
                      symbol with no external callers.
Evidence: grep -rn '_fetch_inner' . --exclude-dir=.git returns 1 hit,
          the function definition itself. No dynamic-dispatch patterns
          (getattr / __getattr__ / import_string) found in the codebase.
Falsification: A getattr-based callsite or test discovers the old name
                via runtime introspection -- surfaces as AttributeError
                in production or a test failure pointing at the renamed
                symbol.
```

The PR merges. Two days later, the Falsification observable surfaces: `AttributeError: 'X' object has no attribute '_fetch_inner'` at `services/dispatcher.py:142`, which dispatches via `getattr(obj, name)` with `name` resolved from a config-string key.

**Step 1.** Chain check: the failure points at `services/dispatcher.py:142`. `git blame` -> PR 321. PR 321's commit `Refs:` line is empty (Trivial-change escape). **File the missing ticket FIRST** as SW#NNN. Goal source: quote-and-link the failed Trivial-change block.

**Step 2.** No prior Assumptions block on the (just-filed) ticket. The implicit Assumption falsified: the Trivial-change Evidence claim "No dynamic-dispatch patterns in the codebase" -- which the grep missed because `_fetch_inner` was constructed at runtime from a config key, not a literal in the source.

**Step 3.** Append the block to SW#NNN:

```
## Post-error revision

Triggered by: PR 321 (the original Trivial-change); incident
              https://sentry.example.com/inc/4567
Observed: AttributeError: 'X' object has no attribute '_fetch_inner'
          at services/dispatcher.py:142 -- the call uses
          getattr(obj, name) with `name` resolved from a
          config-string key in config/dispatch.yml:14.
Falsified assumption: PR 321 Trivial-change Evidence claim "No
                      dynamic-dispatch patterns in the codebase" --
                      original grep missed the getattr-based callsite
                      in services/dispatcher.py:142 because the symbol
                      name was constructed at runtime from a config-string.
Revised model: services/dispatcher.py:142 dispatches via getattr from a
               config-string key; renaming any method referenced from
               config/dispatch.yml requires updating both the
               configuration value and the method symbol.
Implication:
  - Fix PR: rename callsite at services/dispatcher.py:142, update
    config/dispatch.yml:14.
  - File writing-rules:5 meta-ticket: `private-rename` Category should
    require a config-key grep as additional Evidence, not just a
    symbol-name grep.
  - If this is the 3rd Falsification of `private-rename`, the
    Category comes off the trivial-safe list entirely.
```

**Step 4.** SW#NNN gets an Assumptions block with the revised Assumption (originating-wrong + revised-correct pair).

**Step 5.** The fix PR commit body:

```
fix(api): correct getattr dispatch after _fetch_inner rename

The rename in PR 321 missed the config-driven dispatch at
services/dispatcher.py:142. Updating both the callsite and the
config-string key.

Refs: socialwarehouse#NNN Post-error revision dated 2026-05-22
Post-error-revision: https://github.com/.../issues/NNN#post-error-revision
```

## The Trivial-change Category meta-loop

When **≥3** Post-error revisions blame the same Trivial-change Category, the controlled vocabulary in writing-rules:5 is itself revised -- that Category comes off the trivial-safe list (or moves to "borderline" with a stricter Evidence requirement).

v1: the agent encountering the third Falsification files a writing-rules:5 meta-ticket against `_writing-rules-rules.md` and `check-trivial-claim.sh` simultaneously. Both ship in one PR (script constant + rule prose).

v2 (deferred): CI scanner walks the `## Post-error revision` blocks across the repo, counts Falsifications per Category, and auto-files the meta-ticket when a count crosses the threshold.

## Anti-patterns

- **Fixing without revising.** Pushing the fix PR and closing the ticket without writing the Post-error revision block. The next agent reads the original Assumption and rebuilds on a falsified model. (This is the case writing-rules:6 exists to prevent.)
- **Deleting the original Assumption.** Audit trail loss; the wrong-then-corrected pair documents the learning, deleting the wrong-version loses it.
- **Free-text `Observed:` field.** "It broke" / "there was an error" -- same failure mode as free-text Trivial-change Evidence. The `Observed:` field carries the writing-rules:4 evidence-token requirement: paste a log line, a test output, a stat, a URL.
- **Treating in-loop test failures as triggers.** The agent's own write -> fail -> fix iteration cycle is not the trigger. Triggers fire only when the falsified belief was durably written down.
- **Skipping the ticket-creation step when the chain breaks.** If the failed work used a Trivial-change escape (no originating ticket), the response is to file the ticket retroactively, not to skip the revision because there's "nowhere to put it."

## Artifact destination

**If the work has a ticket, the Post-error revision block goes on the ticket. This is not optional.** The block is appended to the originating ticket (Step 3) -- this is inherent to the procedure, not a separate step. But if investigation also produced a Fact Sheet with a Knowledge Loci section, the corrections from Step 4.5 go to each designated knowledge locus as well. A Post-error revision that only updates the ticket's Assumptions block while leaving a docstring or CLAUDE.md section describing the falsified behavior is an incomplete revision.

## Cross-references

- writing-rules:4 -- every "this doesn't apply" claim requires the same evidence chain as a "this happened" claim. The `Observed:` field inherits this requirement.
- writing-rules:5 -- Trivial-change declarations with Cannot-produce-error claims; Falsification field is the writing-rules:6 trigger.
- writing-rules:6 -- the rule this skill implements.
- [skill:evaluate-ticket] -- used to confirm the originating ticket's Assumptions block exists and is well-formed before quoting from it.
- [skill:self-review] -- when the Trivial-change Falsification observable surfaces during self-review of a later PR, that self-review must cross-reference this skill before drafting any fix.
- `scripts/discipline/check-post-error-revision.sh` -- block-structure validator (canonical).
- `hooks/git/post-error-revision-required.sh` -- trailer requirement on revert / regression-fix commits.

## Attribution

Defers to `_writing-rules-rules.md`. No AI / agent attribution in commits, PRs, ticket comments, or Post-error revision blocks.
