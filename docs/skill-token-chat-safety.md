# Skill-token chat safety

Craft Agent host parsing has treated bracketed skill references in ordinary chat as resolver directives. That means an assistant can trigger noisy "skill not found" UI by writing the raw token shape in prose, even when the text is only an example or retrospective note.

## Rule

Do not put raw bracketed skill-reference tokens in operator-facing chat unless the intent is to invoke or test the host resolver.

Use one of these safe forms when discussing a skill as text:

- `skill:code-review` without brackets.
- `[skill colon code-review]` when the brackets matter to the explanation.
- `the code-review skill` in normal prose.
- A generated/sanitized transcript from `scripts/discipline/skill-token-chat-safe.py`.

The same rule applies to rule references: prefer `rule:writing-prose` or `[rule colon writing-prose]` when the message is explanatory text.

## Why code formatting is not enough

In affected sessions, backticks and Markdown examples were not a reliable escape boundary. The host saw the raw token text before Markdown rendering and attempted resolution anyway. Treat raw bracketed references as active syntax in chat.

## Repository docs versus chat

Repository files may still contain raw bracketed references where they are part of the package contract and consumed by Claude/Codex-style runtimes. This safety rule is about chat output, issue comments, PR comments, postmortems, and handoff messages that describe skills as text.

## Sanitizer

For generated retrospectives or handoff text, run:

```bash
python3 scripts/discipline/skill-token-chat-safe.py input.md > safe-output.md
```

It rewrites raw bracketed skill/rule references into display-only forms that do not match the resolver token shape.
