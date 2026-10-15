# Hostile review: epic #962 F4 enforcement dependency risk

Goal source: GitHub issue #962 finding F4 and PR #958 review 5528052640.

## Reviewer independence

The configured cross-review source was attempted first with OpenAI `o3`, but the provider returned `429 insufficient_quota`; Anthropic and Google credentials were unavailable. That failed attempt is not counted as review evidence. An isolated secondary reviewer then reviewed complete patch packets without conversation context. GitHub Copilot exact-SHA review remains required after the draft PR is opened.

## Review rounds

### Round 1: REJECT

1. High: the dependency list was hand-maintained rather than checked against configured/generated edges.
2. High: the review-risk CI test itself remained below Tier C.
3. Medium: generated-output exclusions were documented but not asserted.

Fixes:

- derive configured entrypoints and shared-helper edges;
- classify `bin/_test/review_risk_test.py` and `hooks/_test/review_risk_policy.test.sh` Tier C;
- assert generated catalogs remain Tier A and unknown/advisory helpers remain Tier B.

### Round 2: REJECT

1. High: graph checks could pass when one caller removed an edge because another caller still named the helper.
2. Medium: generated catalogs lacked real mutation/deletion freshness probes.

Fixes:

- pin caller-specific helper edges and add edge-removal mutations;
- invoke each real checker against modified and deleted temporary catalogs, then require the checked-in catalog to pass.

### Round 3: REJECT

1. High: CI edge removal was a basename replacement tautology.
2. High: helper mutation removed all mentions rather than an exact invocation site.
3. Medium: build-generated entrypoints were inferred from two source string shapes.

Fixes:

- run an isolated build and parse its actual blocking manifest and generated settings;
- recognize exact executable assignment/source/execute/validation sites;
- pin exact CI invocation lines and counts.

### Round 4: REJECT

P2: two identical workflow full-build invocations both mutated only the first occurrence.

Fix: mutate each expected occurrence by index.

### Round 5: REJECT

The indexed mutation still used substring matching, so the plain build command could match the build-check line.

Fix: replace the nth whole-line match, preserving indentation/newline, so the build check and both plain builds are distinct.

### Round 6: ACCEPT

The reviewer verified:

- isolated-build entrypoint parsing from generated manifest/settings;
- exact caller/helper invocation sites and individual removal detection;
- exact CI invocation lines, counts, and per-occurrence removal detection;
- real generated-catalog modification/deletion rejection and positive freshness;
- modification/deletion/rename plus declared-B rejection for every F4-added dependency;
- narrow Tier C additions, executable exclusions, metrics, and documentation.

## Disposition

ACCEPT. No open hostile-review findings remain in the candidate patch.
