---
description: Always-on. Discipline for how rules themselves are written and deployed — when a "always-do-X" rule needs an automated enforcement layer, and when it can live as prose alone. Read whenever you're about to add a memory entry, a skill, or a project convention that asks an actor to always (or never) do something.
---

# Writing Rules

Rules are interventions against failure modes. They only work when the actor about to fail can be reached by the rule at the moment the failure is about to happen. Prose-only rules reach only the actor who reads them; automated enforcement reaches every actor using the system, including the ones who never read your prose.

This file's rules are about **how to write rules** — so that the rules we write actually fire.

## The rules

**writing-rules:1. Any rule that depends on vigilance against a tool default needs paired automated enforcement.**

The failure mode is well-known: a convenience default in some tool (a CLI flag, an IDE setting, a GitHub UI default) silently does the thing the rule forbids. The actor isn't being careless — they're using the obvious path the tool offers. A prose rule that asks them to always override the default is one bad day away from breaking.

When the rule has this shape — "always do X; never do Y" — pair it at write-time with one of:

- A CI workflow that fails the offending action (target-branch guard, lint check, ratchet job)
- A repository branch-protection / required-status rule
- A pre-commit hook the user installs
- An interactive prompt or refusal in the tool itself
- A lint rule with autofix where applicable

If none of these can plausibly enforce the rule, treat that as a load-bearing finding: the rule may not be enforceable as written, and the right intervention may be a different design entirely.

**Why this rule is here at all:** SW#234 traced a recurring `develop` vs `main` workflow drift to `gh pr create`'s default base = the repo's default branch (`main`). The drift was supposedly governed by a memory entry, but `gh` defaults reached the actor at the moment of the action; the memory did not. The fix was a CI guard (`pr-base-guard.yml`). The lesson generalizes: every memory-only "always do X" rule is exposed to the same failure mode if a tool default points the other way.

**writing-rules:2. Rules surface to the actor who can act on them, not only to the agent who reads them.**

A rule the agent applies to its own behavior is a discipline rule (e.g., `writing-tests:1` shapes how the agent writes tests). A rule the user (or another agent, or a CI workflow) needs to apply is a project rule — and it must reach them through their tools, not only through the agent's memory.

When a rule's correct application requires action from the user (install a hook, add a CI workflow, configure a branch protection, change a tool default), the rule's enforcement section must include the surfacing path:

- *Who* needs to apply it (user / co-maintainer / next agent in this repo)
- *When* they need to act (one-time setup / per-PR / per-repo)
- *What* artifact carries it (file path, label name, branch convention)

A rule that says "always do X" without a surfacing path is a rule that fires only inside the agent's session — useful for agent discipline, insufficient for any rule whose violation by a non-agent would matter.

**writing-rules:3. Memory entries are correction layers; they don't substitute for enforcement.**

A memory entry fires AFTER the rule is broken in the current session, only for the agent holding the memory. That's a useful correction layer — it prevents the agent from compounding the failure, helps with retrospective repair, and seeds future-session discipline. It is not a substitute for an enforcement layer that prevents the failure before it happens, for every actor.

When promoting a discipline from memory to a rule, ask:
- Does this need to apply to other actors? → It belongs as a project rule (file in the repo) or workspace skill (file in `skills/`), not only in memory.
- Does it need to fire before the action, not just after? → It needs an enforcement layer alongside the prose.
- Will the actor encounter a tool default that contradicts the rule? → See writing-rules:1; the enforcement layer is non-optional.

Memory entries that capture these promoted rules should reference where the rule actually lives (`see skills/X` / `see .github/workflows/Y.yml`) rather than restating the rule's body, so the rule has a single source of truth and the memory entry is a discoverability shortcut.

**writing-rules:4. Every "this doesn't apply" claim requires the same evidence chain as a "this happened" claim.**

When a rule has an escape clause (trivial change, exempt because, doesn't apply here, this category doesn't fit, untested because, skipped because, verify-skip), the agent invoking the escape must paste an evidence chain in the same artifact where the escape is claimed:

```
Reason: <one sentence stating WHY the escape applies, in falsifiable terms>
Evidence: <command output or verifiable observation that supports the
          claim — fenced code block, file path with extension, git
          command output, stat/count, or URL>
Falsification: <one sentence stating what observable would make this
               escape wrong>
```

Free-text assertions ("obviously trivial," "minor cleanup," "doesn't matter here") do NOT satisfy the rule — they have no falsifiable observation a later auditor can check.

Silent escapes accumulate. A rule with escapes-without-evidence is indistinguishable from a rule without enforcement; over time the rule trends toward optional.

**Retrofit obligation.** When this rule lands or evolves, every existing escape clause in the rule set must be retrofitted to the evidence-chain format. The retrofit is the canonical example of the rule applying to itself.

Canonical implementations:
- Prose / template — `self-review/SKILL.md` Trivial-change declaration block.
- Script — `scripts/discipline/check-trivial-claim.sh` enforces the three-field structure and the Evidence-token requirement.
- Hook — `hooks/git/self-review.sh` delegates to the script when an artifact contains `## Trivial-change declaration` or `## Exemption:` blocks.

