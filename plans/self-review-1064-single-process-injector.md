---
ticket_refs:
  - siege-analytics/claude-configs-public#1064: inject-resolver.sh runs python3 three times per prompt
---

# Self-review: #1064 single-process injector

## Assumptions

Pre-author-inventory: before any edit, the injected output of base `4d6fbd2` was captured for a corpus of 20 payloads in `on` and `canary` modes. That baseline is the equivalence oracle. The timing came from the same host before authoring: v3.5.63 at 14–16 ms against v3.5.66 at 355–379 ms per prompt (#1064 body).
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1064
Pre-mortem-artifact: plans/pre-mortem-1064-single-process-injector.md
Hostile-review-artifact: plans/hostile-review-1064-single-process-injector.md
Project-contribution: every consumer of the progressive loader pays about 200 ms less on each prompt, with no change in what gets selected. The size gates now match what the host actually delivers whole, so CI can no longer pass an injection the model only sees as a 2 KB preview.

- **Interpreter startup:** it dominates the hook's cost. Bare `python3 -c pass` takes 77–100 ms on the measuring host, and the selector takes 134–144 ms in total. So removing two of the three interpreters is the available win. A precomputed load set is not possible, because selection depends on the prompt.
- **`$PWD` fallback:** bash exports `PWD`, so the selector's `os.environ["PWD"]` is the value the shell's `$PWD` fallback used. The hostile review checked this, including unset, stale and relative `PWD`.
- **Inline limit:** about 10 KB, measured empirically on Claude Code 2.1.302. Hook outputs of 8,000, 9,500, 9,990 and 10,010 B were delivered whole; 10,200 and 10,500 B were not. Other host versions or SDKs may differ. Not verified.

## Peer review

Shelf checks:
- **writing-code:** the payload parse cannot raise. Each field has its own `try` that falls back to `""`, and the decode is strict UTF-8 inside it. The existing `|| true` and `state: error` paths in the hook are unchanged.
- **writing-tests:** the process-count test was run against the base hook and fails there ("hook started 3 python3 processes"), so it discriminates. The size test now uses the largest tracked selection instead of an easy one.
- **writing-claims:** every number below was observed in this work cycle, and the host load is stated wherever timing is quoted.

Gate evidence on the staged head, with PyYAML 6.0.3 from `requirements-validation.txt` on CPython 3.11:
- `build.py` exit 0, and `build.py --check` complete.
- The CI "Deterministic progressive loading" step:
  - `resolve_load_set_test`, `billing_diagnostic_test`, `progressive_mount_test`, `consumer_runtime_test` and `language_scope_test`: PASS.
  - `progressive_loading.test.sh`: 20 passed, 0 failed.
  - `progressive-loading-metrics.py --check`: current.
- Also passing: `generated-source-authority.py --check`, `generated_source_authority_test`, `kernel_budget_test`, `kernel-budget.py --check`, `package_selection_test`, `selected_registration_test`, `sync-skill-references.py --check` and `review_risk_test`.

## Lead review

- **Does this solve the ticket?** Yes. The hook starts one interpreter per prompt, which the test asserts. Measured time fell from about 350 ms to about 155 ms on the same host.
- **The ticket's 50 ms target:** the target of "within about 50 ms of v3.5.63" is not reachable while selection runs in Python. One interpreter alone is 80–100 ms on this host. This is stated rather than claimed.
- **Class, not instance:** the size ceiling was wrong in two places, the test and the metrics tool. Both now use the measured limit.
- **Scope held:**
  - The selector's per-prompt `git remote get-url` call is unchanged.
  - The root-relative load paths needed for real size headroom are proposed as a follow-up, not done here.

## Findings

See `plans/hostile-review-1064-single-process-injector.md`.
- Finding 1 (invalid UTF-8) and finding 5 are fixed.
- Finding 4 is fixed in part, with a follow-up.
- Findings 2 and 3 are documented behaviour changes, all of them improvements or harmless.

## Quantified claims

- **Equivalence:** 23 payloads × 2 modes = **46** outputs are byte-identical to base `4d6fbd2`, with root paths normalised. Verified with `cmp` over a corpus whose base outputs came from `git archive 4d6fbd2`.
  - Base `state:` values: 22 matched, 2 over-budget and 16 unknown in the first 40; the three later cases are unknown.
  - One case loads a project overlay.
- **Behaviour changes, each reproduced:**
  - a 200 KB prompt: base `state: error`, head `state: matched`;
  - `--help` as the prompt and a lone surrogate, reported by the hostile review.
- **Process count:** **1** python3 per prompt on head and **3** on base, by the PATH-shim test.
- **Timing at load average 22–24:**
  - base 339–373 ms against head 157–227 ms (5 runs each);
  - the hostile review measured 346–355 ms against 152–161 ms (3 rounds of 10).
- **Size:**
  - the test's Python case is 8,450 B;
  - the largest multi-route selection is 9,874 B at a 106-character root, estimated 9,514 B at the GitHub runner root;
  - the metrics tool's normalised maximum is 9,179 characters.
