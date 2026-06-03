# Skill Resolver

**You MUST consult this resolver as the first step of any non-trivial task.** When a task pattern below matches what you're about to do, READ the mapped skill(s) before proceeding. Not after. Not "I know what it says." Read.

This is the enforcement layer for every skill in this collection and the electinfo collection. Skills are only useful if they fire before action.

---

## Trivial vs. Non-Trivial

**Trivial** — no skill consultation required:
- Read-only: search, grep, read, list, explain
- Single-file, single-line reversible edits (undone by `git restore`)
- Exploratory questions / analysis with no file writes
- Draft content not yet committed

**Non-trivial** — resolver must be consulted, appropriate skill invoked:
- Any `git commit`, `git push`, branch create/delete, merge, rebase, reset
- Any write to data files, schemas, Hydra configs, Pydantic models, Parquet/Delta
- Code file writes touching public APIs, imports, or library interfaces
- Ticket creation, PR creation, issue updates, any external API write
- Infrastructure changes: K8s, Airflow DAGs, Rundeck YAML, Spark CRDs
- Documentation writes spanning multiple repos
- Session wrap-up / end-of-session actions

**Rule:** if it cannot be undone with `git restore` or `rm`, it is non-trivial. All commits are
non-trivial — diff size does not matter.

---

## THE FIRST GATE: `think`

> **The most important skill in this entire chain is `think`.** Every catalog-bypass, every premature cutover, every half-designed pipeline this resolver exists to prevent traces back to acting before thinking.

Before ANY of the following, you MUST read `skills/thinking/think/SKILL.md` and produce a written design note:

- Implementing a new feature
- Refactoring existing code
- Changing architecture (new layer, new catalog, new data path, new integration)
- Making a cutover (moving Consumer / production traffic to a new source)
- Proposing a schema change
- Building a new skill, hook, or enforcement mechanism (yes, including this resolver itself)
- Any task estimated > 30 minutes

**Explicit exemptions** (from `think` skill): changes to non-executable content only (markdown prose, comments with no functional effect, whitespace), following step-by-step instructions from the user, research/read-only work. Any change to executable code (`.sh`, `.py`, `.sql`, `.js`, `.ts`, etc.) requires the full pipeline. See #338.

The `think` gate is not a pattern-match entry below — it is the **first gate**. Every other pattern in this resolver assumes `think` has already fired.

**Companion gate: `survey-context`.** When the task references existing entities (models, tables, functions, files, APIs, env vars), `skills/thinking/survey-context/SKILL.md` is the author-time counterpart to the static scanner. Run it before authoring code that touches existing infrastructure. Pairs with `think` Step 1 (Context) and self-review's `Goal source:` field.

**Post-think pipeline: `investigate` → `pre-mortem`.** After think produces a design note and the user approves, the investigation and risk gates fire before implementation:

1. **`investigate`** (`skills/thinking/investigate/SKILL.md`): Evidentiary fact-finding. Produces a Fact Sheet with file:line citations, impact chain (upstream → task → downstream), data shape verification, coherence check, and hypothesis/falsification. Investigation is non-discretionary — it gates ALL artifact CRUD, not just code files. Skill/hook/rule edits are the highest-stakes class (the recursive case) and are never exempt. Two tiers: Full (all sections) for cross-module work, Focused (4 sections) for 1-2 file changes with no interface impact. Hard rule: "File:line or it didn't happen."

2. **`pre-mortem`** (`skills/thinking/pre-mortem/SKILL.md`): Adversarial risk classification using Tiger / Paper Tiger / Elephant framework. Operates on the Fact Sheet — not speculation. Each scenario must pass a coherence check (does it logically follow from the evidence it cites?) before classification. Launch-Blocking Tigers halt implementation until mitigated. Paper Tigers must cite their mitigation. Elephants are named with deferral rationale.

3. **`post-mortem`** (`skills/post-mortem/SKILL.md`): Triggered by confirmed failures (shipped bug, materialized Tiger, misclassified Paper Tiger). Traces backward through the skill pipeline to identify where the failure could have been caught — including whether coherence checks ran at each gate. When root cause is a skill/hook/rule deficiency, action items must fix the pipeline artifact (the recursive case). Action items must be testable, must pass the Allspaw test, and must update skills — not just code.

**Coherence is checked at every stage:** investigate Phase 5 (do the findings agree with each other?), pre-mortem Step 3 (does each scenario follow from its cited evidence?), self-review Lead Phase A (do the artifacts form a consistent logical structure?). Internal coherence first, then external verification.

The full pipeline: think → investigate → pre-mortem → implementation → self-review → (on failure) post-mortem.

---

## How to use

1. **`think` first** if the task has architectural or blast-radius implications (see above).
2. Scan the task patterns below.
3. If any pattern matches, `cat` the mapped SKILL.md and read it in full.
4. If multiple patterns match, read all of them.
5. Only then take the action.
6. If no pattern matches but the action has non-trivial blast radius (data writes, mutations to shared systems, infra changes), consult the **universal checks** at the bottom.

