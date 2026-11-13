---
name: investigate
description: "Investigate an unfamiliar system, disputed premise or failure using actual code and runtime evidence. Use when deeper fact-finding is needed; a separate Fact Sheet is not required for every edit."
user-invocable: true
allowed-tools: Read Grep Glob Bash
---

# Investigate

Resolve uncertainty that affects the requested outcome. Reading relevant code and checking assumptions are normal engineering work; a separately posted Fact Sheet is optional unless the operator requests one.

## Procedure

1. Identify the question whose answer changes the next action. Start from relevant prior work, then verify it against the current target branch or runtime.
2. Read the actual interfaces, schemas, callers, configuration and error output. For data work, inspect representative values and validate boundaries. Follow related failure patterns where they could share the defect.
3. Separate observations, inference and unknowns. Cite enough evidence for another worker to reproduce consequential conclusions. Do not claim a command ran or a runtime changed from source inspection alone.
4. Use the result: fix the issue, refine the approach, or route a concrete dependency to its owner. Preserve useful findings in the existing task, PR or compact note; no prescribed headings, public posting sequence or companion signal is required before implementation.

Investigate only as far as the decision needs. Do not turn every unknown into a new project or keep collecting context after the next useful action is clear. If one operation is blocked, investigate its actual prerequisite and continue independent authorized work; never replay the refused effect through another actor or tool.

Use [skill:think] for implementation scope and [skill:self-review] for validation and publication review.
