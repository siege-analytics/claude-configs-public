## Assumptions
The assigned config repair includes removing unnecessary mutation gates. Git reference-name validation and symbolic-ref inspection are reads. Admit those forms without authorizing actual ref writes, changing shell/global-option policy or requiring a Task just to inspect the branch. Synthetic real-Git fixtures use isolated repositories; no user remotes execute.

## Test plan
Reference validation reproduced six gate refusals before its one-entry correction. Symbolic-ref inspection separately reproduced five gate refusals before its bounded one-ref grammar. The final actual-hook regression pair passed in 4.335s. The genuine content-bound producer then ran all 22 reader-safety tests in 51.632s with no skips and the complete read allowlist: 356 passed, zero failed. Valid and invalid names execute through Git; refs/config and HEAD remain unchanged. Writer, delete, reason-message, two-ref and compound-write controls remain denied. Build, generated source authority and risk metrics checks passed.

## Findings
`check-ref-format` joins GIT_READ. `symbolic-ref` is not added wholesale: its reader grammar accepts one nonempty non-option ref plus quiet/short/recurse flags and the option terminator. Actual branch creation, ref changes and chains that write still require their owning Task. The source scanner remains NONCLEAN if it reports the existing two fail-closed GH parse handlers and aggregate test-discovery finding; those handlers return False and no GH caller changed. Maintained reader suites exist; individual coverage of every exception class is not claimed. No source release, installation or old-session unblock is claimed.

## Independent review
A separate reviewer inspected the final two-file production/test change and accepted its bounded authority and preserved mutation denials. It independently ran the symbolic-ref method: one passed in 3.670s, real HEAD unchanged. The unchanged fail-closed handlers and existing aggregate discovery limitation were reviewed in their actual caller context; none grants read authority on parse failure. The final metadata record does not substitute for the actual test receipt, normal publication checks or required CI.
