<!--
Infra-ticket body template. Rendered by scripts/probe/_common.sh (#662)
via plain sed substitution when a test tool is missing on a shared
machine and cannot be installed by the running agent.

Placeholders (all required, plain string substitution):
  {tool}                canonical tool name (e.g. pytest, playwright, k6)
  {version_requested}   requested version or "any"
  {install_commands}    shell one-liner or multi-line block
  {blocking_tickets}    comma-separated GitHub issue refs (e.g. "#656, #660")
  {layer}               architectural layer (backend / frontend / e2e / performance / ...)
  {repo}                repo basename
  {requester_session}   originating agent session id (or "unknown-session")
-->
## Tool install request: {tool}

**Blocking:** {blocking_tickets} (each cannot execute its automation until {tool} is available).
**Layer:** {layer}
**Repo:** {repo}
**Requested version:** {version_requested}
**Requester session:** {requester_session}

### Suggested install commands

```bash
{install_commands}
```

### Verification

Once installed, run on the shared machine to confirm:

```bash
command -v {tool}
```

Both should return a path. If not, install did not land on this shell's `PATH`; check the target user account and re-shim as needed.

### Notes for the installer

- The blocking tickets above will retry their automation stubs automatically once `{tool}` is available; no re-triggering needed unless the tickets are stale (> 30 days).
- If `{tool}` is intentionally not being installed on this machine (policy decision), close this ticket with a comment naming the alternative tool or the exemption reason so `PROJECT.md`'s `assertion_tools` and `writing-tests:7`-bearing tickets can be updated accordingly.

<!-- Part-of epic #655; template landed via #663; renderer in #662 (scripts/probe/_common.sh). -->
