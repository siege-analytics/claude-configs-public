---
name: verify-failure-premise
description: "MANDATORY diagnosis-first gate. AUTO-TRIGGER: before debugging any reported failure (someone else's report OR your own non-zero exit). Forbids investigating the stated cause until the failure premise is verified against substantive evidence."
allowed-tools: Read Grep Glob Bash
---

# Verify the failure premise

A "failure" report is a claim. Before debugging the stated cause, verify the failure premise. Look at substantive evidence — output files, DB rows, audit tables, partial state — and confirm the work actually didn't happen. If the substantive work appears complete, **the failure signal is the bug; investigate the reporter, not the reported.**

This is not a suggestion. It is a hard gate.

## Why

Failure reports — non-zero exit codes, "FAILED" badges, shared stack traces, "X is broken" Slack messages — are intermediated reports about a system. They are not the system state. The wrapper script, the kubectl probe, the post-success cleanup hook, the JVM shutdown sequence, the API gateway timeout firing independently of the Lambda completing — any of these can produce a false-FAIL signal after the substantive work has completed.

Hours spent on "why did X fail?" when X actually succeeded are hours not spent on "why is the reporter lying?". The wrong-layer chase is seductive because the stack trace points at one layer while the bug lives one layer up.

Concrete example (the rule's originating case):
- A Spark JDBC append wrote 111 audit rows with `status='ok'` to `enterprise.silver_translate_runs`. The substantive work succeeded.
- The Rundeck wrapper reported the job as FAILED. Operators spent time investigating "why is the JDBC write failing."
- The actual bug: something between the successful commit and the process exit (Spark Connect lifecycle, executor cleanup, JVM hook, or the kubectl-probe wrapper) was throwing AFTER the work completed.
- Substantive evidence was sitting in the DB the whole time. Looking at it first would have routed the investigation to the right layer on day one.

## Diagnosis workflow

### Step 1: Find the substantive evidence

Where would the work's output be if it succeeded?

- Audit / status / log tables: did rows get written? What status?
- Output files: present? Expected size? Expected checksums?
- DB tables: target rows present? Expected counts?
- Idempotency markers: lock files, sentinel files, "completed" flags
- Side effects: messages sent, webhooks fired, downstream rows that depend on this work having happened

If you can't name where the substantive evidence would be, you do not yet understand the system well enough to debug it. Read the code that does the work; find its output surface; come back.

### Step 2: Compare evidence to the failure claim

Look at the evidence. Read it explicitly. Do not skip this step.

State, out loud, one of three things:

- **Evidence says didn't-happen.** Work output is absent or partial in a way that matches the claim.
- **Evidence says did-happen.** Work output is present and looks complete.
- **Evidence is ambiguous.** Some output is present; some isn't; you cannot tell from current state whether the work completed.

### Step 3: Route by what the evidence said

| Evidence verdict | Investigation layer |
|---|---|
| Didn't-happen | The work itself. Normal debug path — stack trace, logs, recent changes. |
| Did-happen | The failure signal. Instrumentation bug, wrapper bug, post-success cleanup throw, exit-code lying, monitor misreporting. **The work is not broken; the reporter is.** |
| Ambiguous | Say so explicitly. Do not pick a layer. Collect more evidence first (re-run with verbose logging, query intermediate state, check downstream consumers). |

Going to the wrong layer when the evidence is clear is the failure mode this gate prevents. Going to a layer when the evidence is ambiguous is a worse failure mode — at least the wrong-layer chase produces information; the ambiguous-evidence guess produces incorrect explanations that future debuggers inherit.

## Failure modes this prevents

- "Why did the JDBC write fail?" investigation that ignores 111 successful rows already in the destination table.
- "Why did the deploy fail?" investigation when the deploy succeeded but a smoke-test in the wrapper threw.
- "Why did the Lambda time out?" when the Lambda completed and the API Gateway timeout fired separately.
- "Why did the import error?" when the test ran, recorded results, then a teardown hook crashed.
- "Why did the migration fail?" when the migration completed and a permission-grant post-step failed.
- "Why is the cron broken?" when the cron worked and the alerting wrapper has a broken `kubectl` invocation.

In every case, the pattern is the same: a successful substantive operation followed by a failing instrumentation/cleanup/wrapper layer, with the failure signal pointing at the wrong layer.

## When this skill applies

This skill is **MANDATORY** when:

- A failure is reported to you (Slack, ticket, "can you look at X?")
- A command you ran exits non-zero
- A CI check fails
- A monitor alerts
- Any work product appears to have an "is-broken" status attached

**Exemptions** (the only cases where you may skip):

- The substantive evidence is the same thing as the failure signal (e.g., compiler reports a syntax error AND there is no compiled output to check — the report IS the substantive truth).
- Trivial failures where the evidence and the claim are obviously the same (e.g., `command not found` — there's no work to have happened).
- The user has already done step 1 and 2 and tells you which layer to investigate.

## Iron Laws

1. **Verify the premise before debugging the cause.** Not "after a quick look at the trace." Not "while ssh-ing in." Before any debugging.
2. **Look at substantive evidence, not status signals.** The audit table, the output file, the DB rows. The exit code is intermediated.
3. **State the verdict explicitly.** "Evidence says did-happen / didn't-happen / ambiguous." Don't skip this naming.
4. **Don't pick a layer on ambiguous evidence.** Collect more evidence first. Say "ambiguous" out loud.
5. **A failed reporter is a bug.** When evidence says work succeeded, the reporter is the bug worth fixing. Don't dismiss it as "weird" and move on; future runs will inherit it.

## Pairs with

- `writing-claims` — failure reports are claims; same verification discipline.
- `think` — once diagnosis identifies the right layer, design the fix at that layer per the think gate.
- `brain-first` — checking substantive evidence first is the diagnosis-shaped version of "check existing state before recreating."

## Attribution Policy

NEVER include AI or agent attribution in diagnosis notes, post-mortems, or any output.
