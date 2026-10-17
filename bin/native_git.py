#!/usr/bin/env python3
"""Translate local Git events to the existing bounded effective-policy evaluator.

Local policy decisions are bypassable feedback. Configured receipts never assert
live backend invocation or protected provider authority.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

import selected_registration as registration

ep = registration.ep
require = registration.require
ZERO = '0' * 40
OID = re.compile(r'[0-9a-f]{40}\Z')


def explain(bound, operation):
    loaded = ep.load_registered_inputs(Path(bound['policy_root']), registration_source=Path(bound['policy_inputs']),
                                       registration_sha256=bound['policy_inputs_sha256'])
    result = ep.explain(loaded['contract'], loaded['policy'], loaded['selection'],
                        ep.default_context(bound['identity'], []), operation,
                        selection_source=loaded['registration']['selection_source'])
    require(result['state'] == 'resolved', 'native policy identity is unresolved')
    return result


def range_commits(repo, lines, remote):
    """Validate the native stream; exclude only the actual destination's heads."""
    exclusions = []
    advertised = registration.git(repo, 'ls-remote', '--heads', '--', remote)
    for line in advertised.splitlines():
        fields = line.split()
        require(len(fields) == 2 and OID.fullmatch(fields[0]) and fields[1].startswith('refs/heads/'),
                'malformed destination advertisement')
        registration.git(repo, 'cat-file', '-e', fields[0] + '^{commit}')
        exclusions.append('^' + fields[0])
    updates = []
    for line in lines.splitlines():
        fields = line.split()
        require(len(fields) == 4, 'malformed native update line')
        local_ref, local, remote_ref, prior = fields
        require(OID.fullmatch(local) and OID.fullmatch(prior) and remote_ref.startswith('refs/heads/'),
                'unsupported native update object/ref')
        if local == ZERO:
            updates.append((remote_ref, []))
            continue
        require(local_ref.startswith('refs/heads/') or local_ref == 'HEAD', 'unsupported local native ref')
        registration.git(repo, 'cat-file', '-e', local + '^{commit}')
        bases = list(exclusions)
        if prior != ZERO:
            registration.git(repo, 'cat-file', '-e', prior + '^{commit}')
            bases.append('^' + prior)
        commits = registration.git(repo, 'rev-list', '--reverse', local, *bases).splitlines()
        updates.append((remote_ref, commits))
    require(updates, 'missing native update protocol')
    return updates


def parse_arguments(argv):
    """Keep native payloads outside the control parser, including help handling."""
    if argv and argv[0] in ('commit-msg', 'pre-push'):
        event = argv[0]
        require(argv[1:2] == ['--'], 'native events require -- before Git arguments')
        arguments = argv[2:]
        expected = 1 if event == 'commit-msg' else 2
        require(len(arguments) == expected, event + ' requires exactly ' + str(expected) + ' Git arguments')
        return argparse.Namespace(event=event, arguments=arguments, binding=None, command=None)
    parser = argparse.ArgumentParser(description=__doc__, add_help=False, allow_abbrev=False,
        epilog='Native usage: commit-msg -- MESSAGE_FILE | pre-push -- REMOTE LOCATION')
    parser.add_argument('event', choices=('prompt', 'settings'))
    parser.add_argument('--binding', required=True, action='append')
    parser.add_argument('--command', action='append')
    if argv in (['--help'], ['-h']):
        parser.print_help()
        return None
    args = parser.parse_args(argv)
    require(len(args.binding) == 1, 'exactly one settings binding is required')
    args.binding = args.binding[0]
    if args.event == 'settings':
        require(args.command is not None and len(args.command) == 1, 'exactly one settings command is required')
        args.command = args.command[0]
    else:
        require(args.command is None, 'prompt does not accept a command')
    return args


def main(argv=None):
    try:
        args = parse_arguments(list(sys.argv[1:] if argv is None else argv))
        if args is None:
            return 0
        repo = Path.cwd()
        raw = args.binding if args.binding is not None else registration.git(repo, 'config', '--local', '--get', registration.BINDING_KEY)
        bound = ep.parse_json(raw, 'independently registered native inputs')
        registered_repo = Path(bound['git_repo'])
        if args.event in ('commit-msg', 'pre-push'):
            require(Path(registration.git(repo, 'rev-parse', '--show-toplevel')).resolve() == registered_repo,
                    'native registration belongs to another repository')
        pending = Path(registration.git(registered_repo, 'rev-parse', '--git-path', 'selected-registration-pending.json'))
        if not pending.is_absolute():
            pending = registered_repo / pending
        require(not pending.exists(), 'interrupted registration is unusable; recover before retry')
        definition = registration.verify_runtime(bound)
        if args.event == 'settings':
            template = ep.read_json(Path(bound['hooks_root']) / 'hooks/settings-snippet.json')
            allowed = [[part.replace('${package}', bound['hooks_root']) for part in shlex.split(hook['command'])]
                       for groups in template['hooks'].values() for group in groups for hook in group['hooks']]
            vector = json.loads(args.command)
            require(vector in allowed and definition['adapter'] == 'siege-compatibility', 'unregistered settings command vector')
            return subprocess.run(vector, timeout=90).returncode
        if args.event == 'prompt':
            event = ep.parse_json(sys.stdin.buffer.read(), 'prompt event')
            result = subprocess.run([sys.executable, '-B', str(Path(bound['hooks_root']) / 'bin/resolve-load-set.py'),
                '--repo', bound['identity'], '--prompt', event.get('prompt', ''), '--render-hook', '--mode', 'on'],
                capture_output=True, text=True, timeout=30)
            require(result.returncode == 0, result.stderr)
            print(result.stdout, end='')
            return 0
        if definition['adapter'] == 'siege-compatibility':
            command = Path(bound['hooks_root']) / 'compatibility/.githooks' / args.event
            result = subprocess.run([str(command), *args.arguments], timeout=90)
            return result.returncode
        if args.event == 'commit-msg':
            require(len(args.arguments) == 1, 'commit-msg requires its message file')
            message = Path(args.arguments[0]).read_text().strip()
            operations = [{'type': 'ticket-commit', 'message': message}]
        else:
            require(len(args.arguments) == 2, 'pre-push requires native remote name and location')
            updates = range_commits(repo, sys.stdin.read(), args.arguments[1])
            operations = []
            for ref, commits in updates:
                target = ref[len('refs/heads/'):]
                if target in definition['protected_targets']:
                    operations.append({'type': 'feature-merge', 'target_branch': target})
                for commit in commits:
                    message = registration.git(repo, 'show', '-s', '--format=%B', commit)
                    operations.append({'type': 'ticket-commit', 'message': message.strip()})
        for operation in operations:
            result = explain(bound, operation)
            if result['decision']['policy'] != 'allow':
                print('native-git: policy denied ' + json.dumps(result, sort_keys=True), file=sys.stderr)
                return 1
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print('native-git: incomplete registration/evidence: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
