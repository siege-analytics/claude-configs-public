---
name: ask-questions
description: "Operator question protocol. Use whenever you need answers or decisions from the operator, or when the operator asks you to ask questions. Treat it as a survey: show the complete question list once, together with the first question; ask exactly one question per turn with context, choices, pros and cons, a recommendation and a default; go straight to the next question after each answer without routing answers, updating tickets or starting work on them; after the last answer, summarize and then route and act on all answers in one batch. It never freezes or blocks running work. The single canonical procedure; session-coordination:5 defers to it for hubs."
allowed-tools: Read Grep Glob
tier: on-demand
owner: siege-analytics
status: active
last-reviewed: "2026-11-06"
verification: bin/_test/resolve_load_set_test.py
---

# Ask Questions

This is the single procedure for asking the operator questions. Any agent that needs operator answers uses it. Hubs follow it through [`session-coordination`](../_session-coordination-rules.md) session-coordination:5, which adds only the hub-specific routing rule. Do not restate this procedure elsewhere; link here.

## Operator specification

The operator's words are the specification. Three statements, read together:

- Directive, 2026-10-18 20:37 CDT (siege-analytics/claude-configs-public#1056): "The way to ask questions is one at a time, with context, pros, cons, choices and recommendations. Receive the answer and immediately ask the next question. Do not begin acting or routing till you have all the answers to all your questions."
- Wording relayed by the Siege Utilities Hub as the operator's words, 2026-11-06: "1) describe the questions, one at a time, with a) context b) recommendations 2) ask all your questions, collect all answers, before you dispatch or act."
- The operator's clarification of what the hold means, 2026-11-06 12:59 CST, relayed by the Siege Utilities Hub. It is authoritative for how the first two statements are read: "What I meant was perhaps different. Assume you have ten tasks running, 1-10. Let's assume you have questions about 2-6. What I meant was that when I get each question, do not begin routing the answers to workers and hubs, updating tickets, starting work, etc. because that leaves me sitting here for a while between questions, who knows how long that startup will take? It's better for you to get every answer to the questions you need, think of it as a survey, then start routing and acting. I didn't mean that you should freeze or block work."

So the hold is on acting on the answers until the survey is complete, so the operator is never left waiting between questions. It is not a hold on work. "The default" is carried over from the 2026-09-05 hub decision-checklist correction (session `260905-clever-quasar`), which asked each decision with context, options, a recommendation and a default; it is recorded in the originating evidence of [`session-coordination`](../_session-coordination-rules.md).

## When to use

- One or more open questions would change what you do: a material choice, missing authority, unclear scope or an unapproved consequence ([`strategic-agency`](../_strategic-agency-rules.md) strategic-agency:4).
- The operator asks you to ask questions, or names this skill.

Do not use it to ask about settled decisions or routine methods you can resolve from the task, prior instructions and evidence ([`autonomy`](../_autonomy-rules.md)). The question list is not a new approval gate. Ask only what is actually open.

## Procedure

1. **Check before asking.** Drop any question already answered by an instruction, a prior decision, standing authority or available evidence.
2. **Build the complete list, then show it once, together with the first question.** Number every question and give each a one-line title. Show the numbered list and the first fully formed question in the same message; never end a turn after only listing the questions. Say that you will route and act on the answers after the last one, and that running work continues meanwhile.
3. **Ask exactly one question per turn.** Each question carries:
   - **Context:** what is being decided, why it matters, the evidence, and what the answer changes.
   - **Choices:** the real options, labelled. Do not pad the list with options nobody would pick.
   - **Pros and cons** for each choice.
   - **Recommendation:** the choice you recommend, and why.
   - **Default:** what you will apply if the operator says they have no preference or says "you decide". The default is your recommendation. A default chooses only within existing authorization: it never creates authority and never stands in for a confirmation that a protected-action policy requires.

   Then wait for the answer. Other authorized work may continue while you wait ([`autonomy`](../_autonomy-rules.md)).
4. **On each answer, go straight to the next question.** The next question preempts whatever you were doing while you waited: record the answer and put the next question in the same reply, then resume the other work. Between answers, do not route answers to workers or hubs, update tickets, brief or re-task anyone, or start work based on an answer. That startup would leave the operator waiting between questions.
5. **Treat it as a survey: act on the answers only after the last one.** Take no action, routing, delegation, dispatch, ticket update or spoke briefing based on an answer until every question is answered. This rule governs acting on the answers, not work in general. The protocol never freezes or blocks work: everything already running continues as before, including the tasks the questions are about.
6. **Summarize, then route and act in one batch.** When the last answer arrives, post one numbered summary of every answer. Mark answers the operator delegated as "you decide: applied the recommendation". Then route the answers and act on all of them together.

## Edge cases

- **An answer raises a new question.** Append it to the list, say that the list grew and show the new count, and ask it in order. The survey ends only after the new question is answered.
- **An answer invalidates later questions.** Revise the list, say which questions were dropped or changed and why, and show the revised list before asking the next one.
- **"You decide" or "no preference".** Apply the stated default, which is your recommendation, and record it in the summary as delegated.
- **Silence is not an answer.** Never apply the default because the operator did not reply. A proposed default is not authorization (strategic-agency:4).
- **An explicit stop or revocation.** If the operator says to stop asking ("don't ask", "stop asking"), end the survey at once and do not continue the protocol. If an answer stops or revokes an action ("stop the deploy", "don't merge that"), apply it to that action immediately, even before the remaining answers arrive; ordinary answer-based dispatch still waits until the survey is complete. This is not a new approval step and does not revoke unrelated standing grants.
- **A handoff mid-survey.** A partial-survey handoff may record the answers collected so far, without dispatching on them, so the successor can continue the same survey.
- **The operator interrupts or redirects.** The operator's control surface wins (session-coordination:6). Stop the sequence and follow the redirection. Resume the remaining questions only if they still apply, and show the remaining list when you do. If the operator tells you to act on the answers so far, do so.
- **The operator answers several questions at once, or answers ahead.** Record those answers, skip the answered questions, and ask the next unanswered one.
- **An unclear answer.** Ask a clarifying follow-up on the same question before moving on. It does not count as a new question.
- **A list of one.** Still show it, and still give context, choices, pros and cons, a recommendation and a default. Its single answer is the last one, so route and act on it right away.
- **Work is running while you ask.** Leave it running. Do not pause, block or hold running work, including tasks the questions concern, because a question about them is open.
- **Questions relayed through a hub or another session.** The relaying session uses this same procedure. The asker routes and acts on the answers only after the relay returns every answer.

## Message template

The first message: the list, shown once, followed by the first full question in the same message:

```
Questions (3). I will route and act on the answers after the last one; running work continues meanwhile.
1. <title>
2. <title>
3. <title>

Question 1 of 3: <title>
Context: <what is being decided, why it matters, evidence, what the answer changes>
Choices:
  A. <option>. Pros: <...>. Cons: <...>.
  B. <option>. Pros: <...>. Cons: <...>.
Recommendation: A, because <reason>.
Default (no preference or "you decide"): A.
```

Each later question, one per message:

```
Question 2 of 3: <title>
Context: <what is being decided, why it matters, evidence, what the answer changes>
Choices:
  A. <option>. Pros: <...>. Cons: <...>.
  B. <option>. Pros: <...>. Cons: <...>.
Recommendation: A, because <reason>.
Default (no preference or "you decide"): A.
```

The final summary:

```
Answers:
1. <title>: A (operator).
2. <title>: B (you decide: applied the recommendation).
3. <title>: dropped after answer 1, because <reason>.
Routing and acting on these now: <who gets what, what starts>.
```

## Anti-patterns

- Several questions bundled into one turn, or a vague list of topics with no choices.
- Ending a turn after only listing the questions, without the first question.
- Treating a default or a "you decide" as a grant of authority the operator has not given.
- A question with no recommendation or no default, or choices without pros and cons.
- Routing an answer to a worker or hub, updating a ticket, or starting work on an answer before the last answer is in.
- Status updates or other activity between an answer and the next question.
- Pausing, blocking or freezing running work because questions are open.
- Re-asking a decision that is already settled.
- Applying the default on silence.

## Attribution

Defers to [`output`](../_output-rules.md). No AI or agent attribution in questions, summaries or the actions that follow.
