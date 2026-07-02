---
name: knowledge-base
description: "Platform-agnostic knowledge-base consultation protocol. Projects declare their knowledge sources in PROJECT.md; agents consult them during think/investigate, tag assumptions against findings, and update the KB when contradictions or gaps are found. Pairs with _knowledge-base-rules.md (always-on) and think-gate-guard.sh Level 3 (mechanical enforcement)."
allowed-tools: Read Grep Glob Bash
---

# Knowledge Base

This skill answers: **did you read what the project already knows before forming claims?**

The think skill's Step 1 asks agents to investigate, and the investigate skill produces a Fact Sheet. But neither mechanically verifies that the project's documented knowledge was consulted. Agents routinely form claims that contradict what the wiki, docs/, or knowledge base already says. The contradiction surfaces during hostile review -- too late.

## Why this exists

Two failure modes this skill closes:

1. **Contradicted claims.** The agent writes a design note claiming "JWT lifetime is 24 hours" without reading the wiki page that says "99999 days." The design proceeds on a false premise. Hostile review catches it, but the implementation is already done.
2. **Silent gaps.** The agent investigates and discovers facts the KB doesn't cover. Without a protocol, the discovery dies in the session. The next agent re-discovers the same fact from scratch.

## Declaring your knowledge sources

Projects opt in by adding a `knowledge_base:` section to `PROJECT.md`:

```yaml
knowledge_base:
  - url: https://github.com/org/repo/wiki
    scope: architecture decisions, module contracts
  - url: docs/
    scope: API reference, changelog
  - url: https://confluence.internal/space/PROJECT
    scope: onboarding, runbooks
```

Each source names:
- **url** -- web URL or relative path to a documentation tree
- **scope** -- what kind of questions this source answers (advisory, not enforced)

Projects without `knowledge_base:` are unaffected by this enforcement. Once declared, the think-gate-guard warns when KB consultation is missing.

## The protocol

### 1. Read (during think Step 1)

When starting investigation for a non-trivial task:

1. Check PROJECT.md for `knowledge_base:` sources
2. Identify which source(s) are relevant to the investigation domain
3. Read the relevant pages (wiki pages, doc sections, Notion databases)
4. Record what the KB claims about the topic under investigation

This is not "read everything." Read the pages whose scope matches the task. A DB migration task reads architecture pages, not marketing docs.

### 2. Tag (during think Step 2)

Every assumption in the design note gets one of four tags:

| Tag | Meaning | Example |
|---|---|---|
| `kb-confirmed` | KB agrees with the assumption | "ERD confirms unique constraint -- wiki/architecture.md" |
| `kb-contradicted` | KB disagrees with the assumption | "Wiki says 24h JWT, actual is 99999d" |
| `kb-silent` | KB has no coverage of this topic | "No wiki page on rate limiting" |
| `kb-not-applicable` | This assumption is not knowledge-dependent | "pytest is the project's test runner (declared in PROJECT.md)" |

**Untagged assumptions are hidden claims.** If an assumption has no KB tag, it means the agent did not check whether the project already has documented knowledge about it. This is the gap the tagging discipline closes.

### 3. Update (during the work)

| Finding | Action | Done when |
|---|---|---|
| `kb-contradicted` | File a KB update (wiki edit, docs/ PR, page update) or a ticket for deferred update | Delta reference exists (PR URL, ticket number, commit hash) |
| `kb-silent` + investigation answered the question | Draft a KB addition | Addition drafted or ticket filed |
| `kb-confirmed` | No action needed | -- |
| `kb-not-applicable` | No action needed | -- |

The delta is part of the definition of done (`[`definition-of-done`](../_definition-of-done-rules.md)` criterion (f)). A contradiction without a filed delta is technical debt.

### Default edit shape for contradictions

When updating a KB page to correct a contradiction:

```markdown
## [Section Title]

> **CONTRADICTED (2026-06-09):** Prior claim was "[old claim]."
> Corrected per [primary source]: [new claim].
> See #NNN for investigation context.

[Updated content]
```

The CONTRADICTED block preserves the prior claim (so readers understand what changed), cites the primary source (not the agent's judgment), and links to the investigation ticket for audit trail.

### Signal file integration

After completing the tag step, record KB consultation in `think-gate.json`:

```json
{
  "kb": {
    "sources": ["https://github.com/org/repo/wiki", "docs/"],
    "consulted": true,
    "tags": {
      "confirmed": ["ERD confirms unique constraint -- wiki/architecture.md"],
      "contradicted": ["Wiki says 24h JWT lifetime, actual is 99999d -- delta: #207"],
      "silent": ["No wiki coverage of rate limiting -- addition drafted"]
    }
  }
}
```

The `kb` key is optional in the signal file. The think-gate-guard Level 3 checks for its presence when the project declares `knowledge_base:`.

## Platform-specific access

This skill defines the protocol (what to do), not the tool (how to access). The agent uses whatever tools are available:

| Platform | Access method |
|---|---|
| GitHub wiki | `gh api repos/{owner}/{repo}/wiki/pages` or clone wiki repo |
| docs/ tree | `Read` tool, `Grep` for content |
| Confluence | REST API or browser tool |
| Notion | Notion MCP source or browser tool |
| External URLs | `WebFetch` or browser tool |

The skill does not prescribe a specific access method. If the platform is unreachable (credentials missing, network error), tag the assumption `kb-silent` with a note explaining why the source could not be consulted. A source that cannot be consulted is not the same as a source that was not consulted -- the distinction matters for the audit trail.

## Cross-references

- `[`knowledge-base`](../_knowledge-base-rules.md)` -- always-on rules for KB consultation discipline
- `[`definition-of-done`](../_definition-of-done-rules.md)` criterion (f) -- KB delta as done criterion (opt-in)
- `[`think`](../think/SKILL.md)` Step 1 -- investigation is where KB consultation happens
- `[`investigate`](../investigate/SKILL.md)` -- Fact Sheet is the output of investigation; KB tags inform it
- `hooks/resolver/think-gate-guard.sh` Level 3 -- mechanical warning when KB section missing
