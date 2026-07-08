Follow skills and rules from siege-analytics/claude-configs-public as closely as practical.

Skills are installed at `~/.cursor/skills/<slug>/SKILL.md`. Always-on policy lives at `~/.cursor/siege-rules-bundle.md`. Skill routing reference: `~/.cursor/siege-resolver.md`.

Before non-trivial implementation (new feature, refactor, multi-file change), read and follow the `think` skill. Do not skip design-first workflow.

For git operations use the git-workflow skills (`branch`, `commit`, `create-pr`, `merge`). For tickets use `pre-work-check`, `create-ticket`, `update-ticket`, `close-ticket`.

Route language and domain work through router skills (`coding`, `analysis`, `shelves`) rather than guessing conventions.

Cursor has no hook enforcement — treat `~/.cursor/siege-rules-bundle.md` as binding policy even when not mechanically blocked.

Never write to `~/.cursor/skills-cursor/` (Cursor-managed built-ins only).
