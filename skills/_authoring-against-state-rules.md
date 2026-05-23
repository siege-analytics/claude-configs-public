---
description: Always-on. Investigation-as-deliverable discipline for code, config, and commands whose runtime behavior depends on the state of an external resource. The author must read the inputs (ticket, epic, documentation), measure the contact-point surfaces (rules 1-5), and record the findings in the ticket itself (rule 6) before authoring. Sibling to writing-code (verify-before-touching-code) and writing-claims (verify-before-claiming) -- this file covers verify-the-external-state-before-writing-against-it and the requirement that the verification artifact lives in the ticket, not in chat.
---

# Authoring Against State

These rules apply whenever the agent writes code, configuration, or commands whose runtime behavior depends on the state of an external resource the author has not just inventoried in the same response.

The existing shelves treat the diff as the unit of work. `[rule:writing-code]` verifies symbols and shapes within the code; `[rule:writing-claims]` verifies facts the diff asserts; `[rule:verify-before-execute]` requires same-turn evidence for any side-effecting action. None compel the author to measure the **external** state -- the state of the cluster, the data, the runtime topology, the version actually resolved at runtime -- that the code will encounter.

Tonight's failure mode (recurring across electinfo/enterprise#2076-#2093 between 2026-05-22 and 2026-05-23): correctly-written code, shipped under correctness-shaped review, that assumed a runtime reality which had drifted from the author's mental model. The diff was right relative to imagined state. It was wrong relative to measured state. Six distinct production failures in one backfill cycle, each preventable by a one-line measurement command run before the code was written.

These rules close that category by making the measurement compulsory at write time, **with the output retained in the ticket so the next author doesn't have to re-discover.** The shelf has two layers: rules 1-5 specify WHAT to measure (the contact-point categories); rule 6 specifies HOW the act is performed (read the inputs first; apply rules 1-5; record findings) and WHERE the record lives (in the ticket body, not in chat, not in agent memory). Rules 1-5 without rule 6 reduce to "the author measured something then forgot it"; rule 6 without rules 1-5 reduces to "the author wrote a section header in the ticket and called it done." Both layers are required.

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

2. **Inventory the contact points listed in rules 1-5.** For each rule that triggers -- data-shape, config-state, topology, plan-shape, version-resolution -- run the rule's "Concrete measurements" against the actual current state. Memory of state from a prior session is stale by default; the same-turn evidence requirement of writing-claims:1 applies.

3. **Inventory other surface areas of contact, not just the five rule categories.** Rules 1-5 are the categories the originating arcs hardened against. Real systems have more contact surfaces: existing tables to add to, existing functions to reuse, connection strings, credentials providers, file system layouts, schema registries, downstream subscribers, GitOps configs. The author scans every surface the change will touch -- not just the five categorized rules -- and records what's there. The five rules are the floor of the inventory, not the ceiling.

4. **Write the findings into the ticket itself.** The investigation is a deliverable, not an internal scratchpad. The agent updates the ticket body, appends a comment, or attaches a structured `## Pre-author inventory` section (template below) BEFORE the authoring step begins. The next reader of the ticket -- including future-you -- must be able to see what was measured without re-discovering it. A measurement done in chat is invisible to anyone who joins after the chat is compacted.

5. **State explicitly what was NOT measured.** If a contact-point rule fired but the author chose not to measure (e.g. via Trivial-against-state declaration), state that in the inventory section and cross-reference the Trivial-against-state Reason / Evidence / Falsification. Silence is not equivalent to "doesn't apply."

**Inventory template** (one block per contact-point category that triggered; expand for other surfaces touched):

