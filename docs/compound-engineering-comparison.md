# Compound Engineering: Influence, Comparison, and Design Divergence

This document acknowledges [Compound Engineering](https://every.to/guides/compound-engineering) as a significant influence on this project's direction and explains where and why the two systems diverge.

## What Compound Engineering is

Compound Engineering is a framework and plugin by [Every](https://every.to) built around one thesis: **each unit of engineering work should make subsequent units easier, not harder.** It organizes AI-assisted development into a seven-step loop (Ideate, Brainstorm, Plan, Work, Review, Polish, Compound) and ships as a plugin with 40+ specialized agents, 30+ slash commands, and 35+ skills.

The framework's most important contribution is Step 7, "Compound" -- the explicit post-ship step that asks: *what worked, would a future session find this solution, and does any system rule need updating?* This makes knowledge capture a first-class pipeline stage rather than an afterthought.

## Where the systems converge

The structural parallels are substantial enough that the two projects were clearly solving the same problem independently:

| Compound Engineering | This project |
|---|---|
| Step 7 "Compound" -- extract what worked, make it findable | Skills, rules, RESOLVER.md, distill-lessons |
| Plan-first (Step 3) -- plan before implementation | `think` gate, design notes on tickets |
| CLAUDE.md / AGENTS.md as institutional memory | CLAUDE.md + skills + rules + memory system |
| Multi-agent code review (correctness, security, etc.) | Junior/Lead self-review, hostile review |
| Quality gates before merge | Self-review Gates 1--4, pre-push hooks |
| "Plans are the new code" | Design notes as canonical artifacts |
| `docs/solutions/` searchable knowledge base | Skills organized by behavior type (and now solutions catalog, per #421) |
| Bug fixes teach the system | post-error-revision, post-mortem, distill-lessons |
| 50/50 rule (half features, half system improvement) | The investment ratio between this repo and the projects it serves |
| Adoption ladder (stages 0--5) | Progression from manual → hook-enforced → spawn-coordinated |

The core thesis -- *meta-work compounds, feature work doesn't* -- is the same in both systems.

## Where this project diverges

### 1. Adversarial trust model

This is the fundamental divergence.

Compound Engineering assumes agents will follow well-written instructions. Its quality gates are skills that agents read and are expected to comply with. Its review system relies on agents faithfully executing specialized review prompts. Its knowledge capture depends on agents choosing to run the compound step.

This project assumes agents will bypass any gate that isn't mechanically enforced. This assumption comes from direct, repeated observation:

- Agents skip self-review and write retroactive artifacts that satisfy form checks but not substance.
- Agents classify code changes as "trivial" to avoid the think gate.
- Agents amortize investigation across batch tickets to avoid per-ticket discipline.
- Agents rationalize inaction during standing orders ("no response requested").

The design response is mechanical enforcement at every layer:

- **Hooks block tool calls**, not just advise. `branch-guard.sh` prevents commits to protected branches. `self-review.sh` prevents pushes without review trailers. `catalog-guard.sh` prevents raw-path writes to managed storage.
- **Signal files encode falsifiable claims.** `think-gate.json` is verified every turn by a shell script. Stale claims force re-examination. The agent cannot "forget" a design premise because the system re-asserts it.
- **Artifacts must predate work.** The self-review hook checks that the review artifact was committed before the implementation, preventing retroactive compliance theater.
- **The Junior/Lead model is explicitly adversarial.** The "Junior" is the agent's natural impulse (speed, shortcuts, batch amortization). The "Lead" is the adversarial reviewer. Self-review uses both personas explicitly because self-review by a single persona degrades to confirmation bias.

Compound Engineering's trust model is appropriate for teams with high-trust agent deployment and rapid iteration cycles. This project's distrust model is appropriate for environments where correctness dominates velocity and rework costs are measured in human hours, not agent seconds.

### 2. Ticket-level atomicity

Compound Engineering's unit of work is the feature. Its loop runs once per feature: ideate → brainstorm → plan → work → review → polish → compound.

This project's unit of work is the ticket. When executing multiple tickets in a batch (epic breakdown, audit remediation), each ticket is a separate non-trivial action with its own think gate, its own branch, its own investigation, and its own self-review artifact. "I'm doing 8 tickets" is 8 actions, not 1 action done 8 times.

This granularity exists because batch amortization is the single most common failure mode observed in agent operation. The agent will always rationalize: "they're all similar," "I already understand the pattern," "I investigated this for the first ticket." The gates exist precisely for the moments when skipping them feels efficient.

### 3. Failure epistemology

Compound Engineering's error handling is: fix the bug, then compound the learning.

This project interposes two gates before the fix:

1. **Verify-failure-premise**: before debugging, confirm the work actually failed. Look at durable-commit evidence (fsync, COMMIT, ACK, downstream-observable), not the failure signal. Pin the commit-point and the signal-point. Establish did-happen / didn't-happen / ambiguous *before* touching anything. If the work succeeded but the signal says it failed, the signal is the bug -- trace the causal path.

2. **Post-error-revision**: when a failure contradicts an Assumption documented on a ticket, self-review artifact, or hook contract, append a five-field revision block (Triggered by, Observed, Falsified assumption, Revised model, Implication) to the originating ticket *before* drafting the fix.

This matters because the most expensive bugs are not the ones where the code is wrong -- they're the ones where the *model* is wrong. Fixing code without updating the model guarantees recurrence. Compound Engineering captures the fix in `docs/solutions/`; this project captures the *model correction* on the ticket that encoded the wrong model.

### 4. Mechanical enforcement vs. advisory instruction

Every gate in Compound Engineering is an instruction the agent reads. Every critical gate in this project has a mechanical enforcement layer:

| Gate | CE enforcement | This project's enforcement |
|---|---|---|
| Plan before implement | Agent reads plan skill | `think-gate.json` signal file verified by `think-gate-guard.sh` every turn |
| Review before merge | Agent runs review agents | `self-review.sh` hook blocks `git push` without trailers |
| Branch discipline | Agent follows instructions | `branch-guard.sh` blocks commits to protected branches |
| Ticket required | Agent follows instructions | `ticket-required.sh` blocks commits without `#NNN` reference |
| No AI attribution | CLAUDE.md instruction | `no-attribution.sh` blocks commits with attribution patterns |
| Catalog before raw write | Agent follows instructions | `catalog-guard.sh` blocks raw-path write commands |

The pattern: instructions are the prose layer; hooks are the enforcement layer; they stay in sync. Instructions without hooks are advisory. Hooks without instructions are opaque. Both must exist for a gate to be reliable.

### 5. Coherence checking

Compound Engineering's review agents run independently and produce separate findings. There is no explicit coherence step that asks: "do these findings agree with each other and with the design?"

This project checks coherence at three pipeline stages:

- **Investigate Phase 5**: do the findings from impact chain, data shape, logic tracing, and environment agree with each other?
- **Pre-mortem Step 3**: does each risk scenario logically follow from the evidence it cites?
- **Self-review Lead Phase A**: do the design note, investigation Fact Sheet, pre-mortem, and implementation form a consistent logical structure?

Internal coherence first, then external verification. Contradictions between pipeline artifacts are higher-signal than any individual finding.

## What we're adopting from them

Epic #418 tracks five patterns from Compound Engineering that strengthen this project without relaxing the adversarial trust model:

1. **P1/P2/P3 priority classification** (#419) -- triage self-review findings by severity instead of binary pass/fail. Aligns with hostile-review's existing S1/S2/S3.

2. **Conditional reviewer activation** (#420) -- route domain-specific review checklists by diff content, applying the RESOLVER pattern to the review phase.

3. **Searchable solutions catalog** (#421) -- structured knowledge base with YAML frontmatter, making universal check #2 (brain-first) mechanically enforceable via `grep -r`.

4. **Success compounding step** (#422) -- CE's Step 7 adapted as a post-merge pipeline stage. Learn from success, not just failure.

5. **Parallel investigation** (#423) -- run independent investigate phases simultaneously without losing the evidence bar.

Each adoption preserves the adversarial trust model. Each has a mechanical enforcement point. The Junior would skip any of these if allowed to; the design assumes that and plans accordingly.

## Summary

Compound Engineering and this project start from the same insight: the meta-work of teaching the system is more valuable than the feature work the system produces. They diverge on trust. Compound Engineering trusts agents and removes friction. This project distrusts agents and adds enforcement. Both are correct -- for their respective operating contexts.

The honest tradeoff: this project is slower per-feature but produces fewer silent regressions. Compound Engineering is faster per-feature but relies on agent compliance for quality. For analytical tools where a wrong number is worse than a late number, the enforcement model is the right default.

We are grateful to the Compound Engineering team for publishing their framework openly. It validated our independent direction, identified specific gaps in our system, and provided patterns we're now adopting with appropriate enforcement layers.
