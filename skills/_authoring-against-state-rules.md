---
description: Always-on. Investigation-as-deliverable discipline for code, config, and commands whose runtime behavior depends on the state of an external resource. The author must read the inputs (ticket, epic, documentation), enumerate the knowledge requirements (the open questions whose answers determine how the code is written), measure the contact-point surfaces (rules 1-5), record the findings in the ticket itself, and state the falsifiable truth-functional hypothesis the code will implement (rule 6), before authoring. Sibling to writing-code (verify-before-touching-code) and writing-claims (verify-before-claiming) -- this file covers verify-the-external-state-before-writing-against-it and the requirement that both the verification artifact and the spec the code is to satisfy live in the ticket, not in chat.
---

# Authoring Against State

These rules apply whenever the agent writes code, configuration, or commands whose runtime behavior depends on the state of an external resource the author has not just inventoried in the same response.

The existing shelves treat the diff as the unit of work. `[rule:writing-code]` verifies symbols and shapes within the code; `[rule:writing-claims]` verifies facts the diff asserts; `[rule:verify-before-execute]` requires same-turn evidence for any side-effecting action. None compel the author to measure the **external** state -- the state of the cluster, the data, the runtime topology, the version actually resolved at runtime -- that the code will encounter.

Tonight's failure mode (recurring across electinfo/enterprise#2076-#2093 between 2026-05-22 and 2026-05-23): correctly-written code, shipped under correctness-shaped review, that assumed a runtime reality which had drifted from the author's mental model. The diff was right relative to imagined state. It was wrong relative to measured state. Six distinct production failures in one backfill cycle, each preventable by a one-line measurement command run before the code was written.

These rules close that category by making the measurement compulsory at write time, **with the output retained in the ticket so the next author doesn't have to re-discover.** The shelf has two layers: rules 1-5 specify WHAT to measure (the contact-point categories); rule 6 specifies HOW the act is performed (read the inputs; enumerate the knowledge requirements -- the open questions whose answers determine how the code is written; apply rules 1-5 plus a broader surface scan to answer them; record findings; state a falsifiable hypothesis of what the code will implement) and WHERE the record lives (in the ticket body, not in chat, not in agent memory). Rules 1-5 without rule 6 reduce to "the author measured something then forgot it"; rule 6 without its knowledge-requirements clause reduces to "the author measured what they happened to think of and missed the rest"; rule 6 without its inventory clause reduces to "the author wrote a section header in the ticket and called it done"; rule 6 without its hypothesis clause reduces to "the author recorded what was true but never wrote what they intended to make true, so the reviewer has nothing to check the diff against." All four pieces -- enumerated questions, inventory of measured state, inventory of other surfaces, and falsifiable hypothesis of intended end-state -- are required. The four map onto rule 6's seven-step procedure as follows: steps 1+2 produce the questions (read the inputs; enumerate what we need to know); steps 3+4 produce the inventories (rule-1-to-5 contact-point measurements; other surface areas); steps 5+6 govern recording (write findings into the ticket; state what was NOT measured); step 7 produces the hypothesis. Each piece is a separate failure mode if skipped; the seven steps make the four pieces operationally inviolable rather than structurally implicit.

## Scope: cross-platform

The concrete examples in each rule's "Concrete measurements" block come from the Spark / Kubernetes / Rundeck / Unity Catalog stack the shelf was forged against (the electinfo incident chain). They are illustrative, not definitive. The *act* of measure-before-write applies regardless of platform: any contact category that maps to "code or config whose behavior depends on a measurable external state the author has not just inventoried" triggers the rule. A consumer working in a different stack (e.g. a Go service against PostgreSQL + Redis, a frontend against a REST API, an embedded device against a hardware bus) reads the contact category, identifies the analogous measurement, and runs that.

## The rules

**authoring-against-state:1. Data-shape contact -- measure the actual data before writing code that consumes it.**

When the code being written reads, joins, unions, or aggregates external data, and the runtime behavior depends on the data's shape (row count, row size, partition layout, cardinality), the author must measure the actual shape before writing the code. Estimates derived from the diff alone are insufficient; the measurement must come from the live source.

Concrete measurements, in increasing thoroughness:

```bash
# Row count
spark.read.table("X.bronze.sb_2024").count()
# Or via the catalog API for paginated table list
curl -s "$UC_API/tables?catalog_name=X&schema_name=bronze" | jq '.tables | length'

# Average row size (crude, usually within 2x)
spark.read.parquet("s3a://bucket/path/").limit(1000).rdd.map(lambda r: len(str(r))).mean()

# Distribution / skew (when join keys or partition columns are involved)
spark.read.table("X.silver.f3").groupBy("filer_committee_fec_id").count().agg(F.expr("percentile_approx(count, array(0.5, 0.9, 0.99))"))
```

The measurement output goes in the authoring artifact -- commit body trailer (`Inventoried-shape:` line), PR description "Inventory" section, or `pre-write-inventory.md` artifact in the same change-set. The output IS the record of the measurement; absence equals "the author asserted shape without measuring."

**Trigger:** any change to pipeline transformation code (DLT MV bodies, Spark SQL, ETL job logic, materialization functions) where the upstream data could have changed shape since the last time the agent worked in this area. New session counts as new -- prior-session memory of data shape is stale by default.

**Composes with `[rule:writing-claims]` writing-claims:1.** writing-claims:1 says "grep before declaring complete." authoring-against-state:1 says "measure before declaring the consumer code will fit." The two together close the "wrote code that's right against imagined data, wrong against measured data" failure mode.

**authoring-against-state:2. Config-state contact -- read the actual cluster config before writing code that runs under it.**

When the code being written will run under runtime config (memory limits, timeouts, page sizes, recursion depths, parallelism counts), the author must inventory the actual config values from the cluster -- not the values the author remembers or the values documented in a skill -- before writing assumptions into the code or sizing the work.

Skills go stale; ConfigMaps drift from GitOps source. The cluster is the source of truth at any given moment.

Concrete measurements:

