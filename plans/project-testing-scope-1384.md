## Assumptions

Address #1384 from develop. A testing declaration belongs to its repository, not every consumer of this library. Preserve existing project identity precedence and bound-task versus unbound native receipt checks.

## Test plan

Reproduce a foreign consumer overlay imposing a receipt requirement. Verify that only the identity-matched overlay requires evidence, root declarations remain enforced, and the maintained receipt and project-resolution controls pass. Declare this repository's own testing policy rather than borrowing Siege Utilities' pytest policy.

## Findings

The original hook scans all consumer descriptors. The foreign-overlay regression fails against that code. The correction reuses project identity selection, exposes its selected descriptor, and checks only that descriptor or the target's root declaration. The guard suite passed seventeen scenarios, project resolution passed five, project-scoped gates passed three, test evidence passed seventeen and the scoped execution lane passed seven. The final genuine producer also passed build, inventory, source authority, risk freshness and all three hook validators. Consumer distributions do not contain the author repository PROJECT.md.

## Independent review

An independent reviewer accepted the identity selection and source-only author declaration. Its controlled missing-resolver comparison found an unintended dependency for repositories with no declarations; the final candidate probe and paired real-hook controls corrected it. The reviewer accepted that correction. A second review found that a failed Git identity read could appear as absent policy. The metadata CLI now distinguishes a real absent origin from process errors/timeouts, preserving the old fallback for existing project-slug callers. Paired actual Git-error and timeout regressions failed before this change and pass afterward; the genuine no-origin case remains allowed. The complete final staged scan reported sixty-five findings. The independent reviewer accepted the unchanged handler contexts and the new explicit metadata-failure exit after inspecting the real failure/timeout regressions. Public final review: https://github.com/siege-analytics/claude-configs-public/issues/1384#issuecomment-6869878161. Required exact-head CI remains outstanding; no installed runtime result is claimed.
