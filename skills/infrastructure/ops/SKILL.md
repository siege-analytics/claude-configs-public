---
name: infrastructure-ops
description: "Rules for safe interaction with shared infrastructure (cyberpower, K8s, Rundeck). Prevents process accumulation, server overload, and cascading failures."
user-invocable: false
paths: "**/*.sh,**/*.yaml,**/*.yml"
---

# Infrastructure Operations Skill

This skill governs ALL interactions with shared infrastructure — servers, clusters, batch systems. It exists because a prior incident (2026-03-13) overloaded cyberpower to load avg 69 and filled disk to 100% due to unconstrained parallel execution.

## Core Principle

**Measure twice, cut once.** Research before executing. One thing at a time. Use established tools. Rules are constraints, not guidelines.

---

## SSH to Shared Servers

### NEVER do:
- `nohup ssh server 'long-running-command' &` — no backgrounded long-running processes via SSH
- Multiple parallel SSH sessions to the same server
- Ad-hoc Spark/Python batch jobs via SSH — that's what Rundeck is for
- Monitoring loops (`while true; ssh server 'ps aux'; sleep 5; done`)

### ALWAYS do:
- **One SSH command at a time** — run it, read the full result, then decide the next action
- **State your purpose before each SSH** — "I'm checking load average because X"
- **Use Rundeck for batch work** — download, parse, load, register jobs all go through Rundeck
- **Check server health first** — `uptime && df -h /` before launching any work

### SSH command template:
```
ssh cyberpower '<single focused command>'
```
Wait for the result. Read it. Then decide whether to run another.

---

## Batch Job Execution

### NEVER do:
- Launch Spark jobs directly via SSH
- Run multiple heavy processes concurrently on shared servers
- Use `nohup` or `screen` or `tmux` to background jobs outside Rundeck
- Download large datasets to local disk instead of S3

### ALWAYS do:
- **Use Rundeck** for all batch jobs (Rundeck API token and project are configured)
- **One job at a time** — wait for completion before starting the next
- **Use enterprise storage paths** — S3 buckets, not local filesystem
- **Set `multipleExecutions: false`** in Rundeck job definitions
- **Monitor via Rundeck API** — not ad-hoc SSH polling

---

## Process Management

### Before launching ANY process on a shared server:
1. Check current load: `uptime`
2. Check disk: `df -h /`
3. If load > 2x core count OR disk > 90%, **STOP** — do not add more work

### If something goes wrong:
1. Run ONE diagnostic command
2. Read the result completely
3. Decide on ONE corrective action
4. Execute it
5. Verify
6. Do NOT panic-fire multiple commands

---

## Local Bash / Background Tasks (Craft Agent specific)

In Craft Agent, every Bash tool call runs in background and produces a task notification.

### NEVER do:
- Launch more than 2 background tasks at once
- Try to `cat` the output file of an expired task (cascading reads)
- Fire background commands to check if other background commands finished
- React to stale task notifications from previous context windows

### ALWAYS do:
- Use the **Read tool** to read output files (not `cat` via Bash)
- If a task output expires, accept the loss and run a **fresh** command
- Say "stale" and ignore old task notifications after context compaction
- For simple checks (git status, ls, file reads), prefer Read/Glob tools over Bash

---

## Concurrency Limits

| Resource | Max Concurrent |
|----------|---------------|
| SSH sessions to cyberpower | 1 |
| Spark jobs on cyberpower | 1 (via Rundeck) |
| Background Bash tasks (local) | 2 |
| Rundeck job executions per server | 1 |

---

## Pre-flight Checklist (before any server interaction)

- [ ] Do I have a clear, single purpose for this command?
- [ ] Am I using the established tool (Rundeck, fec CLI, enterprise paths)?
- [ ] Have I checked server health (load, disk)?
- [ ] Am I running only ONE command, not a batch?
- [ ] Will I wait for the result before taking the next action?

If any answer is "no", stop and reconsider.
