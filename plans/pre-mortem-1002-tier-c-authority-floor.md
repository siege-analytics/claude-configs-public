# Pre-mortem — #1002 authority dependency Tier C floor

## Scope

Before the configured resolver participates in enforcement, make its authority dependency closure mechanically Tier C using the existing review-risk classifier. This slice does not implement composition, protected acceptance, or live host capability proof.

## Failure modes

1. **Helper-only downgrade:** `bin/effective_policy.py` or `bin/gate_contract.py` changes while the classifier permits Tier B.
   - Control: exact high-risk patterns and direct/staged mutation tests.
2. **Receipt-only downgrade:** the selected policy revision/blob/digests change through `catalog/effective-policy-selection.json` under Tier B.
   - Control: exact receipt path plus modify/delete/rename and declared-B rejection tests.
3. **Contract drift:** schema/catalog or their advertised behavioral tests change without Tier C evidence.
   - Control: include helper, schema, catalog, and both behavioral test modules in one explicit floor.
4. **Authority confusion:** mutable working policy or synthetic project fixtures are promoted to Tier C and then misread as approved authority.
   - Control: explicit Tier B regressions for proposal-only policy/fixtures; selection receipt remains separate.
5. **Pattern near miss:** underscore/hyphen or anchored-path mistakes leave one dependency at Tier B.
   - Control: enumerate every exact path in `AUTHORITY_DEPENDENCY_FLOOR` and assert each independently.
6. **Rename/deletion bypass:** moving an authority file to a trivial path evades classification.
   - Control: existing staged change parser retains source and destination; run modification, deletion, and rename-source regressions for each dependency.
7. **Parallel registry:** adding a second authority list diverges from the canonical classifier.
   - Control: only extend `catalog/review-risk-policy.json`; the test list is an executable expected closure, not another runtime registry.

## Rollback

Revert this bounded commit to restore the previous classification only. It changes review evidence requirements, not policy values, generated instructions, runtime gates, installations, protected branches, or release artifacts.