```bash
# Spark Connect server config
kubectl exec -n spark deploy/spark-connect-server -- grep -E '(executor|driver)\.(memory|memoryOverhead|cores)|spark\.dynamicAllocation' /opt/spark/conf/spark-defaults.conf

# Pod container limits (separate concern from JVM heap; both must agree)
kubectl get pod -n <ns> <pod> -o jsonpath='{.spec.containers[*].resources}'

# HTTP timeout in a utility being changed
grep -rn 'timeout=' <util-path>

# Maximum page size / list size for a paginated API
time curl -s '<endpoint>' | jq '.[]' | wc -l
```

The measurement output goes in the authoring artifact, same as authoring-against-state:1.

**Trigger:** code that calls into a service whose limits matter (cluster resource demands, HTTP timeouts, batch sizes, recursion depths). Includes adding a new union upstream, raising parallelism, adding a long-running query, scaling a partition count.

**Composes with the skill's documented minimum.** If a skill says "X must be at least Y," the author must STILL measure -- the skill is the *floor* for spec, the cluster is the floor for reality. Tonight's spark-connect ConfigMap was below the documented EE skill minimum (24g + 8g overhead vs deployed 24g + default ~2.4g overhead) for unknown duration. Author quoting skill memory without measuring is what missed it.

**authoring-against-state:3. Topology contact -- measure pod and node state before targeting them at kick time.**

When the code or command being written targets a specific pod, node, or service (kicks a job whose runtime is a known pod, applies a config to a node, requires a specific runtime to be healthy), the author must measure the runtime's current state before producing the artifact. Topology drifts continuously; "the runner was up two hours ago" is not evidence it is up now.

Concrete measurements:

```bash
# Pod age (startTime) + restart count
kubectl get pod -n <ns> <pod> -o jsonpath='startTime={.status.startTime}; restartCount={.status.containerStatuses[*].restartCount}'

# Recent restart events
kubectl get events -n <ns> --field-selector involvedObject.name=<pod>,reason=Killing --sort-by=.lastTimestamp | tail

# Node health
kubectl describe node <node> | grep -E 'Condition|MemoryPressure|DiskPressure|PIDPressure'

# Node-pinned hostPath dependency check (when pod is pinned via nodeSelector)
kubectl get pod -n <ns> <pod> -o jsonpath='{.spec.nodeSelector}'
```

**Trigger:** any kick of a long-running job (anything that will take more than 5 minutes), any kubectl apply that depends on a target pod being reachable, any operation against a node-pinned hostPath. The trigger fires at the kick, not at the diff that adds the kick.

**Carve-out:** trivial commands (status reads, log fetches, single-line kubectl get) do not require a topology measurement -- the cost-to-recover from a failed read is low. The rule fires when the cost-to-recover is high (a multi-minute job kicked and lost mid-run).

**Composes with `[rule:writing-code]` writing-code:15 (every blocking I/O call declares a timeout).** writing-code:15 protects against unbounded hangs in the code; authoring-against-state:3 protects against kicking into a degraded runtime in the first place. The hang protection is the floor; the topology check is the ceiling.

**authoring-against-state:4. Plan-shape contact -- measure the structural complexity of the plan you are about to author against the serializer's tolerance.**

When the code being written produces a query plan whose complexity depends on the size of an input set (depth of unions chained over N upstreams, breadth of a join across M tables, fan-out of a partition across K keys), the author must measure the expected plan complexity against the serialization layer's known tolerance before writing the code.

Spark Connect's protobuf encoder has practical depth limits in the dozens of nested Relation messages; gRPC has a 4 MiB default message size; JSON has parser-imposed depth limits. Each layer between client and cluster has a quiet ceiling the new plan can exceed.

Concrete measurements:

```bash
# Count of upstream unions in the planned MV body
# (run BEFORE writing the new code, against the current set)
grep -n 'unionByName\|UNION ALL\|union(' <file-being-changed>

# For chained accumulator loops, count the iteration count
python3 -c "from utilities.config import list_partitioned_combinations; print(sum(1 for _ in list_partitioned_combinations()))"

# Maximum plan depth Spark Connect's client tolerates -- known empirically as ~25 nested Union nodes; rule of thumb is "do not chain more than 8 in a single MV body without balancing"
```

If the planned union depth exceeds ~25 in a linear chain, the author has two choices: (a) rewrite as a balanced binary tree (depth = ceil(log2(N))), or (b) materialize at an upstream stage to lower the per-MV input count. Either choice is allowed; the choice not allowed is "write the linear chain and hope it serializes."

**Trigger:** code that chains unions, joins, or other multi-input plan nodes over a set whose size is parameterized by another part of the system (e.g. "one upstream per subschedule" where subschedule count can grow).

**Composes with `[rule:writing-code]` writing-code:3 (no speculative abstractions).** writing-code:3 says "don't build a balanced-tree helper when a linear loop would do." authoring-against-state:4 says "and inversely, don't write a linear loop when the input count would exceed serializer tolerance." Both are forms of fitting the code to the actual scale.

**authoring-against-state:5. Version-resolution contact -- measure which version actually resolves at runtime before authoring symbols whose import paths are shadowable.**

When the code being written adds, removes, or modifies a public symbol in a package whose name can be reached by multiple installations on the same PYTHONPATH / module-search-path / sys.path, the author must measure which copy the runtime actually resolves to, before writing the change. "I added the symbol to the right file in the repo" is not evidence the runtime will see the new version; cross-project shadows, PYTHONPATH ordering quirks, and version-skew between deployed artifacts and source repos all break this assumption silently.

Concrete measurements:

```bash
# Which file does the runtime actually import?
kubectl exec -n <ns> <runtime-pod> -- python3 -c 'import <pkg>.<module> as m; print(m.__file__)'

# Or for a specific symbol
kubectl exec -n <ns> <runtime-pod> -- python3 -c 'from <pkg>.<module> import <symbol>; print(<symbol>.__module__)'

# All copies on the runtime's sys.path
kubectl exec -n <ns> <runtime-pod> -- python3 -c 'import sys; [print(p) for p in sys.path]'

# Grep for sibling copies on the cluster
grep -rln 'def <symbol>' /path/to/sibling-project/<pkg>/ /path/to/this-project/<pkg>/
```

