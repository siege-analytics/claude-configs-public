---
description: Always-on. Knowledge-base consultation discipline. Projects declare their knowledge sources in PROJECT.md; agents must consult them during investigation, tag every assumption, update the KB when contradictions are found, and treat silence as a finding. Protocol details live in `skills/knowledge-base/SKILL.md`.
---

# Knowledge Base

These rules enforce knowledge-base consultation discipline. They complement the think/investigate pipeline (which governs _how_ to investigate) with requirements for _what to consult_ and _what to do with findings_.

The enforcement model follows the established pattern: the skill educates (`[skill:knowledge-base]`), the rules define vocabulary (this file), and the think-gate-guard Level 3 warns mechanically.

## The rules

**knowledge-base:1. Read before claiming.**

Do not write think Step 1 conclusions without having read the relevant KB pages. If the project declares `knowledge_base:` in PROJECT.md, the listed sources are the minimum consultation set for any investigation whose scope overlaps the source's declared scope.

"I didn't check the wiki" is not an assumption tag -- it is an admission that the investigation skipped a documented source. The think-gate-guard Level 3 warns when the signal file lacks a `kb` section for projects that declare knowledge sources.

Enforcement: think-gate-guard.sh Level 3 warns when `kb.consulted` is missing or false. Judgment-enforced via `[skill:self-review]` peer review section.

**knowledge-base:2. Tag every assumption.**

Every assumption in the design note's Step 2 gets a KB tag: `kb-confirmed`, `kb-contradicted`, `kb-silent`, or `kb-not-applicable`. Untagged assumptions are hidden claims -- the agent did not verify whether the project has documented knowledge about the topic.

The tag discipline serves two purposes: (a) it forces the agent to check each assumption against the KB explicitly, and (b) it makes the consultation auditable in the think-gate signal file.

Enforcement: judgment-enforced via `[skill:self-review]` peer review section. The think-gate-guard Level 3 checks that `kb.tags` is non-empty when the signal file has a `kb` section.

**knowledge-base:3. Update on contradiction.**

A `kb-contradicted` finding without a filed delta (KB update PR, docs/ edit, wiki page update, or ticket for deferred update) is technical debt. The contradiction was found, documented, and then abandoned. The next agent will re-discover the same contradiction.

The delta does not have to be merged before the current work ships. A filed PR or a ticket referencing the contradiction is sufficient. What matters is that the correction entered the work-tracking system, not that it was completed synchronously.

Part of the definition of done: `[rule:definition-of-done]` criterion (f) (opt-in per project).

Enforcement: self-review peer review section checks `kb-contradicted` entries for delta references. Think-gate-guard Level 3 warns on unresolved contradictions (entries in `kb.tags.contradicted` without a `delta:` or `#NNN` reference).

**knowledge-base:4. Silence is a finding.**

A KB gap is information about the KB, not about the topic. When investigation answers a question that the KB is silent on, the answer should flow back to the KB as an addition -- or at minimum, the gap should be noted so future agents know the KB was checked and found lacking.

`kb-silent` tags that investigation later resolved should produce a KB addition (docs/ edit, wiki page, knowledge-base PR) or a ticket for the addition. This is not mandatory at the same urgency as contradictions -- gaps are debt, not lies -- but tracking them turns the KB into a living document instead of a static artifact that agents learn to ignore.

Enforcement: judgment-enforced. No mechanical block for unresolved silence; tracked via self-review lead review section as a dismissed finding.

## Operationalization

| Rule | Enforcement |
|---|---|
| knowledge-base:1 (read before claiming) | think-gate-guard.sh Level 3 warns when `kb` section missing; self-review peer review |
| knowledge-base:2 (tag every assumption) | think-gate-guard.sh Level 3 warns when `kb.tags` empty; self-review peer review |
| knowledge-base:3 (update on contradiction) | think-gate-guard.sh Level 3 warns on unresolved contradictions; self-review peer review; definition-of-done criterion (f) |
| knowledge-base:4 (silence is a finding) | Self-review lead review; judgment-enforced |

## Cross-references

- `[skill:knowledge-base]` -- protocol details, platform access, signal file schema
- `[rule:definition-of-done]` criterion (f) -- KB delta as done criterion (opt-in per project)
- `[skill:think]` Step 1 -- investigation is where KB consultation happens
- `hooks/resolver/think-gate-guard.sh` Level 3 -- mechanical warning enforcement

## Attribution

Defers to `[rule:output]`. No AI/agent attribution in code, commits, or comments.
