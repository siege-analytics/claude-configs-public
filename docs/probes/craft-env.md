# Probe: Craft Agents environment variables

Evidence for the signals used by `hooks/lib/detect-host.sh`. Captured 2026-09-01
against `craft-agent` 0.10.4 on cyberpower.

This file exists because prose is not evidence. `CRAFT_AGENT_SESSION_ID`,
`CRAFT_AGENT_SESSION_DIR` and `CRAFT_AGENT_WORKSPACE` entered this codebase as
confident assertions about environment state, are read by three live hooks, and
are set by nothing. Every branch behind them has always taken the fallback. A
detector built the same way would repeat that, so each variable below is
recorded with the command that produced it.

## Process-wide (server environment, inherited by children)

```
$ PID=$(docker inspect craft-agent --format '{{.State.Pid}}')
$ sudo cat /proc/$PID/environ | tr '\0' '\n' | grep -E '^CRAFT_[A-Z_]+=' | sed 's/=.*/=<set>/'
CRAFT_CLAUDE_OAUTH_TOKEN=<set>
CRAFT_RPC_PORT=<set>
CRAFT_IS_PACKAGED=<set>
CRAFT_WEBUI_DIR=<set>
CRAFT_RESOURCES_PATH=<set>
CRAFT_SCRIPTS=<set>
CRAFT_BUNDLED_ASSETS_ROOT=<set>
CRAFT_SERVER_TOKEN=<set>
CRAFT_UV=<set>
CRAFT_RPC_HOST=<set>
```

Values are redacted deliberately. `CRAFT_CLAUDE_OAUTH_TOKEN` is a live
credential and is excluded from the detector for that reason — see
`electinfo/ops#397`.

## Per-session (set when the agent subprocess is spawned)

These do **not** appear in the server's own environment, so probing the daemon
alone will not find them. They are present where hooks run, which is inside a
session.

```
$ docker exec craft-agent sh -c 'grep -rhoE "CRAFT_SESSION_[A-Z_]*" /app | sort | uniq -c | sort -rn'
     10 CRAFT_SESSION_NAME
      5 CRAFT_SESSION_DIR
      4 CRAFT_SESSION_ID
      2 CRAFT_SESSION_METADATA
```

Corroborated by a live hook in this repository that has been consuming one of
them: `hooks/resolver/skill-enforcement-gate.sh:26` reads `CRAFT_SESSION_DIR`
and resolves `$CRAFT_SESSION_DIR/session.jsonl`. Independently probed and
recorded in `plans/self-review-449.md`:

```
| CRAFT_SESSION_DIR env var available in Craft Agent | `env | grep CRAFT_SESSION_DIR` -> set in current session | Yes |
```

## Claude Code

```
$ env | grep -E '^(CLAUDE|CLAUDECODE)' | sed 's/=.*/=<set>/'
CLAUDE_CODE_ENTRYPOINT=<set>
CLAUDECODE=<set>
CLAUDE_CODE_SESSION_ID=<set>
CLAUDE_CODE_EXECPATH=<set>
CLAUDE_PROJECT_DIR unset in this session; retained as a signal because it is
set when Claude Code runs with a project directory.
```

## Why Craft is tested first

Craft spawns Claude Code as a child. The child sets `CLAUDECODE` for itself and
inherits the `CRAFT_*` variables, so a hook running under Craft sees both
families at once. The server environment carries ten `CRAFT_*` and zero
`CLAUDE*`:

```
$ sudo cat /proc/$PID/environ | tr '\0' '\n' | grep -cE '^(CLAUDE|CLAUDECODE)'
0
```

So "both present" means craft, not claude-code.

## Names that are set by nothing

Asserted in code, never exported by any runtime. Listed so the regression test
can keep them out:

| Name | Read by |
|---|---|
| `CRAFT_AGENT_SESSION_ID` | `hooks/lib/resolve-think-gate.py` |
| `CRAFT_AGENT_SESSION_DIR` | `hooks/lib/resolve-think-gate.py` |
| `CRAFT_AGENT_WORKSPACE` | `hooks/lib/log-block.sh` |

The real names carry no `AGENT`. `CRAFT_SESSION_ID` exists and is what
`CRAFT_AGENT_SESSION_ID` was reaching for.

## Refreshing this capture

Re-run after any Craft upgrade; the version is in `/app/package.json`.

```bash
PID=$(docker inspect craft-agent --format '{{.State.Pid}}')
sudo cat /proc/$PID/environ | tr '\0' '\n' | grep -E '^CRAFT_[A-Z_]+=' | sed 's/=.*/=<set>/'
docker exec craft-agent sh -c 'grep -rhoE "CRAFT_SESSION_[A-Z_]*" /app | sort | uniq -c'
```
