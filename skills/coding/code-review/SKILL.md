---
name: code-review
description: Systematic code review methodology. Covers correctness, security, performance, readability, and how to prioritize findings.
disable-model-invocation: true
allowed-tools: Read Grep Glob
argument-hint: "[PR-number-or-path] [optional-focus-area]"
---

# Code Review

## When to Use This Skill

When reviewing a pull request, a diff, or code written during a session. Apply this methodology systematically — don't rely on skimming to catch issues.

## Review Order

Review in this order. Stop at each layer before proceeding — a correctness bug matters more than a style nit.

### 1. Correctness

Does the code do what it claims to do?

**Check:**
- Does every function return what its name and docstring promise?
- Are edge cases handled? (empty input, None, zero, negative, very large)
- Are off-by-one errors present in loops, slices, or ranges?
- Do conditionals cover all branches? Are there impossible else clauses?
- Are comparisons correct? (`>=` vs `>`, `==` vs `is`, `and` vs `or`)
- For data transforms: does every row make it through, or are rows silently dropped?
- For SQL: does the JOIN type match the intent? (INNER drops non-matches, LEFT keeps them)

**Red flags:**
```python
# Silent data loss: NULLs dropped without comment
df = df.filter(F.col("amount").isNotNull())
# Ask: is dropping NULLs the right behavior? Should they be zero? Logged?

# Wrong comparison
if status == "active" or "pending":    # always True — "pending" is truthy
if status == "active" or status == "pending":  # correct
if status in ("active", "pending"):            # better

# Off-by-one
for i in range(1, len(items)):  # skips first item — intentional?
```

### 2. Security

Could this code be exploited or leak sensitive data?

**Check:**
- SQL injection: are queries built with string concatenation or f-strings?
- Command injection: is user input passed to `subprocess`, `os.system`, or shell commands?
- Path traversal: can user input reach file paths (`../../../etc/passwd`)?
- Secrets in code: API keys, passwords, tokens hardcoded or logged?
- Authentication/authorization: does every endpoint check permissions?
- Input validation: is external input (API parameters, file uploads, form data) validated before use?
- Sensitive data in logs: are PII fields (names, addresses, SSNs) being logged?

**Red flags:**
```python
# SQL injection
query = f"SELECT * FROM users WHERE name = '{user_input}'"  # never
cursor.execute("SELECT * FROM users WHERE name = %s", (user_input,))  # correct

# Command injection
os.system(f"grep {pattern} {filename}")  # user controls pattern or filename
subprocess.run(["grep", pattern, filename])  # safe: no shell interpretation

# Secrets in code
API_KEY = "sk-abc123..."  # should be in environment variable or secrets manager
```

### 3. Data Integrity

For data pipelines and database operations: will this corrupt or lose data?

**Check:**
- Write mode: is `overwrite` used where `append` is correct (or vice versa)?
- Schema changes: will this break downstream consumers?
- Transactions: are multi-step operations atomic? What happens if step 2 fails after step 1 succeeds?
- Deduplication: will re-running this job create duplicates?
- Idempotency: does running the same job twice produce the same result?
- Ordering: does the result depend on row order that isn't guaranteed?

**Red flags:**
```python
# Non-idempotent append
df.write.format("delta").mode("append").saveAsTable(table)
# If the job retries, every row is duplicated. Use merge instead.

# Overwriting bronze
df.write.format("delta").mode("overwrite").saveAsTable("main.bronze.filings")
# Bronze is the audit trail — never overwrite it.

# Schema drift
df.write.option("mergeSchema", "true")
# New columns silently added — will downstream jobs handle them?
```

### 4. Performance

Will this be fast enough at production scale?

**Check:**
- Are there N+1 query patterns? (Loop that issues one query per row)
- Are large collections created in memory unnecessarily? (`.collect()` on millions of rows)
- Are joins on indexed/partitioned columns?
- Are there unnecessary full table scans?
- Is caching used for DataFrames read multiple times?
- Are UDFs used where built-in functions would work?

**Red flags:**
```python
# N+1 pattern
for donor_id in donor_ids:  # 100,000 iterations
    result = db.query(Donation).filter_by(donor_id=donor_id).all()
# Should be: db.query(Donation).filter(Donation.donor_id.in_(donor_ids)).all()

# Collecting large data to the driver
all_rows = spark_df.collect()  # 10M rows → OOM
for row in all_rows:
    process(row)
# Should be: spark_df.foreach(process) or write to storage

# Unindexed query
SELECT * FROM donations WHERE UPPER(contributor_name) = 'SMITH'
# Function on column prevents index use. Add a functional index or store normalized.
```

