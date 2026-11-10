#!/usr/bin/env python3
"""Pinned queue admission only; higher-level merge authority is unchanged (#1207)."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import time
from urllib.parse import quote
from task_actions import shell_tokens, github_graphql

SHA = r'[0-9a-fA-F]{40}'
ID = r'[A-Za-z0-9_-]+'
REPO = r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*'
# Policy: the only destination branches whose queue enqueue needs no task gate.
# Any other base (for example a release `main`) keeps the ordinary task path.
QUEUE_EXEMPT_BASES = ('develop',)
NODE_QUERY = 'query($id:ID!){node(id:$id){... on PullRequest{id number baseRefName headRefOid repository{nameWithOwner}}}}'


class ProofUnavailable(ValueError):
    """The bounded read could not run or answer; this is not a mismatch."""


def require(value, message, error=ValueError):
    if not value:
        raise error('pinned merge queue: ' + message)


def merge_flags(args, check_pins):
    """Inspect literal merge flags while keeping option values as data."""
    flags, pins, index = [], [], 3
    value_flags = {'--match-head-commit', '--repo', '-R', '--subject', '-t',
                   '--body', '-b', '--body-file', '-F', '--author-email', '-A'}
    while index < len(args):
        word = args[index]
        if word == '--':
            break
        flag, equal, value = word.partition('=')
        if word.startswith('-'):
            require(flag != '--admin', 'admin bypass is not supported')
            flags.append((flag, bool(equal)))
            if check_pins and flag.startswith('--match'):
                require(flag == '--match-head-commit', 'unsupported head pin option')
                if not equal:
                    value = args[index + 1] if index + 1 < len(args) else ''
                require(re.fullmatch(SHA, value), 'full head pin required')
                pins.append(value)
            if flag in value_flags and not equal:
                index += 1
        index += 1
    return flags, pins


def command_segments(tokens):
    """Inspect supported control segments, excluding redirection operands."""
    segment, index = [], 0
    while index < len(tokens):
        word, operator, _globs = tokens[index]
        if operator and word in {'&&', '||', ';', '|'}:
            yield segment
            segment = []
        elif operator and re.fullmatch(r'[0-9]*(?:>>|>&|<&|>\||>|<)|&>>|&>', word):
            index += 1  # The redirected filename is not a command or an option.
        elif not operator:
            segment.append(word)
        index += 1
    yield segment


def parse(command):
    """One complete literal command. No shell or GraphQL program extension."""
    if not re.match(r'^\s*gh\s+(?:pr\s+merge|api\s+graphql)(?:\s|$)', command):
        return None
    tokens = shell_tokens(command)
    args = [word for word, _, _ in tokens]
    if args[:3] == ['gh', 'api', 'graphql']:
        try:
            document = github_graphql(args)
        except (ValueError, TypeError, KeyError):
            return None  # Ordinary action parser owns unsupported non-queue transport.
        if document.get('kind') != 'other-mutation' or 'enqueuePullRequest' not in document.get('fields', []):
            return None
    if args[:3] == ['gh', 'pr', 'merge']:
        segments = list(command_segments(tokens))
        for segment in segments[1:]:
            if segment[:3] == ['gh', 'pr', 'merge']:
                merge_flags(segment, False)  # An ordinary fallback cannot hide a later admin merge.
        flags, pins = merge_flags(segments[0], True)
        require(len(pins) <= 1, 'one full head pin required')
        if not pins:
            return None  # Ordinary task-scoped merge, never a queue exemption.
        if any(operator or globs for _, operator, globs in tokens):
            return None  # Ordinary composition must cover every target; no queue exemption.
        canonical = {'--merge', '--match-head-commit', '--repo', '-R'}
        if any(flag not in canonical or equal for flag, equal in flags):
            return None  # Non-exempt CLI options retain all ordinary guards.
        if len(args) < 4 or not re.fullmatch(r'[1-9][0-9]*', args[3]):
            return None  # Branch/URL/default selectors are not the canonical queue form.
    require(not any(operator or globs for _, operator, globs in tokens), 'standalone command required')
    require('\x00' not in command and '\n' not in command and '\r' not in command, 'single line required')
    # Shell double quotes keep a backslash before ordinary characters but shell_tokens drops it,
    # and GraphQL decodes \uXXXX: the validated bytes must be the delivered bytes.
    require('\\' not in command, 'backslash escapes unsupported')
    if args[:3] == ['gh', 'pr', 'merge']:
        if len(args) < 7:
            return None
        fields = {}
        i = 4
        while i < len(args):
            flag = args[i]
            if flag not in {'--merge', '--match-head-commit', '--repo', '-R'}:
                return None
            key = '--repo' if flag == '-R' else flag
            if key in fields:
                return None
            if key == '--merge':
                fields[key] = True
                i += 1
            else:
                if i + 1 >= len(args):
                    return None
                fields[key] = args[i + 1]
                i += 2
        if fields.get('--merge') is not True:
            return None
        repo = fields.get('--repo', '')
        if repo and not re.fullmatch(REPO, repo):
            return None
        return {'form': 'cli', 'number': int(args[3]), 'head': fields['--match-head-commit'].lower(), 'repo': repo}
    require(args[:3] == ['gh', 'api', 'graphql'], 'literal GraphQL endpoint required')
    fields = {}
    for i in range(3, len(args), 2):
        require(i + 1 < len(args) and args[i] == '-f', 'only literal -f fields supported')
        key, equal, value = args[i + 1].partition('=')
        require(equal and key not in fields and key in {'query', 'id', 'oid'}, 'unknown or duplicate GraphQL field')
        fields[key] = value
    query = fields.get('query', '')
    # Lexically exact operation/response grammar, allowing ordinary whitespace.
    def graphql_tokens(text):
        pattern = re.compile(r'"[^"\\\r\n]*"|[_A-Za-z][_0-9A-Za-z]*|[$!():{},]')
        words, end = [], 0
        for match in pattern.finditer(text):
            require(not text[end:match.start()].strip(), 'unsupported GraphQL token')
            words.append(match.group())
            end = match.end()
        require(not text[end:].strip(), 'unsupported GraphQL token')
        return words
    words = graphql_tokens(query)
    variable = 'mutation($id:ID!,$oid:GitObjectID!){enqueuePullRequest(input:{pullRequestId:$id,expectedHeadOid:$oid}){mergeQueueEntry{position state}}}'
    literal = 'mutation{enqueuePullRequest(input:{pullRequestId:"NODE",expectedHeadOid:"HEAD"}){mergeQueueEntry{position state}}}'
    if words == graphql_tokens(variable):
        require(set(fields) == {'query', 'id', 'oid'}, 'both bound GraphQL variables required')
        node, head = fields['id'], fields['oid']
    else:
        expected = graphql_tokens(literal)
        require(set(fields) == {'query'} and len(words) == len(expected), 'single exact enqueuePullRequest operation required')
        node_index, head_index = expected.index('"NODE"'), expected.index('"HEAD"')
        node, head = words[node_index], words[head_index]
        require(re.fullmatch('"' + ID + '"', node) and re.fullmatch('"' + SHA + '"', head), 'literal PR node and full expected head required')
        words[node_index], words[head_index] = '"NODE"', '"HEAD"'
        require(words == expected, 'single exact enqueuePullRequest operation required')
        node, head = node[1:-1], head[1:-1]
    require(re.fullmatch(ID, node) and re.fullmatch(SHA, head), 'literal PR node and full expected head required')
    return {'form': 'graphql', 'node': node, 'head': head.lower()}


def verify(target, cwd):
    """Fixed read-only lookups under one shared three-second execution budget.

    None grants no queue exemption and leaves the ordinary task path. A CLI
    proof that cannot be read returns None for that path; GraphQL has no
    ordinary path, so its unreadable proof denies.
    """
    try:
        return _verify(target, cwd)
    except ProofUnavailable:
        if target['form'] == 'cli':
            return None  # Canonical pinned merge keeps its task scope; never an exemption.
        raise


def _verify(target, cwd):
    require((os.environ.get('GH_HOST') or 'github.com') == 'github.com', 'ambient GitHub host override unsupported', ProofUnavailable)
    spec = importlib.util.spec_from_file_location('queue_runner', Path(__file__).with_name('craft-settings-router.py'))
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    deadline = time.monotonic() + 3.0

    def read(args):
        remaining = deadline - time.monotonic()
        require(remaining > 0, 'read deadline exhausted', ProofUnavailable)
        try:
            result, output, _error = runner.execute_hook('cd -- ' + shlex.quote(cwd) + ' && ' + shlex.join(['gh'] + args), b'', dict(os.environ), remaining)
            require(result == 0 and len(output.encode()) <= 65536, 'bounded GitHub proof failed', ProofUnavailable)
            return json.loads(output)
        except ProofUnavailable:
            raise
        except ValueError as exc:  # Runner timeout/output bound and undecodable JSON.
            raise ProofUnavailable('pinned merge queue: bounded GitHub proof failed') from exc

    if target['form'] == 'graphql':
        answer = read(['api', '--hostname', 'github.com', 'graphql', '-f', 'query=' + NODE_QUERY, '-f', 'id=' + target['node']])
        data = answer.get('data') if isinstance(answer, dict) else None
        pr = data.get('node') if isinstance(data, dict) else None
        require(isinstance(pr, dict) and pr.get('id') == target['node'], 'PR node lookup failed')
        owner = pr.get('repository')  # The base repository, where the merge lands.
        repo = owner.get('nameWithOwner') if isinstance(owner, dict) else None
        require(isinstance(repo, str) and re.fullmatch(REPO, repo), 'invalid PR repository identity')
        number = pr.get('number')
        require(type(number) is int and number > 0, 'invalid PR number')
        require(isinstance(pr.get('headRefOid'), str) and re.fullmatch(SHA, pr['headRefOid']) and pr['headRefOid'].lower() == target['head'], 'PR head changed or invalid')
        require(isinstance(pr.get('baseRefName'), str) and pr['baseRefName'], 'missing destination branch')
        if pr['baseRefName'] not in QUEUE_EXEMPT_BASES:
            return None  # No exemption; the ordinary path does not model GraphQL.
        return dict(target, repository=repo, number=number, base=pr['baseRefName'])
    args = ['pr', 'view', str(target['number']), '--json', 'id,number,url,headRefOid,baseRefName']
    if target['repo']:
        args += ['--repo', target['repo']]
    pr = read(args)
    require(isinstance(pr, dict), 'missing PR identity')
    match = re.fullmatch(r'https://github\.com/(' + REPO + r')/pull/([1-9][0-9]*)', pr['url'])
    require(match and int(match[2]) == pr['number'] and isinstance(pr['number'], int), 'invalid PR URL identity')
    repo = match[1]
    require(isinstance(pr.get('headRefOid'), str) and re.fullmatch(SHA, pr['headRefOid']) and pr['headRefOid'].lower() == target['head'], 'PR head changed or invalid')
    require(isinstance(pr.get('id'), str) and re.fullmatch(ID, pr['id']), 'invalid PR node identity')
    require(pr['number'] == target['number'] and (not target['repo'] or target['repo'].lower() == repo.lower()), 'PR repository mismatch')
    require(isinstance(pr['baseRefName'], str) and pr['baseRefName'], 'missing destination branch')
    if pr['baseRefName'] not in QUEUE_EXEMPT_BASES:
        return None  # Not an exempt base: the ordinary task path applies.
    rules = read(['api', '--hostname', 'github.com', 'repos/' + repo + '/rules/branches/' + quote(pr['baseRefName'], safe='')])
    require(isinstance(rules, list), 'malformed effective branch rules')
    if not any(isinstance(rule, dict) and rule.get('type') == 'merge_queue' for rule in rules):
        return None  # Confirmed ordinary merge: retain task and publication checks.
    return dict(target, repository=repo, number=pr['number'], node=pr['id'], base=pr['baseRefName'])


def audit(target, session, directory):
    """Permission decision is durable before allow; this is not enqueue success."""
    root = Path(directory)
    require(session and root.is_absolute() and root.name == session, 'bound own-session directory required')
    for part in [root, *root.parents]:
        require(not part.is_symlink(), 'symlinked session path rejected')
    require(root.is_dir(), 'own session directory does not exist')
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            os.mkdir('data', mode=0o700, dir_fd=root_fd)
        except FileExistsError:
            pass  # Existing directory is checked with O_NOFOLLOW below.
        data_fd = os.open('data', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        try:
            fd = os.open('merge-queue-decisions.jsonl', os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=data_fd)
        finally:
            os.close(data_fd)
    finally:
        os.close(root_fd)
    try:
        st = os.fstat(fd)
        require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_uid == os.getuid(), 'unsafe audit file')
        record = dict(schema_version=1, decision='allow-enqueue', session=session, pr=target['number'],
                      repository=target['repository'], head=target['head'], node=target['node'], base=target['base'],
                      form=target['form'], time=time.time(), remote_success=False)
        blob = (json.dumps(record, sort_keys=True) + '\n').encode()
        require(os.write(fd, blob) == len(blob), 'incomplete audit write')
        os.fsync(fd)
    finally:
        os.close(fd)


if __name__ == '__main__':
    import sys
    # Pure grammar inspection has no authority. Guard exemptions use the fresh
    # queue predicate; UMG separately owns admission and the single audit.
    try:
        target = parse(sys.argv[2]) if len(sys.argv) in {3, 4} else None
        matched = target is not None and (
            len(sys.argv) == 3 and sys.argv[1] == '--classify'
            or len(sys.argv) == 4 and sys.argv[1] == '--queue-required'
            and verify(target, sys.argv[3]) is not None)
    except (OSError, ValueError, TypeError, KeyError, ImportError, SyntaxError):
        matched = False
    sys.exit(0 if matched else 1)
