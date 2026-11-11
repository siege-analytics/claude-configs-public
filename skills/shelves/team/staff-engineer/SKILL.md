---
name: staff-engineer
description: 'Operate effectively at the Staff-plus engineering level -- the IC role beyond Senior that influences across teams without managing them. Use when the user mentions "Staff engineer", "Principal engineer", "staff archetypes", "tech lead vs architect", "engineering strategy", "managing technical quality", "promotion packets", "staying aligned with authority", "create space for others", or "Staff-plus path". Also trigger when scoping work that requires cross-team influence, writing engineering strategy documents, deciding whether to be tech-lead vs solver vs architect, navigating executive presentations, or coaching senior ICs on the path to Staff. Covers four archetypes (Tech Lead / Architect / Solver / Right Hand), operating disciplines, and getting-the-title mechanics. For management-track leadership see drive-motivation; for team operating models see 37signals-way.'
license: CC-BY-NC
metadata:
  source: 'staffeng.com (Will Larson, free companion site to Staff Engineer book)'
  coverage: 'Partial -- companion-site stories + ~25 guides. Full book paid; absorb that when procured.'
---

# Staff Engineer Framework

A framework for the Individual Contributor role beyond Senior -- the engineering path where influence comes from technical judgment, cross-team leadership, and organizational fluency rather than from direct reports. Apply when scoping work that needs Staff-plus impact, deciding which archetype to play, writing engineering strategy, or navigating the promotion to Staff.

## Core Principle

**Staff engineers don't have direct authority; they create alignment.** The job at Staff and above is to identify what matters, get people to converge on it, and make sure it gets done well -- without the org chart doing the convergence for you. Authority is borrowed (from sponsors, from executive attention, from the trust the team places in your judgment) rather than granted.

**The foundation:** the Staff role is not "senior engineer plus more years." It's a different operating mode. Senior engineers solve assigned problems; Staff engineers identify which problems are worth solving, then ensure the solving happens. Most failures at Staff aren't technical -- they're failures to read organizational politics, to time interventions, to build the network that supplies sponsorship and information.

## Scoring

