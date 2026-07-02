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

The spawn call must satisfy `spawn-guard.sh`: explicit permission, model,
reasoning level, source list, and rule binding. Review sessions use high or
higher reasoning and the strongest suitable model available.

```
spawn_session(
  name: "Cross-review: <provider> reviews <filename>",
  llmConnection: "<resolved-connection-slug>",
  model: "<resolved-strong-review-model>",
  permissionMode: "allow-all",
  thinkingLevel: "high",
  enabledSourceSlugs: [<explicit required source slugs, or [] if none>],
  labels: ["cross-review"],
  prompt: <see Prompt Template below>,
  attachments: [
    { path: "<file-under-review>" },
    { path: "<skill-file>", name: "review-skill.md" },
    { path: "<repo>/dist/flat/RULES_BUNDLE.md or <repo>/RESOLVER.md", name: "rules-bundle.md" }
  ]
)
```

If no built rules bundle exists, attach `RESOLVER.md` and any required rule
files directly, or inline their relevant sections in the prompt. Do not spawn an
unbound reviewer.

### Step 6: Request findings delivery

After spawning, send a follow-up message only for clarification. The reviewer
must return findings to the parent through `send_agent_message`; the parent,
which remains hook-bound, posts any ticket comment after reviewing the proposed
body.

```
send_agent_message(
  sessionId: "<spawned-session-id>",
  message: "When done, send findings back to parent session <parent-session-id>
            via send_agent_message. Do not call gh issue comment or mutate
            issue/PR status directly. Then call set_session_status done."
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

- Follow the attached RULES_BUNDLE/RESOLVER/session-coordination rules.
- You are a reviewer, not an implementer. Do not modify any files.
- Cite file:line for every finding.
- Rate severity per the review skill's scale.
- Return findings to parent via send_agent_message; do not post ticket/PR comments directly.
- When complete, call set_session_status done.
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
CLI and CI environments. The invoking agent is responsible for validating and posting the returned
findings to the ticket from the hook-bound parent runtime.

## Incorporating Results

When findings arrive (via `send_agent_message` reply or ticket comment):

1. Read the findings
2. Triage by severity: S1 findings block merge, S2 findings get tickets, S3 findings are tracked
3. If the reviewer is on a different provider, weight findings that both
   providers agree on more heavily — cross-provider consensus is strong signal
4. Update the self-review artifact with a "Cross-review" section noting
   provider, model, and finding count
5. Record the review location in the self-review artifact's
   `Hostile-review-artifact:` field (ticket comment link or file path)

## Reviewer session lifecycle (originating agent owns cleanup)

The agent that spawned the reviewer is responsible for closing its **session**
once the review task reaches a terminal state. Do not rely on the reviewer
self-closing: a reviewer that errors or stalls (e.g. a provider rejects every
turn) cannot always set its own status to done, and a lingering reviewer
clutters the session list.

Track the `sessionId` returned by `spawn_session` for each reviewer -- persist
it somewhere durable that survives a parent restart (the self-review artifact, a
ticket comment, or session labels) so cleanup can resume if the parent is
interrupted. When the review task reaches a terminal state, close the reviewer
with:

```
set_session_status(sessionId: "<spawned-session-id>", status: "done")
```

(`set_session_status` accepts a `sessionId`, so the parent can close any reviewer
it spawned directly. Setting `done` is idempotent -- harmless if the reviewer
already self-closed -- so close it whenever it is still open.)

Keep two things distinct: the **review task** (has independent review coverage
actually been obtained?) and the **reviewer session** (is the spawned session
still open?). Terminal cases:

- **Merged / review served its purpose** -- the reviewer delivered findings and
  they were incorporated. Close the session.
- **Abandoned** -- the PR was closed without merge or the review is no longer
  needed. Close the session.
- **Reviewer wedged or errored** -- closing the dead session is cleanup, but it
  does NOT by itself satisfy the review task. If the underlying work is still
  active, first obtain review coverage another way (spawn a replacement reviewer,
  fall back to the MCP cross-review server, or explicitly record that
  cross-review was waived/failed), THEN close the wedged session. Do not treat
  "I closed the reviewer" as "the work was reviewed."

The MCP fallback path spawns no session, so it needs no cleanup. Closing every
reviewer session it spawned is part of the originating agent's definition of
done; the task is not complete while a reviewer it spawned is still open.

## Review-Gate Lifecycle

The review-gate signal file ensures that fixes pushed after a review
automatically trigger re-review. This works in both Craft Agent and
pure Claude Code.

### On request-changes verdict

After the review produces a request-changes verdict, write the signal
file so the hook can detect when fixes land:

**Craft Agent:** `<workspace>/review-gate.json`
**Claude Code:** `<repo>/.review-gate.json`

```json
{
  "ticket": "owner/repo#NNN",
  "branch": "<current-branch>",
  "reviewed_commit": "<HEAD at review time>",
  "skill": "<review-skill-slug>",
  "provider": "<provider-name>",
  "verdict": "request-changes",
  "findings_location": "<ticket-comment-URL or file path>",
  "created": "<ISO 8601 timestamp>",
  "lastChecked": "<ISO 8601 timestamp>"
}
```

### On approve verdict

Delete the signal file:

```bash
rm review-gate.json          # Craft Agent
rm .review-gate.json         # Claude Code
```

### How re-review triggers

The `review-gate-guard.sh` hook runs on every turn. When it detects
that the branch has new commits since `reviewed_commit`, it emits a
re-review directive. The agent must then re-fire the review on the
current code before pushing.

After re-review, update `reviewed_commit` to the current HEAD.

### Cross-runtime compatibility

The signal file is just JSON on disk. The hook uses only `git` and
`python3`. No Craft Agent primitives required.

## Attribution Policy

NEVER include AI or agent attribution in review findings, ticket comments,
or any output. The review is a tool output, not a co-authored artifact.
