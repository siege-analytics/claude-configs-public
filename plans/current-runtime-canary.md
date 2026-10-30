# Runtime recovery follow-up  -  #1003

## Assumptions

The operator approved the recorded remediation plan and requested completion. Existing valid host/task compatibility must survive; protected mutations remain fail closed.

Pre-mortem-artifact: plans/current-runtime-canary.md
Hostile-review-artifact: plans/hostile-review-current-runtime-canary.md

## Design

Move installed version/digest values from validator constants into the immutable run manifest. Retain exact package identities, schema fields, absolute paths, SHA256 validation, adapter markers and runtime discovery checks. Changing a run changes its approval subject. Add non-authorizing read-only capture-runtime-pins for installed public app artifacts; never auto-update an approval or relabel historical evidence.

Alternatives: retain historical constants/generic fallback (reproduces the defects), or add a separate workflow engine (duplicates authority). This change repairs the existing boundary.

## Pre-mortem

Schema or identity tightening can reject legitimate runtimes. Preserve explicit compatibility controls and give rerun/repair diagnostics; do not fabricate host evidence. Generated pins/catalogs must match authored bytes. Keep live root clone on clean main and install only reviewed exact remote main.

## Peer review

Independent exact-source review requested; no acceptance claimed yet.

## Lead review

Source boundary and failure behavior inspected; no active deployment from this branch.

## Quantified claims

Fifteen canary packet tests passed before capture helper; final rerun pending. Actual current app capture succeeds with no authority effect. Backend live evidence remains separately required.

## Test plan

Run targeted positive/negative regressions, full generated freshness and relevant hook/packet suites, then required CI and exact-head independent review. Rollback uses the prior reviewed package and retained managed-file backup; preserve session data and evidence.

Independent exact-source review approved351b9ba; all15 packet tests independently pass20.404s. Current installed public artifact capture confirms Craft0.15.6/SDK0.3.302 with authorization_effect none. This is not live Pi enforcement.
