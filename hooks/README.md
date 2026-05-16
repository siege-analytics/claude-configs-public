# Hooks

Claude Code hooks that enforce the rules described in the skills.
Skills are advisory — they tell the agent what to do. Hooks are
mandatory — they block the agent when it tries to break a rule.

## Relationship to Skills

Each hook enforces one or more skills. The hook blocks the bad
behavior; the skill explains the correct behavior.

| Hook | Enforces | Blocks |
|------|----------|--------|
| `git/branch-guard.sh` | develop-guard, branch, commit (step 0) | Commits to main, develop, master, staging |
| `git/ticket-required.sh` | commit (ticket enforcement) | Commits without a ticket reference |
| `git/no-attribution.sh` | commit (attribution policy), all CLAUDE.md | Commits with AI/agent attribution |
| `git/no-sensitive-files.sh` | commit (sensitive files) | Staging .env, credentials, keys |
| `git/no-broad-staging.sh` | commit (staging patterns) | `git add -A`, `git add .`, `git add --all` |
| `git/self-review.sh` | `skills/self-review/SKILL.md`, `feedback_self_code_review` memory | `git push`, `gh pr create`, `gh pr merge` when latest commit lacks `Self-Review:` / `Self-Review-Source:` trailers, or the source artifact lacks required sections. v1 mechanical checks; v2 follow-ups tracked in the skill. |
| `agent-comms/no-slug-form-outbound.sh` | parser-drop guard (LESSON 323a0f5) | `mcp__session__send_agent_message` calls whose body contains `[skill:slug]` or `[rule:slug]` literal forms (host parser silently drops the carrier message). Use the angle-bracket form `[skill:<name>]` instead. |

## Installation

For workspace consumers (Craft Agent and similar) the canonical install
sequence -- rsync `hooks/` from `release/flat`, then merge the snippet,
then verify a hook fires -- is documented in the top-level
[README "Wire and verify hooks" section](../README.md#wire-and-verify-hooks).
Order matters: the snippet's `command` paths reference on-disk hook
scripts, so the rsync must precede the settings.json merge.

The steps below cover direct-clone installs (the historical pattern),
where the repo is cloned to a fixed path and the snippet's
`/path/to/claude-configs-public` placeholder is rewritten to that path.

### 1. Make scripts executable

```bash
chmod +x hooks/git/*.sh hooks/agent-comms/*.sh hooks/infrastructure/*.sh hooks/resolver/*.sh hooks/write/*.sh
```

### 2. Add hooks to your project settings

Copy the hooks block from the unified [`settings-snippet.json`](settings-snippet.json) (at the
hooks root) into your project's `.claude/settings.json` (or
`settings.local.json`). The unified snippet wires the `UserPromptSubmit`
resolver injector, the `Bash`-matcher hooks (catalog-guard, branch-guard,
no-attribution, ticket-required, no-sensitive-files, no-broad-staging),
and the `mcp__session__send_agent_message`-matcher agent-comms hook
(no-slug-form-outbound).

Replace `/path/to/claude-configs-public` with the actual path:

```bash
sed 's|/path/to/claude-configs-public|<absolute path to this repo>|g' \
    hooks/settings-snippet.json
```

### 3. Or install globally

Add to `~/.claude/settings.json` to enforce across all projects.

### 4. Verify a hook fires

```bash
# Should print BLOCKED... and exit 2
echo '{"tool_input":{"message":"see [skill:think]"}}' \
  | hooks/agent-comms/no-slug-form-outbound.sh
echo "exit=$?"
```

Exit 0 here means the script ran without finding a literal slug-form
token (so the test input was wrong); exit 2 means the hook blocked as
expected. To test settings.json wiring end-to-end, attempt a real
`mcp__session__send_agent_message` call with a literal `[skill:foo]` in
the body -- the call should be blocked with the same stderr.

## How Hooks Work

- Hooks run as `PreToolUse` — before Claude Code executes a tool
- They receive JSON on stdin with the tool name and arguments
- Exit 0 = allow, Exit 2 = block (message shown to agent)
- The agent sees the block message and must adjust its approach
- Hooks cannot be bypassed by the agent — they are system-level

## Testing

```bash
# Test branch guard
echo '{"cwd":"/tmp","tool_input":{"command":"git commit -m test"}}' | \
    ./hooks/git/branch-guard.sh
echo "Exit: $?"

# Test attribution blocker
echo '{"tool_input":{"command":"git commit -m \"Co-Authored-By: Claude\""}}' | \
    ./hooks/git/no-attribution.sh
echo "Exit: $?"
```

## Adding New Hooks

1. Create a script in the appropriate subdirectory (`git/`, or a new category)
2. Follow the pattern: read JSON from stdin, parse with jq, exit 0 or 2
3. Document which skill(s) it enforces in the header comment
4. Add to `settings-snippet.json`
5. Update this README
