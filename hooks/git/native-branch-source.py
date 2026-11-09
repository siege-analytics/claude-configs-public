#!/usr/bin/env python3
"""Typed GitHub branch-creation source guard; no network calls or mutation.

Supports the current GitHub connector and the legacy GitHub MCP schema. A
provider resolves an explicit develop branch at operation time. SHA-only,
default-source calls use the canonical helper instead. Explicit develop-from-main
bootstrap is the standing authorized exception and requires provider create-only
semantics (GitHub POST refs, never PATCH/update).
"""
import json
import re
import sys

sys.dont_write_bytecode = True


def check(payload):
    tool = payload.get('tool_name', '')
    if not isinstance(tool, str) or not re.fullmatch(r'mcp__.*github.*create_branch', tool):
        return
    args = payload.get('tool_input')
    if not isinstance(args, dict):
        raise ValueError('GitHub branch creation arguments are unavailable')
    if 'repository_full_name' in args:
        if set(args) - {'repository_full_name', 'branch_name', 'base_ref', 'sha'}:
            raise ValueError('unsupported GitHub creation fields; update/force options cannot create develop safely')
        repository = args.get('repository_full_name')
        branch = args.get('branch_name')
        source = args.get('base_ref')
        sha = args.get('sha')
    else:
        if set(args) - {'owner', 'repo', 'branch', 'from_branch', 'sha'}:
            raise ValueError('unsupported GitHub creation fields; update/force options cannot create develop safely')
        owner, repo = args.get('owner'), args.get('repo')
        repository = f'{owner}/{repo}' if isinstance(owner, str) and isinstance(repo, str) else None
        branch = args.get('branch')
        source = args.get('from_branch')
        sha = args.get('sha')
    if not isinstance(repository, str) or not re.fullmatch(r'[^/\s]+/[^/\s]+', repository):
        raise ValueError('exact GitHub repository is required')
    if not isinstance(branch, str) or not branch:
        raise ValueError('new branch name is required')
    if branch == 'develop' and not sha and source in {'main', 'refs/heads/main'}:
        return  # Standing bootstrap authority; provider CREATE must reject an existing ref.
    if branch in {'develop', 'main', 'master'}:
        raise ValueError('protected ref creation requires explicit develop-from-main bootstrap with create-only semantics')
    if sha or source not in {'develop', 'refs/heads/develop'}:
        raise ValueError('normal GitHub branch creation requires explicit develop source; main, default-source and unverified SHA sources cannot substitute. For an already-authorized release/backport, use the CLI with its selected own Task branch_source_authorization exact-source record; no new approval is required')


def main():
    try:
        check(json.load(sys.stdin))
    except (ValueError, TypeError, AttributeError) as error:
        print('BLOCKED: ' + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
