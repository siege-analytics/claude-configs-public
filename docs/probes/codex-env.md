# Probe: Codex CLI environment variables

Evidence for the `codex-cli` signals used by `hooks/lib/detect-host.sh`
(added #882, this doc #892).

This file follows the same discipline as `craft-env.md`: prose is not evidence.
An environment variable is a valid detector signal only if it is shown to be
**exported into the process a hook runs in** -- an injection site in source, or
a capture from a live process. Counting mentions proves only that the tool names
a variable, not that it is set.

## Status: UNVERIFIED against a live capture

The two markers currently in `detect-host.sh`:

```
CODEX_SANDBOX
CODEX_SANDBOX_NETWORK_DISABLED
```

were selected from the OpenAI Codex CLI's documented sandbox behavior, NOT from a
`/proc/<pid>/environ` capture of a running Codex tool subprocess. They are the
sandbox-policy variables the CLI is documented to export into the command it
runs (`CODEX_SANDBOX=seatbelt` on macOS Seatbelt / `linux-landlock` on Linux;
`CODEX_SANDBOX_NETWORK_DISABLED=1` under the default network-off policy).

**They must be confirmed by capture before they are trusted as load-bearing.**
Until then, treat `codex-cli` detection as best-effort: a false negative degrades
to `unknown` (least-capable host), which is safe. A false positive would require
one of these names to be exported by a non-Codex runtime, which is unlikely for
the `CODEX_` prefix but is not proven here.

## How to capture (to be run in a real Codex CLI session)

From inside a Codex CLI tool invocation, dump the environment and record which
`CODEX_` names are present:

```
$ env | grep -E '^CODEX_[A-Z_]+=' | sed 's/=.*/=<set>/' | sort
```

Paste the result here (values redacted), with the Codex CLI version and OS, and
change the status above to "verified <date> against codex <version> on <os>".
If a name in `detect-host.sh` is absent from the capture, remove it from the
detector; if additional stable `CODEX_` markers appear, add them.

## Why detection order puts codex after craft

`detect-host.sh` tests craft first, then codex, then claude-code. The ordering is
defensive: if a future host spawns Codex as a child (as Craft spawns Claude
Code), the parent's markers should win. Codex and Craft/Claude markers are
disjoint prefixes today, so the order only matters for that hypothetical.
