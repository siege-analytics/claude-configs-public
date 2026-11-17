"""Bounded own-task ready/landed-close proof; never executes the candidate (#1218)."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from task_actions import shell_tokens, github_ticket_reference as reference

REPO = r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_][A-Za-z0-9_.-]*'
SHA = r'[0-9a-f]{40}'
_DEADLINE = 0


def require(value, message):
    if not value:
        raise ValueError(message)


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def read(args):
    runner = module('mechanical_bounded_runner', 'craft-settings-router.py')
    remaining = _DEADLINE - time.monotonic()
    require(remaining > 0, 'GitHub proof exceeded its total eight-second budget')
    code, output, _ = runner.execute_hook(shlex.join(['gh', 'api', '--hostname', 'github.com', *args]), b'', dict(os.environ), min(3.0, remaining))
    require(code == 0, 'GitHub read failed; retry the read-only proof')
    require(len(output.encode()) <= 65536, 'GitHub response exceeds 64 KiB')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate GitHub response key')
            result[key] = value
        return result
    value = json.loads(output, object_pairs_hook=unique)
    require(isinstance(value, dict), 'invalid GitHub object')
    return value


def git(cwd, *args):
    try:
        p = subprocess.run(['git', '--no-optional-locks', '-C', cwd, *args], capture_output=True, text=True, timeout=1)
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError('local Git ownership read failed') from error
    require(p.returncode == 0 and len(p.stdout) < 8192, 'cannot establish local Git ownership')
    return p.stdout.strip()


def item_url_matches(value, repo, resource, number):
    """GitHub owner/repo are case-insensitive; URL structure is not folded."""
    if not isinstance(value, str):
        return False
    match = re.fullmatch(r'https://github\.com/([^/]+)/([^/]+)/(pull|issues)/([1-9][0-9]*)', value)
    return bool(match and f'{match[1]}/{match[2]}'.casefold() == repo.casefold()
                and match[3] == resource and match[4] == str(number))




def verify(command, cwd, body):
    """Return False outside the exact grammar; proof failures are diagnostic."""
    if not re.match(r'^\s*(?:gh\s+(?:pr\s+ready|(?:issue|pr)\s+close)\s|cd\s|CCP_TASK_ID=)', command):
        return False
    global _DEADLINE
    _DEADLINE = time.monotonic() + 8.0
    tokens = shell_tokens(command)
    prefix_root = None
    if len(tokens) > 4 and tokens[0][0] == 'cd' and tokens[2][:2] == ('&&', True):
        require(not tokens[1][1] and not tokens[1][2] and os.path.isabs(tokens[1][0]), 'cd prefix requires one literal absolute task worktree')
        prefix_root = str(Path(tokens[1][0]).resolve())
        tokens = tokens[3:]
    command_binding = ''
    if tokens and not tokens[0][1] and tokens[0][0].startswith('CCP_TASK_ID='):
        require(not tokens[0][2], 'task binding must be literal')
        command_binding = tokens[0][0].split('=', 1)[1]
        require(command_binding and len(command_binding) <= 1024 and not any(ord(c) < 32 or ord(c) == 127 for c in command_binding), 'invalid literal task binding')
        tokens = tokens[1:]
    require(not any(op or glob for _, op, glob in tokens), 'split mechanical transitions into one literal gh command')
    args = [word for word, _, _ in tokens]
    if args[:3] not in (['gh', 'pr', 'ready'], ['gh', 'issue', 'close'], ['gh', 'pr', 'close']):
        return False
    require(len(args) >= 4 and re.fullmatch(r'[1-9][0-9]*', args[3]), 'use an explicit numeric item selector')
    kind, action, number = args[1], args[2], int(args[3])
    flags = {}; i = 4
    while i < len(args):
        flag, equal, value = args[i].partition('=')
        flag = {'-R': '--repo', '-c': '--comment'}.get(flag, flag)
        require(flag in {'--repo', '--comment', '--reason'} and flag not in flags, 'unsupported or duplicate mechanical transition option')
        if not equal:
            i += 1
            require(i < len(args), 'missing mechanical transition option value')
            value = args[i]
        flags[flag] = value; i += 1
    repos = [flags['--repo']] if '--repo' in flags else []
    require(len(repos) == 1 and re.fullmatch(REPO, repos[0]), 'supply one literal --repo owner/repository')
    repo = repos[0]
    body = flags.get('--comment', '')
    require((os.environ.get('GH_HOST') or 'github.com') == 'github.com', 'only github.com proof is supported')
    require(not os.environ.get('GH_REPO') or os.environ['GH_REPO'].lower() == repo.lower(), 'conflicting ambient repository')
    require(action != 'ready' or set(flags) <= {'--repo', '-R'}, 'ready accepts only its repository selector')
    require(flags.get('--reason', 'completed') == 'completed', 'only mechanically completed issue closes are supported')
    resolver = module('mechanical_task_resolver', 'resolve-think-gate.py')
    sid = resolver.session_id_from_env()
    require(sid, 'restore the own-session task identity')
    workspace = os.environ.get('CRAFT_AGENT_WORKSPACE') or cwd
    ambient_binding = resolver.task_binding()
    require(not command_binding or not ambient_binding or command_binding == ambient_binding, 'conflicting command and current task bindings')
    binding = command_binding or ambient_binding
    candidates = []; ready_candidates = []
    for gate in resolver.find_all_gates(workspace):
        data = gate['data']
        ticket = data.get('ticket') or data.get('task_id', '')
        match = re.fullmatch(rf'({REPO})#([1-9][0-9]*)', ticket) if isinstance(ticket, str) else None
        if match and (not binding or resolver.task_identity(data) == binding):
            if match[1].lower() == repo.lower():
                candidates.append(gate)
            elif action == 'ready' and isinstance(data.get('repo_root'), str):
                context = prefix_root or resolver.canonical(cwd)
                if binding or resolver._within(context, data['repo_root']):
                    ready_candidates.append(gate)
    # Preserve existing same-repository selection. A bound central ticket may
    # target its actual code worktree; this adds no cross-repository close.
    candidates = candidates or ready_candidates
    require(len(candidates) == 1, 'select one unambiguous own task for the literal repository (use its existing task binding)')
    task_root = candidates[0]['data'].get('repo_root')
    require(isinstance(task_root, str) and os.path.isabs(task_root), 'own task needs its physical repository worktree')
    task_root = resolver.canonical(task_root)
    require(prefix_root is None or prefix_root == task_root, 'cd prefix does not select the bound task worktree')
    require(git(task_root, 'rev-parse', '--show-toplevel') == task_root, 'own task root is not its Git worktree')
    selected = resolver.select_task(workspace, [task_root], binding=resolver.task_identity(candidates[0]['data']))
    require(selected.get('gate'), selected.get('error') or 'select the own bound task')
    task = selected['gate']['data']
    # The universal mutation gate owns lifecycle authority. Do not introduce
    # another phase gate here (verification/closure may have its own task).
    role = str(task.get('role', '')).lower()
    require(not re.search(r'read.only|review.only', role) and role not in {'reviewer', 'observer', 'comment-only'}, 'existing read-only/review-only/comment-only task does not authorize state transitions')
    ticket = task.get('ticket') or task.get('task_id')
    match = re.fullmatch(rf'({REPO})#([1-9][0-9]*)', ticket or '')
    require(match and (action == 'ready' or match[1].lower() == repo.lower()), 'own task needs a canonical ticket; close must target the same repository')
    ticket_repo = match[1]
    task_number = int(match[2])
    alias = task.get('task_id', '')
    require(not re.fullmatch(rf'{REPO}#[1-9][0-9]*', alias) or alias.lower() == ticket.lower(), 'conflicting canonical task and ticket identities')
    directory = Path(resolver.own_session_directory(workspace, sid))
    metadata = {}
    if (directory/'session.jsonl').exists():
        with (directory/'session.jsonl').open() as f:
            metadata = json.loads(f.readline(65537))
    labels = metadata.get('labels', [])
    require(isinstance(labels, list) and not set(labels) & {'role::reviewer', 'role::observer'}, 'review-only session role cannot ready or close items')
    viewer = None
    if kind == 'pr':
        # Installation tokens cannot read REST /user. The fixed GraphQL
        # viewer read proves the same existing actor without changing tokens.
        identity = read(['graphql', '-f', 'query=query { viewer { login } }'])
        require(not identity.get('errors'), 'GitHub viewer identity lookup returned errors')
        data = identity.get('data')
        require(isinstance(data, dict) and isinstance(data.get('viewer'), dict), 'missing or malformed GitHub viewer identity')
        viewer = data['viewer'].get('login')
        require(isinstance(viewer, str) and viewer and not any(c.isspace() for c in viewer), 'missing authenticated GitHub actor')

    def pr(n):
        value = read([f'repos/{repo}/pulls/{n}'])
        require(type(value.get('number')) is int and value['number'] == n and item_url_matches(value.get('html_url'), repo, 'pull', n), 'GitHub PR identity does not match')
        require(value.get('base', {}).get('repo', {}).get('full_name', '').lower() == repo.lower(), 'PR base repository mismatch')
        return value

    if action == 'ready':
        value = pr(number)
        require(value.get('state') == 'open' and value.get('draft') is True, 'PR must be an open draft')
        require(value.get('user', {}).get('login') == viewer, 'PR author is another GitHub actor; obtain its owner signoff')
        head = value.get('head', {})
        require(head.get('repo', {}).get('full_name', '').lower() == repo.lower(), 'own PR must originate in the selected PR repository')
        require(head.get('ref') == git(task_root, 'branch', '--show-current') and head.get('sha') == git(task_root, 'rev-parse', 'HEAD'), 'PR head does not match this task worktree branch and commit')
        require(reference(value.get('body'), task_number, ticket_repo, source_repo=repo) or reference(value.get('body'), task_number, ticket_repo, 'reference', source_repo=repo), 'PR body lacks a Refs/Fixes declaration for the own-task ticket')
        return True

    nomination = re.fullmatch(r'(fixed|superseded) by PR #([1-9][0-9]*)[.!]?', body.strip().splitlines()[0] if body.strip() else '', re.I)
    require(nomination, 'nominate evidence as Fixed by PR #N or Superseded by PR #N')
    source = pr(int(nomination[2]))
    require(source.get('merged') is True and source.get('state') == 'closed' and re.fullmatch(SHA, source.get('merge_commit_sha') or ''), 'fixing/superseding PR has not landed with a merge commit')
    base = source.get('base', {}).get('ref')
    require(isinstance(base, str) and re.fullmatch(r'[A-Za-z0-9_./-]+', base) and '..' not in base, 'invalid PR base branch')
    from urllib.parse import quote
    comparison = read([f'repos/{repo}/compare/{quote(base, safe="")}...{source["merge_commit_sha"]}'])
    require(comparison.get('status') in {'behind', 'identical'}, 'merge commit is not reachable from the live PR base')
    if kind == 'issue':
        require(task_number == number, 'issue close does not match the own-task ticket')
        target = read([f'repos/{repo}/issues/{number}'])
        require(type(target.get('number')) is int and target['number'] == number
                and item_url_matches(target.get('html_url'), repo, 'issues', number)
                and target.get('state') == 'open' and 'pull_request' not in target,
                'close target is not the exact open GitHub issue')
        relation = reference(source.get('body'), number, repo) or reference(source.get('body'), number, repo, 'reference')
        if nomination[1].lower() == 'superseded':
            relation = relation or reference(source.get('body'), number, repo, 'supersede')
        require(relation, 'landed PR body lacks a Refs/Fixes/Supersedes declaration for this issue')
        # GitHub's default integration branch is an existing repository
        # contract, not a caller-selected approval. In develop -> main repos
        # a develop merge alone is insufficient to close the delivery issue.
        repository = read([f'repos/{repo}'])
        default = repository.get('default_branch')
        require(repository.get('full_name', '').lower() == repo.lower() and isinstance(default, str)
                and re.fullmatch(r'[A-Za-z0-9_./-]+', default) and '..' not in default, 'cannot establish repository default integration branch')
        integrated = read([f'repos/{repo}/compare/{quote(default, safe="")}...{source["merge_commit_sha"]}'])
        require(integrated.get('status') in {'behind', 'identical'}, 'fix has not reached the repository default integration branch')
    else:
        require(nomination[1].lower() == 'superseded' and int(nomination[2]) != number, 'PR close needs a distinct superseding PR')
        target = pr(number)
        require(target.get('state') == 'open' and target.get('user', {}).get('login') == viewer, 'superseded PR must be open and owned by this GitHub actor')
        require(target.get('base', {}).get('ref') == base, 'superseding and target PR base branches differ')
        require(reference(source.get('body'), number, repo, 'supersede', 'pull') and (reference(source.get('body'), task_number, repo) or reference(source.get('body'), task_number, repo, 'reference')), 'landed PR lacks exact supersession and own-task ticket relationships')
    return True


if __name__ == '__main__':
    try:
        sys.exit(0 if verify(sys.argv[1], sys.argv[2] or os.getcwd(), '') else 1)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError) as error:
        print('Mechanical transition proof: ' + str(error), file=sys.stderr)
        sys.exit(1)