### 5. Error Handling

Does the code fail gracefully or fail loudly?

**Check:**
- Are exceptions caught at the right level? (Not too broad, not too narrow)
- Are errors logged with enough context to diagnose? (Include the input that caused the failure)
- Are retries appropriate? (Network calls: yes. Validation errors: no.)
- Does the code distinguish between recoverable and fatal errors?
- Are resources cleaned up on failure? (Files closed, connections returned, temp files deleted)

**Red flags:**
```python
# Too broad
try:
    complex_operation()
except Exception:
    pass  # silently swallows every possible error

# Not enough context
except ValueError:
    logger.error("Invalid value")  # which value? from where? what input?

# Missing cleanup
f = open(path)
data = f.read()
process(data)
f.close()  # never reached if process() throws
# Use: with open(path) as f:
```

### 6. Readability

Can someone unfamiliar with this code understand it in one pass?

**Check:**
- Do function and variable names describe what they represent?
- Is the control flow linear (top-to-bottom), or does it jump around?
- Are there magic numbers or strings that should be named constants?
- Are comments explaining *why*, not *what*? (The code says what; comments should say why)
- Is the code doing too much in one function?
- Are there deep nesting levels (3+ indentation levels)?

**Red flags:**
```python
# Magic number
if amount > 2900:  # what is 2900? FEC individual contribution limit
MAX_INDIVIDUAL_CONTRIBUTION = 2900  # from 52 USC §30116(a)(1)
if amount > MAX_INDIVIDUAL_CONTRIBUTION:

# Deep nesting
if a:
    if b:
        for x in items:
            if c:
                do_thing()
# Refactor with early returns and extract functions

# Comment restates code
x = x + 1  # increment x by 1
# Delete this comment. If you need to explain why, write: # compensate for 0-based index
```

## How to Report Findings

### Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| **Blocker** | Correctness bug, security vulnerability, data loss risk | Must fix before merge |
| **Major** | Performance problem at scale, missing error handling, broken idempotency | Should fix before merge |
| **Minor** | Readability issue, style inconsistency, missing edge case that's unlikely | Fix or acknowledge |
| **Nit** | Preference, naming suggestion, minor formatting | Author's call |

### Format

```
## [Blocker] Possible SQL injection in search endpoint

**File:** api/views/search.py:47
**Code:**
    query = f"SELECT * FROM donors WHERE name LIKE '%{search_term}%'"

**Problem:** User input is interpolated directly into SQL. An attacker can inject
arbitrary SQL by submitting `'; DROP TABLE donors; --` as the search term.

**Fix:** Use parameterized queries:
    cursor.execute("SELECT * FROM donors WHERE name LIKE %s", (f"%{search_term}%",))
```

### Review Checklist

Before approving:

- [ ] Read every line of the diff (not just the files you know)
- [ ] Check that tests exist for new behavior and pass
- [ ] Check that tests test the *right thing* (not just that they pass)
- [ ] Verify no secrets, credentials, or PII in the diff
- [ ] Verify no `TODO` or `FIXME` without a linked issue
- [ ] Run the code locally if the change is non-trivial
- [ ] Check for unintended changes (auto-formatted files, lock file churn, moved files)

### When to Approve vs. Request Changes

**Approve** when:
- All blockers and majors are resolved
- Remaining items are minors/nits
- The code is better than what it replaces

**Request changes** when:
- Any blocker exists
- Multiple majors exist
- The approach is fundamentally wrong (suggest a different design)

**Don't block on:**
- Style preferences not documented in the project's style guide
- Hypothetical future requirements ("what if we need X someday?")
- Refactoring unrelated code ("while you're here, could you also...")

## Reviewing Different Types of Changes

### Data Pipeline Changes
- Verify source/target tables are correct
- Check write mode (append vs overwrite)
- Verify idempotency
- Check for schema evolution impact on downstream
- Verify partition strategy makes sense for query patterns

### API Changes
- Check for backwards compatibility (new fields ok, removed/renamed fields break clients)
- Verify input validation on all new parameters
- Check authentication/authorization on new endpoints
- Verify error responses are consistent with existing API patterns

### Database Migration Changes
- Check for table locks that block production traffic
- Verify rollback strategy exists
- Check that indexes are added for new foreign keys
- Verify default values for new NOT NULL columns

### Configuration Changes
- Check for secrets (should be env vars or secret manager, not in code)
- Verify feature flags have sensible defaults
- Check that configuration is consistent across environments

## Attribution Policy

NEVER include AI or agent attribution in review comments, commits, or documentation.