---

## electinfo Workspace Overrides

These rules take precedence over anything in individual skill files:

1. **Git remotes:** Always use HTTPS with `${GITHUB_PERSONAL_ACCESS_TOKEN}`. Never SSH. See `[skill:git]`.
2. **Ticket creation:** Use `[skill:qaticket]` — defaults to adam@elect.info assignee, Engineering team, QA label. The generic `planning/create-ticket` skill is a fallback only for non-Linear/non-GitHub platforms.
3. **No AI attribution:** No `Co-Authored-By`, no bot markers, no tool credits anywhere in commits, tickets, or docs.

### electinfo-specific routing

| Trigger | Skill |
|---|---|
| Editing `rundeck/jobs/fec-enterprise/*.yaml` | `enterprise-spark-jobs/SKILL.md` + `git-workflow/commit/SKILL.md` |
| Spark executor OOM, exit code 52, memory tuning | `enterprise-spark-jobs/SKILL.md` |
| Debugging or retrieving a Rundeck execution log | `rundeck-logs/SKILL.md` |
| Posting comments to Linear or GitHub issues | `adammode/SKILL.md` (prepends `From adam@elect.info:`) |
| Creating a ticket in Linear or GitHub | `qaticket/SKILL.md` |
| Any Delta/Parquet write to S3 bronze/silver/gold | `infrastructure/unity-catalog/SKILL.md` |
| PostGIS queries, spatial joins, ST_* functions | `coding/postgis/SKILL.md` + `analysis/spatial/SKILL.md` |
| Session end, committing work | `session/wrap-up/SKILL.md` + `git-workflow/commit/SKILL.md` |

---

## Project-specific rules and skills

Some repositories have project-specific rules and skills that supplement (and can override) the general set. Project source lives under `projects/<project-slug>/`. When published, **project skills and rules are prefix-flattened so the slug fully encodes the project** — no shadowing, no per-context disambiguation at load time. See [projects/CONTRIBUTING.md](projects/CONTRIBUTING.md) for the authoring convention.

### Naming convention (prefix-flatten)

| Source path | Flat slug | Flat file |
|---|---|---|
| `projects/<project>/skills/<skill>/SKILL.md` | `<project>--<skill>` | `skills/<project>--<skill>/SKILL.md` |
| `projects/<project>/_rules.md` | `<project>--rules` | `skills/_<project>--rules.md` |
| `projects/<project>/PROJECT.md` | (not a routing target) | `projects/<project>/PROJECT.md` |

Tokens use the prefixed slug directly: `[skill:siege-utilities--hostile-review]`, `[rule:siege-utilities--rules]`.

### Precedence model

Items marked **[build-enforced]** are validated by `bin/build.py`. Items marked **[convention]** are author-discipline; the build cannot check them.

1. **Routing entries are conditional.** [convention] The agent only invokes a `<project>--<skill>` skill when the routing entry that references it is in scope — typically when the working directory matches the project's `repo:` field. The build validates that token references resolve to existing slugs, but cannot validate trigger semantics.
2. **No implicit shadowing.** [build-enforced] A project skill with the same base name as a general skill produces two distinct flat slugs (e.g., `siege-utilities--self-review` and `self-review`). The build rejects collisions between project and general slugs. Which one fires is set by the routing entry, not by precedence rules at load time.
3. **Weakening overrides must be declared.** [convention] If a project rule weakens a general rule (permits something the general rule prohibits), it must appear in the project's Overrides table in `_rules.md`. An undeclared weakening is void — the general rule wins. The build cannot detect semantic weakening; this is enforced at PR review.
4. **No cross-project inheritance.** [convention] Project B cannot reference or import Project A's rules. Each project is a self-contained overlay on the general set.
5. **Scope is repo-bound.** [convention] Project rules and the conditional routing entries below activate when the working directory matches the `repo` field in `PROJECT.md`. The build validates that `repo:` is present and unique across projects, but does not verify that the repo exists or that the working directory matches at runtime. The prefixed slugs remain visible in the catalog regardless — they're addressable but not invoked out of scope.

### Active projects

| Project | Repo | Rules | Skills |
|---|---|---|---|
| `siege-utilities` | `siege-analytics/siege_utilities` | `siege-utilities--rules` | `siege-utilities--hostile-review`, `siege-utilities--notebook-impact`, `siege-utilities--error-path-tests` |

### siege-utilities-specific routing

These triggers apply only when the working directory matches `siege-analytics/siege_utilities`.

