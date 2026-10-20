---
ticket_refs:
  - siege-analytics/claude-configs-public#1097: universal-mutation-gate fails open when it cannot read its own input
---

# Self-review: #1097 universal-mutation-gate fails closed on unreadable input

## Assumptions

Pre-author-inventory: on develop `e4ae6a2`, the final fixture fails 17 of its 27 cases. electinfo's #335 fixture fails the same 5 cases on its develop and on the v3.5.73 assembled tree.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1097
Pre-mortem-artifact: plans/pre-mortem-1097-gate-fail-closed.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1097#issuecomment-6288368865
Project-contribution: the mutation gate can no longer be silenced by breaking its input path or padding the payload. Each Bash call costs one python3 start instead of three. Downstream, electinfo retires its override (electinfo#375), and this keeps #335's protection once the override is gone.

- A real hook payload is always a JSON object. One probe parses it and returns the status, the command, `cwd` and `tool_name`, plus a slim copy for the environment. It replaces the three `extract-json.py` calls and follows their output rules exactly: the same path walk, the same empty rules, `json.dumps` for containers and `str` for scalars, trailing newlines stripped and NULs dropped.
- Empty stdin and `{}` stay allowed, as they were. Whoever controls stdin already controls the command.
- Commands over 64 KiB block. The command is later passed as an argv string, which must stay under the kernel's 128 KiB per-string limit. No legitimate command is that long.
- The exported `CCP_HOOK_INPUT_JSON` is the slim copy: every string over 4 KiB is emptied except `tool_input.command`. Its readers use only session ids, `cwd`, the command and path fields (`hooks/lib/resolve-think-gate.py:113,544,650,808`). None of them read file content.

## Peer review

- **writing-code:** three preconditions, then the probe. Every failure goes through `_fail_closed`, which logs the block (#602), names the cause and exits 2. The probe's status must be exactly `ok`, so a crashed or substituted python3 blocks too.
- **writing-tests:** `universal_mutation_gate_fail_closed.test.sh` has 27 cases:
  - broken inputs: missing, unreadable, syntax-error, empty and directory extractors; no python3 and a no-op python3; non-JSON, truncated and array payloads; a lone-surrogate command; a 70 KB command. Each blocks, and its message is asserted;
  - legitimate inputs: no command field, empty stdin, `{}`, read-only git, and a 140 KiB Write that decides like a 10-byte one;
  - must-blocks: destructive `rm`, an ungated Write into the repository, and the same Write padded past 128 KiB.
- **Mutation:** removing any one of the six defences fails 1 to 4 cases. Those are the extractor check, the python3 check, the status match, the size limit, the unreadable-text status and the slim export.
- **Hostile review:** MERGE-SAFE, with three should-fixes, all fixed here:
  - a broken extractor on a payload that parses still allowed;
  - every payload over 128 KiB hit `E2BIG`, which on develop let a padded command through, and with the first version of this fix blocked large Writes with the wrong message;
  - the python3 check was untested.

  Its NITs are fixed too: a no-op python3 now blocks, the new blocks are logged, and the extractor directory case is covered. Two NITs are accepted. Payloads Claude Code never emits (`tool_input` as a string, `"command": null`) parse as a payload with no command and still exit 0. The unreadable-extractor case is skipped when the suite runs as root.

## Test plan

- `bash hooks/_test/universal_mutation_gate_fail_closed.test.sh`: 27/0 here; 17 failures on develop.
- The corpus replay of 2,845 real commands, develop gate against this one, in two gate states.
- The full CI validate job, run locally.
- Timing: 30 `git status` calls through each gate.

## Lead review

- **Solves #1097:** yes.
- **Out of scope:** the other hooks share the `extract-json.py ... || true` pattern. They should be swept separately.

## Quantified claims

- Corpus replay: 0 of 2,845 commands change exit code, in either gate state.
- Fixture: 27 cases, 17 of which fail on develop. Each of the 6 defences is pinned by at least one case.
- Latency: 163 ms per Bash call on develop, 119 ms here.
