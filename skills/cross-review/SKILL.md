---
name: cross-review
description: "Multi-provider code review dispatcher. Discovers available LLM connections, selects an alternate provider (Claude↔Codex, Codex↔Gemini, etc.), and spawns a review session on that provider using a portable review skill. Falls back to same-provider review or the MCP cross-review server when no alternate is available."
allowed-tools: Read Glob Grep spawn_session send_agent_message get_session_info set_session_status
---

# Cross-Review

Dispatch a code review to a different LLM provider so the reviewer is
architecturally independent from the author. Claude reviews Codex's work,
Codex reviews Claude's, and so on.

## When to Use

- After completing work on a ticket, before merge
- When self-review has passed but you want an independent second opinion
- When the resolver or pipeline calls for cross-model review

## Inputs

The invoking agent must supply:

| Input | Required | Description |
|-------|----------|-------------|
| File path(s) | Yes | The file(s) to review |
| Review skill | Yes | Which review skill to use (`hostile-review`, `self-review`, `code-review`, `over-engineering-audit`) |
| Ticket reference | No | Repo and issue number for posting findings (e.g., `siege-analytics/claude-configs-public#445`) |

## Provider Resolution

### Step 1: Discover connections

```
result = spawn_session(help=true)
connections = result.connections
```

### Step 2: Identify current provider

Determine the current session's provider type. If unknown, assume `anthropic`.

### Step 3: Select alternate provider

Partition `connections` by `providerType`. Resolution order:

1. **Alternate provider available** — a connection where `providerType` differs
   from the current session's. Prefer the connection with the most capable
   `defaultModel`. This gives true cross-model review: Claude reviews Codex's
   work, Codex reviews Claude's.

2. **Same provider, different model** — if no alternate provider exists, use a
   connection on the same provider but select a different model than the
   current session's. Still valuable for independent review even without
   cross-model independence.

3. **MCP cross-review server** — if `spawn_session` is unavailable (CLI-only,
   CI pipelines, environments without Craft Agents), fall back to the
   `cross-review` MCP source. This uses API keys and provides single-shot
   review without tool access.

### Step 4: Read the review skill

Read the SKILL.md for the chosen review skill. The full content becomes part
of the spawn prompt — the reviewer needs the complete instructions.

Search paths for skills (in order):
- `<repo>/dist/flat/skills/<slug>/SKILL.md`
- `<repo>/skills/<slug>/SKILL.md`
- `~/.craft-agent/workspaces/my-workspace/skills/<slug>/SKILL.md`

### Step 5: Spawn the reviewer

```
spawn_session(
  name: "Cross-review: <provider> reviews <filename>",
  llmConnection: "<resolved-connection-slug>",
  model: "<resolved-model>",
  permissionMode: "allow-all",
  enabledSourceSlugs: [<inherit from parent session>],
  labels: ["cross-review"],
  prompt: <see Prompt Template below>,
  attachments: [
    { path: "<file-under-review>" },
    { path: "<skill-file>", name: "review-skill.md" }
  ]
)
```

### Step 6: Request findings delivery

After spawning, send a follow-up message:

```
send_agent_message(
  sessionId: "<spawned-session-id>",
  message: "When done, post your findings as a comment on <ticket-ref>
            using `gh issue comment`. Then set your session status to done.
            If gh is unavailable, send findings back to me via
            send_agent_message with session ID <parent-session-id>."
)
```

## Prompt Template

The spawn prompt combines the review instructions with context:

```
You are performing an independent code review as a <provider> agent.

## Your task

Review the attached file using the review methodology in review-skill.md.

## Context

- File under review: <filename>
- Ticket: <ticket-ref> (if provided)
- Author's provider: <current-provider> — you are reviewing from <reviewer-provider>

## Output

1. Produce your findings in the format specified by the review skill.
2. Post findings as a comment on the ticket: gh issue comment <number> -R <repo> --body "<findings>"
3. If you cannot post to the ticket, use send_agent_message to send findings
   back to the parent session.
4. When complete, set your session status to done.

## Rules

- You are a reviewer, not an implementer. Do not modify any files.
- Cite file:line for every finding.
- Rate severity per the review skill's scale.
- Do not add AI/assistant attribution to any output.
```

## MCP Fallback

When `spawn_session` is not available, use the cross-review MCP source
(ticket #443):

```
cross-review review(
  file_path: "<path>",
  skill_slug: "<review-skill>",
  provider: "<available-provider>"
)
```

This path is single-shot (no tool access, no ticket posting) but works in
CLI and CI environments. The invoking agent is responsible for posting the
returned findings to the ticket.

## Incorporating Results

When findings arrive (via `send_agent_message` reply or ticket comment):

1. Read the findings
2. Triage by severity: S1 findings block merge, S2 findings get tickets, S3 findings are tracked
3. If the reviewer is on a different provider, weight findings that both
   providers agree on more heavily — cross-provider consensus is strong signal
4. Update the self-review artifact with a "Cross-review" section noting
   provider, model, and finding count

## Reviewer session lifecycle (originating agent owns cleanup)

The agent that spawned the reviewer is responsible for closing it down once the
review task is resolved -- whether the underlying work was **merged** or
**abandoned**. Do not rely on the reviewer self-closing: a spawned reviewer that
errors or stalls (e.g. a provider rejects every turn) cannot always set its own
status to done, and a lingering reviewer clutters the session list.

Track the `sessionId` returned by `spawn_session` for each reviewer. When the
review task reaches a terminal state, close the reviewer with:

```
set_session_status(sessionId: "<spawned-session-id>", status: "done")
```

(`set_session_status` accepts a `sessionId`, so the parent can close any
reviewer it spawned directly.) This applies in both terminal cases:

- **Merged / review served its purpose** -- confirm the reviewer delivered its
  findings, then close it.
- **Abandoned** -- PR closed without merge, review no longer needed, or the
  reviewer wedged on an error -- close it anyway.

Closing every reviewer it spawned is part of the originating agent's definition
of done. The task is not complete while a reviewer it spawned is still open.

## Attribution Policy

NEVER include AI or agent attribution in review findings, ticket comments,
or any output. The review is a tool output, not a co-authored artifact.
