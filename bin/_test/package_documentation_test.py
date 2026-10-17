#!/usr/bin/env python3
"""Run advertised consumer diagnostics from copied packages without source paths."""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]


def validate_links(package):
    for name in ('README.md', 'CONTRIBUTING.md'):
        for target in re.findall(r'\]\(([^)]+)\)', (package / name).read_text()):
            parsed = urlsplit(target)
            if parsed.scheme:
                assert parsed.scheme == 'https' and parsed.hostname == 'github.com', target
                assert re.search(r'/[0-9a-f]{40}/', target), target
                continue
            path = (package / target).resolve()
            assert path.is_relative_to(package.resolve()) and path.is_file(), (name, target)


def main():
    with tempfile.TemporaryDirectory(prefix='package-documentation-') as raw:
        base = Path(raw); empty_home = base / 'empty-home'; empty_home.mkdir()
        interpreter = base / 'tools'; interpreter.mkdir()
        (interpreter / 'python3').write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' "$@"\n')
        (interpreter / 'python3').chmod(0o755)
        # Only child processes receive the empty home; the operator environment
        # and shared workspace are unchanged. No source-path override is passed.
        environment = {'PATH': str(interpreter) + os.pathsep + os.environ.get('PATH', ''),
                       'HOME': str(empty_home), 'PYTHONDONTWRITEBYTECODE': '1'}
        for form in ('nested', 'flat', 'claude-code', 'craft-agent'):
            package = base / 'copied artifacts' / form
            shutil.copytree(ROOT / 'dist' / form, package)
            assert not (package / '.git').exists(), form
            validate_links(package)
            text = (package / 'README.md').read_text()
            blocks = re.findall(r'```sh\n(.*?)```', text, re.S)
            commands = [shlex.split(line) for block in blocks for line in block.splitlines() if line.strip()]
            assert len(commands) == (3 if form in ('claude-code', 'craft-agent') else 2), form
            for command in commands:
                assert command[0] == 'python3' and (package / command[1]).is_file(), (form, command)
                result = subprocess.run(command, cwd=package, env=environment, capture_output=True, text=True, timeout=60)
                assert result.returncode == 0, (form, command, result.stdout, result.stderr)
                if command[1] == 'bin/resolve-load-set.py':
                    selected = json.loads(result.stdout)['selected']; assert selected, form
                    for item in selected:
                        assert (package / item['load_path']).is_file(), (form, item)
                elif command[1] == 'bin/review-risk.py':
                    assert json.loads(result.stdout)['computed_tier'] == 'A', form
            payload = json.dumps({'prompt': 'review this Python diff', 'cwd': str(package)})
            result = subprocess.run(['bash', 'hooks/resolver/inject-resolver.sh'], cwd=package, env=environment,
                                    input=payload, capture_output=True, text=True, timeout=60)
            assert result.returncode == 0 and '<skill-kernel' in result.stdout, (form, result.stdout, result.stderr)
            assert 'state: error' not in result.stdout and '"continue":false' not in result.stdout, (form, result.stdout)
            assert str(ROOT) not in result.stdout, (form, 'source checkout leak')
            # A missing advertised file must be visible to the documentation check.
            path = package / 'catalog/resolver-manifest.json'; path.unlink()
            try:
                validate_links(package)
            except AssertionError:
                pass
            else:
                raise AssertionError((form, 'missing documented path accepted'))
    print('package documentation: PASS (4 copied packages, pinned links, 10 advertised commands, clean-home prompt probes, missing-file negatives)')


if __name__ == '__main__':
    main()
