# Self-review: shared ontology (#1007)

Pre-mortem-artifact: plans/pre-mortem-1007-ontology.md
Hostile-review-artifact: plans/hostile-review-1007-ontology.md

## Assumptions

The approved scope is vocabulary, relationships, generated wiki documentation,
structured references and CI validation. Runtime policy and permission behavior
remain with the existing work in #851/#848 and #1001–#1005. The initial checked
bindings annotate existing fields without renaming them. Private consumer
evidence is represented only by the sanitized public comparison on #1000.

The wiki Git remote is unavailable. Checked-in wiki pages are reviewable source;
publication to the separate GitHub Wiki remains pending and is not implied.

## Peer review

The other implementer supplied ontology-specific A/B requirements on #1007.
Their [independent review of `3eb0e9a`](https://github.com/siege-analytics/claude-configs-public/pull/1008#issuecomment-6201087559)
required changes because relationship shape validation accepted configuration
and replacement as authorization sources. The bounded allowlist and regressions
address that finding locally; independent review of the replacement head is
pending. Earlier green checks did not establish the missing invariant.

## Lead review

Reviewed the validator's failure paths, the canonical definitions and relationship
endpoints, compatibility mappings, actual resolver/manifest bindings and wiki
generation. A local symlink overwrite issue was corrected with a negative canary.
The independent authority finding is corrected with explicit permitted signatures
at protected endpoints, not a list of forbidden verbs or owner-based permission.
The required canonical terms remain protected after ownership changes; new
authority-owned terms cannot introduce unchecked edges. Ordinary relationships
remain extensible, and invalid authority edges fail before wiki generation.
The CI change adds validation after the existing full build and changes no
publication condition, permissions or runtime registration.

The ontology stays on demand. Its definitions do not enter the resident kernel
or alter selected skill contents. A terminology pass checks reference validity,
the bounded authority relationship invariant, field existence, JSON types and
documentation freshness. It does not prove arbitrary prose or runtime behavior.

## Quantified claims

- 34 canonical terms, 14 relationships and 6 ambiguous/deprecated spellings.
- Two existing structured artifacts, six declared field bindings and 93 matched
  values at this baseline.
- 25 focused tests pass. Seven added tests reproduce the independent finding and
  cover the authority boundary, its bypass attempts and CLI preservation. The
  existing tests cover staleness, field/type failures and the symlink canary.
- Executed the 75-command repository matrix, including 19 Python test files,
  36 hook test files, workflow policy tests, consumer layouts and catalog checks.
  The first run passed 71 commands; four checks reported stale skill-inventory
  evidence after the new test became tracked. Regenerated that inventory and
  reran all four successfully. Its only changes are 41 heuristic test-evidence
  references to the new test file; source definitions and runtime outputs did
  not change. Hosted validation also passed at `3eb0e9a`; that evidence precedes
  the authority correction. The replacement passes all 25 focused tests,
  ontology freshness, build/reference validation and skill-inventory freshness.
  Hosted validation of the replacement will be recorded on the PR.
- The kernel budget remains 6,995 characters; the ontology is not resident.
- Computed and declared risk: Tier C because the CI workflow changes.

## Test plan

Run the full existing build/Python/hook/workflow/catalog/consumer validation
matrix, the new ontology tests, `bin/ontology.py --check`, and staged whitespace
checks. Recheck generated-page freshness after definition changes. Publish the
exact candidate for independent review without claiming a merge or live install.

## Rollback

Revert this change as a unit: remove its CI invocation, registry/bindings,
validator/tests and wiki references/pages. It creates no shared runtime state,
changes no production configuration and adds no data migration.
