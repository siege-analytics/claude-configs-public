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
from task_actions import shell_tokens

SHA = r'[0-9a-fA-F]{40}'
ID = r'[A-Za-z0-9_-]+'


def require(value, message):
    if not value:
        raise ValueError('pinned merge queue: ' + message)


def parse(command):
    """One complete literal command. No shell or GraphQL program extension."""
    if not re.match(r'^\s*gh\s+(?:pr\s+merge|api\s+graphql)(?:\s|$)', command):
        return None
    tokens = shell_tokens(command)
    args = [word for word, _, _ in tokens]
    if args[:3] == ['gh', 'pr', 'merge'] and not any(word.startswith('--match') for word in args[3:]):
        require(not any(word.split('=', 1)[0] in {'--admin', '--auto', '--disable-auto'} for word in args[3:]), 'unsupported merge bypass/auto option')
        # Ordinary scoped merges remain ordinary mutations. Returning None
        # grants no permission: the existing action/task/ownership path runs.
        return None
    require(not any(operator or globs for _, operator, globs in tokens), 'standalone command required')
    require('\x00' not in command and '\n' not in command and '\r' not in command, 'single line required')
    if args[:3] == ['gh', 'pr', 'merge']:
        require(len(args) >= 7 and re.fullmatch(r'[1-9][0-9]*', args[3]), 'literal PR number required')
        fields = {}
        i = 4
        while i < len(args):
            flag = args[i]
            require(flag in {'--merge', '--match-head-commit', '--repo', '-R'}, 'unsupported merge option')
            key = '--repo' if flag == '-R' else flag
            require(key not in fields, 'duplicate merge option')
            if key == '--merge':
                fields[key] = True
                i += 1
            else:
                require(i + 1 < len(args), 'missing option value')
                fields[key] = args[i + 1]
                i += 2
        require(fields.get('--merge') is True and re.fullmatch(SHA, fields.get('--match-head-commit', '')), 'merge and full head pin required')
        repo = fields.get('--repo', '')
        require(not repo or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*', repo), 'literal GitHub repository required')
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
    """Two fixed read-only lookups, one shared three-second execution budget."""
    require((os.environ.get('GH_HOST') or 'github.com') == 'github.com', 'ambient GitHub host override unsupported')
    if target['form'] == 'graphql':
        return dict(target, repository=None, number=None, base=None)
    spec = importlib.util.spec_from_file_location('queue_runner', Path(__file__).with_name('craft-settings-router.py'))
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    deadline = time.monotonic() + 3.0

    def read(args):
        remaining = deadline - time.monotonic()
        require(remaining > 0, 'read deadline exhausted')
        result, output, _error = runner.execute_hook('cd -- ' + shlex.quote(cwd) + ' && ' + shlex.join(['gh'] + args), b'', dict(os.environ), remaining)
        require(result == 0 and len(output.encode()) <= 65536, 'bounded GitHub proof failed')
        return json.loads(output)

    args = ['pr', 'view', str(target['number']), '--json', 'id,number,url,headRefOid,baseRefName']
    if target['repo']:
        args += ['--repo', target['repo']]
    pr = read(args)
    require(isinstance(pr, dict), 'missing PR identity')
    match = re.fullmatch(r'https://github\.com/([A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*)/pull/([1-9][0-9]*)', pr['url'])
    require(match and int(match[2]) == pr['number'] and isinstance(pr['number'], int), 'invalid PR URL identity')
    repo = match[1]
    require(isinstance(pr.get('headRefOid'), str) and re.fullmatch(SHA, pr['headRefOid']) and pr['headRefOid'].lower() == target['head'], 'PR head changed or invalid')
    require(isinstance(pr.get('id'), str) and re.fullmatch(ID, pr['id']), 'invalid PR node identity')
    if target['form'] == 'cli':
        require(pr['number'] == target['number'] and (not target['repo'] or target['repo'].lower() == repo.lower()), 'PR repository mismatch')
    require(isinstance(pr['baseRefName'], str) and pr['baseRefName'], 'missing destination branch')
    rules = read(['api', '--hostname', 'github.com', 'repos/' + repo + '/rules/branches/' + quote(pr['baseRefName'], safe='')])
    require(isinstance(rules, list) and any(isinstance(rule, dict) and rule.get('type') == 'merge_queue' for rule in rules), 'effective branch rules do not prove a required merge queue')
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
    # Local publication guards classify shape only. They grant no remote
    # authority: UMG separately proves queue rules and durably audits once.
    try:
        matched = len(sys.argv) == 3 and sys.argv[1] == '--classify' and parse(sys.argv[2]) is not None
    except ValueError:
        matched = False
    sys.exit(0 if matched else 1)