| Trigger | Skill |
|---|---|
| Any PR or code review in siege_utilities | `siege-utilities--hostile-review` |
| Any change to a function signature, return type, or exception contract | `siege-utilities--notebook-impact` |
| Adding or backfilling error-path tests, SU-4b compliance | `siege-utilities--error-path-tests` |
| Auditing error-path test coverage for any module | `test-coverage-audit` |
| `except Exception: pass` or `except: pass` anywhere | Bug — see `siege-utilities--rules` (SU-1) |
| Function returns empty DataFrame/list/dict/string on error path | Bug — see `siege-utilities--rules` (SU-1) |
| Code under `examples/` or `notebooks/` | Held to library standard — see `siege-utilities--rules` (SU-3) |

### How to add a project

See [projects/CONTRIBUTING.md](projects/CONTRIBUTING.md) for the full authoring workflow. Short version:

1. Create `projects/<slug>/PROJECT.md` with name, repo, scope, owners, and key invariants.
2. Create `projects/<slug>/_rules.md` with project-specific rules and an Overrides table (even if empty).
3. Add project-specific skills under `projects/<slug>/skills/<skill-name>/SKILL.md`.
4. Add the project to the Active projects table above and create a project-specific routing subsection beneath it.
5. PR to this repo with evidence for why the rules exist (at minimum: one incident or audit finding per rule).

---

## Task patterns → required skills

### Data, catalogs, storage

| About to… | Read first |
|---|---|
| Write Delta/Parquet/Iceberg to any path | `skills/infrastructure/unity-catalog/SKILL.md` |
| Use `.write.save(...)`, `.write.parquet(...)`, or any raw-path write | `skills/infrastructure/unity-catalog/SKILL.md` |
| Use `saveAsTable(...)` | `skills/infrastructure/unity-catalog/SKILL.md` |
| Register a table in Hive Metastore or Unity Catalog | `skills/infrastructure/unity-catalog/SKILL.md` |
| Touch `s3a://hive-warehouse/*`, `s3://silver/*`, `s3://gold/*`, or any shared bucket | `skills/infrastructure/unity-catalog/SKILL.md` |
| Run a batch data processing job | `electinfo_claude_skills/skills/pipeline-guard/SKILL.md` |
| Schedule a recurring pipeline job | `skills/coding/pipeline-jobs/SKILL.md` + `electinfo_claude_skills/skills/rundeck-job/SKILL.md` |

### Writing code

