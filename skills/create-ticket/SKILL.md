---
name: create-ticket
description: Create a well-described ticket in the user's ticketing system (GitHub, GitLab, Jira, Linear, etc.)
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash
argument-hint: "[ticket-type] [title]"
---

# Instructions

1. Determine which ticketing system the user is using
2. There may be many systems involved, many users have multiple projects
    1. Different repositories belong to different tracking systems
    2. Different systems may have many accounts
    3. Categorise repos, group them by namespace and descriptive adjective
       1. Example `siege_analytics` (namespace) + `public` (adjective) 
       2. Example `siege_analytics` (namespace) + `private` (adjective)
    4. Detect the ticketing platform from repo context
       1. If `.git/config` has a `github.com` remote, use `gh` CLI
       2. If `.git/config` has a `gitlab.com` or self-hosted GitLab remote, use `glab` CLI or the GitLab API
       3. If the project uses Jira, Linear, or another system, ask the user which CLI or API to use
       4. Use existing authenticated CLI tools. Never store credentials in plaintext. Refer to the project's established auth patterns (e.g., `gh auth`, `glab auth`, 1Password CLI, environment variables).
   5. Create the ticket according to template for each system
      1. Each system has its own syntax, like Jira's "Epics", for example
      2. Each system may have different field names for necessary information

# Ticket concepts

Each system will have its own synonyms for these concepts. Do not get confused by the label, look at the definitions above to determine the type.

## Fundamentals

* Ticket - A task to be accomplished by a user, that is either
  * bugfix - a correction when observed behaviour deviates from intended
  * feature - new behaviour added to the software
  * task - a named, fixed set of work to be accomplished
* Epic - a collection of thematically related tickets

Sometimes they will be called "issues" (GitHub, GitLab, Linear). Other systems may call them "tasks". 

## Ticket fields

1. Ticket creator                    : the user who created this ticket
2. Ticket creation date              : the datetime of the ticket's creation
3. Ticket begin date                 : the datetime of when work begins on this ticket
4. Ticket due date                   : the datetime of when work should be done on this ticket
5. Ticket assignee                   : the user who is supposed to do the work of the ticket
6. Ticket type                       : whether this ticket is a bugfix, feature or epic
7. Ticket priority                   : where in sequence this ticket should appear
8. Ticket urgency                    : magnitude of failure is this ticket is not resolved
9. Ticket size                       : magnitude of the amount of work this ticket requires
10. Ticket estimated completion time : magnitude of time estimated to complete the ticket
11. Ticket epic                      : the epic containing this ticket
12. Ticket relationships             : the tickets that this ticket inherits from, is sequentially related to, enables or blocks
13. Ticket reviewer                  : the user assigned to examine the work of the ticket 
14. Ticket observers                 : the users assigned to observe the work on the ticket or comment on it
15. Ticket labels                    : semantic tags that provide explanatory context and grouping for the ticket
16. Ticket milestones                : where in the project sequencing this ticket lives
17. Ticket attachments               : file artifacts that are relevant to the work of the ticket
18. Ticket text body                 : the descriptive text of the work

# Writing a ticket

When writing a ticket, please use the following considerations:

## Sequencing and ID

If there are multiple tickets that have a logical sequence, create them in order of the logical sequence so that the ticket id's increase as the user moves through logical order

## Name

title_descriptive_string: Find a vivid, clear description of what the ticket is meant to accomplish that is between the length of a slug and a sentence.

```ticket_name = f"{ticket_type} : {title_descriptive string}"```

### Examples
```
bugfix: Addresses are rendering coordinates in lat/long, want long/lat
bugfix: Namecase proper names in paragraphs
feature: Allow user to specify whether to calculate area in imperial or metric units
feature: Allow user to select which language she prefers to use for admin panel
epic: Introduce Grapelli admin to system
epic: Integrate data from Nevada to data warehouse

```
## Ticket fields

Fill out as many of the ticket fields exist. Ensure that all information is precise and accurate.

## Ticket body

* Focus on human legibility 
  * vary tone
  * use active voice verbs
  * be vivid in illustration and demonstration
  * link to appropriate documentation and examples as hyperlinks so that prose legibility is maintained
* Language and tone will depend on context
  * You will either be
    * domain expert
    * project manager
    * senior technical lead
    * junior engineer/analyst
  * speaking to 
    * domain expert
    * project manager
    * senior technical lead
    * junior engineer/analyst
* Every ticket MUST begin with a **plain-language summary** — a short paragraph at the very top, before any technical sections, that explains:
  * **What this task does** in one sentence a non-technical person can understand
  * **Why we need it** — the business reason, not the technical reason
  * **What it relates to** — which part of the product or pipeline this belongs to
  * This summary is for the project manager (who may not be technical) to understand what this work is about so she can plan sprints, set priorities, and ask informed questions. It should be written at a 5th-grade reading level. No jargon. No acronyms without explanation.
