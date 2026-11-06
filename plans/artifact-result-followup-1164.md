# Artifact-local results and empty review diagnostics

Goal source: siege-analytics/claude-configs-public#1164 and #1168. Root authorized this isolated follow-up before code after exact-head independent review found the residuals. Base is immutable canonical author commit c2d8c77f5c812328a450b688bd3d7848c8685ae1; its branch/worktree/history are preserved.

## Investigation and design

Readable body-file reproduction: a Junior/Senior Review with its ticket and "Review completed: no blocking findings" is denied because artifact_claims counts completed as lane completion and demands owner/merge/rollout evidence. Canonical Senior checklist completion has the same circular requirement. Real "Deployment completed" and "Release shipped to production" correctly deny.

Inside the existing marked comment-only artifact lane, remove only explicit completed-artifact/check subject phrases from completion-token analysis: review, investigation, fact sheet, audit, checklist and checks (optionally named/listed/adversarial) with optional is/are/was/were/has been/have been and complete/completed/done. Scan remaining clauses and tokens normally. Thus "Review complete; deployment complete" and "named checks done; project ready" still deny. Leave state-changing actions, actual evidence requirements, hypothetical-field handling and all nonartifact behavior untouched. This is bounded phrase handling, not general natural-language classification or an owner-approval waiver.

The commit-msg aggregation currently recognizes empty Self-Review and Self-Review-Source by presence and omits them from the missing list; native push already requires nonempty values. Apply that existing nonempty rule to these two fields at commit time, without adding fields. Test three empty/missing values in one diagnostic, a completed valid message and Tier A behavior.

## Pre-mortem and verification

Tiger: stripping an entire line could launder a deployment clause. Replace only the bounded matching phrase, then scan remaining text; actual mixed-claim and deployment negatives must deny. Tiger: treating artifact completion as operator signoff recreates the circular prerequisite. Canonical Junior/Senior readable body-file positives must pass without false N/A footers. Tiger: changing trailer policy rather than diagnostics adds friction. Preserve existing Tier A/B/C fields and exemptions; require only their already-required nonempty values.

Red-first focused hook cases, current parent coordinator/trailer suites, syntax and validator checks, native content-bound test receipts and exact-head protected CI. Root owns independent final review, integration and activation. No global settings, installs or protected merges in this lane.

Pre-mortem-artifact: plans/artifact-result-followup-1164.md#pre-mortem-and-verification
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1164
