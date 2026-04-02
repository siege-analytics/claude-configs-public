---
name: update-docs
description: Update the cascading-documentation documentation when making changes
---

# Instructions

1. Identify what levels of documentation exist for the repository
   1. Code inline documentation
      1. Structurally placed around existing code
      2. Docstrings
      3. Line by line comment
   2. Documentation files
      1. README.MD
      2. documentation folder, e.g., "docs", "how to"
      3. Sample scripts / notebooks
   3. Repository level
      1. Is there something like a wiki or documentation section that is administered as feature of the repository
      2. If not, can one be created?
         1. If yes, should I create it and use it?
         2. If not, what should we do instead?
   4. Knowledge management system
      1. Is there a company wide knowledge management system
         1. Confluence
         2. Notion
         3. Wiki
      2. If not, can one be created?
         1. If yes, should I create it and use it?
         2. If not, what should we do instead?
2. Once documentation inventory has been assessed, ensure documentation
   1. Use all skills for ticket creation, commits, PR's, etc.
   2. Add appropriate levels of documentation at each level - as we move upwards, abstraction increases and larger purpose and contect apply
   3. Consider documentation to be federated. Like government, it's important to not miss a level. 
      1. If level 4 does not exist, that's regrettable, but permissible.
      2. Everything else should be encouraged to exist.
3. Assess inter-relationships of documentation
   1. How do levels mutually relate?
   2. Are there style guides for each one?
      1. If yes, confirm that these are good choices.
         2. If they are, accept them.
         3. If they are not, suggest better ones. 
         4. If the user disagrees with your suggestion for a valid reason, accept his disagreement.
      2. If not, announce which style guides you will be using, and pick appropriate ones.
      3. Use the style guides.
   2. Are there systems that transform information between levels?
   3. Are there synchs between systems that require transforms?
   4. What sorts of sample scripts, test scripts and notebooks exist? If they do not, recommend them.
4. Execute appropriate documentation and synchs
   1. Synchs may requiree editing and updating synch files
      1. Track what is automatically generated vs. what is manually generated
      2. If change is significant, get user approval.
   2. Ensure that all writing matches style guides for clarity and legibility.

# Documentation philosophy

In the same way that all work worth doing is worth documenting in a ticket, any work that is worth doing is worth documenting.
That is why we have many skills around committing, updating tickets, creating pull requests, etc.
This skill is about using the correct level of documentation at every level of documentation the level of federation.

Inline documentation should 
   * function like Python docstrings: 
     * describing the function or method's purpose
     * describing arguments and types
     * describing the returns
   * observing and describing significant
     * constants
     * variables
     * computations
     * transformations
     * decisions
   * observe and describing returns
   * structurally describe the script
     * anchors at each significant point
     * outline structure
     * abstract description at top of script and near every section

README and markdown files should provide:
   * Highest level descriptions of what these projects are for 
   * How to use them
   * Significant decision points
   * Known break points 

Repository level documentation should provide:

   * Architecture decisions
   * Programming and style guides
   * Tables of contents and navigation
   * Decisions
   * Dictionaries
   * Catalogs
   * Sample scripts
   * Notebooks
   * Usability guides
   * Known errors
   * Roadmaps for development
   * Dependencies

Company knowledge managements should provide:

   * Ticketing - is the information on the right ticket and epic
   * Projects/Milestones - is everything related to the correct milestone
   * Comprehensive knowledge at every level of abstraction
     * high
     * mid
     * low
   * Correct relationships between knowledge systems: ticketing system to wiki, for example

