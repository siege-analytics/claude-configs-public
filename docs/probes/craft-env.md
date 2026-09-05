# Probe: Craft Agents environment variables

Evidence for the signals used by `hooks/lib/detect-host.sh`. Captured
2026-09-01 against `craft-agent` 0.10.4 on cyberpower.

This file exists because prose is not evidence. `CRAFT_AGENT_SESSION_ID`,
`CRAFT_AGENT_SESSION_DIR` and `CRAFT_AGENT_WORKSPACE` entered this codebase as
confident assertions about environment state, are read by three live hooks, and
are set by nothing. Every branch behind them has always taken the fallback.

The first revision of this document repeated that mistake — it listed
`CRAFT_SESSION_ID` and `CRAFT_SESSION_NAME` as session variables on the strength
of `grep` counts in `/app`. They are automation template variables and are
absent from a hook's environment. **Counting mentions in source proves only that
the application names a variable; it says nothing about whether it is
exported.** Each entry below therefore records the injection site or the capture
command, not a count.

## Process-wide (server environment, inherited by children)

Eleven variables:

```
$ PID=$(docker inspect craft-agent --format '{{.State.Pid}}')
$ sudo cat /proc/$PID/environ | tr '\0' '\n' | grep -E '^CRAFT_[A-Z_]+=' | sed 's/=.*/=<set>/' | sort
CRAFT_APP_ROOT=<set>
CRAFT_BUNDLED_ASSETS_ROOT=<set>
CRAFT_CLAUDE_OAUTH_TOKEN=<set>
CRAFT_IS_PACKAGED=<set>
CRAFT_RESOURCES_PATH=<set>
CRAFT_RPC_HOST=<set>
CRAFT_RPC_PORT=<set>
CRAFT_SCRIPTS=<set>
CRAFT_SERVER_TOKEN=<set>
CRAFT_UV=<set>
CRAFT_WEBUI_DIR=<set>
```

Values redacted deliberately. `CRAFT_CLAUDE_OAUTH_TOKEN` is a live credential
and is excluded from the detector for that reason — see `electinfo/ops#397`.

## Per-session (injected into the agent subprocess)

**Exactly two**, from the spawn site in `packages/shared/src/agent/pi-agent.ts`:

```js
const child = spawn(nodePath, args, {
  env: {
    ...process.env,
    ...
    // Pass session dir for cross-process toolMetadataStore
    ...(sessionDir ? { CRAFT_SESSION_DIR: sessionDir } : {}),
    // Propagate debug mode
    CRAFT_DEBUG: (...) ? '1' : '0',
  },
});
```

`CRAFT_SESSION_DIR` is a signal. `CRAFT_DEBUG` is not — a developer may set it
anywhere, so it marks nothing about the runtime.

Corroborated by a live consumer in this repository:
`hooks/resolver/skill-enforcement-gate.sh:26` reads `CRAFT_SESSION_DIR` and
resolves `$CRAFT_SESSION_DIR/session.jsonl` beneath it.

Note `SessionManager.ts` also assigns `process.env.CRAFT_SESSION_DIR` on the
server process itself, so it can appear in the daemon environment as well as the
child's. Either way its presence means Craft.

## Deliberately NOT signals

| Name | Why not |
|---|---|
| `CRAFT_SESSION_ID` | Automation template variable, built in `automations/utils.ts` from `payload.sessionId`. Documented in `resources/docs/automations.md:226`. Not in a hook's environment. |
| `CRAFT_SESSION_NAME` | Same origin (`automations.md:227`), and derived from a **user-typed session label**. Anything could set it and be reported as craft. |
| `CRAFT_DEBUG` | Injected per-session, but it is a debug flag rather than a runtime marker. |
| `CRAFT_CLAUDE_OAUTH_TOKEN` | A credential. Reading it to answer this question would only spread it. |

## Claude Code

```
$ env | grep -E '^(CLAUDE|CLAUDECODE)' | sed 's/=.*/=<set>/'
CLAUDE_CODE_ENTRYPOINT=<set>
CLAUDECODE=<set>
CLAUDE_CODE_SESSION_ID=<set>
CLAUDE_CODE_EXECPATH=<set>
```

`CLAUDE_PROJECT_DIR` was unset in the capturing session; it is retained as a
signal because Claude Code sets it when running with a project directory.

## Why Craft is tested first

Craft spawns Claude Code as a child. The child sets `CLAUDECODE` for itself and
inherits the `CRAFT_*` variables, so a hook running under Craft sees both
families. The server environment carries eleven `CRAFT_*` and zero `CLAUDE*`:

```
$ sudo cat /proc/$PID/environ | tr '\0' '\n' | grep -cE '^(CLAUDE|CLAUDECODE)'
0
```

So "both present" means craft, not claude-code.

## Names that are set by nothing

Asserted in code, exported by no runtime. Verified zero occurrences anywhere in
the bundled application:

```
$ for v in CRAFT_AGENT_SESSION_ID CRAFT_AGENT_SESSION_DIR CRAFT_AGENT_WORKSPACE; do
      docker exec craft-agent sh -c "grep -rho '$v' /app | wc -l"; done
0
0
0
```

| Name | Read by |
|---|---|
| `CRAFT_AGENT_SESSION_ID` | `hooks/lib/resolve-think-gate.py` |
| `CRAFT_AGENT_SESSION_DIR` | `hooks/lib/resolve-think-gate.py` |
| `CRAFT_AGENT_WORKSPACE` | `hooks/lib/log-block.sh` |

**Do not generalise this to "the real names carry no `AGENT`"** — an earlier
revision did, and it is false. Craft exports `CRAFT_AGENT_ID` and
`CRAFT_AGENT_TYPE` from `automations/sdk-bridge.ts`:

```js
if (input.agent_id)   env.CRAFT_AGENT_ID = input.agent_id;
if (input.agent_type) env.CRAFT_AGENT_TYPE = input.agent_type;
```

The narrow claim — those three specific names are set by nothing — holds. The
categorical one does not.

## Refreshing this capture

Re-run after any Craft upgrade; the version is in `/app/package.json`.

```bash
PID=$(docker inspect craft-agent --format '{{.State.Pid}}')
sudo cat /proc/$PID/environ | tr '\0' '\n' | grep -E '^CRAFT_[A-Z_]+=' | sed 's/=.*/=<set>/' | sort
docker exec craft-agent sh -c "grep -rhoE 'CRAFT_SESSION_DIR: sessionDir.{0,40}' /app"
```
