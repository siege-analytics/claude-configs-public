# #844 consumer package contracts

Pre-mortem-artifact: this document, Failure analysis
Hostile-review-artifact: this document, Peer review (pending)

## Assumptions

The four generated outputs serve different consumers. A package README must
name its own files and commands; source-only install/deploy tooling must remain
an explicit external dependency. Extracting files is not host registration.

## Failure analysis

- A copied source README promises absent tools: generate output-specific README
  and contribution links after all output contents have been assembled.
- A future builder drops an advertised file: fail generation and the copied
  artifact link test instead of leaving a plausible but broken instruction.
- A command only works on a developer checkout: run each advertised command
  from a copied package with no Git checkout, an empty child-process home and
  no source-specific environment variables.
- The old bundle banner implies current Craft support: remove the historical
  host claim and describe its source-build compatibility/reference scope.
- Configuration validation is mistaken for enforcement: separate the advertised
  package diagnostics from required host/backend and native registration proof.

## Peer review

Pending exact-head independent review. Existing #962 runtime tests are retained;
#845/#1002/#1003 own registration, protected operations and live host acceptance.

## Lead review

One documentation generator derives output contracts from actual shipped files.
It does not introduce another install registry or change a running workspace.
Source README and source tools remain in the source repository; generated package
contribution links pin that source revision.

## Quantified claims

Initial focused test passed across four copied packages: all local documentation
links exist; all ten advertised commands succeed; all four clean-home prompt
probes use package-local content; removing an advertised resolver catalog fails
validation. Full repository validation: 82/82 commands pass in 381.8 seconds,
including the existing consumer runtime suites, 36 hook suites, two workflow
suites, both builds, source/metric freshness and all hook validators. Evidence:
`/tmp/cc-844-focused.log` and `/tmp/cc-844-full-validation.log`. Independent
exact-head review and hosted checks remain pending.

## Canary and rollback

Disposable copies only. Keep the original runtime tests and package validators;
revert the generator through normal develop review if package contracts regress.
No release publication, installation, settings merge or host registration occurs.
