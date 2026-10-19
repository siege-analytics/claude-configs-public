---
ticket_refs:
  - siege-analytics/claude-configs-public#1064: findings and dispositions summarized in the PR
---

# Hostile review: #1064 single-process injector

Reviewer: an adversarial pass the implementer commissioned over the staged v1 diff. The reviewer was isolated and read-only, and ran its probes on full tree copies of base `4d6fbd2` and the change. This is not the independent PR review.

Method:
- 36 adversarial payloads, each run through both hooks in `on`, `canary`, `kernel-only` and `off` modes from the same cwd, with `CRAFT_AGENT_PLANS_PATH=/nonexistent`.
- Before diffing, each tree's root path in the output was replaced with a placeholder.

## Checked and found not defective

- **JSON shape:** non-dict JSON, null, empty stdin, garbage, NaN, a trailing-data payload and duplicate keys.
- **Prompt values:** a prompt that is a dict, list, bool or float. A falsy prompt (`0`, `false`, `[]`) falling back to `tool_input.prompt`. `tool_input` given as a string.
- **Cwd values:** an int, a relative path, a symlink, trailing `\n` or `\r`, and an embedded NUL.
- **Prompt text:** leading-dash prompts containing spaces, CRLF, unicode and emoji, and `LC_ALL=C`/`POSIX`.
- **`PWD`:** unset, stale in both directions, bogus or relative. Bash fixes up and exports `PWD`, so the selector sees the same value the shell used.
- **Modes:** `kernel-only` and `off`. A deleted cwd gives `error` in both versions.
- **Callers:** no other tracked file reads `PROMPT` or `PROMPT_CWD`. The packaged forms ship the hook and the selector together (`bin/build.py:1520`).
- **Timing:** 3 rounds of 10 runs at load average about 22. Old took 346–355 ms per prompt and new 152–161 ms. In `off` mode, time fell from 208 ms to 13 ms.

## Findings and dispositions

1. **Minor, fixed.** Invalid UTF-8 anywhere in the payload produced `state: error`, where the old path fell back gracefully to `state: unknown`. `sys.stdin.read()` decoded before `payload_fields()` ran.
   - Fix: read `sys.stdin.buffer` and decode strictly inside each field's fallback. A strict UTF-8 decode, not `json.loads(bytes)`, which would accept a BOM that the old text-mode parse rejected.
   - Re-verified: bad UTF-8 in an unrelated field, bad UTF-8 in the prompt, and a leading BOM all give `state: unknown` in both versions (corpus cases 21–23).
2. **Minor, accepted and documented.** Three inputs the old path rejected now route normally:
   - a prompt of exactly `--help` (argparse rejected `--prompt --help`);
   - a lone surrogate (`print()` raised);
   - a prompt over 128 KiB (the argument limit).

   All are improvements. The CHANGELOG now scopes "byte-identical" to the corpus and lists them.
3. **Nit, accepted and documented.** A NUL byte in a prompt is now kept. Bash command substitution used to drop it.
4. **Minor, fixed in part; follow-up proposed.** The 10,000-byte ceiling was exercised only on a 2-load prompt.
   - The test now also asserts on the largest multi-route selection the metrics tool tracks: 8 loads, 9,874 B at a 106-character root in this worktree.
   - `bin/progressive-loading-metrics.py` uses the same 10,000 ceiling.
   - The message now says bytes.
   - Remaining risk: every load line embeds the absolute install path, and the metric normalises it away. The real worst case is about 9.5–9.9 KB depending on the root, and the pipeline-status block appended when plan files exist is extra. Proposed follow-up: make load paths root-relative, or add the root length to the budget.
5. **Nit, fixed.**
   - The process-count test no longer aborts without a summary line when no python3 starts.
   - `--payload-stdin` overriding `--prompt` and `--cwd` is now stated in its help text.

## Verdict

The reviewer's verdict was: approve with fixes. Findings 1 and 5 are fixed, and finding 4 is fixed in part, with a follow-up. Findings 2 and 3 are documented.