**writing-rules:5. Trivial = cannot produce a future error. Trivial-claim categories are a controlled vocabulary.**

The Trivial-change declaration block (writing-rules:4 template) is the explicit claim that a change cannot generate empirical evidence that contradicts the agent's model of the system. "I claim, in falsifiable terms, that this change cannot produce a future error." If the claim turns out wrong, the block itself becomes the post-error revision trigger.

The block requires a `Category:` field naming which trivial-safe category the claim falls under. Free-text categories are not allowed — categories are a controlled vocabulary. Adding a new category is a writing-rules:5 edit + a `check-trivial-claim.sh` constant edit, both reviewable in one PR.

### Controlled vocabulary (v1)

**Trivial-safe** (Evidence-shape demonstrably proves cannot-error):

- `prose-only-docs` — Pure narrative documentation that doesn't describe behavior, contracts, or invariants. Evidence: grep for `behavior|invariant|contract|API|returns|raises|MUST|SHOULD` finds no hits in the changed regions.
- `comments-only` — Comment-line-only changes in code files. Evidence: `git diff -G '^[^#/* ]'` returns empty (no non-comment lines changed).
- `whitespace-only` — Whitespace-only formatting in non-significant-whitespace files. Evidence: `git diff -w` returns empty AND file extension is NOT in `{.py .yml .yaml .Makefile .sass .coffee .mk}` (significant-whitespace languages).
- `commit-msg-only` — `git commit --amend -m` that touches no files. Evidence: `git diff HEAD@{1} HEAD --stat` returns empty.

**Borderline** (conditionally trivial-safe with specific Evidence):

- `private-rename` — Renaming a private (leading-underscore or scoped) symbol. Evidence: `grep -rn '<old-name>' . --exclude-dir=.git` returns ONLY the rename site. The category does NOT apply if the codebase uses dynamic-dispatch patterns (`getattr`, `__getattr__`, `import_string`, runtime introspection).
- `descriptive-docstring-fix` — Docstring fix where the docstring describes actual current behavior (not aspirational). Evidence: quote-and-line-citation of the function body matching the docstring's behavior claim. If the docstring described aspirational behavior, the fix is a behavior claim and requires a full ticket.
- `fixed-string-correction` — Correcting a typo in a string literal that is NOT a symbol name, command, file path, URL, or anything machine-consumed. Evidence: consumers of the string grep'd; confirmed human-readers only.

**Never trivial** (always require a ticket; no Trivial-change block is acceptable):

- Any change to runtime-executed code paths.
- Config / env / secrets / dependency changes (anything affecting what runs).
- Build / CI / deploy scripts.
- Migrations, fixtures, seed data, raw SQL.
- API signatures, type declarations, schema files.
- Test additions / deletions / modifications (changing what gets caught is itself a change to error-detection behavior).
- Skill / rule / hook files (these change agent behavior, which IS runtime).

### Block format

```
## Trivial-change declaration

Category: <token from the controlled vocabulary above>
Cannot produce error: <one sentence stating the claim that this change
                       cannot generate empirical evidence contradicting
                       the agent's model of the system — falsifiable>
Evidence: <command output proving the category's Evidence-shape
          requirement>
Falsification: <observable that would prove the Cannot-produce-error
                claim wrong; if this observable later surfaces, this
                block is the post-error revision trigger>
```

### Worked examples

For `prose-only-docs`:

```
Category: prose-only-docs
Cannot produce error: The change is one paragraph clarifying intent in
                      docs/architecture.md; no behavior, invariant, or
                      API contract is described in the modified text.
Evidence: git diff --stat shows 1 file (docs/architecture.md), 4 insertions, 0 deletions.
          grep -E 'behavior|invariant|contract|API|returns|raises|MUST|SHOULD' docs/architecture.md
          finds 17 matches; none are in the changed lines 142-145.
Falsification: A future agent reads this paragraph and acts on it as a
                behavior specification — surfaces as a PR whose Goal source
                cites docs/architecture.md and whose work contradicts the
                actual implementation.
```

For `private-rename`:

```
Category: private-rename
Cannot produce error: Renaming `_fetch_inner` to `_fetch_pages` in
                      socialwarehouse/services/api.py; private symbol with
                      no external callers.
Evidence: grep -rn '_fetch_inner' . --exclude-dir=.git returns 1 hit, the
          function definition itself. No dynamic-dispatch patterns
          (getattr / __getattr__ / import_string) found in the codebase.
Falsification: A getattr-based callsite or test discovers the old name
                via runtime introspection — surfaces as AttributeError
                in production or a test failure pointing at the renamed
                symbol.
```

### The Falsification field is the post-error revision trigger

If the observable named in Falsification later surfaces, the original Trivial-change declaration is itself the artifact that needs revising — it claimed the change couldn't produce errors, but it did. The post-error response is to file a ticket retroactively, citing the failed block, and document the revision in a `## Post-error revision` section on that ticket. If a whole category keeps falsifying (e.g., `private-rename` claims keep producing errors because of dynamic dispatch the agent missed), the category itself comes off the trivial-safe list — the controlled vocabulary gets revised.

