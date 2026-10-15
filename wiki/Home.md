# Scaffolding wiki

The [shared ontology](Ontology.md) defines the terms used by policy contracts,
project composition, host adapters and verification reports. It includes examples,
relationships and migration guidance for ambiguous terminology.

Definitions are maintained in `catalog/ontology.json` and rendered into the
ontology page by `bin/ontology.py`. Review source changes with their generated
documentation. The [contributor guide](../CONTRIBUTING.md#shared-terminology)
describes validation and adoption by new contracts.

This repository-backed wiki is the reviewable documentation source. Publication
to GitHub's separate Wiki is tracked on [#1007](https://github.com/siege-analytics/claude-configs-public/issues/1007).
