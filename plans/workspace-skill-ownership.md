# Workspace skill ownership

Goal source: operator request to finish the remaining repairs, delegated by the
coordinator under #1134. Scope is the workspace skills copier; user/global
settings and the live workspace remain outside this change.

The previous copier deleted the entire skills tree and restored only root
Markdown files. An operator skill directory or extra file inside an incoming
managed skill therefore disappeared during installation. Refresh exact incoming
file paths instead. Preserve all other paths, including obsolete paths whose
ownership cannot be established. Incoming managed files retain the existing
physical-path checks and overwrite contract.

Retire only the observed legacy skills/RESOLVER.md artifact when both
size and SHA256 match the committed catalog. Its provenance is an observed legacy
installation artifact, with no asserted upstream commit. A same-name operator
modification survives. The coordinator retains the pre-install backup.

Investigation: deploy_to_workspace used shutil.rmtree(ws_skills), followed by a
root Markdown-only restoration loop. No prior ownership receipt existed.
Pre-mortem: broad cleanup could remove operator content; filename-only retirement
could delete a customized dispatcher; mutable retirement metadata could weaken
immutable deployment. Conservative exact-file copying and accepted-snapshot
catalog loading address those failure modes. Obsolete unknown files
remain; a general ownership/upgrade schema stays within the #1134 umbrella.

Validation uses the actual immutable deployment fixture with a synthetic
committed legacy hash, avoiding publication of private observed dispatcher bytes.
It checks custom top-level and nested files, unrelated root Markdown, matching
legacy retirement, and equal-size modified legacy preservation. The production
catalog retains only the observed hash and size supplied by the coordinator.
