# Git target-state correction

Refs: #1107, #1110

## Goal and review inventory

New inline review4463324623 and both follow-ups in original review5762350995 were read in full. The Major follow-up and new inline finding concern the same effective-directory class. The Minor follow-up concerns hub preflight parsing before the existing input bound. Both are addressed. The fallback prefix/single-kernel nit is covered by stronger assertions; the future scanner global-stem collision nit has no demonstrated current pair and remains deferred under #1135.

## Assumptions

This is literal supplied-code inspection, not arbitrary external-program introspection. One bounded target-state resolver serves ordinary and opaque paths. Supported navigation is a healthy literal absolute cd target on an && chain, including -P, -L, -- and bounded literal command/builtin wrappers. Logical parent traversal, relative/CDPATH uncertainty, unknown operators and unsupported parent-shell mutators carry UNKNOWN. External command/env wrappers cannot prove a parent directory change. Proved reads and data remain separate from unparsed supplied Git code, which cannot borrow foreign payload cwd as scope proof.

CCP_TASK_ID is task-binding metadata, not a target or startup override. It retains normal ticket validation without adding another general environment exception. Other unproved assignments, startup overrides and parent environment transitions remain conservative across groups. A marker before cd applies to that shell command; it is not propagated as Git environment or used as ticket authority.

## Plan and implementation

Reproduce old-source scope failures with owned/foreign disposable repositories. Normalize only the supported literal navigation subset and retain unknown state for failure/control-flow and environment uncertainty. Preserve quoted argv boundaries before recursive opaque inspection. Reject possible literal Git candidates under unknown state; use an explicit tool cwd or Git -C path for unsupported navigation.

Strict-unresolved execution contexts, including unsupported shell startup flags, carry unknown target state rather than borrowing the initial foreign cwd. Recognized shell execution with a parsed foreign Git target retains its normal result.

Bound the hub preflight read to 1 MiB plus one before JSON decoding. Process substitution keeps producer SIGPIPE out of the preflight decision. Oversized input continues to the existing closed metadata rejection path; small malformed input remains advisory. An actual 2 MiB Bash callback tests the full pipeline.

## Pre-mortem

Unconditional directory updates after failed cd or || can donate foreign scope to an owned commit. Ignoring directory-changing wrappers or environment prefixes has the same effect. Quoted prose must remain data, and parsed foreign targets must retain their normal path. A bounded-reader SIGPIPE must not become advisory acceptance. Actual paired controls cover these cases without executing candidate commit commands.

## Peer review

Independent native review accepted the original five frozen inputs at tree 3ca6468e20774b2a2236e70a5a94da17a17a9218. A later startup-context correction changes only the Git helper main function and adds paired callback cases; separate exact-source native peer closure accepted tree 4244b447ab97dc8495876551b9fff90b708c2da3 and its current S01/S02 scanner dispositions. The final focused evidence is reported separately below. Receipts are peer-review-git-target-state-1147.md, peer-review-git-target-scanner-1147.md and peer-review-git-startup-delta-1147.md. These are native independent reviews, not Craft Agents provider approval.

## Lead review

Coordinator adversarial review identified nested and external wrapper distinctions, target/startup environment state and the required task-disambiguation marker. Each became a paired actual-hook control. Final source closure and aggregate evidence remain separate from protected CI, main promotion and installation.

## Quantified claims

The genuine original 20-group producer passed at stable HEAD 977c060 with its original five source hashes, including ticket552, payload11, inline16 and the complete task-keyed77 suite. The late startup-context correction was not tested by that original aggregate. The final delta producer bound the changed Git helper and ticket fixture: nine groups passed (ticket562, reader16, risk, fault controls, commit detector, destructive, fix-shape, self-review and freshness). Its task-binding command failed before execution because the method was selected under Gates instead of Hub. That failed aggregate receipt is retained. A separate genuine producer then ran the correct Hub method successfully in 3.308 seconds, binding both final inputs with stable HEAD. A final short genuine producer then passed ten actual startup-context hook pairs and the correct Hub method (3.083 seconds), binding both final blobs with stable HEAD. This directly exercises the changed main branch. No failed receipt was edited or called successful. The task-keyed77 result remains pre-delta evidence: task_actions imports the changed Git file, although its consumed prefix function and SAFE_ENV are unchanged. Protected CI must rerun the full suite on the final commit. Earlier unsupported foreign-group expectations remain changed-expectation regressions; not every grouped read is supported.

Pre-mortem-artifact: plans/git-target-state-1147.md
Hostile-review-artifact: plans/peer-review-git-target-state-1147.md
Verified-by: bash hooks/_test/ticket_required.test.sh; python3 -B bin/_test/hook_payload_test.py; python3 -B bin/_test/inline_delivery_test.py; cwd-evidence-20261103/before.log, original-20-group-integration.log, delta-integration.log, binding-correction.log and final-focused-integration.log; full review API bodies retained by coordinator.