```markdown
## Pre-author inventory

### Inputs read
- Ticket: <link or paste of the load-bearing requirements>
- Epic: <link or paste of the load-bearing constraints>
- Documentation consulted: <links>
- Standing rules / skills consulted: <rule IDs or skill names>

### Contact-point measurements (per rules 1-5)
- **data-shape (authoring-against-state:1):** [measurement output OR `N/A` with Trivial-against-state cross-reference]
- **config-state (authoring-against-state:2):** [measurement output OR `N/A`]
- **topology (authoring-against-state:3):** [measurement output OR `N/A`]
- **plan-shape (authoring-against-state:4):** [measurement output OR `N/A`]
- **version-resolution (authoring-against-state:5):** [measurement output OR `N/A`]

### Surface areas inventoried beyond rules 1-5
[Free-form list. For "put county shapefile in PSQL" this might include:
 - DB connection string + credentials path
 - Target table existence + schema (or note "table does not exist; will create")
 - Existing loader function in `utilities/<thing>.py` (or note "none; will write")
 - SRID of source shapefile vs SRID of target column
 - Indexes the table already has
 - Downstream consumers reading the table (any that pin schema?)
]

### Conclusions
[One sentence per axis: is the assumed state consistent with measured state?
 If not, what's the gap, and how does the planned change handle it?]
```

**Trigger:** any change that triggers ANY of rules 1-5 (the contact-point rules). Rule 6 is the meta-rule that wraps them: the 5 rules dictate WHAT to measure; rule 6 dictates WHERE the measurement record lives and WHICH inputs frame the measurement.

**Composes with `[rule:writing-claims]` writing-claims:1 + writing-claims:2.** writing-claims:1 says "grep before declaring fix complete." Rule 6 says "and write the grep output into the ticket so it survives the session." writing-claims:2 says "countable claims need same-turn evidence." Rule 6 says "and the evidence belongs in the ticket, not in a chat-window message that will be compacted away."

**Composes with `[rule:definition-of-done]`.** Definition-of-done already requires the ticket exists and gets updated. Rule 6 specifies what the *initial* update looks like (the inventory section) -- before any authoring -- and treats it as a precondition to authoring rather than a closeout step.

**Composes with `[rule:writing-rules]` writing-rules:3.** Memory entries are correction layers, not enforcement substitutes. Rule 6 acknowledges that: the inventory cannot live in agent memory across sessions, because that's invisible to the next actor. The ticket is the durable record.

**Empirical evidence:** electinfo/enterprise#2094 silver_exp.sb Delta-format regression (2026-05-23). The work was authored without inventorying:

- the actual format (parquet vs Delta) of the existing silver_exp.* tables -- the epic implied Delta but didn't say it explicitly, the docs were silent, and the running tables were parquet because PR #2067 had silently regressed them. A pre-author inventory of `DESCRIBE EXTENDED` output on silver_exp.sa would have surfaced `Provider = parquet` and made the regression visible before the smoke test was designed.
- the V1 mirror stub state in `spark_catalog.silver_exp.*`. A pre-author inventory of `SHOW TABLES IN spark_catalog.silver_exp` would have surfaced stale stubs from prior runs with incompatible partition schemas; without it, the stubs collided with the new DLT registration and failed the smoke at minute 4.
- the Spark Connect server's catalog binding + `spark.sql.extensions` list. A pre-author inventory of `kubectl exec spark-connect-server -- grep -E '(catalog.fec_filings_enterprise_experimental|sql.extensions)' /opt/spark/conf/spark-defaults.conf` would have surfaced `PatchedUCSingleCatalog` (not Delta) and `SedonaSqlExtensions` only (no Delta), making the cluster-side gap visible before the pipeline yaml was edited.

Each missing inventory cost one or more smoke-cycle iterations. Each could have been recorded in the parent ticket (#2094) at the investigation stage, in a `## Pre-author inventory` section, and the next author would have started from that record instead of from a chat history that the next session can't see.

The session's retrospective on "why did investigation + epic documentation not surface this?" identified four contributing layers: (a) the epic implicit on Delta requirement, (b) PR #2067's "no functional change" claim went unchallenged in review, (c) memory entry mis-distilled from #2067's commit body, (d) the shelf had rules 1-5 but no rule that mandated reading the inputs + writing findings into the ticket. Rule 6 closes layer (d). The other layers reduce to layer (d) once rule 6 is in place: if the inventory section had been required, the agent would have read the epic (catching layer a), noticed the format drift (catching layer b), and updated the memory (catching layer c) at investigation time.

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
