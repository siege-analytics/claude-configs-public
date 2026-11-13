# Self-review artifact contract

## Artifact format

Use one compact record for Tier B/C. An existing PR, task comment or repository note can serve as the record. Tier A needs only the short review summary. The substance below matters; no role-playing, compulsory mistake-finding or separately posted preparation artifacts are required.

```markdown
## Assumptions
Goal source: <original request, task or design reference>
<Relevant documentation/source references actually consulted, what they establish, how they inform the change, and consequential assumptions/scope/compatibility facts.>

## Test plan
<Actual commands and results, regression/failure cases, and remaining limitations. Clearly distinguish planned checks from executed checks.>

## Findings
<Material findings and resolutions, or a supported statement that none were found.
For an actual P1 finding use one line: P1: <finding>; Resolution: fixed|unresolved.
P1 findings without an explicit fixed resolution block publication. Context and explanations may remain prose.>

## Independent review
<Tier C: actual reviewer, reviewed revision/scope, evidence link and finding resolutions.>
```

The independent reviewer must actually inspect the change; the author cannot manufacture independence by assuming Junior, Senior, Lead or VP titles. Review the latest revision, or identify why a later generated-only change leaves the reviewed behavior unchanged.

Preparation evidence must demonstrate actual consultation and reasoning, not merely list links or assert effort. Include research when an unfamiliar or changeable external contract materially affects correctness; do not require unrelated research for an already established local fact.

Keep claims truthful and reproducible. Cite the motivating request rather than inventing it after the change. Do not backdate artifacts, invent tests or label non-clean scanner output clean. A record may be authored during review; it need not be committed in a separate ancestor before the implementation. Relevant history is evidence, not an additional publication ceremony.

Resolve defects that make the requested behavior wrong, unsafe or incompatible. Record useful non-blocking follow-ups without turning them into a whole-goal hold. Where a project policy requires a particular review or owner approval, preserve that requirement for its actual scope.

`Self-Review-Source:` points to this record. Tier C's compatible `Hostile-Review:` trailer points to the real independent review; the field name does not require a special title, provider or hostile attitude. See [Self-review](SKILL.md) for proportional validation and publication.
