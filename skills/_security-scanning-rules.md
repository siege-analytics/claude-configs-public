---
description: Always-on security scanning standards using Bandit. Apply when writing Python code that handles user input, credentials, shell commands, or network requests.
---

# Security Scanning Standards

Apply these standards when writing or reviewing Python code for security.

## Static analysis with Bandit

- Run Bandit on every PR. A new high-severity finding blocks merge.
- Configure Bandit in `pyproject.toml` under `[tool.bandit]`. Exclude test files from high-severity enforcement but still scan them for credential leaks.
- Maintain a baseline of known findings. New code must not introduce new findings. Existing findings are tracked as debt with tickets.

## Injection prevention

- Never construct SQL from string concatenation or f-strings. Use parameterized queries, ORM methods, or query builders exclusively.
- Never pass unsanitized input to `subprocess.run()`, `os.system()`, or `eval()`. If shell execution is unavoidable, use `shlex.quote()` and pass `shell=False`.
- Never construct file paths from user input without validation. Use `pathlib.Path.resolve()` and verify the result is within the expected directory.

## Credential handling

- Never hardcode credentials, API keys, or tokens in source files. Use environment variables or a secret manager (1Password CLI, AWS Secrets Manager).
- Never log credentials, even at DEBUG level. Scrub sensitive fields before logging request/response objects.
- Never commit `.env` files, credential JSON, or private keys. Enforce via `.gitignore` and a pre-commit check.

## Network security

- Use HTTPS for all external requests. If a legacy endpoint requires HTTP, document the exception and the risk.
- Verify TLS certificates by default. `verify=False` is acceptable only for local development with self-signed certs, and must be gated on a `DEBUG` or `ALLOW_INSECURE` flag.
- Set timeouts on all network requests. An unbounded request is a denial-of-service vector.

## Serialization safety

- Never use `pickle.load()` or `yaml.load()` (without `Loader=SafeLoader`) on untrusted input. These deserialize arbitrary objects and enable remote code execution.
- Prefer JSON for data interchange. When YAML is required, always use `yaml.safe_load()`.

## Dependency security

- Monitor dependencies for known vulnerabilities (Dependabot, `pip-audit`, or equivalent).
- Pin dependencies in lock files for reproducible builds. Use lower-bound pins (not exact) in `pyproject.toml` for library compatibility.


---

## Attribution

Standards derived from [Bandit documentation](https://bandit.readthedocs.io/) and [OWASP Python Security](https://owasp.org/www-project-python-security/). Both are open-source community resources.