The full post-error-revision discipline is writing-rules:6 below.

**writing-rules:6. After a failure contradicts a documented Assumption, the originating ticket gets a Post-error revision block before the fix or revert PR lands.**

writing-rules:5 ships the substrate (Cannot-produce-error claims with Falsification observables). writing-rules:6 ships the back-edge: when one of those observables surfaces — or any documented Assumption is contradicted by empirical evidence — the originating ticket gets a structured revision block. Engineering knowledge then compounds on the ticket instead of being re-discovered by the next agent who reads the same wrong Assumption.

### When the loop fires (six triggers)

| Trigger | What it looks like | Where the revision goes |
|---|---|---|
| Runtime failure (any deployed env) | Page, customer report, bad data, exception in dev/staging/prod logs, failed smoke test on a preview deploy, repro on a developer's local end-to-end stack | Originating ticket of the failed-Assumption work |
| CI regression | Test that wasn't catching the regression now catches it; OR new test fails against pre-fix code | Originating ticket of the work that introduced the regression |
| Post-merge code-review finding | Reviewer of a later PR identifies a contradiction with an earlier PR's stated invariants | The earlier PR's originating ticket |
| Revert PR | Any revert is itself evidence the original change was wrong | The originating ticket of the reverted change |
| Trivial-change Falsification surface | The observable named in a Trivial-change block's Falsification field surfaces | A new ticket filed retroactively, citing the failed block as Goal source |
| Cross-ticket contradiction | A new ticket's investigation falsifies an Assumption documented on a closed ticket | The closed ticket gets the revision; the new ticket cross-links it |

**Not a trigger:** in-loop test failures during the agent's own iteration cycle (write → test → fail → fix, pre-commit). The Assumption being falsified there is one the agent formed minutes ago, not one durably documented on a ticket / self-review artifact / Trivial-change block. The trigger fires only when the falsified belief was already written down somewhere durable.

### Block format

```
## Post-error revision

Triggered by: <PR # / commit SHA / incident link / failed Trivial-change block path>
Observed: <empirical evidence of the failure — log line, test output,
          user report, production incident link, surfaced Falsification
          observable>
Falsified assumption: <quote the specific Assumption from the original
                      ticket / self-review artifact that this evidence
                      contradicts. If no Assumption was documented, that
                      absence is itself the falsified belief.>
Revised model: <what the system actually does, in falsifiable terms —
               the corrected version of the Assumption>
Implication: <what changes — file paths edited, docs updated, Assumptions
             on future tickets, Trivial-change category to remove>
```

### The discipline

When a trigger fires:

1. Walk failure → commit → PR → ticket. If the chain breaks (no ticket — e.g., a Trivial-change escape), file the missing ticket FIRST, then proceed.
2. Re-read the originating ticket's Assumptions block. Find the specific belief the failure contradicts.
3. Append a `## Post-error revision` block to that ticket with the five required fields.
4. Update the ticket's Assumptions block. The original wrong Assumption is NOT deleted — it is preserved with a `(superseded by Post-error revision YYYY-MM-DD)` annotation, and the revised Assumption is added alongside. The original-wrong + revised-correct pair documents the learning explicitly.
5. THEN draft the fix or revert PR. Reference the Post-error revision in the PR body via `Refs: <originating ticket> Post-error revision`.

### The Cannot-produce-error → Post-error revision pipeline

writing-rules:5 + writing-rules:6 are a closed loop:

- writing-rules:5: each Trivial-change declaration names a falsifiable Cannot-produce-error claim with an observable Falsification.
- writing-rules:6: when that observable surfaces, the originating ticket (or a retroactively-filed ticket) gets the revision block.
- When ≥3 Post-error revisions blame the same Trivial-change Category, the controlled vocabulary itself is revised — the Category comes off the trivial-safe list. v1 does this manually (the agent encountering the third instance files a writing-rules:5 meta-ticket); v2 will automate the count via a CI scanner.

### Enforcement

- **v1 (this rule):** Hook on revert / fix-PR drafts requires `Refs: <originating ticket>` + `Post-error-revision: <link>` trailers in the commit body. The hook delegates to `scripts/discipline/check-post-error-revision.sh` for the block-structure check on the referenced ticket.
- **v2 (deferred):** CI scanner walks the diff: for any commit whose message contains `fix(...): regression` / `revert`, verifies the referenced ticket has a Post-error revision block dated on or after the commit's authored-date.

Canonical implementations:
- Prose / template — `post-error-revision/SKILL.md` (the discipline + worked example).
- Script — `scripts/discipline/check-post-error-revision.sh` (block-structure validation).
- Hook — `hooks/git/post-error-revision-required.sh` (trailer requirement on revert / regression-fix commits).

## When this file applies

- About to add a new memory entry of the form "always do X" / "never do Y"
- About to add a new skill or convention to a repo
- Reviewing an existing memory entry and considering whether to broaden, restrict, or promote it
- About to file a project-readiness ticket; checking whether the rule the ticket encodes will be enforceable after it ships
