---
ticket_refs: ["siege-analytics/claude-configs-public#205"]
---

# Design note: Inventoried-shape commit trailer enforcement (#205)

## What

Add v2.5 check to self-review.sh: require `Inventoried-shape:` trailer
in commit messages when executable code is in the diff. Exemption via
`Trivial-against-state:` declaration in self-review artifact.

## Why

v1.2 enforces `Pre-author-inventory:` in the self-review artifact — proves
the agent CLAIMS to have measured. But the commit itself carries no evidence.
Reading `git log` shows no measurement trace. The agent can satisfy v1.2
by writing `Pre-author-inventory: I measured the shapes` without measuring.

Adding `Inventoried-shape:` to the commit message puts measurement evidence
in the durable commit history, visible to anyone reading `git log`.

## Design

### Location
self-review.sh, after v2.3 (hostile-review-artifact check). New version: v2.4.

### Logic
1. Check if diff contains executable code files (.py, .sh, .sql, .js, .ts,
   .rb, .go, .rs, .java, .c, .cpp, .h)
2. If yes, check commit message for `Inventoried-shape:` trailer (regex:
   `^Inventoried-shape:[[:space:]]+\S`)
3. If missing, check self-review artifact for `Trivial-against-state:`
   declaration (already parsed by v1.2)
4. If neither found, BLOCK with message pointing at
   `_authoring-against-state-rules.md:1`

### Exemptions
- Non-executable changes (markdown, comments, whitespace) — no check
- `Trivial-against-state:` declaration present in self-review artifact — skip
- `[no-review]` commits — already handled by v2.1, which has its own
  executable-line threshold

### Rollback
Remove the v2.4 block from self-review.sh. No other files affected.

## Alternatives considered
1. **Separate hook** — more modular but fragments pre-push enforcement
   across too many scripts. self-review.sh is the canonical pre-push gate.
2. **Require `pre-write-inventory.md` in diff** — too rigid, many legitimate
   workflows record inventory on the ticket, not in a file.
3. **Check ticket body via `gh api`** — adds network dependency to a git
   hook; unreliable offline; slow.
