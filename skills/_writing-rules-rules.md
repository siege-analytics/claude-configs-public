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

## When this file applies

- About to add a new memory entry of the form "always do X" / "never do Y"
- About to add a new skill or convention to a repo
- Reviewing an existing memory entry and considering whether to broaden, restrict, or promote it
- About to file a project-readiness ticket; checking whether the rule the ticket encodes will be enforceable after it ships
