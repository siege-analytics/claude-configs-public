---
ticket_refs:
  - siege-analytics/claude-configs-public#1064: inject-resolver.sh runs python3 three times per prompt
---

## Pre-Mortem

Task: have `bin/resolve-load-set.py` read `prompt` and `cwd` from the hook payload (`--payload-stdin`), so that `hooks/resolver/inject-resolver.sh` starts one interpreter per prompt instead of three.
Ticket: siege-analytics/claude-configs-public#1064

Imagine the change shipped and went wrong. These are the ways it could have.

### Tigers

#### Tiger 1: Different selection for some payloads

The two removed parsers had particular semantics:
- they printed via `print()`;
- shell command substitution then stripped trailing newlines;
- each field failed independently to `""`;
- a missing or non-directory `cwd` fell back to the shell's `$PWD`.

If `payload_fields()` diverges from any of these, some prompts load a different skill set, with no error.

Mitigation:
- `payload_fields()` reproduces each rule explicitly: `str()`, `rstrip("\n")`, a per-field `try`, and a `PWD` fallback, then `os.getcwd()`.
- The injected output was captured from base `4d6fbd2` before any edit, for a 20-payload corpus in both `on` and `canary` modes. Three cases were added after the hostile review (bad UTF-8 in a field, bad UTF-8 in the prompt, a leading BOM), giving 23. The payloads cover generic, Python, `tool_input.prompt`, missing, null, numeric and empty prompts, non-JSON, empty stdin, a JSON array, `tool_input` as a string, a non-existent cwd, a file as cwd, a missing cwd, a git repo with a project overlay, special characters and unicode, a leading dash, trailing newlines, and an over-budget explicit selection.
- After the change, all 46 outputs are byte-identical, with root paths normalised.
- An independent hostile review probes further cases (see the hostile-review artifact).

#### Tiger 2: The payload parse escapes the selector's error handling

The parse runs before `main()`'s `try` block. An exception there would produce a traceback and empty output.

Mitigation:
- `payload_fields()` reads bytes and catches every exception per field, including the UTF-8 decode. That case was found by the hostile review and fixed.
- `Path.is_dir()` returns `False` instead of raising on invalid paths, including NUL bytes, on Python 3.8 and later.
- The hook still applies `|| true` and the `state: error` fallback when the result is empty.

#### Tiger 3: The size ceiling breaks CI for legitimate selections

The test's ceiling drops from 12,000 to 10,000 characters.

Mitigation:
- The largest tracked selection (multi-route, 8 loads) is 9,874 B at this worktree's 106-character root, and about 9.5–9.6 KB at typical install roots. The margin is thin, so a follow-up is proposed.
- The ceiling exists because output over about 10 KB is not delivered whole: measured on Claude Code 2.1.302, 10,010 B inlined and 10,200 B did not.
- A selection that exceeds it is a real defect the test should catch, not a false failure.

#### Tiger 4: The process-count test is fragile

The test puts a `python3` shim on `PATH`.

Mitigation:
- The hook does not reset `PATH`, and the shim `exec`s the real interpreter.
- Run against the base hook, the test fails with "started 3 python3 processes", so it discriminates.

### Paper Tigers

#### Paper Tiger 1: Other callers of `--prompt`/`--cwd` break

`--payload-stdin` is additive. `bin/build.py` and `bin/progressive-loading-metrics.py` keep using `--prompt`/`--repo` unchanged, and `PROMPT_CWD` has no other tracked users (`git grep`).

### Elephants

#### Elephant 1: Python startup is still the floor

One interpreter costs about 80–100 ms on the measuring host, under load. This change removes two of the three, not the floor. The selector also still runs `git remote get-url` per prompt.

#### Elephant 2: Prompts over the argv limit now select instead of erroring

The old path passed the prompt as a command-line argument. A prompt over Linux's per-argument limit (128 KiB) made the exec fail, which produced `state: error`, kernel only. The new path reads it from stdin and selects normally. This is a behaviour change, and an improvement, outside the byte-identical corpus.

### Launch-Blocking Assessment

None of the above blocks the change, provided the corpus equivalence and the CI "Deterministic progressive loading" step hold on the head commit.
