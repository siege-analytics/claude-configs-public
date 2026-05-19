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
- A Spark JDBC append wrote 111 audit rows with `status='ok'` to a destination table. The substantive work durably committed.
- The wrapper reported the job as FAILED. Operators spent time investigating "why is the JDBC write failing."
- **Commit-point**: the JDBC append's COMMIT to the destination table.
- **Signal-point**: the wrapper's exit-code interpretation downstream of process exit.
- **Causal path** between them: JDBC connection close, executor task wrap-up, session-context stop, shutdown hooks, process exit, wrapper's status probe, wrapper's exit-code interpretation. The bug lives somewhere on that path.
- Durable-commit evidence was sitting in the destination table the whole time. Looking at it first (Steps 1–3) would have routed the investigation to the causal-path layer (Step 4) on day one.

## Diagnosis workflow

### Step 1: Find the durable-commit evidence

The evidence has to confirm the work **durably committed**, not that "the function returned without raising." In-memory success before a final flush is not success — it looks like success in stack traces and looks like failure in the durable surface.

Where would the work's *durable* output be if it succeeded?

- Audit / status / log tables: rows visible to a **fresh transaction** in another session (not your own write-cache), with content that matches what the success path would have written.
- Output files: fsynced, with the expected size/checksum, observable by **another process** than the writer.
- DB target tables: target rows present in a fresh transaction; counts match expected.
- Idempotency markers: lock files released, sentinel files renamed-to-final, "completed" flags set.
- Side effects: messages observable by the **downstream consumer** (queue depth, downstream-table row, webhook ACK).

The pivot is **durability, not return-value**. A function that returned without raising but whose write hasn't been fsynced/committed/ACKed has not yet succeeded.

If you can't name where the durable evidence would be, you do not yet understand the system well enough to debug it. Read the code that does the work; find the *commit-point* (next section); come back.

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

### Step 4: Trace the causal path (when evidence says did-happen)

When the evidence verdict is **did-happen**, the bug lives somewhere on the causal path between the commit-point and the signal-point. That path is enumerable. The unit-of-step varies by substrate; the discipline does not.

**Commit-point** = the moment the substantive work became durable. The pivot is durability, not return-value:

| Substrate | Commit-point |
|---|---|
| RDBMS write | The COMMIT, not the INSERT |
| File write | The fsync, not the `write()` |
| Spark / dataframe action | The action's durable-write to storage, not the lazy plan or the local result |
| RPC / message send | The ACK from the callee, not the local send |
| Shell pipeline | The successful exit of the producing process, not the pipe write |
| In-memory state only | (no commit-point — there is no durable substantive surface; the rule does not apply) |

**Signal-point** = the moment the failure status was set. Exit code emitted, FAILED badge written, error frame raised, alert fired, monitor incremented. Walk back observers: who set the badge → reading what value → from which subprocess → whose return code.

**Causal path** = every step the system actually ran between commit-point and signal-point. The unit varies; the discipline does not:

| Substrate | "Step" |
|---|---|
| Python (function-shaped) | Function call, decorator wrap, context-manager `__exit__`, atexit hook, `finally` block, library cleanup runtime hook |
| Python (imperative script) | Statement, library-cleanup runtime hook, atexit handler, signal handler |
| SQL script | Statement, ON-COMMIT trigger, deferred-constraint check, transaction-scope cleanup |
| Shell script | Command, redirection, EXIT/ERR trap, subshell exit, `set -e`-driven abort |
| Spark / distributed job | Action's executor-side cleanup, driver-side post-action work, JDBC driver close, session/context stop, shutdown hook, JVM shutdown |
| Container | Process exit code → wrapper interpretation → STOPSIGNAL handling → post-stop hooks → container-runtime exit code |
| Wrapper / orchestrator | Wrapper's post-process check (probe, status query), exit-code interpretation, alerting rule, monitor-side check |

**Trace procedure**:

1. **Locate the commit-point precisely.** File + line, or query + clause, or command + redirection — whatever pins durability in this substrate. If you can't pin it, you can't use this method; say so and stop until you can.
2. **Locate the signal-point precisely.** The actual source of the FAILED status, not where it was observed. Walk back observers: who set this badge → reading what value → from which subprocess → whose return code.
3. **Enumerate the path.** Every step between commit-point and signal-point in this substrate. Hooks, triggers, traps, cleanup handlers, and wrapper observers all count. Write the list down — guessing about completeness defeats the method.
4. **Rank suspects.** Likelihood-of-throw factors: recent changes (`git blame` the path), known-flaky steps (Spark Connect lifecycle, kubectl probes, anything network), external-dependency steps, steps that touch the durable store after commit (re-reads, fresh queries, downstream FKs).
5. **Bisect.** Pick the highest-likelihood suspect; instrument it (log line, breakpoint, intermediate state query). Each negative narrows the path; do not skip the instrumentation in favor of guessing further.

**Strong recommendation, not a hard gate.** The hard gate is the premise verification (Steps 1-3 above). Step 4 is the methodology *given* you're past the gate. Hard-gating "you must enumerate every hook" invites malicious compliance; the discipline is the named-pivots + enumerate-then-bisect shape, not a checklist.

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
2. **Look at durable-commit evidence, not status signals.** Pivot on durability (fsync / COMMIT / ACK / downstream-observable), not on return-value. The exit code is intermediated; the audit row in a fresh transaction is not.
3. **State the verdict explicitly.** "Evidence says did-happen / didn't-happen / ambiguous." Don't skip this naming.
4. **Don't pick a layer on ambiguous evidence.** Collect more evidence first. Say "ambiguous" out loud.
5. **A failed reporter is a bug.** When evidence says work succeeded, the reporter is the bug worth fixing. Don't dismiss it as "weird" and move on; future runs will inherit it.
6. **Pin both pivots before tracing.** Commit-point (where the work became durable) and signal-point (where FAILED was set). The bug lives on the path between them; if you can't pin the pivots, you cannot enumerate the path.
7. **Enumerate then bisect, don't guess.** Write the path down before suspecting any single step. Bisect by instrumentation, not by hunch. Each negative narrows the path; each guess that skips instrumentation re-opens it.

## Pairs with

- `writing-claims` — failure reports are claims; same verification discipline.
- `think` — once diagnosis identifies the right layer (and the causal-path trace identifies the suspect step), design the fix at that step per the think gate.
- `brain-first` — checking durable-commit evidence first is the diagnosis-shaped version of "check existing state before recreating."

## Vocabulary

- **Commit-point** — the moment the substantive work became *durable* (fsync, COMMIT, ACK, downstream-observable). Substrate-specific; substrate-listed above.
- **Signal-point** — the moment the failure status was *set* (exit code emitted, FAILED badge written, error frame raised). Substrate-specific; not necessarily where it was observed.
- **Causal path** — the enumerable sequence of steps the system actually ran between commit-point and signal-point. Unit-of-step varies by substrate (statement, function, hook, trigger, trap, wrapper observer); the discipline of enumerate-then-bisect does not.
- **Durable-commit evidence** — observable proof that the commit-point was reached. Always observable by a process other than the writer (fresh transaction, fresh process, downstream consumer).

## Attribution Policy

NEVER include AI or agent attribution in diagnosis notes, post-mortems, or any output.
