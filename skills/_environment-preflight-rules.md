---
description: Always-on. Before writing or testing code in a repo not yet inventoried this session, run an environment preflight. Skipping is allowed but must be explicit. Came out of a session where the agent claimed Spark and pyspark were unavailable when they were installed under pyenv and orchestrated by the user's SZSH config.
---

# Environment preflight

Before substantive code or test work in a repository the agent has not touched in this session, run an inventory of what is actually installed and what can actually be executed. This applies on first entry to a repo, after `git checkout` onto a different project, and after any environment-changing event (new shell, new container).

## Why this rule exists

In one extended siege_utilities session the agent burned hours assuming pyspark was unavailable because `python -c "import pyspark"` failed against the default Python on PATH. The user's machine had two pyenv environments with pyspark and sedona installed, plus a full SZSH shell config that exported `SPARK_HOME`, `JAVA_HOME`, and routed `python` through pyenv when fully initialised. The agent shipped multiple PRs claiming "Spark probes skip cleanly without pyspark" when in fact they could have been run on the laptop. Two tests in those PRs were wrong-by-construction (`PostGISEngine()` no-arg constructor; missing `PYSPARK_PYTHON` env var) and one `pytest tests/property/` would have caught both immediately.

The narrow fix was "remember SZSH exists." The broader fix is to inventory the environment before assuming anything about it.

## The preflight

Run these checks. Output a short summary in chat so the user sees what was found. The summary anchors later "I can / cannot run this" claims.

### 1. Read the README's environment section

Specifically these section names:

- `Environment`, `Setup`, `Installation`, `Quick start`
- `Related projects`, `Companion`, `See also`
- Any section naming a shell config, dotfiles repo, or dev-env builder

The README often names the canonical companion environment. The siege_utilities README has a "Related: Siege Analytics ZSH Configuration" section that names the entire companion toolchain; the agent missed it for a full day.

### 2. Inventory interpreters and core deps

`pyenv versions`, `ls -d ~/.virtualenvs/* venv .venv`, `cat .python-version pyproject.toml | grep -E "^(version|python|requires-python)"`.

For each interpreter that looks project-relevant, probe the deps the project actually imports. Use the project's own pyproject `optional-dependencies` sections to know what to look for. Do not run `pip install` without permission; just probe with `python -c "import X"` against each candidate interpreter.

### 3. Inventory the shell environment

`ZSH_FORCE_FULL_INIT=1 zsh -ic 'env | grep -E "(SPARK_HOME|JAVA_HOME|PYSPARK_|SDKMAN|PYENV)" | head -20'`.

If the project's README names a shell config repo, look at that repo's modules directory for what it sets up. `~/.config/zsh/modules/` or similar is a strong signal that the user has a curated dev env.

### 4. Inventory local services

`pg_isready`, `redis-cli ping`, `docker ps`, `lsof -nP -iTCP -sTCP:LISTEN | grep -E ':(5432|6379|9092|8983|9200)'`.

A Postgres on localhost means Django ORM tests can actually run. A locally-running Redis or Kafka means broker-dependent tests are not doomed to skip. The skip column hides a lot.

### 5. Inventory credentials and config

`ls ~/.aws/credentials ~/.gcp/* ~/.siege-test-credentials.yaml ~/.config/<project>/*`.

If the project has a credentials path documented (the way Sprint B documented `~/.siege-test-credentials.yaml`), check whether it exists. If it does, live-API tests can run; if not, document the gap.

### 6. Compare CI to local

`ls .github/workflows/*.yml`. Open the main workflow. Note which tests it `--ignore`s, which tests have fixtures that probe for optional deps and skip, and which tests run unconditionally. Anything CI ignores is something the local machine may be able to run that CI cannot.

## Output

After the preflight, state in chat what was found, in this shape:

    Environment preflight for <project>:
    - Interpreters: <list and what is in each>
    - Shell env: <SPARK_HOME, JAVA_HOME, etc. if relevant>
    - Services running: <postgres / redis / kafka / none>
    - Credentials present: <which / none>
    - CI ignores locally: <list of tests CI skips that this machine could run>
    - What this means: <plain English of which test surfaces can be exercised here>

The user sees the summary and either confirms or corrects. The summary anchors later claims about what can and cannot be run.

## Cost vs. value

The preflight takes 30-90 seconds depending on how many checks fire. The cost of skipping it is hours of false "I cannot run this" framing, plus test code that is wrong because it assumed an environment that was not actually verified. Always cheaper to run.

## Skip clause

The preflight is mandatory before substantive code or test work. It can be skipped when:

- The task is purely documentation or chat (no code, no tests)
- The repository is already inventoried in this session's memory
- The user has told the agent to skip ("do not preflight, just code")

If skipping, say so in one sentence so the audit trail is explicit: "Skipping preflight: <reason>."

## What this rule does NOT mean

- Do not run `pip install` without permission. Probing for missing deps is fine; installing them is a separate ask.
- Do not run destructive commands during preflight (no `pyenv shell` that changes user-visible state, no `docker stop`, no service restarts).
- Do not preflight on every command. Preflight once per repo per session; rely on the saved summary thereafter.

## Cross-references

- `[`verify-before-execute`](_verify-before-execute-rules.md)` is the parent discipline. This rule extends it from "verify before code claims" to "verify before environment claims."
- `[`no-ai-fingerprints`](_no-ai-fingerprints-rules.md)` rule 12 is the per-action application of this inventory: "you must have already verified the dependency is reachable in the target environment, and you must exercise the real dependency before claiming the code works." This rule establishes the baseline; rule 12 enforces it on every action.
- Per-repo memory entries (e.g. `reference_szsh_environment`) contain the canonical preflight result for projects already inventoried; if one is in scope, lean on it and skip step 3 onward.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in preflight summaries, in commits, or anywhere else.
