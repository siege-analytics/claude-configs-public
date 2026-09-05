---
name: tool-availability-probe
description: "Probe whether a named test tool is installed in the target environment before a ticket-scaffold hook renders a stub against it. On absent, attempt install per project policy; on failure, file an infra ticket while still permitting the stub to land so it becomes runnable the moment the tool arrives. Consumed by hooks/create-ticket/scaffold-test-stub.sh (#661); pairs with skills/testing-frameworks (which declares the tools) and rule writing-tests:7 (which mandates the tool be declared)."
allowed-tools: Read Grep Glob Bash
---

# Tool Availability Probe

This skill answers: **is the tool this ticket's AC names actually installed here, and if not, what happens next?**

Part of epic #655 (falsifiable acceptance criteria + auto-gen test stubs). Called by the scaffold hook (`hooks/create-ticket/scaffold-test-stub.sh`, #661) before it renders a stub. Also runnable manually to diagnose environment gaps.

## Why this exists

Rule `writing-tests:7` requires every acceptance criterion to name a `Falsifiable-by:` observable and a test tool drawn from the touched layer's `assertion_tools` in `PROJECT.md`. If the tool isn't installed, the AC cannot be verified and the ticket is deferred waiting on infra rather than sitting green with false coverage. The probe closes the gap: check before render, install where allowed, file an infra ticket where blocked, and always render the stub so no work is lost.

## Protocol

Per invocation (one tool at a time):

1. **Check presence.** `command -v <bin>` OR `python3 -c "import <module>"` OR `npx --no-install <cli> --version`. If any succeeds, the tool is present.
2. **Present:** emit `{"status": "installed", "tool": "<name>", "version": "<v>"}` on stdout; exit 0.
3. **Absent:** resolve `tool_install_policy` from `PROJECT.md` at the target repo root. Values: `allow`, `prompt`, `block`. Env `TOOL_INSTALL_POLICY` overrides. Default `block`.
4. **`allow`:** run the tool's install command. On success, re-probe; emit `{"status": "installed-just-now", ...}` and exit 0. On failure, fall through to step 5.
5. **`block` (or install failed):** render the infra-ticket body from `templates/infra-ticket-tool-install.md` (#663), file via `gh issue create --label task`, emit `{"status": "blocked-on-infra", "tool": "<name>", "ticket": "<url>"}`, exit 78.

The `prompt` value behaves like `block` unless env `TOOL_INSTALL_YES=1` is set, in which case it behaves like `allow`. This lets a human-in-the-loop caller consent to install per-invocation without changing the repo-wide policy.

## Output schema

Single-line JSON on stdout:

```json
{"status": "installed", "tool": "pytest", "version": "pytest 8.3.3"}
{"status": "installed-just-now", "tool": "playwright", "version": "Version 1.47.0"}
{"status": "blocked-on-infra", "tool": "k6", "ticket": "https://github.com/org/repo/issues/N"}
```

Human-readable status on stderr; exit codes:

| Code | Meaning |
|---|---|
| 0 | installed / installed-just-now |
| 2 | probe prerequisite missing (e.g. no `gh` CLI for infra-ticket filing) |
| 78 | blocked-on-infra (`EX_CONFIG`) |

## Supported tools

Shipped in v1 under `scripts/probe/`:

| Tool | Script | Install command | Layer |
|---|---|---|---|
| pytest | `pytest.sh` | `python3 -m pip install --user pytest` | backend |
| playwright | `playwright.sh` | `npm install -D @playwright/test && npx playwright install --with-deps` | e2e |
| vitest | `vitest.sh` | `npm install -D vitest` | frontend |
| schemathesis | `schemathesis.sh` | `python3 -m pip install --user schemathesis` | api-contract |
| great-expectations | `great-expectations.sh` | `python3 -m pip install --user great-expectations` | data-pipeline |
| k6 | `k6.sh` | Darwin: `brew install k6`; Linux: signed apt repo (see script) | performance |

Adding a new probe: copy the shape of `pytest.sh` (tool with a Python module) or `playwright.sh` (tool with an npx CLI + no direct binary), source `_common.sh`, call `probe_run` with the tool name, binary name, install command, optional module name, layer, and optional blocking-ticket argument.

## Invocation

Directly from a shell:

```bash
scripts/probe/pytest.sh
scripts/probe/playwright.sh 656   # 656 is the blocking ticket
```

From the scaffold hook (#661):

```bash
# hook reads the AC's tool name; dispatches to the matching probe
"$REPO_ROOT/scripts/probe/${tool}.sh" "$ticket_id"
```

The hook interprets exit 78 as "render the stub AND set `Blocked-by:` on the ticket body to the infra ticket URL." Exit 0 means proceed silently.

## Policy: tool_install_policy

Declare in `PROJECT.md` at the repo root:

```yaml
tool_install_policy: block  # default on shared machines
# tool_install_policy: prompt  # ask (via TOOL_INSTALL_YES=1) per invocation
# tool_install_policy: allow  # auto-install on absent
```

Recommended defaults:
- Individual dev laptop: `prompt` (dev consents per invocation).
- Shared build/CI machine: `block` (only Steve/infra installs; agent files a ticket).
- Ephemeral container / GH Actions runner: `allow` (install fresh each run).

Env `TOOL_INSTALL_POLICY` overrides for one-off cases.

## Cross-references

- `[rule:writing-tests]` writing-tests:7 (#656) — requires the tool be named on ACs; this skill is what verifies it exists.
- `[skill:testing-frameworks]` (#659) — declares the tool set (`assertion_tools` per layer) this skill probes against.
- `templates/tests/` (#660) — the skeletons the scaffold hook renders after this skill returns installed-or-blocked.
- `hooks/create-ticket/scaffold-test-stub.sh` (#661) — the primary consumer.
- `templates/infra-ticket-tool-install.md` (#663) — the body this skill renders when blocked.
- Epic #655.
