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
| `agent-comms/no-slug-form-outbound.sh` | parser-drop guard (LESSON 323a0f5) | `mcp__session__send_agent_message` calls whose body contains `[skill:slug]` or `[rule:slug]` literal forms (host parser silently drops the carrier message). Use the angle-bracket form `[skill:<name>]` instead. |

## Installation

### 1. Make scripts executable

```bash
chmod +x hooks/git/*.sh hooks/agent-comms/*.sh
```

### 2. Add hooks to your project settings

Copy the hooks block from the unified `settings-snippet.json` (at the
hooks root) into your project's `.claude/settings.json` (or
`settings.local.json`). The unified snippet wires both the `Bash`-matcher
hooks (git/, infrastructure/) and the MCP-matcher agent-comms hook.

Replace `/path/to/claude-configs-public` with the actual path:

```bash
# Example for electinfo
sed 's|/path/to/claude-configs-public|/home/dheerajchand/git/electinfo/claude-configs-public|g' \
    hooks/git/settings-snippet.json
```

### 3. Or install globally

Add to `~/.claude/settings.json` to enforce across all projects.

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