The measurement output goes in the authoring artifact AND in the rule's required "shadow-audit.toml" inventory if one exists for the project.

**Trigger:** adding or renaming a public symbol (top-level def, class, module-level constant) in a package that is on a shared PYTHONPATH, IS used by multiple consumers, or HAS sibling installations on the same runtime.

**This rule supersedes writing-code:16 in scope.** writing-code:16 in the electinfo_claude_skills downstream covered the same failure mode (cross-project shadow audit) at edit time. authoring-against-state:5 is the same rule promoted to this shelf with the same trigger but explicit framing as a state-measurement act. Resolution of the downstream supersession is tracked in electinfo/electinfo_claude_skills#23.

**Empirical evidence:** electinfo/enterprise#2079 (2026-05-22). Symbol `verify_known_families_lockfile` was added to `enterprise/rundeck/pipelines/utilities/fec_hydra_schema.py`. The EE pipeline at runtime resolved `utilities.fec_hydra_schema` to a sibling Rundeck project's older copy lacking the new function. Bronze stage hit ImportError 4 hours after the merge.

**authoring-against-state:6. Investigation-as-deliverable -- the inventory IS the ticket.**

Rules 1-5 specify what to measure. Rule 6 specifies how the measurement act is performed, and where the record lives.

Before authoring a runtime artifact that triggers any of rules 1-5, the author must:

1. **Read all inputs.** The work-item ticket. Any parent epic. Any standing rules or skills that govern this area. Any documentation for the resources being touched. Don't infer the requirements from the ticket title alone; the body and the epic typically carry the load-bearing constraints (format requirements, partition shape, target catalog, downstream consumer expectations). A ticket that says "put county shapefile in PSQL" without naming the target table, the connection, the existing schema, the SRID, or the load function is incomplete input -- the agent must read the epic and the docs and the existing code to fill that in, then write the fill-in into the ticket.

2. **Enumerate what we need to know in order to do this work.** Before measuring, list the open questions whose answers determine *how* the code is written. These are the knowledge gaps between the requirements (from step 1) and the artifact about to be authored: schemas the code will touch but the author has not seen, functions the code will call but the author has not located, credentials the code will use but the author has not verified, version-pinned behavior the author has not checked, conventions the author is assuming. The act of enumeration is what surfaces "I don't actually know X, and X determines the diff" before X becomes an incident. For the "put county shapefile in PSQL" case the open questions include: What SRID does the source shapefile use, and does it match the target column? Does the target table exist; if yes, what's its current schema, indexes, and row count? What loader function is canonical here -- `ogr2ogr`, `shp2pgsql`, or an in-repo helper, and does it stream or buffer? Where are the PSQL credentials stored, and what role do they grant? Is `{vintage_column}` typed as `date` or as `integer year`? What's the dedup key when re-loading the same vintage? Are there downstream consumers that pin the table's schema? Each enumerated question becomes a measurement target for steps 3-4; the inventory's job is to answer them. Questions left unanswered at write time become deferred risk and must be cross-referenced under "What was NOT measured" (step 6) -- silence in the inventory is not the same as "no question to ask."

3. **Inventory the contact points listed in rules 1-5.** For each rule that triggers -- data-shape, config-state, topology, plan-shape, version-resolution -- run the rule's "Concrete measurements" against the actual current state. Memory of state from a prior session is stale by default; the same-turn evidence requirement of writing-claims:1 applies. Each measurement answers one or more of the questions enumerated in step 2; if a question doesn't map to a rule-1-to-5 category, it falls to step 4.

