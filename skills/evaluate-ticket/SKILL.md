---
name: evaluate-ticket
description: "Review a ticket for unclear intent, missing evidence or acceptance criteria when creating or improving it. Optional structural diagnostics; not a prerequisite for reading a diff or continuing an authorized task."
allowed-tools: Bash
---

# Evaluate Ticket

Help make the requested outcome and its evidence clear enough to act on. Read the original request, ticket and relevant source. Identify missing facts or material ambiguity, then improve the ticket within the existing grant. Ask the decision owner only when the intended outcome, scope or authority cannot be resolved from available evidence.

A missing heading, design-note link, formal rubric result or exemption block does not prohibit investigation, implementation or review. A well-formatted ticket does not authorize work or prove its facts. Preserve actual owner instructions and action-specific holds; keep independent eligible work moving while resolving a consequential gap.

## Review the substance

Look for the actual problem or goal, relevant observations, intended behavior, important assumptions and evidence that would demonstrate completion. Scale detail to the change. A direct user request or existing project record can establish intent without being rewritten into a prescribed template. Do not create extra tickets or review paperwork solely to satisfy this skill.

When creating a batch of tickets, inspect the first actual result against the requested outcomes before repeating the pattern. Correct factual or scope errors; do not make every ticket wait for a stylistic PASS.

## Optional structural diagnostic

When a structural check is useful, run:

```bash
bash scripts/discipline/evaluate-ticket.sh 'owner/repo#234'
```

The existing helper checks a historical six-part rubric: title shape, Context/Goal/Acceptance headings, an evidence token, a design-note link, an Assumptions block and falsification language for behavior-change labels. It also accepts a local file. GitHub reads use `gh`; Linear/Jira references are recognized but their fetchers remain unsupported.

The helper retains its legacy interface: exit 0 with PASS, exit 2 with BLOCK and a gap list. These are diagnostic results, not execution or publication permission. Separate an unavailable fetch method from a substantive ticket problem. Resolve useful gaps, report material uncertainty and continue work whose intent and authority are already established. Do not invent an exemption ceremony or claim that current hooks rerun this helper unless the actual installed hook does so.

For code review, follow [skill:code-review]: establish intent and inspect the diff. Ticket improvement can accompany review; it is not a veto on reading the code that would clarify the ticket.
