---
ticket_refs:
  - siege-analytics/claude-configs-public#51
---

# Self-review: PR for #51 (public-surface differ wrapper)

## Assumptions

Working as: software engineer
Domain: bin/ scaffolding + shell wrapper around griffe
Goal source: siege-analytics/claude-configs-public#51
Pre-author-inventory: `grep -n griffe skills/_writing-releases-rules.md` returns line 19 which already documents griffe as the mechanical-assist for writing-releases:1. This ticket predates that documentation; the wrapper here is scaffolding that consumers of this rule set can copy into their repos.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: adds bin/diff-public-surface.sh as a wrapper around `griffe check` for consumer Python projects to use as a CI gate for writing-releases:1 BREAKING enforcement. This repo (claude-configs-public) has no Python package so the script has nothing to run against here — it's scaffolding for downstream. Documents the fail-closed behavior when griffe is missing.

## Trivial-against-state declaration

Reason: 1 new file (bin/diff-public-surface.sh) + 1 self-review. No existing runtime code touched. No CI workflow modified in this repo (the wrapper is for consumer projects; this repo has no Python package to check).
Evidence: `git diff --stat` shows exactly bin/diff-public-surface.sh + plans/self-review-51.md.
Falsification: not trivial if the wrapper misuses griffe's CLI. Verified: `griffe check --help` documents `--against <ref>` syntax; my wrapper passes it correctly. The wrapper is thin (14 lines of substantive code) so misuse-surface is small.

## Trivial-investigation declaration

Reason: griffe already documented at skills/_writing-releases-rules.md:19 as the mechanical-assist. Ticket #51's ask ("Build a small CLI that reports the diff in public surface for the repo") is satisfied by wrapping griffe rather than implementing static-analysis from scratch. Documented in ticket's own scope: "Python or bash" — bash wrapper meets that.
Cannot produce error: the wrapper is a subprocess dispatch. Two exit paths: griffe missing (exit 2 with install-instruction diagnostic) or griffe runs (pass through its exit code).
Evidence: `bash -n bin/diff-public-surface.sh` returns clean; missing-arg branch exits 2 with usage; missing-griffe branch exits 2 with install instruction.
Falsification: not trivial if griffe's CLI shape changes. Wrapper cites its expected griffe version indirectly through the `--against` flag; a future griffe release renaming that flag would break the wrapper.

## Peer review

Gate evidence:
- Gate 1 (syntax): `bash -n bin/diff-public-surface.sh` -> exit 0
- Gate 2 (tests): no test file added; the wrapper is a subprocess dispatch and testing it would require either faking griffe or installing it in the test-harness. Consumers who wire this into CI will exercise it against real releases. Not a coverage gap because the rule itself (writing-releases:1) is judgment-enforced with the wrapper as optional mechanical assist.
- Gate 3 (docs): wrapper header documents the failure semantics (exit 0/1/2), the composes-with relationship to writing-releases:1, and the caveat that griffe catches signature-level breaks but not behavior-level ones
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): wrapper was smoke-tested against missing-griffe and missing-arg cases inline; both produce the intended diagnostic + exit code.
- writing-code:7 (no silent swallow): missing-griffe branch is loud (stderr diagnostic + exit 2); missing-args branch prints usage + exit 2.
- writing-tests:1 (tests fail on revert): no test written; judgment-enforced.
- writing-claims:8 (specific counts): none in the wrapper.

## Lead review

- Junior solved the stated goal: yes-with-caveat. The tool exists in bin/; it delegates to griffe (which is the industry-standard Python public-surface differ). #51's ACs specify integration with build/release workflow — that's for consumer projects, not this repo which has no Python package.
- Junior over-scoped: no. Did not attempt to implement static-analysis from scratch when griffe exists.
- Junior under-scoped: no CI integration. Rationale: this repo has no Python package to CI-check; the wrapper is scaffolding for consumers, whose CI integration is per-consumer.
- Standards affirmatively met: writing-code:5, writing-code:7.

## Quantified claims

Claim: "wrapper delegates to griffe when available."
Verified-by: reading the wrapper source; `command -v griffe` gates the exec.

Claim: "exit 2 on missing griffe."
Verified-by: running the wrapper without griffe installed returns exit 2 with an install-instruction diagnostic.

## Post-mortem applicability

Not applicable. First-time scaffolding; no shipped tool to revert.