* After the summary, each ticket should contain the following sections, using this template:

```markdown
> **Summary**: [One paragraph, plain language, no jargon. What does this do,
> why do we need it, and what part of the system does it belong to? Written
> so a non-technical project manager can understand it and plan around it.]

## Intended outcome
What the world looks like when this ticket is done.

## Starting conditions
Current state of the code, data, or infrastructure relevant to this work.

## Known blockers
Other tickets, infrastructure issues, or decisions that must be resolved first.

## Observed current outcome
(If applicable) What is happening now that deviates from the intended behaviour.

## Acceptance criteria
- [ ] Criterion 1
- [ ] Criterion 2

## QA / Verification
How a quality assurance team can review this ticket. Applicable examples include:
- Playwright test descriptions
- Integration, regression, or unit tests
- Data quality checks, known scripts or processes
```

# Creating epics

An epic is a parent ticket that groups thematically related sub-tickets. When creating an epic:

1. Create the epic (parent issue) first
2. Create each sub-ticket in logical sequence
3. Link sub-tickets to the parent using the platform's native mechanism:
   - **GitHub**: Use the sub-issues API (`addSubIssue` GraphQL mutation) or reference the parent in the body
   - **GitLab**: Use related issues or epics
   - **Jira**: Use the epic link field
   - **Linear**: Use sub-issues or project grouping
4. Add all tickets (epic + sub-tickets) to the relevant project board

# Full example

Below is a complete ticket as it would appear on GitHub Issues.

**Title**: `bugfix: Silver table drops records where committee_id contains leading zeros`

**Labels**: `bug`, `data-quality`, `silver`  
**Assignee**: dheerajchand  
**Milestone**: E-1: Bronze + Silver  
**Priority**: P1  
**Size**: S  

**Body**:

```markdown
> **Summary**: When we process committee records from raw FEC filings, some
> committee ID numbers are losing their leading zeros (like "C00000547" becoming
> just "547"). This makes it impossible to match committees correctly, because
> different committees can look identical without those zeros. This is a data
> quality bug in the FEC processing pipeline.

## Intended outcome
All committee records from bronze propagate to silver with their original
`committee_id` intact, including IDs like `C00000547` that have leading zeros.

## Starting conditions
The bronze-to-silver transform in `silver_transforms.py:48` casts `committee_id`
to integer before writing to Delta Lake. This strips leading zeros, which are
significant in FEC identifiers (they encode registration era).

## Known blockers
None — this can be fixed independently.

## Observed current outcome
Silver table has 6.8M records but ~12K committees have mismatched IDs when
joined back to the FEC bulk download. Example: `C00000547` becomes `547`,
which collides with `C00000000547` (a different entity).

## Acceptance criteria
- [ ] `committee_id` remains a zero-padded string (9 chars) through the full pipeline
- [ ] Round-trip test: bronze → silver → re-read matches original FEC file
- [ ] No regression in row counts (silver should still have >= 6.8M records)

## QA / Verification
- Unit test: assert `transform_committee("C00000547")` preserves the string
- Integration test: load 100 sample bronze records, write to silver, read back and compare
- Data quality: `SELECT COUNT(*) FROM silver WHERE LENGTH(committee_id) != 9` should return 0
```

# Attribution policy

**NEVER** include AI or agent attribution in tickets, issue bodies, or comments. This includes:
- No "Generated with Claude Code", "Made with Cursor", "Built with Codex", or any AI tool mentions
- No `🤖`, `[bot]`, or other markers that signal AI involvement
- No attribution to any AI assistant, code generation tool, or agent framework
- This applies to the ticket title, body, comments, and any linked content

# Checklist

- [ ] Detected the correct ticketing platform from repo context
- [ ] Authenticated via existing CLI tools (no plaintext credentials)
- [ ] Found platform synonyms for key terms (issue vs ticket, epic vs parent, etc.)
- [ ] If there are many tickets to be created, they are sequenced in logical order
- [ ] Epics created first, sub-tickets linked to parent
- [ ] Ticket fields are correctly populated
- [ ] Ticket begins with a plain-language summary (no jargon, 5th-grade reading level)
- [ ] Summary explains what, why, and what part of the system — readable by a non-technical PM
- [ ] Ticket body follows the template and is well written
- [ ] No AI/agent attribution anywhere in the ticket (no "Generated with", no "Made with", no tool mentions)
- [ ] The above have all been reviewed and iterated upon
