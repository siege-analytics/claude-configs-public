---
name: create-ticket
description: Create a well described ticket in the user's system (Jira, Linear, GitHub, GitLab, etc.)
---

# Instructions

1. Determine which ticketing system the user is using
2. There may be many systems involved, many users have multiple projects
    1. Different repositories belong to different tracking systems
    2. Different systems may have many accounts
    3. Categorise repos, group them by namespace and descriptive adjective
       1. Example `siege_analytics` (namespace) + `public` (adjective) 
       2. Example `siege_analytics` (namespace) + `private` (adjective)
    4. Collect the credentials for each system
       1. API keys
       2. Login and password
       3. ssh key
   5. Persist the method of getting each credential so that you don't need to ask each time
   6. Create the ticket according to template for each system
      1. Each system has its own syntax, like Jira's "Epics", for example
      2. Each system may different field names for necessary information

# Ticket concepts

Each system will have its own synonyms for these concepts. Do not get confuused by the label, look at the definitions above to determine the type.

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
3. Ticket begin date                 : the datatime of when work begins on this ticket
4. Ticket due date                   : the datatime of when work should be done on this ticket
5. Ticket assignee                   ; the user who is supposed to do the work of the ticket
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
feature: Allow user to select which langauge she prefers to use for admin panel
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
* Each ticket should contain the following sections
  * Intended / desired outcome
  * Starting conditions
  * Known blockers
  * Observed current outcome (if relevant)
  * Acceptance criteria
  * Known acceptance / success criteria
  * How a quality assurance team can review this ticket. Applicable examples include:
    * descriptions for Playwright
    * tests
      * integration
      * regression
      * unit
    * data quality checks, known scripts or processes
  

# Checklist

- [ ] Authenticated to the correct system
- [ ] Found synonyms for key terms
- [ ] If there are many tickets to be created, they are sequenced in logical order
- [ ] Ticket fields are correctly populated
- [ ] Ticket body is well written and descriptive
- [ ] The above have all been reviewed and iterated upon
