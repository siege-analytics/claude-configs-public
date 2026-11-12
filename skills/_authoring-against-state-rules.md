---
description: Verify runtime facts that materially affect code or operational actions; retain useful evidence without mandatory inventory artifacts.
---

# Authoring Against State

When a change depends on external state, inspect the facts that determine its correctness. Do not substitute remembered configuration, an old design or a source diff for actual runtime evidence. Scale investigation to the uncertainty and consequences.

**authoring-against-state:1. Data shape.** Inspect relevant schemas and representative values before relying on columns, identifiers, types or cardinalities. Validate assumptions at boundaries; handle actual missing and invalid data.

**authoring-against-state:2. Configuration.** Inspect the effective configuration used by the consumer when it affects the result. Distinguish checked-in defaults from installed settings and runtime overrides. Preserve operator-owned settings.

**authoring-against-state:3. Topology.** Before consequential jobs or deployments, verify the actual target, relevant health and capacity. Preserve live job handles; a polling timeout does not establish termination or authorize a duplicate launch.

**authoring-against-state:4. Plan shape.** Fit query, serialization and processing strategies to actual input scale and engine constraints. Use representative execution or meaningful structural checks where excessive plan size or resource use could cause failure.

**authoring-against-state:5. Version resolution.** When multiple installations or shared import paths could change behavior, verify which code the actual consumer resolves. Installing or committing a version does not prove that the consumer uses it.

**authoring-against-state:6. Useful records.** Preserve consequential observations, assumptions and limitations in the existing task, PR or review. No prescribed inventory template, separate ticket comment, one-line-fix declaration or public posting is required before authoring. Record when evidence was actually gathered; never fabricate pre-work provenance. Use already reliable evidence until a relevant change calls for rechecking it.

An unresolved factual question usually calls for investigation within the existing grant. It becomes an owner decision only when actual authority or a material tradeoff is missing. Hold that action and continue independent work. See [skill:think], [skill:investigate] and [skill:self-review].