| About to… | Read first |
|---|---|
| Write Python | `skills/coding/SKILL.md` → `skills/coding/python/SKILL.md` |
| Write SQL (Postgres/PostGIS/SparkSQL) | `skills/coding/SKILL.md` → `skills/coding/sql/SKILL.md` |
| Write PySpark / use DataFrame API / write to Delta | `skills/coding/SKILL.md` → `skills/coding/spark/SKILL.md` + `skills/infrastructure/unity-catalog/SKILL.md` |
| Write a pipeline / ETL / scheduled data job | `skills/coding/pipeline-jobs/SKILL.md` |
| Write a Rundeck job YAML | `electinfo_claude_skills/skills/rundeck-job/SKILL.md` |
| Review existing code (yours or others') | `skills/coding/code-review/SKILL.md` |
| Review an extracted QML component (properties-in / signals-out, MuseScore plugins) | `skills/coding/qml-component-review/SKILL.md` |
| Write Scala on Databricks notebooks, `.scala` files, `Dataset[T]` Spark code | `skills/coding/scala-on-spark/SKILL.md` (delegates to `shelves/languages/effective-java/`, `effective-kotlin/`, and `coding/spark/`) |
| Design a service / module boundary | `skills/thinking/think/SKILL.md` (gate) → `skills/shelves/engineering-principles/clean-architecture/SKILL.md` |
| Pick a storage engine, replication scheme, or partitioning strategy | `skills/thinking/think/SKILL.md` (gate) → `skills/shelves/systems-architecture/data-intensive/SKILL.md` |
| Write a Python utility, helper, formatter, validator, file/path/HTTP/spatial helper | `skills/_siege-utilities-rules.md` (check `siege_utilities` first) |
| Do any spatial work — pick engine, write spatial SQL/Python/Scala, run a spatial join | `skills/analysis/spatial/SKILL.md` (router; dispatches to `coding/postgis`, `coding/geopandas`, `coding/sedona`, `coding/duckdb-spatial`) |
| Fix a bug or issue identified by code review / audit / static analysis | `skills/thinking/think/SKILL.md` Step 1 sibling-grep gate is MANDATORY. The audit finding is a hypothesis, not an investigation. The ticket must state: (a) the sibling-set from grep, (b) a falsification criterion per `evaluate-ticket` criterion 6, (c) the test that goes red on revert. Without these three, the fix is untested speculation that happened to compile. |

### Design & planning

| About to… | Read first |
|---|---|
| Implement a new feature, refactor, or architecture change | `skills/thinking/think/SKILL.md` (MANDATORY before any code) → `skills/thinking/investigate/SKILL.md` (Fact Sheet before implementation) → `skills/thinking/pre-mortem/SKILL.md` (Tiger/Paper Tiger/Elephant before implementation) |
| Fix a shipped bug (post-merge, found by user/reviewer/CI) | `skills/post-mortem/SKILL.md` (trace failure through skill pipeline) → then `skills/thinking/think/SKILL.md` for the fix |
| Do spatial / geographic analysis | `skills/analysis/SKILL.md` → `skills/analysis/spatial/SKILL.md` |
| Do statistical / graph / entity-resolution / text analysis | `skills/analysis/SKILL.md` |

### Failure handling

The auto-trigger language in `verify-failure-premise` and `post-error-revision` is honor-system on the agent unless the resolver surfaces it. These rows make that routing explicit. **The first action on any failure is the Pre-fix pause, not the fix.**

| Encountering… | Read first |
|---|---|
| **ANY failure** — non-zero exit, push-hook block, CI red, FAILED badge, runtime exception, blocked merge, customer report, monitor alert | **Pre-fix pause** (writing-rules:6, post-error-revision Step 0): before attempting a fix, ask "what did I believe that this evidence contradicts?" If the answer names a durable artifact (skill / rule / ticket / hook / docstring / Trivial-change block), the contradiction is a writing-rules:6 trigger — route to the next two rows in order. If the answer is "nothing durable — I formed this belief minutes ago," note in-loop+no-contract explicitly and continue. |
| Pre-fix pause found a durable contradiction OR the failure shape is unambiguous (production incident, CI regression caught by a test, revert PR being drafted) | `skills/thinking/verify-failure-premise/SKILL.md` — verify the premise BEFORE debugging the cause; pin commit-point + signal-point; route by did-happen / didn't-happen / ambiguous |
| `verify-failure-premise` resolved AND the failure contradicts an Assumption documented on a ticket, self-review artifact, hook contract, or Trivial-change block | `skills/post-error-revision/SKILL.md` — writing-rules:6 back-edge; append the five-field block to the originating ticket BEFORE drafting the fix or revert PR |

### Git & tickets

| About to… | Read first |
|---|---|
| Create a git branch | `skills/git-workflow/branch/SKILL.md` + `skills/git-workflow/develop-guard/SKILL.md` |
| Create a commit | `skills/git-workflow/commit/SKILL.md` |
| Merge a branch | `skills/git-workflow/merge/SKILL.md` — **self-review gate applies at merge time, not just push time.** Before executing `gh pr merge` or `git merge`, verify the self-review artifact exists and trailers are on the latest commit. If artifacts are missing when told to merge, ask: "Are you telling me to forego review?" A "merge" instruction authorizes the destination, not the method. |
| Open a pull request | `skills/git-workflow/create-pr/SKILL.md` |
| Triage / respond to PR comments | `skills/session/pr-comments/SKILL.md` |
| Create a ticket | `skills/planning/create-ticket/SKILL.md` |
| Create ≥2 tickets in one session (epic breakdown, audit findings, batch triage) | `skills/planning/create-ticket/SKILL.md` + `skills/evaluate-ticket/SKILL.md` per ticket. **Test-before-bulk applies:** create the first ticket, run `evaluate-ticket`, fix gaps until it PASSes, THEN continue to the next. Each ticket is an independent act of investigation, not a line item in a list. |
| Update a ticket (progress comment, field change) | `skills/planning/update-ticket/SKILL.md` |
| Close a ticket | `skills/planning/close-ticket/SKILL.md` |
| Start work on a ticket (first commit, mark In Progress, assign to self) | `skills/planning/pre-work-check/SKILL.md` |
| Execute >=2 tickets in one session (epic work, audit remediation, batch fixes) | `skills/thinking/think/SKILL.md` per ticket (not per epic). Each ticket is a discrete action: own design note, own branch, own self-review. Universal check #10 (batch-execution-is-not-one-action) is the enforcement. The `think` gate fires N times, not once. |

### Documentation

| About to… | Read first |
|---|---|
| Write or update docs in any repo | `skills/documentation/cascading-documentation/SKILL.md` |
| Author a Notion page | `skills/documentation/notion-knowledge-base/SKILL.md` |
| Administer the elect-info Notion workspace | `electinfo_claude_skills/skills/notion-sync-admin/SKILL.md` |
| Consolidate / deduplicate documentation | `skills/maintenance/consolidate/SKILL.md` |

### Session & operations

| About to… | Read first |
|---|---|
| End a session / hand off work | `skills/session/wrap-up/SKILL.md` |
| Spawn sub-sessions / delegate work to parallel agents | Universal check #11 (spawn-protocol). Requires: worktree isolation, checkpoint-and-wait in prompt, artifact attachment to tickets, Phase 0 read instruction. |
| Receive a standing "work until X" instruction from user | Universal check #12 (standing-order continuity). Maintain running agents + ScheduleWakeup at all times. Never go idle with pending work. |
| Recover from a magnum / enterprise-runner outage | `electinfo_claude_skills/skills/monitor-magnum/SKILL.md` |
| SSH to a shared server / launch a batch job / triage server health | `skills/infrastructure/ops/SKILL.md` |
| Create a new skill | `skills/meta/skillbuilder/SKILL.md` |

---

## Universal pre-action checks (always apply)

These fire for every non-trivial action, regardless of whether a pattern above matched:

0. **THINK FIRST** (the non-negotiable gate): for anything beyond a change to non-executable content only (markdown prose, comments with no functional effect, whitespace), read `skills/thinking/think/SKILL.md` and write a design note. Any change to `.sh`, `.py`, `.sql`, `.js`, `.ts`, or other executable code is non-trivial — the Junior cannot classify code changes out of the pipeline. If you can't state what you're about to do, why, what could go wrong, and what the rollback looks like — you are not ready to act. Every serious failure in this session traces back to skipping this. **Signal file:** after producing the design note, write `<workspace>/think-gate.json` with falsifiable claims encoding design premises. The `think-gate-guard.sh` hook verifies claims every turn; stale claims force re-examination. When encountering a stale signal file from a prior task, read the referenced design note, post a disposition comment on the prior ticket, then update or delete the signal file. **Class-of-bug fixes** (same pattern in multiple files) require at least one Schema A claim (file + grep + expected) asserting zero remaining unguarded instances. See #262, #338.

1. **Catalog-first**: if the action touches data that lives under a catalog (Unity Catalog, Hive Metastore), go through the catalog. Never write raw paths to bucket locations the catalog manages. Confirm the table's registered location BEFORE writing.

2. **Brain-first** (borrowed from GBrain): before calling any external API or running any mutation, check if we have the answer / target already. Re-use before recreating.

3. **Verify-failure-premise**: before debugging a reported failure (someone else's report OR your own non-zero exit), confirm the work actually didn't durably commit. Look at **durable-commit evidence** (fsync / COMMIT / ACK / downstream-observable in a fresh transaction or process), NOT the failure signal. If evidence says the work succeeded, the reporter is the bug — trace the **causal path** from commit-point to signal-point (enumerate every step between durability and the FAILED status; bisect by instrumentation, not hunch). See `skills/thinking/verify-failure-premise/SKILL.md`. Iron law: state the evidence verdict (did-happen / didn't-happen / ambiguous) explicitly before picking an investigation layer; pin both pivots before tracing.

4. **Test-before-bulk**: any batch operation (≥20 items) runs on 3–5 items first, verifies, then scales.

5. **Ticket-required + Epic-in-project + Dependency-clear**: Any work that creates a change in state or behavior of the software that will impact the product requires a ticket. Typographical corrections with no functional effect are exempt. That ticket must belong to a project or epic — unprojected tickets are not worked. All blocking upstream tickets must be Done before you start. Include the ticket reference in every commit. Read `skills/planning/pre-work-check/SKILL.md` before starting any such work.

6. **Branch-correct**: you are on a feature branch, not main / master / develop, for any write. The PR base is `develop` (or its synonym — `dev`, `development`, `staging`, `next`, `integration`, `trunk`), NOT `main`. **Invariant:** develop is the origin of all work. `main` is downstream of develop, never upstream of unblessed work. Recurring stale-develop is workflow drift to *repair*, not a workflow to *accept*. If `develop` is missing or stale, STOP and ask the user — do not silently create develop, do not silently fall back to main, and do not patch the rule to accommodate the violation. See `skills/git-workflow/develop-guard/SKILL.md`.

7. **Dual-mirror check** (for dual-tracked repos electinfo↔gitlab): after acting on one side, mirror to the other.

8. **No-attribution**: never add Claude/AI attribution to commits, PRs, or public-facing content.

9. **Measure twice, cut once**: for destructive or irreversible actions (drops, deletes, force-push, hard-reset), confirm scope first. More broadly: the Junior optimizes for speed of one task; the Lead optimizes for speed of the project. Every 2-second check the agent skips costs the human operator hours of rework. The agent's seconds are cheap; the human's hours are not. This is not caution — it is resource allocation.

10. **Batch-execution is not one action**: when executing multiple tickets, issues, or tasks in sequence (epic breakdown, audit remediation, batch triage fixes), each ticket is a separate non-trivial action. Each gets its own `think` gate (design note), its own branch, its own self-review artifact. "I'm doing 8 tickets" is 8 actions, not 1 action done 8 times. No amortization of investigation, design, or review across tickets. The agent will take any excuse to skip per-ticket discipline during batch work — speed, momentum, "they're all similar," "I already understand the pattern." These are the Junior's rationalizations. The gates exist precisely for the moments when skipping them feels efficient.

    **Mechanical test:** if you are about to commit work for ticket N+1 without having produced a design note for ticket N+1 specifically (not "the epic design note that covers all of them"), you are violating this check. Stop and produce the note.

    **Interaction with test-before-bulk (#4):** test-before-bulk applies to batch data operations (20+ items). This check applies to batch ticket execution (2+ tickets). They are complementary: test-before-bulk prevents data damage from untested batch operations; batch-execution-is-not-one-action prevents quality damage from uninvestigated batch implementations. Both fire when the agent is doing "many of something."

11. **Spawn-protocol**: when spawning sub-sessions (via `spawn_session`, `Agent`, or any delegation mechanism) for work that writes code or creates commits:

    a. **Check for existing WIP and prior resolution before spawning.** Before creating a session for ticket N, perform two checks:

       **Check 1 — branch exists?** `git branch -r --list "origin/fix/*N*" "origin/feat/*N*"`. If found, inspect (commits ahead of develop, PR state via `gh pr list --head`):
       - Branch exists + PR already open → do NOT spawn; review the PR instead.
       - Branch exists + no PR → inspect commits; decide whether to push+PR (work complete) or resume (work incomplete).
       - No branch → proceed to Check 2.

       **Check 2 — already resolved on develop?** `git log origin/develop --oneline --grep="N"` (where N is the ticket number). If a fix commit is already merged:
       - Verify the ticket is closed or the code matches the fix description.
       - If resolved → do NOT spawn; close the ticket if still open and move on.
       - If ambiguous → spawn with explicit instruction to verify-before-implementing.

       (Incidents: (1) successor session spawned agent for #692 which was already committed and PR'd. (2) Spawned agents for #690 and #689 which were already fixed on develop — agents correctly identified this but wasted startup time re-deriving what a 2-second `git log --grep` would have shown.)

    b. **Worktree isolation is required.** Parallel sessions sharing a single working tree cause stash collisions, branch drift, and commits landing on wrong branches. Use `isolation: "worktree"` or equivalent. If the tool doesn't support isolation (e.g., `spawn_session` has no worktree parameter), instruct agents to create their own worktree in the prompt: `git worktree add /tmp/fix-NNN origin/develop && cd /tmp/fix-NNN`. If worktrees are impractical, serialize — do not run parallel sessions on a shared checkout. (Incident: siege_utilities #800 session had its uncommitted edits stashed by sibling session #801; commit later landed on wrong branch via checkout race.)

    c. **Supervised vs unsupervised determines checkpoint behavior.**
       - **Supervised** (coordinator session is actively monitoring — has ScheduleWakeup or is in interactive mode with user): agents run self-driving. They post artifacts to tickets and continue without waiting. The coordinator reviews asynchronously and sends corrections via `send_agent_message` if needed.
       - **Unsupervised** (spawning into an unmonitored window — overnight, fire-and-forget): use checkpoint-and-wait. The prompt must include explicit checkpoints where the session stops and routes work back to the coordinator before proceeding. Checkpoints: (1) design note, (2) investigation findings, (3) implementation complete (no PR yet), (4) self-review artifact. At each: "send to coordinator via `send_agent_message` and WAIT for reply before proceeding." Do NOT rely on follow-up messages to redirect — they arrive too late.
       (Incident rationale: self-driving was validated for supervised sessions in the #776 batch. Checkpoint-and-wait prevents runaway agents in unmonitored windows. Both are correct — in different contexts.)

    d. **Attach artifacts to tickets, not just session plans.** Session-scoped plan files are ephemeral. The coordinator must ensure that investigation Fact Sheets and self-review artifacts are posted to the ticket as comments (or committed to the repo and linked from the ticket) before the session is dismissed. The next agent who works on related code must be able to find these artifacts without re-deriving them.

    e. **Investigation reads existing knowledge.** The spawn prompt must instruct the session to check for prior investigations, related tickets, and existing documentation before starting its own investigation (see `investigate` skill Phase 0). Re-deriving facts already documented elsewhere is wasted work.

    **Mechanical test:** if you are about to call `spawn_session` without (a) checking for existing WIP branches AND (b) either checkpoint instructions (unsupervised) or ticket-posting instructions (supervised) in the prompt, you are violating this check.

12. **Standing-order continuity**: when the user gives a standing instruction to work autonomously until a specified time or condition ("work until 10:00 AM", "keep going overnight", "clear as much ground as you can"), that instruction is a **standing order**. Think of it as shift work: you know what you are supposed to be doing, do it according to the rules, and only ask for help when it becomes necessary.

    ### Signal file

    Standing orders are mechanically enforced via a signal file at `<workspace>/standing-order.json`. The `standing-order-guard.sh` hook reads this file on every `UserPromptSubmit` and injects the shift directive. This means **even loop prompts and stacked messages** carry the standing order.

    **Lifecycle:**
    - **Activation:** When you receive a standing order, write the signal file:
      ```json
      {
        "active": true,
        "deadline": "2026-05-29T10:00:00-05:00",
        "directive": "Work Epic #776 tickets using the skills pipeline",
        "work_queue": ["#816", "#768"]
      }
      ```
    - **Update:** Keep `work_queue` current as items complete.
    - **Deactivation:** When the deadline passes, all work exhausts, or the user cancels, delete the file or set `"active": false`.

    ### Rules of the shift

    a. **Idle state is a violation.** At no point during a standing order may the agent be idle — defined as: no running agents, no scheduled wakeup, no active tool call, AND pending work remains. All three absent simultaneously with work remaining is equivalent to ignoring a direct instruction.

    b. **"No response requested" is never valid during a standing order.** The standing order IS the request. Only the user, the deadline, or the exhaustion of all work items terminates it. Stacked loop prompts, absence of user messages, and "the user said no response requested to an earlier message" are not termination signals.

    c. **ScheduleWakeup is mandatory, not optional.** When the agent's turn ends with background agents still running, it MUST schedule a wakeup. Failure to schedule a wakeup when agents are running is the mechanical root cause of the overnight-idle incident.

    d. **End-of-turn saturation.** Before ending any turn during a standing order, verify: "Is there work I could spawn right now that I'm not spawning?" If the answer is yes and resources allow, spawn it.

    ### Mandatory loop prompt template

    When scheduling a ScheduleWakeup during a standing order, the `prompt` field MUST be a directive, not a description. Use this template:

    ```
    Standing order active — [DIRECTIVE]. Check on running agents, spawn
    new work for any completed items, update the signal file work queue.
    Do not stop until the deadline or all work is exhausted.
    ```

    Do NOT use prompts like "check on progress" or "continue if needed" — these create an off-ramp the agent will take.

    **Mechanical test:** if you are about to end a response during a standing order without either (a) a ScheduleWakeup call in this response, or (b) all work items exhausted, you are violating this check. The `standing-order-guard.sh` hook will remind you on the next turn, but you should not need the reminder.

    **Incident justification:** Epic #776 dogfood session (2026-05-28/29). Agent went idle 7 hours overnight (no ScheduleWakeup after last agent completed) and produced "No response requested" twice when loop prompts stacked up. Root cause: rules alone don't prevent the agent from rationalizing inaction. The signal file + hook injection makes the standing order mechanically persistent — it cannot be "forgotten" or rationalized away because it is re-injected on every turn.

12. **Standing-order continuity**: when the user gives a standing instruction to work autonomously until a specified time or condition ("work until 10:00 AM", "keep going overnight", "clear as much ground as you can"), that instruction is a **standing order**. Think of it as shift work: you know what you are supposed to be doing, do it according to the rules, and only ask for help when it becomes necessary.

    ### Signal file

    Standing orders are mechanically enforced via a signal file at `<workspace>/standing-order.json`. The `standing-order-guard.sh` hook reads this file on every `UserPromptSubmit` and injects the shift directive. This means **even loop prompts and stacked messages** carry the standing order.

    **Lifecycle:**
    - **Activation:** When you receive a standing order, write the signal file:
      ```json
      {
        "active": true,
        "deadline": "2026-05-29T10:00:00-05:00",
        "directive": "Work Epic #776 tickets using the skills pipeline",
        "work_queue": ["#816", "#768"]
      }
      ```
    - **Update:** Keep `work_queue` current as items complete.
    - **Deactivation:** When the deadline passes, all work exhausts, or the user cancels, delete the file or set `"active": false`.

    ### Rules of the shift

    a. **Idle state is a violation.** At no point during a standing order may the agent be idle — defined as: no running agents, no scheduled wakeup, no active tool call, AND pending work remains. All three absent simultaneously with work remaining is equivalent to ignoring a direct instruction.

    b. **"No response requested" is never valid during a standing order.** The standing order IS the request. Only the user, the deadline, or the exhaustion of all work items terminates it. Stacked loop prompts, absence of user messages, and "the user said no response requested to an earlier message" are not termination signals.

    c. **ScheduleWakeup is mandatory, not optional.** When the agent's turn ends with background agents still running, it MUST schedule a wakeup. Failure to schedule a wakeup when agents are running is the mechanical root cause of the overnight-idle incident.

    d. **End-of-turn saturation.** Before ending any turn during a standing order, verify: "Is there work I could spawn right now that I'm not spawning?" If the answer is yes and resources allow, spawn it.

    ### Mandatory loop prompt template

    When scheduling a ScheduleWakeup during a standing order, the `prompt` field MUST be a directive, not a description. Use this template:

    ```
    Standing order active — [DIRECTIVE]. Check on running agents, spawn
    new work for any completed items, update the signal file work queue.
    Do not stop until the deadline or all work is exhausted.
    ```

    Do NOT use prompts like "check on progress" or "continue if needed" — these create an off-ramp the agent will take.

    **Mechanical test:** if you are about to end a response during a standing order without either (a) a ScheduleWakeup call in this response, or (b) all work items exhausted, you are violating this check. The `standing-order-guard.sh` hook will remind you on the next turn, but you should not need the reminder.

    **Incident justification:** Epic #776 dogfood session (2026-05-28/29). Agent went idle 7 hours overnight (no ScheduleWakeup after last agent completed) and produced "No response requested" twice when loop prompts stacked up. Root cause: rules alone don't prevent the agent from rationalizing inaction. The signal file + hook injection makes the standing order mechanically persistent — it cannot be "forgotten" or rationalized away because it is re-injected on every turn.

13. **Verify-before-push**: the self-review skill's mechanical verification floor (Gates 1–4) is **non-negotiable**. Before any `git push`, all applicable gates must have run and their evidence must appear in the self-review artifact:

    - **Gate 1** — `ast.parse` on every changed `.py` file.
    - **Gate 2** — `pytest tests/ -x -q -o "addopts=" -m smoke` (exit 0).
    - **Gate 3** — `sphinx-build -q docs/source/ /tmp/docs-verify` (exit 0), required when any file under `docs/` was modified.
    - **Gate 4** — Notebook API verification: every library call in changed `.ipynb` files grep-verified against source. Required when any `.ipynb` is in the diff.

    **Scope rationalizations are the exact failure mode these gates exist to prevent.** "Doc-only changes can't break tests," "config-only changes don't need a build," "test-only changes are self-verifying," "the notebook runs so the API must be right" — these are the sentences the Junior says right before pushing a broken commit. The gates are fast (seconds). The rework from skipping them is hours.

    **Mechanical test:** if a self-review artifact lacks Gate 1 and Gate 2 evidence lines, the push MUST NOT proceed. If `docs/` was modified and Gate 3 evidence is missing, the push MUST NOT proceed. If `.ipynb` files are in the diff and Gate 4 evidence is missing, the push MUST NOT proceed.

    **Incident justification:** Session 260603-golden-shark (2026-06-03). Four PRs merged across #816, #580, #970 without running `pytest` or `sphinx-build` once. Every self-review declared "trivial — doc/notebook only" and skipped verification. Zero of the four were actually verified before push. Hostile review then found 3 S2 notebook bugs (wrong method name, false narrative claims, output contradicting story) that Gate 4 would have caught mechanically.

---

## What if nothing matches?

If you're doing something truly novel that no skill covers, default to:

1. **Read `skills/thinking/think/SKILL.md`** and write a brief design note.
2. **Confirm with the user** before acting if blast radius is non-trivial.
3. **File a skill-creation task** if this turns out to be a recurring pattern — see `skills/meta/skillbuilder/SKILL.md`.

---

## Enforcement

This resolver is surfaced into every session via:

- **Session start**: referenced from every project's CLAUDE.md.
- **Every user turn**: injected via `UserPromptSubmit` hook (`hooks/resolver/inject-resolver.sh`) so it stays in active context.
- **Pre-tool-use**: `PreToolUse` hooks on `Bash` match dangerous catalog/data-write patterns and block with a STOP-read-skill reminder (`hooks/infrastructure/catalog-guard.sh`). The git / PR hook stack is also enforced at `PreToolUse`:
  - `hooks/git/branch-guard.sh` blocks direct commits to protected branches.
  - `hooks/git/pr-base-guard.sh` blocks PR/MR-create commands whose effective base is a main-role branch when the head is not develop-role / `release/*` / `promote/*` / `hotfix/*` (or carries the `hotfix-direct-to-main` bypass label). Catches both GitHub (`gh pr create --base`) and GitLab (`glab mr create --target-branch`); see CCP#201 for the GitLab-parity addition. This is the local mechanical enforcement of `skills/git-workflow/develop-guard/SKILL.md` — the skill is the prose layer; the hook closes the gap when the agent treats PR/MR-create as procedural and never consults the skill.
  - `hooks/git/self-review.sh` blocks push / PR/MR-create / PR/MR-merge without Self-Review trailers (both `gh pr create|merge` and `glab mr create|merge`).

Skills collection paths (all relative to their repo roots):

- **Siege (this repo)**: `~/git/electinfo/claude-configs-public/skills/`
- **Electinfo**: `~/git/electinfo/electinfo_claude_skills/skills/` (includes a subtree of siege skills under `skills/siege/` plus electinfo-specific skills at the top level)

---

## Disambiguation rules

1. **Prefer the most specific skill.** `coderabbit-response` beats `code-review` when a bot posted the review.
2. **Skills chain explicitly.** `create-pr` → `commit` → `branch` in reverse.
3. **Conventions always apply.** Every skill that writes a commit reads `_output-rules.md` first.
4. **Router sub-skills load only when triggered.** A `.py` file without `pyspark` imports doesn't load `coding/spark/`.
5. **When in doubt, ask the user.**