**Goal: 10/10.** When evaluating Staff-level work (a strategy doc, a cross-team initiative, a promotion packet, a quarter's impact), rate 0-10 based on whether it demonstrates the archetype's competencies AND the operating disciplines below. A 10/10 means clear archetype fit, demonstrated technical quality / strategy / influence at the appropriate scope, sponsorship and visibility working as intended. Lower scores indicate misfit, narrow scope, or missing organizational legibility.

- **9-10:** Archetype matches work, strategy is written and adopted, technical quality is measurably improving, sponsor relationship is active, executive presentations land.
- **7-8:** Archetype roughly right, strategy exists but partial adoption, quality improving in spots, sponsor relationship intermittent.
- **5-6:** Archetype mismatch (e.g. acting Architect in a Tech-Lead org), strategy missing or unread, quality unmanaged, sponsor relationship transactional.
- **3-4:** No archetype clarity, no strategy, individual heroics instead of org leverage, no sponsor.
- **1-2:** "Senior engineer doing more work," not Staff-shaped at all.

## The Four Staff Archetypes

Larson identifies four canonical archetypes. Which one fits depends on the organization's shape (team-based vs individual-ownership), the size, and the work's nature.

| Archetype | What they do | When it fits |
|---|---|---|
| **Tech Lead** | Guides approach + execution of one team, partnered with one or more managers. | Team-based orgs emphasizing ownership + agile delivery. Most accessible first Staff role. |
| **Architect** | Owns direction, quality, approach within a critical complex area. | Large companies with complex codebases or significant tech debt to address. |
| **Solver** | Drops into arbitrarily-complex problems, finds a path forward, moves on. | Orgs that organize around individual ownership rather than teams. |
| **Right Hand** | Extends an executive's attention; borrows their scope and authority. | Rare -- typically only in 100+ engineer orgs with cross-functional crisis-shaped work. |

**Mismatch is the most common failure mode.** Acting Architect in a Tech-Lead org reads as "doesn't ship"; acting Tech Lead in a Solver org reads as "limited scope." The archetype must fit the org, not the person's preference.

## Operating Disciplines (selected guides -- full set at staffeng.com/guides)

### 1. Work on what matters

The Staff job is partly *picking* the work, not just doing it. Larson's framing: focus on the high-leverage problems that are not getting addressed by the org chart's natural flow. Most engineers default to the work assigned; Staff engineers default to the work that *needs* assigning.

**Signals you're working on what matters:**
- The work would not have happened without your intervention.
- Multiple senior people would name your work as load-bearing.
- The work has a measurable outcome that ties to a company priority.

**Anti-pattern:** "Snacking" on small easy wins that flatter your week but don't move the needle.

### 2. Write engineering strategy

Strategy is a document that says "here's how we're going to make this decision class go, and why." It's not a roadmap. It's not a list of projects. It's the *frame* that makes future decisions easier.

**Strategy is good when:**
- Engineers facing a new decision read it and know what to do without asking.
- It names trade-offs explicitly, including ones the company is choosing to accept.
- It survives ~12 months without rewrite.

**Anti-pattern:** Strategy as marketing -- long prose, no decision content, nobody references it after publication.

### 3. Manage technical quality

Larson's framing: technical quality is a *flow* problem, not a one-time fix. You're managing the *rate* at which new problems are created vs the rate at which old problems are paid down. A migration-led approach (incremental, measured, sustained) beats a refactor-led approach (one big push that bounces off real-world constraints).

**Signals technical quality is being managed:**
- A measurable quality metric is improving across quarters.
- Engineers can describe the migration plan and its current phase.
- New code is rarely a source of new tech debt.

**Anti-pattern:** "Tech debt week" once per year that fixes the symptoms but not the rate-of-creation.

### 4. Stay aligned with authority

Authority is your sponsor's, not yours. Staying aligned means knowing what they care about, what they fear, and what they'd reject; then making your work *visibly* serve that. Misalignment kills Staff careers more than technical errors do.

**Mechanics:**
- 1:1 cadence with sponsor; bring agenda; show the work.
- Ask "what would you not want to find out about this in three months?" -- that's the misalignment risk surface.
- When you disagree with sponsor, disagree explicitly and early; never in public.

**Anti-pattern:** Going dark on the sponsor for weeks because the work is interesting; surfacing only when it lands or breaks.

### 5. Create space for others

Staff engineers grow other engineers; that's part of the job, not a side project. Creating space means visibly choosing to *not* take the most interesting problem so a Senior can grow into it, mentoring without taking over, and crediting publicly when others land work.

**Signals you're creating space:**
- Engineers report to you informally for technical guidance though you don't manage them.
- The team's overall skill ceiling is rising, not just your own.
- Promotions are happening on your team because of capability growth, not tenure.

**Anti-pattern:** "Hero Staff engineer" who takes the interesting problems and leaves the routine work to Seniors -- short-term throughput, long-term skill ceiling stuck.

### 6. Present to executives

Executive communication is its own skill. The format is conclusion-first, evidence-second, ask-last. The reader has 90 seconds; assume that and write accordingly.

**Mechanics:**
- Lead with the recommendation or decision being asked for.
- Trade-offs as a table or short bulleted list, not prose.
- Make the ask explicit -- what specific decision do you need from this audience?

**Anti-pattern:** Prose-heavy strategy doc presented to executives without conclusion in the first paragraph; the room reads the title, scans for the ask, doesn't find it, defers the decision.

## Getting the Title

The companion site has substantial guides on getting promoted to Staff -- within your current org or by switching. Key disciplines:

- **Promotion packets** -- evidence-gathering document showing impact at Staff scope.
- **Find your sponsor** -- Staff promotion needs a sponsor advocating in the calibration room.
- **Staff projects** -- pick visible, high-leverage work that demonstrates the archetype you'd be promoted into.
- **Being visible** -- Staff-shaped impact that nobody sees doesn't promote you. Document, present, write.

For the switching-companies track: deciding-to-switch, finding-the-right-company, interviewing-for-Staff, negotiating-your-offer. The site has ~5 guides on these topics.

## When this skill does NOT apply

- **Management track** -- Staff is the IC path. If the question is about managing direct reports, hiring, performance, see drive-motivation (motivation systems) or external mgmt sources. The book *An Elegant Puzzle* (Larson, paid) covers the management track explicitly; absorb that when procured.
- **Pre-Senior career questions** -- this skill assumes the engineer is already operating at Senior with the question being "what comes next?" For earlier-career advice the framing changes.
- **Org strategy / company strategy** -- Staff engineers WRITE engineering strategy. Org-level / company-level strategy is a different shelf (strategy/).

## Companions

- `engineering-principles/` shelf -- the technical-craft floor that Staff engineers should be fluent in.
- `systems-architecture/` shelf -- Architect-archetype Staff engineers lean on this heavily.
- `drive-motivation` -- Right-Hand and Tech-Lead archetypes interact with motivation systems regularly.
- `37signals-way` -- for the team-operating-model questions Tech-Lead archetypes face.

## Source + license

- **Source:** staffeng.com (the free companion site to the *Staff Engineer* book by Will Larson).
- **License:** Creative Commons (CC BY-NC equivalent; companion-site content). The full book is paid (Stripe Press, Amazon); absorb book-only content when procured.
- **Coverage gap to flag for future absorption:** the full book covers archetypes in deeper detail with case studies, plus a curated set of staff-engineer interviews. The companion site has SOME interviews and guide excerpts but not the full book material.

## See also

- References subdirectory (when populated) for excerpts from specific staffeng.com guides.
- shelf-recommendations-for-su-roles.md in the session that originated this skill (260502-pure-vista) -- context on why Staff Engineer was the chosen tech-lead-shelf entry.