4. **Inventory other surface areas of contact, not just the five rule categories.** Rules 1-5 are the categories the originating arcs hardened against. Real systems have more contact surfaces: existing tables to add to, existing functions to reuse, connection strings, credentials providers, file system layouts, schema registries, downstream subscribers, GitOps configs. The author scans every surface the change will touch -- not just the five categorized rules -- and records what's there. The five rules are the floor of the inventory, not the ceiling. Together with step 3, the inventory must cover every question enumerated in step 2; coverage is the test, not category-count.

   Two failure modes step 4 has to defend against: (i) the agent enumerates surfaces it already knows about and misses surfaces it doesn't -- which is the whole point of the inventory; (ii) the agent enumerates every conceivable surface and the inventory becomes ritual rather than measurement. The defense against both is a starter "Common surfaces by stack" lookup the author begins from, then extends per change. Starter (non-exhaustive; extend per project):

   | Stack | Common surfaces beyond rules 1-5 |
   |---|---|
   | Spark / Delta / Unity Catalog | UC catalog binding, `spark.sql.extensions` list, DLT pipeline yaml, GitOps Argo config, downstream MVs that pin schema, partition column conventions, stale V1 mirror stubs in `spark_catalog.*` |
   | Django / Postgres | Migration state (`django_migrations` table vs unapplied migrations), connection alias in `DATABASES`, model fields that exist in code but not in DB (or vice versa), signal handlers, custom managers, downstream serializers, fixture data, related-name reverse accessors |
   | Frontend / REST | API response schema (live, not docs), feature-flag config endpoint, downstream component contracts (prop shapes), bundler config, CDN cache rules, auth/cookie state, browser-side feature detection |
   | Go / Postgres / Redis | DB connection-pool config, pgx/sqlc generated code drift, Redis key prefix conventions, downstream gRPC contracts, env-var resolution order, build tag selection |
   | Embedded / hardware | Bus voltage + protocol, firmware version on the peer, EEPROM layout, fuse settings, downstream consumers polling the bus |

   The starter list is to defeat failure mode (i) by surfacing categories the author wouldn't have thought to scan. Failure mode (ii) is bounded by the step 2 enumeration: surfaces enter the inventory because a knowledge requirement points at them, not because they exist. If a surface from the table doesn't map to any enumerated question, the author either adds the question (the enumeration missed something) or omits the surface (it's not actually contacted). Extending the table per project is a follow-on rather than a blocker -- the rule's floor is "scan beyond the five categories"; the table is the scaffolding.

5. **Write the findings into the ticket itself.** The investigation is a deliverable, not an internal scratchpad. The agent updates the ticket body, appends a comment, or attaches a structured `## Pre-author inventory` section (template below) BEFORE the authoring step begins. The next reader of the ticket -- including future-you -- must be able to see what was measured without re-discovering it. A measurement done in chat is invisible to anyone who joins after the chat is compacted.

6. **State explicitly what was NOT measured.** If a contact-point rule fired but the author chose not to measure (e.g. via Trivial-against-state declaration), state that in the inventory section and cross-reference the Trivial-against-state Reason / Evidence / Falsification. Silence is not equivalent to "doesn't apply." Likewise, any question enumerated in step 2 that the inventory did not answer must be listed here -- "open question deferred" is a valid record; "question never written down" is not.

7. **State the falsifiable, truth-functional hypothesis the code will implement.** In the same `## Pre-author inventory` section, write a declarative statement of what the new code, config, or command will do. Use `{placeholders}` for values surfaced in the inventory above -- this grounds the hypothesis in measured state rather than assumed state. Each clause must be independently checkable against the resulting implementation. Each conditional ("if X then Y, else Z") is a separate falsifiable predicate; the resulting code must either handle both branches or explicitly state which branch is not handled and why. The hypothesis is what the reviewer (and future-you, in the next session) verifies the diff against -- without it, the only spec is whatever the author was thinking, which doesn't survive the session. The inventory tells the reader what is true now; the hypothesis tells the reader what the code is going to make true. Both belong in the ticket; neither is optional. **Hypothesis depth scales to change scope:** when the change is single-axis (one input, one output, no conditionals), the hypothesis is one sentence and may border on tautology -- write it anyway, because the reviewer still needs the spec to check the diff against. When the change is multi-axis (multiple conditionals, multiple downstream effects, branching on measured state), each axis is its own predicate and each conditional is its own checkable clause. A one-sentence hypothesis for a one-line fix is correct; a one-sentence hypothesis for a multi-table change is hand-waving and triggers the writing-claims:3 unquantified-completeness check.

Worked example for the "put county shapefile in PSQL" case the rule is framed around:

> "The county shapefile at `{path}` is to be added to `{spatial_database}`, reached with `{credentials}` or `{method}`, using `{function}`. This will create a new table named for the human-legible version of the geography if it is not already in existence and make the year of the shapefile's release the value of `{vintage_column}`. If the table exists, it will append these records, using the year of the shapefile's release as the value of the `{vintage_column}`, and deduplicate."

Each placeholder resolves to a value the inventory surfaced (path from "Inputs read", spatial_database from "Surface areas inventoried", function from "Surface areas inventoried", vintage_column from the existing schema if applicable). Each conditional ("if not already in existence", "if the table exists") is a separate predicate the implementation must handle.

Non-Spark worked example (Django ORM migration against an existing table):

> Ticket asks: "Add `verified_at` timestamp to `accounts.User` and backfill from `auth_log.last_verified` where present."
>
> **Step 1 (Inputs read):** ticket body, the parent epic naming the compliance deadline, `accounts/models.py`, the existing `auth_log` model, prior migrations under `accounts/migrations/`, the project's migration policy doc (zero-downtime requirement).
>
> **Step 2 (Knowledge requirements):** Does the `User` table already have a `verified_at` column from an unapplied or out-of-band migration? What's the row count of `accounts_user` (determines backfill strategy)? Is `auth_log.last_verified` nullable, and what's the null rate? What's the dedup key when multiple `auth_log` rows exist per user? Are there model signals (`post_save`) on `User` that would fire on backfill? Are there downstream serializers that pin the User schema? What's the connection alias -- is the table in the default DB or a secondary one?
>
> **Step 3 (Contact-point measurements):** authoring-against-state:1 data-shape -- `SELECT COUNT(*) FROM accounts_user;` and `SELECT COUNT(*), COUNT(last_verified) FROM auth_log;`. authoring-against-state:5 version-resolution -- `python manage.py showmigrations accounts` to confirm no pending migrations, plus `\d accounts_user` against the live DB to confirm the column doesn't already exist (model drift check). Other rules N/A (no Spark, no kubectl, no plan-shape).
>
> **Step 4 (Other surfaces):** `django_migrations` table state (per the starter table), `DATABASES` alias check (single default), `post_save` signal handlers on User (`grep -rn "post_save.*User"` in the apps), downstream serializers (`grep -rn "class UserSerializer"`), fixture data referencing User (`grep -rn "accounts.user" fixtures/`).
>
> **Step 5 (Recorded in ticket):** the inventory above is appended to the ticket as a `## Pre-author inventory` section before the migration file is written.
>
> **Step 6 (Not measured):** any read-replica lag implications -- deferred, the compliance deadline doesn't depend on replica freshness; flagged as an open question for the deploy review.
>
> **Step 7 (Hypothesis):** "A new migration on `accounts.User` adds a nullable `verified_at` timestamp column (nullable so the schema change is non-blocking against the `{user_row_count}` row table). A data migration backfills `verified_at` from `auth_log.last_verified` for users where exactly one `auth_log` row exists with non-null `last_verified`; users with zero such rows keep `verified_at = NULL`; users with multiple such rows use the most recent `last_verified` (dedup key = `MAX(last_verified)`). The `post_save` signal `{signal_handler_path}` is suppressed during backfill via `User.objects.bulk_update(...)`. No serializer changes; downstream serializer `UserSerializer` will surface `verified_at` automatically via `Meta.fields = '__all__'`."

The shape is identical to the Spark/PSQL example -- inputs, enumerated questions, rule-1-to-5 measurements (the categories that fire are different; the act is the same), other-surfaces scan from the Django row of the starter table, ticket-as-deliverable, explicit "not measured" call-out, and a multi-clause hypothesis where each conditional ("zero rows" / "one row" / "multiple rows") is its own predicate. The rule is stack-independent; the measurement commands are stack-specific.

**Inventory template** (one block per contact-point category that triggered; expand for other surfaces touched):

```markdown
## Pre-author inventory

### Inputs read (step 1)
- Ticket: <link or paste of the load-bearing requirements>
- Epic: <link or paste of the load-bearing constraints>
- Documentation consulted: <links>
- Standing rules / skills consulted: <rule IDs or skill names>

### Knowledge requirements (step 2 — what we need to know in order to do this work)
[The open questions whose answers determine HOW the code is written.
 Each question is a measurement target the inventory below must answer
 (or explicitly defer under "What was NOT measured"). For the
 "put county shapefile in PSQL" case the list might include:
 - What SRID does the source shapefile use?
 - What SRID does the target column expect (and what's the reprojection step if they differ)?
 - Does the target table exist? If yes, what's its current schema, indexes, and row count?
 - What loader function is canonical here (`ogr2ogr` / `shp2pgsql` / in-repo helper)?
 - Where are the PSQL credentials stored, and what role do they grant?
 - Is `{vintage_column}` typed as `date` or `integer year`?
 - What's the dedup key when re-loading the same vintage?
 - Are there indexes the load step needs to drop + rebuild?
 - Are there downstream consumers that pin the table's schema?
]

### Contact-point measurements (step 3 — per rules 1-5)
- **data-shape (authoring-against-state:1):** [measurement output OR `N/A` with Trivial-against-state cross-reference]
- **config-state (authoring-against-state:2):** [measurement output OR `N/A`]
- **topology (authoring-against-state:3):** [measurement output OR `N/A`]
- **plan-shape (authoring-against-state:4):** [measurement output OR `N/A`]
- **version-resolution (authoring-against-state:5):** [measurement output OR `N/A`]

### Surface areas inventoried beyond rules 1-5 (step 4)
[Free-form list. For "put county shapefile in PSQL" this might include:
 - DB connection string + credentials path
 - Target table existence + schema (or note "table does not exist; will create")
 - Existing loader function in `utilities/<thing>.py` (or note "none; will write")
 - SRID of source shapefile vs SRID of target column
 - Indexes the table already has
 - Downstream consumers reading the table (any that pin schema?)
]

### Hypothesis (step 7 — what the code will implement; falsifiable)
[A declarative statement of what the new code/config does. Use
 `{placeholders}` for values surfaced in the inventory above so the
 hypothesis is grounded in measured state. Each clause must be
 independently checkable against the resulting implementation. Each
 conditional ("if X then Y, else Z") is a separate falsifiable
 predicate; the code must either handle both branches or state
 explicitly which branch is not handled and why.

 Worked example (the "put county shapefile in PSQL" case the rule is
 framed around):

 "The county shapefile at `{path}` is to be added to `{spatial_database}`,
  reached with `{credentials}` or `{method}`, using `{function}`. This will
  create a new table named for the human-legible version of the geography
  if it is not already in existence and make the year of the shapefile's
  release the value of `{vintage_column}`. If the table exists, it will
  append these records, using the year of the shapefile's release as the
  value of the `{vintage_column}`, and deduplicate."
]

### Conclusions (steps 5+6 — write into the ticket; state explicitly what was NOT measured)
[One sentence per axis: is the assumed state consistent with measured state?
 If not, what's the gap, and how does the planned change handle it?
 Is the hypothesis above achievable given the inventory, or does any clause
 conflict with measured state? Are all knowledge requirements from the
 enumeration above answered, or is any question still open? Resolve
 conflicts and answer open questions before authoring, not after.]
```

**Trigger:** any change that triggers ANY of rules 1-5 (the contact-point rules). Rule 6 is the meta-rule that wraps them: the 5 rules dictate WHAT to measure; rule 6 dictates WHERE the measurement record lives and WHICH inputs frame the measurement.

**Composes with `[rule:writing-claims]` writing-claims:1 + writing-claims:2.** writing-claims:1 says "grep before declaring fix complete." Rule 6 says "and write the grep output into the ticket so it survives the session." writing-claims:2 says "countable claims need same-turn evidence." Rule 6 says "and the evidence belongs in the ticket, not in a chat-window message that will be compacted away."

**Composes with `[rule:definition-of-done]`.** Definition-of-done already requires the ticket exists and gets updated. Rule 6 specifies what the *initial* update looks like (the inventory section) -- before any authoring -- and treats it as a precondition to authoring rather than a closeout step.

**Composes with `[rule:writing-rules]` writing-rules:3.** Memory entries are correction layers, not enforcement substitutes. Rule 6 acknowledges that: the inventory cannot live in agent memory across sessions, because that's invisible to the next actor. The ticket is the durable record.

**Composes with `[rule:verify-before-execute]`.** verify-before-execute's Evidence clause requires same-turn evidence for any side-effecting action. Rule 6 refines that clause: it specifies WHERE the evidence lives (the ticket body, not the chat-window scratchpad) and WHEN it gets recorded (before the side-effecting authoring act begins, not after). Rule 6 is the verify-before-execute Evidence clause operationalized for state-touching authoring.

**Empirical evidence:** electinfo/enterprise#2094 silver_exp.sb Delta-format regression (2026-05-23). The work was authored without inventorying:

- the actual format (parquet vs Delta) of the existing silver_exp.* tables -- the epic implied Delta but didn't say it explicitly, the docs were silent, and the running tables were parquet because PR #2067 had silently regressed them. A pre-author inventory of `DESCRIBE EXTENDED` output on silver_exp.sa would have surfaced `Provider = parquet` and made the regression visible before the smoke test was designed.
- the V1 mirror stub state in `spark_catalog.silver_exp.*`. A pre-author inventory of `SHOW TABLES IN spark_catalog.silver_exp` would have surfaced stale stubs from prior runs with incompatible partition schemas; without it, the stubs collided with the new DLT registration and failed the smoke at minute 4.
- the Spark Connect server's catalog binding + `spark.sql.extensions` list. A pre-author inventory of `kubectl exec spark-connect-server -- grep -E '(catalog.fec_filings_enterprise_experimental|sql.extensions)' /opt/spark/conf/spark-defaults.conf` would have surfaced `PatchedUCSingleCatalog` (not Delta) and `SedonaSqlExtensions` only (no Delta), making the cluster-side gap visible before the pipeline yaml was edited.

Each missing inventory cost one or more smoke-cycle iterations. Each could have been recorded in the parent ticket (#2094) at the investigation stage, in a `## Pre-author inventory` section, and the next author would have started from that record instead of from a chat history that the next session can't see.

The session's retrospective on "why did investigation + epic documentation not surface this?" identified four contributing layers: (a) the epic implicit on Delta requirement, (b) PR #2067's "no functional change" claim went unchallenged in review, (c) memory entry mis-distilled from #2067's commit body, (d) the shelf had rules 1-5 but no rule that mandated reading the inputs + writing findings into the ticket. Rule 6 closes layer (d). The other layers reduce to layer (d) once rule 6 is in place: if the inventory section had been required, the agent would have read the epic (catching layer a), noticed the format drift (catching layer b), and updated the memory (catching layer c) at investigation time.

## Scale of investigation

Rule 6 is heavy. Seven steps + a template with eight sections, applied to every PR that triggers any of rules 1-5, is a substantial discipline burden. The agent's instinct on a small change will be to skip a step ("this is one line, the inventory is overkill"). That instinct is the failure mode the rule exists to prevent.

The `Trivial-against-state:` declaration covers "this change does not trigger any contact-point rule." It does NOT cover "this change triggers a rule but is small." The latter case still requires rule 6 in full -- but the *form* is fixed, the *depth* of each section flexes with the scope of the change.

What this means concretely:

- **A one-line config tweak that touches config-state (rule 2):** Pre-author inventory still required. Inputs read = the ticket + the one ConfigMap. Knowledge requirements = one or two open questions ("what's the current value? what consumers depend on it?"). Contact-point measurement = the `kubectl exec ... grep` output, one line. Other surfaces = none if nothing else reads the value. Hypothesis = one sentence with `{old_value}` and `{new_value}` placeholders. Five minutes of work, not fifty.
- **A multi-table DLT MV body change that triggers data-shape + plan-shape + config-state:** Pre-author inventory still required. Inputs read = ticket + epic + DLT docs + at least one sibling MV. Knowledge requirements = a dozen open questions. Contact-point measurements = a `count()` per upstream + a `unionByName` depth count + a Spark Connect server `grep`. Other surfaces = the GitOps catalog config + downstream subscribers + materialization target schema. Hypothesis = a multi-clause statement with several conditional predicates. An hour of work, properly.

The rule is inviolable in form: every section of the Pre-author inventory template appears in every triggering PR. The rule is proportionate in content: each section's depth flexes with what the change actually touches.

The depth flex described here is the *form-side* scale knob; step 7's hypothesis-scaling rule (single-axis change = one-sentence hypothesis; multi-axis change = one predicate per axis) is the *content-side* scale knob. Together they're the rule's two-sided proportionality: the form is fixed but flexes in depth, and the hypothesis content is fixed in structure but flexes in predicate count. A reader applying the rule to a small change consults both — the depth-flex tells them how short each inventory section can be; the hypothesis-scaling tells them whether their one-sentence spec is calibration or hand-waving.

Why "the agent decides per change" doesn't work as the carve-out: the agent is the wrong actor to decide what's small enough to skip a step. Every one of #2094's smoke-cycle iterations started from a change the author thought was small. The author's perception of small != actual blast radius; the inventory IS the act of measuring whether the author's perception matches reality. Skipping the inventory because the change feels small is the perception itself talking.

Two operator-auditable signals that the inventory's depth was wrong:

- An incident matches a contact category the inventory left blank or wrote `N/A` for. The Post-error revision section below covers the rule's response: the missing measurement is added to the relevant rule, the next author has the command pre-staged, and (if the contact category was outside rules 1-5) a new rule may be filed.
- A reviewer cannot verify the diff against the hypothesis because the hypothesis was empty or hand-waved. The reviewer can request a rewrite per writing-claims:3 (unquantified completeness claims need grounding).

Heaviness is the price of inviolability. The shelf is honest about that rather than pretending the form is light.

## Common rationalizations to refuse

Scale of investigation above describes the form / depth discipline at the abstract level. Empirically, rule 6 fails along five specific rationalization shapes. Each looks reasonable in the moment; each is the author talking themselves out of the rule. Naming them so the author catches the cheat at write time:

**1. "This is a one-line fix; the inventory is bigger than the fix."**

The form is the requirement, not the depth. A one-line fix gets a one-line inventory entry, not zero. The cheat is treating fix-size as a proxy for inventory-need; Scale of investigation above explicitly rejects that proxy. Empirically, the smallest fixes are the ones whose underlying causes were three layers deep -- a Java type name (one character), a session-default check (one boolean), a sibling-class instance check (one type). Each "one line" sat on top of a missing inventory of how the surrounding system actually resolved a request.

Refutation: produce an inventory entry. Three bullets is fine. The point is the act of writing it, which forces the surface scan that would otherwise be skipped.

**2. "I already have all the context from the last cycle; the inventory would be repetitive."**

The inventory for cycle N is a *delta* from the inventory for cycle N-1, not a restatement. Cite the previous inventory by link. Write only what's new: the new measurement, the assumption that just got revised, the new question. The cheat is letting "I have the context" stand in for "the record has the context"; only the latter survives the session, and only the latter is what the next reader (including future-the-same-author after compaction) will see.

Refutation: write the inventory as `## Cycle N inventory (delta from cycle N-1: <link>)` with new measurements + revised assumptions + new questions only. Short is fine; absent is not.

**3. "Time is tight; let me push and document later."**

There is no "document later." Documentation in the past tense is post-mortem, not pre-author inventory. Rule 6's inventory IS the gate to action; without the artifact, the action is blocked. "Later" never comes -- the next failure repeats the same uninvestigated gap, and the author repeats the same time-tight rationalization on the next retrigger.

Refutation: the action waits for the inventory. If time is genuinely tight, the inventory is short. If the inventory is genuinely impossible (cluster on fire, operator needs an answer in 30 seconds), write an explicit `Inventory deferred for emergency response, see incident <link>` entry. That stub IS the inventory record and forces the post-incident follow-up.

**4. "The operator just said 'yes' -- that's authorization."**

Operator authorization is granted ON TOP OF the rule, not in lieu of it. A fast `yes` means the operator trusts the author's judgment on the proposal; it does not mean the operator wants the rule skipped. The cheat is laundering operator-trust into rule-skip-license -- using the operator's velocity as a substitute for the author's discipline.

Refutation: the operator `yes` authorizes the *plan*. The inventory remains a precondition to executing the plan. If the operator wants the rule waived for a specific action, that requires explicit `[rule:authoring-against-state]:6 waived for <reason>` in the ticket -- not implied by an unmarked `yes`. Operator latitude does not include skip-the-rule unless the operator says skip-the-rule.

**5. "Retrigger isn't authoring."**

Retriggering a runtime artifact that already failed once IS a triggering of a state-touching action under rule 6's trigger scope (a "kick" per the rule body). Specifically, any kick of code that previously failed in this session requires inventory of *what changed since the last failure*. If nothing changed, the conclusion in the inventory is "expected to fail again; not retriggering" -- which itself prevents the wasted cycle and breaks the fix-and-retrigger loop.

Refutation: every retrigger gets an inventory, even if the inventory is one sentence ("Same as cycle N-1 inventory: <link>; no changes since; conclusion: not retriggering, breaking the loop"). The inventory either justifies the action or refuses it.

### Where these were empirically observed

electinfo/enterprise#2094 (2026-05-23). The author of rule 6 itself hit all five rationalizations in five consecutive cycles handled with the diagnose / fix / retrigger loop instead of the inventory loop. The operator called the pattern out three times within the same arc:

- "more smoke bugs are really tedious" (frustration with reactive arc)
- "It's starting to look deeply reactive again, rather than investigative and measured, which should be compelled by rules"
- "Every failure should be resulting in an inventory and assumption revision. I don't know why it hasn't."

Each callout produced an inventory comment on the ticket; each comment was followed by more fix-and-retrigger cycles without inventories. The pattern only broke when the rationalizations themselves got named in writing. This section is the writing-down.

The five rationalizations are saved as named anti-patterns so the next author -- including future-the-same-author across sessions -- catches them at write time. Recognition is the first defense; the form-fixed / depth-flexible discipline above is the second.

## Inheriting brokenness: prior failures, prior follow-ups, prior latent bugs

Rule 6's seven-step procedure presumes the author can enumerate the surfaces the change will touch. When the change is **a wrapper around an existing artifact** — a DAG wrapping a pipeline, a function wrapping a library, a script kicking a known runtime — the enumeration must include the wrapped artifact's known-broken state, not just the wrapper's own diff. The wrapper inherits every failure mode of what it wraps; treating the wrapped as a black box is the failure mode this section exists to prevent.

Three concrete shapes the inherited-brokenness inventory must cover:

**a. Wrapper authoring: the wrapped artifact's state is your state.**

When the artifact being authored is a wrapper that invokes pre-existing code at runtime (an Airflow DAG that runs `run_pipeline.py`, a CLI that calls a third-party SDK, a CI step that invokes a vendored test harness), the pre-author inventory must include the wrapped artifact's known failure surface:

- What modules will the wrapped artifact load at register/import time?
- What enumerative calls (`listTables`, `glob`, `os.walk`, `pkg_resources.iter_entry_points`) will fire?
- What environmental assumptions will it make?
- What prior failures of the wrapped artifact are recorded in memory or in prior tickets?

Concrete measurement: read the wrapped artifact's entry point + scan one level deep for module imports, glob loads, and catalog enumerations. The wrapper's behavior includes every failure mode of the things it triggers.

Empirical: electinfo/enterprise#2094 (2026-05-24). Gold attempt 2 failed in 2 seconds because `pipeline-gold.yml`'s `libraries: - glob: include: ../utilities/**` loaded `utilities/entity_match_stats.py` which has a bare `from create_entity_match_tables import ...` that depends on filesystem glob order. The author's pre-flight for the wrapping DAG (PR electinfo/airflow#55) checked the DAG file but not the wrapped pipeline's load path. The bare-import bug was known from prior smoke cycle 15 of the same arc — captured in memory as a follow-up but not brought forward as a blocker for the wrapper-shipping work.

**b. After a class-bug fires, grep the class before fixing the instance.**

When a failure exposes a specific instance of a recognizable bug class (a bare import that depends on glob order, a `listTables` that fan-fails on an orphan, a write that assumes a column type the upstream table doesn't have), the response is to scan for ALL instances of the class, not to fix the one that fired. The fix-and-retrigger loop produces longer time-to-green than the grep-the-class-once approach, because each retrigger reveals the next instance of the same class.

Concrete measurement (per class):

```bash
# Bare imports of sibling-module symbols (the entity_match_stats class)
grep -rEn "^from [a-z_]+ import" <utility-tree>/ | grep -v "from \(stdlib\|known-stable\) import"

# listTables fan-failures (the sf_delta_test orphan class)
grep -rEn "listTables\(" <transformation-tree>/

# Hardcoded paths whose existence is assumed (the path-orphan class)
grep -rEn "['\"]s3a?://[^'\"]+['\"]" <transformation-tree>/
```

Empirical: same arc, gold attempts 2 + 3. After attempt 2's entity_match_stats failure, the right reflex was `grep "^from [a-z_]+ import" utilities/` to find the other three files with the same shape (audit_quicksilver_catalog, reset_entity_match_tables, validate_tier_quality). Instead the response was a 1-line fix + retrigger queued. The class-scan happened only after operator callout.

**c. Carry-forward of prior-session follow-ups: not backlog, blockers.**

When a memory entry, comment, or ticket marks a known issue as "follow-up" or "later" or "tracking" — and the work now being authored will execute the code path that issue affects — the issue is NOT backlog. It is a blocker for the new work.

The pre-author inventory must include: search prior memory entries, ticket comments, and PR notes for known issues affecting the authoring path. Each known issue is either (a) resolved before authoring, or (b) explicitly declared in the inventory as `Deferred-known-broken: will fail on <observable>; fix planned after <event>` with the observable specified. Silent carry-forward of follow-ups is the cheat-shape that produces the "I already documented this but didn't fix it" failure mode.

Empirical: the memory entry cross-referencing the entity_match_stats bug was created during smoke cycle 15 (2026-05-23). PR electinfo/airflow#55 (2026-05-24 ~03:13 UTC) shipped DAGs that wrap pipeline-gold.yml. The known-broken entity_match_stats.py was not surfaced as a blocker; the DAGs shipped; gold attempt 2 hit the known bug 2 seconds in.

**Trigger:** any pre-author inventory for work that (a) authors a wrapper around an existing artifact, OR (b) follows a failure of the same artifact within the same session/arc, OR (c) touches a code path with prior-session known-broken memory entries. The trigger fires at the inventory step (rule 6 step 4), not at the diff that adds the wrapper.

**Composes with rule 6 step 4.** Step 4 already says "inventory other surface areas of contact, not just the five rule categories." This section names the inherited-brokenness surface as one such category that's empirically high-frequency for wrapper authoring. The starter "Common surfaces by stack" table in step 4 gains a new row applicable to all stacks: "wrapper / vendored artifact authoring → known-broken state of the wrapped artifact (prior incident comments, follow-up-marked memory entries, unresolved tickets touching the path)."

**Composes with the cheat-shapes above.** Cheat-shape 2 ("I already have all the context from the last cycle") describes the temptation; this section describes the discipline that resists it. Cheat-shape 1 ("one-line fix") frames why grepping the class matters — the one-line fix that ships the wrong instance produces a second one-line fix on retrigger.

## Trivial-change declaration

A change that does not introduce a new authoring-against-state contact-point trigger may be declared trivial in the commit body, but the declaration is itself a `[rule:writing-rules]` writing-rules:4 claim ("this doesn't apply") and requires the same evidence chain as a "this happened" claim.

Format:

```
Trivial-against-state: <category from the controlled list below>
Reason: <one-sentence statement of why the change does not touch a contact-point trigger>
Evidence: <grep output, file paths, command output, or other same-turn evidence proving the Reason>
Falsification: <the observation that would prove the Reason wrong, e.g. "if `grep -rn 'spark.read' <files>` returns a match, this declaration is incorrect">
```

Acceptable Reason categories (controlled list per `[rule:writing-rules]` writing-rules:5):

- `docs-only` -- pure documentation change, no code touched. Falsification: `git diff --name-only HEAD~1 | grep -v -E '\.(md|rst|txt)$'` returns nothing.
- `comment-only` -- comment-only change to existing code. Falsification: `git diff HEAD~1` shows only added/removed lines beginning with `#` (Python), `//` (JS), or equivalent comment markers; no executable code lines changed.
- `local-only` -- change to a code path that does not run under shared cluster state (local script, fixture, test). Falsification: the path is not imported by any code under `<deployed-paths>` (project-local list).
- `inputs-already-measured` -- change to a code path whose behavior depends only on inputs the author just verified in the same response. Falsification: the inventory commands from rules 1-5 do not return a different result than what the author recorded in the same response.

A `Trivial-against-state:` declaration that omits Reason / Evidence / Falsification (or names a category outside the controlled list) is itself a `writing-rules:4` violation. The trivial declaration is operator-auditable; the evidence chain makes the auditability mechanical.

A change that includes the declaration but actually does touch a contact-point category is a `writing-rules:5` violation -- "trivial" means "cannot produce a future error," and a contact-point touch can always produce a future error per the empirical evidence in each rule.

## Post-error revision

When a runtime failure occurs that this rule would have prevented (failure mode matches one of the five contact categories above, and a measurement command would have surfaced the gap), the author must:

1. Add the missing measurement command to the relevant rule's "Concrete measurements" block as an addendum, AND
2. File or update a `pre-write-inventory.md` template for the project so the next author has the command ready, AND
3. If the failure was a class the rules did not cover, file an addition to the rules (don't just absorb the lesson silently).

The point of the rule is that failures expand it, not that they get re-discovered.

## When this file applies

This file applies whenever the agent is about to produce a runtime artifact -- code, config, command, or kick -- whose behavior depends on a measurable external state.

It does **not** apply to:
- Pure analysis or reading tasks (no artifact produced).
- Code that runs only in process-local memory (no cluster contact).
- Code whose only external state is a stable contract (e.g. a versioned API guaranteed by the platform team to not drift mid-PR).

It composes with all the per-act shelves: writing-code remains the verify-before-touching-code shelf; writing-claims remains the verify-before-claiming shelf; this file is the verify-the-state-before-authoring-against-it shelf.

## Why this shelf is separate from writing-code

The per-act shelves (writing-code, writing-prose, writing-tests, etc.) are split by the kind of artifact being produced. authoring-against-state cross-cuts: a pipeline transformation, a kubectl apply, a config-file edit, and a Rundeck job kick can all trigger the rules in this file. The boundary is "is the author producing an artifact whose behavior depends on state the author has not just measured?", not "is the author writing code vs prose vs tests."

Promoting individual contact-point rules into writing-code would have left them buried under the code-correctness rules and would have applied only when code was being written. The kick-time and config-edit-time triggers would not have fit. The separate shelf preserves the trigger discipline.

## Override

These rules are mandatory. No override flag. The trivial-change declaration above is the only relief valve, and it is operator-auditable (not author-self-declared).

Same shape as the rule cohort across `_writing-prose-rules.md`, `_writing-code-rules.md`, `_writing-tests-rules.md`, `_writing-releases-rules.md`, `_writing-claims-rules.md` -- no `[*-skip]` override.

## Cross-references

- `[rule:writing-code]` is the verify-before-touching-code sibling. Rules in that file fire when editing code; rules in this file fire when the code being edited has a contact-point dependency on external state.
- `[rule:writing-claims]` is the verify-before-claiming sibling. Rules in that file fire when stating facts in commit/PR bodies or chat; rules in this file fire one step earlier, when the code being authored makes implicit factual claims about the state of the runtime.
- `[rule:verify-before-execute]` is the parent meta-rule. Its Evidence clause already requires same-turn evidence for any side-effecting action; this file refines that clause to specify which evidence is required for each of five contact categories.
- `[rule:environment-preflight]` is the one-time-per-repo inventory of interpreters, services, credentials. This file extends environment-preflight to PER-PR inventory of mutable state.
