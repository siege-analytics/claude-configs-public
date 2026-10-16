#!/usr/bin/env python3
"""Record and verify exact release outputs; publish their refs atomically.

The manifest is a handoff from the authorized release producer, not a signature
or runtime authorization. Never infer a missing output from a release branch.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

FORMS = ('nested', 'flat', 'claude-code', 'craft-agent')
SHA = re.compile(r'[0-9a-f]{40}')
SHA256 = re.compile(r'[0-9a-f]{64}')
TAG = re.compile(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')
MANIFEST = 'release-manifest.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def revision(root, ref):
    return git(root, 'rev-parse', '--verify', ref).decode().strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fields(value, names, context):
    require(isinstance(value, dict) and set(value) == set(names), f'{context}: invalid fields')


def validate_shape(data, repository, tag, source):
    fields(data, ('schema_version', 'repository', 'tag', 'source_commit', 'source_tree', 'changelog_sha256', 'outputs'), 'release manifest')
    require(type(data['schema_version']) is int and data['schema_version'] == 1, 'unsupported release manifest version')
    require(isinstance(tag, str) and TAG.fullmatch(tag), 'invalid release tag')
    require(data['repository'] == repository and data['tag'] == tag, 'foreign release manifest')
    require(isinstance(source, str) and SHA.fullmatch(source) and data['source_commit'] == source, 'source commit mismatch')
    require(isinstance(data['source_tree'], str) and SHA.fullmatch(data['source_tree']), 'invalid source tree')
    require(isinstance(data['changelog_sha256'], str) and SHA256.fullmatch(data['changelog_sha256']), 'invalid changelog digest')
    fields(data['outputs'], FORMS, 'release outputs')
    for form, entry in data['outputs'].items():
        fields(entry, ('commit', 'tree', 'archive', 'sha256'), form)
        for key in ('commit', 'tree'):
            require(isinstance(entry[key], str) and SHA.fullmatch(entry[key]), f'{form}: invalid {key}')
        require(entry['archive'] == f'{form}-{tag}.tar.gz', f'{form}: invalid archive name')
        require(isinstance(entry['sha256'], str) and SHA256.fullmatch(entry['sha256']), f'{form}: invalid archive digest')


def verify(root, data, assets, repository, tag, source, *, fetch=False):
    validate_shape(data, repository, tag, source)
    require(revision(root, source + '^{tree}') == data['source_tree'], 'source tree mismatch')
    for form, entry in data['outputs'].items():
        commit = entry['commit']
        if fetch:
            # Missing historical objects are a failure, never a branch-tip fallback.
            git(root, 'fetch', '--no-tags', 'origin', commit)
        require(revision(root, commit + '^{commit}') == commit, f'{form}: not an exact commit')
        require(revision(root, commit + '^{tree}') == entry['tree'], f'{form}: tree mismatch')
        changelog = git(root, 'show', commit + ':CHANGELOG.md')
        require(digest(changelog) == data['changelog_sha256'], f'{form}: changelog differs')
        require(re.search(rb'^## \[' + re.escape(tag[1:].encode()) + rb'\](?:\s|$)', changelog, re.M), f'{form}: version heading missing')
        required_files = {'CHANGELOG.md': changelog}
        if form in ('claude-code', 'craft-agent'):
            required_files['package.json'] = git(root, 'show', commit + ':package.json')
            package = json.loads(required_files['package.json'])
            require(package.get('package') == form and package.get('version') == tag[1:], f'{form}: package version mismatch')
            require(package.get('source_commit') == source, f'{form}: package source mismatch')
        archive = assets / entry['archive']
        require(archive.is_file() and not archive.is_symlink(), f'{form}: missing archive')
        raw = archive.read_bytes()
        require(digest(raw) == entry['sha256'], f'{form}: archive digest mismatch')
        unpacked = gzip.decompress(raw)
        require(unpacked == git(root, 'archive', '--format=tar', commit), f'{form}: archive does not represent recorded commit')
        # Git export attributes must not silently remove/substitute the release
        # metadata from an archive whose commit otherwise passes verification.
        with tarfile.open(fileobj=io.BytesIO(unpacked)) as tar:
            names = tar.getnames()
            for name, expected in required_files.items():
                require(names.count(name) == 1 and tar.getmember(name).isfile(), f'{form}: archive missing release metadata {name}')
                require(tar.extractfile(name).read() == expected, f'{form}: archived release metadata differs: {name}')
    return data


def record(root, outputs_root, assets, repository, tag, source):
    require(TAG.fullmatch(tag), 'invalid release tag')
    require(revision(root, 'HEAD') == source and SHA.fullmatch(source), 'producer source must be exact HEAD')
    changes = git(root, 'diff', '--name-only', 'HEAD').decode().splitlines()
    require(set(changes) <= {'VERSION', 'CHANGELOG.md'}, 'source has uncommitted changes outside release preparation')
    require(not git(root, 'ls-files', '--others', '--exclude-standard'), 'source has untracked input files')
    require((root / 'VERSION').read_text().strip() == tag[1:], 'prepared VERSION differs')
    changelog = (root / 'CHANGELOG.md').read_bytes()
    require(re.search(rb'^## \[' + re.escape(tag[1:].encode()) + rb'\](?:\s|$)', changelog, re.M), 'promote changelog before building')
    require(not assets.exists(), 'release asset directory already exists; refusing overwrite')
    data = {'schema_version': 1, 'repository': repository, 'tag': tag, 'source_commit': source,
            'source_tree': revision(root, source + '^{tree}'), 'changelog_sha256': digest(changelog), 'outputs': {}}
    archives = {}
    for form in FORMS:
        output = outputs_root / ('release-' + form)
        require(not git(output, 'status', '--porcelain', '--untracked-files=all'), f'{form}: output worktree is dirty')
        commit = revision(output, 'HEAD')
        require(git(root, 'show', commit + ':CHANGELOG.md') == changelog, f'{form}: built changelog differs')
        raw = gzip.compress(git(root, 'archive', '--format=tar', commit), mtime=0)
        name = f'{form}-{tag}.tar.gz'
        archives[name] = raw
        data['outputs'][form] = {'commit': commit, 'tree': revision(root, commit + '^{tree}'), 'archive': name, 'sha256': digest(raw)}
    validate_shape(data, repository, tag, source)
    assets.mkdir(parents=True)
    for name, raw in archives.items():
        (assets / name).write_bytes(raw)
    verify(root, data, assets, repository, tag, source)
    (assets / MANIFEST).write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')
    return data


def remote_tags(root, tags):
    refs = ['refs/tags/' + tag for tag in tags]
    lines = git(root, 'ls-remote', 'origin', *refs, *(ref + '^{}' for ref in refs)).decode().splitlines()
    found = dict(line.split('\t')[::-1] for line in lines)
    return {tag: found.get('refs/tags/' + tag + '^{}', found.get('refs/tags/' + tag)) for tag in tags}


def publish(root, data, assets, repository, tag, source, *, branches=False, fetch=False):
    verify(root, data, assets, repository, tag, source, fetch=fetch)
    targets = {tag: source, **{tag + '-' + form: data['outputs'][form]['commit'] for form in FORMS}}
    existing = remote_tags(root, targets)
    if not branches:
        require(existing[tag] == source, 'repair requires the existing source tag at the recorded commit')
    # Preflight the whole set before any refs change. Matching annotated tags
    # are accepted through their peeled commit, and never rewritten.
    for name, target in targets.items():
        require(existing[name] in (None, target), f'existing tag {name} differs from release manifest')
    refs = [f'{target}:refs/tags/{name}' for name, target in targets.items() if existing[name] is None]
    if branches:
        refs += [f'+{entry["commit"]}:refs/heads/release/{form}' for form, entry in data['outputs'].items()]
    if refs:
        git(root, 'push', '--atomic', 'origin', *refs)
    require(remote_tags(root, targets) == targets, 'published tags do not match the release manifest')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('record', 'verify', 'publish'))
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--outputs-root', type=Path, default=Path('/tmp'))
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--branches', action='store_true', help='Producer only: atomically publish release branches with source/consumer tags')
    parser.add_argument('--fetch', action='store_true', help='Fetch only exact output commits from origin before verification')
    args = parser.parse_args()
    if args.command == 'record':
        record(args.root, args.outputs_root, args.assets, args.repository, args.tag, args.source)
    else:
        data = json.loads((args.assets / MANIFEST).read_text())
        if args.command == 'verify':
            verify(args.root, data, args.assets, args.repository, args.tag, args.source, fetch=args.fetch)
        else:
            publish(args.root, data, args.assets, args.repository, args.tag, args.source, branches=args.branches, fetch=args.fetch)
    print(f'{args.command}: verified {args.tag} ({len(FORMS)} exact outputs)')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'release handoff failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
