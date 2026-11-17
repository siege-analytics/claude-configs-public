## Assumptions

SQL used in conventionally identified test files is test setup, not production transformation work. Task scope, ordinary test evidence, review requirements and real operational holds still apply.

## Test plan

Actual JSON and raw native fallback invocations of self-review.sh reproduce the original inherited SQL fixture refusal. Test-path controls must pass without production probe trailers; production SQL, template and write-code changes, including mixed test/production commits, must still be refused without real evidence. Filenames containing spaces remain intact.

## Findings

The transformation predicate searched whole changed files, so inherited in-memory fixture SQL imposed production pipeline ceremony. The predicate now excludes conventional test paths before checking production filenames and contents. Other publication predicates are unchanged. This is not a change to the separate pre-push range-review helper or a claim that it enforces transformation probes.

## Independent review

The reviewer found a test-like parent directory could hide production files; filename checks now use only the basename. Actual independent production refusals and test-file admissions passed on the corrected source. Accepted review: https://github.com/siege-analytics/claude-configs-public/issues/1413#issuecomment-6874966771 . Genuine focused tests and the complete staged scan passed; no live installation or original-owner retry is claimed.
