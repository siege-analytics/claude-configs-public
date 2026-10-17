# #1004 coherent package generations

Pre-mortem-artifact: this document, Failure analysis
Hostile-review-artifact: this document, Peer review (independent review pending)

## Assumptions

The generation store is operator-owned artifact state, not an authorization
service. The release manifest is explicitly pinned, the source/consumer commits
are exact, and all candidate source is read as data. Existing host registration
remains authoritative. A live Craft workspace is not used as a test fixture.

## Failure analysis

- Independently updated skills/settings/runtime expose mixed versions: keep one
  complete generation and resolve its immutable path once per operation.
- A bad archive, copied hook or policy digest looks verified: reuse the existing
  handoff/resolver/composer and verify all hashes before selection.
- Ambient checkout files shadow declared customization: read exact Git objects
  and explicit preserved namespaces; reject unapproved managed-path collisions.
- A failed stage or selection damages the previous install: stage privately,
  retain the previous generation, then replace one selection record under a lock.
- Rollback resurrects approval: retain content but issue a new selection epoch;
  never copy task/operation receipts into the generation.
- Active payload damage prevents recovery: mark the broken set's observations
  unknown and permit recovery only to the completely verified previous set.
- A new tool silently reinterprets an old generation: record exact composer and
  resolver dependency hashes and reject unsupported version/schema combinations.
- Artifact verification is mistaken for host proof: keep authorization effect
  none and require separate #1002/#1003 evidence before runtime claims.

## Peer review

Independent review pending. The accepted #1002 operation adapter is integrated
from develop `73fb88da02b3915b72e2a3082126754dc4d611c2`. Its hosted activation
remains incomplete: the subsequent-head probe in #1019 ran the default branch's
old workflow without the new adapter. These local transition tests cannot
establish provider execution. The existing coordinator owns that repair.
No additional worker or alternate workflow policy engine is introduced here.

## Lead review

This is an explicit generation-store mode. The existing in-place production
installer is not used to demonstrate atomicity. Host registration, cached context
and live authority switching remain separately visible acceptance boundaries.

## Quantified claims

Real-build transition suite: 18 scenarios pass in 101.771 seconds, using two
complete builds and four exact release output/archive forms per build. The
accepted adapter replays four Git cases across initial selection, upgrade and
rollback: valid ticketed integration allows; wrong feature target, missing ticket
and changed installed guidance deny. The restored generation receives epoch 3.
The damaged-active recovery case also passes. Log:
`/tmp/cc-1004-adapter-recovery-focused.log`.

At the earlier `28c4690` checkpoint, full repository validation passed
82/82 commands in 457.0 seconds, including Python modules, 36 hook suites,
two workflow suites, generated freshness and all package hook validators. The
transition test also validates scoped ontology bindings against a real generated
manifest. Logs: `/tmp/cc-1004-full-validation.log` and
`/tmp/cc-1004-focused-batch.log` (the earlier 12-case checkpoint).
Fresh full validation of this integrated recovery checkpoint and independent
review remain pending. No final acceptance or ticket closure is claimed.

## Canary and rollback

All builds, consumer repositories, generation stores and failures are disposable.
Test preserved project replacement/extension/resident behavior, nested operator
skills/settings, exact compatibility hooks, interrupted staging/selection, drift,
wrong releases, stale epochs and coherent rollback. Re-run the same operation
corpus against both generations and the accepted #1002 Git boundary before merge.
