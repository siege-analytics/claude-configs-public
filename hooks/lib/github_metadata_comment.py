"""Typed standalone metadata posts, not Task authorization (#1245).

True selects the descriptive-post lane; None preserves existing single-command
checks; False declines this lane for malformed/dynamic/composed candidates.
No GitHub call or candidate executable is run. Both coordinator and destructive guards consume
this same recognizer; UMG owns the actual selected Task and remote target.
"""
import os
from pathlib import Path
import re
import task_actions

def metadata_comment(command, cwd, *, details=None):
    try:
        lexed = task_actions.shell_tokens(command)
    except ValueError:
        return None  # Unparsed syntax never gains this lane; preserve old checks.
    words = [word for word, _, _ in lexed]
    if any(operator for _, operator, _ in lexed) and any(
            words[i].rsplit('/', 1)[-1] == 'gh' and words[i + 1] in {'issue', 'pr'}
            and (words[i + 2] in {'comment', 'edit', 'review'} or words[i + 1:i + 3] == ['issue', 'create']) for i in range(len(words) - 2)):
        return False
    # Parse the existing binding metasyntax without changing the actual command
    # passed to UMG. Other environment/startup overrides take the old route.
    from git_command import SAFE_ENV, literal_prefix
    try:
        words, environment = literal_prefix(words, strict=True)
    except ValueError:
        return None
    if any(name not in SAFE_ENV for name in environment):
        return None
    start = 0
    if len(words) < start + 3 or words[start].rsplit('/', 1)[-1] != 'gh':
        return None
    resource, verb = words[start + 1:start + 3]
    if resource not in {'issue', 'pr'} or verb not in {'comment', 'edit', 'review', 'create'}:
        return None
    if verb == 'create' and resource != 'issue':
        return None
    if verb == 'review' and '--comment' not in words[start + 3:]:
        return None  # Approval/request-changes keep the existing transition proof.
    if any(operator or globs for _, operator, globs in lexed):
        return False
    args = words[start + 3:]
    values, flags, target = {}, set(), None
    value_flags = {'--body': 'body', '-b': 'body', '--body-file': 'file', '-F': 'file',
                   '--repo': 'repo', '-R': 'repo'}
    if verb == 'create':
        value_flags.update({'--title': 'title', '-t': 'title'})
    i = 0
    while i < len(args):
        word = args[i]
        flag, separator, attached = word.partition('=')
        if flag in value_flags:
            key = value_flags[flag]
            if key in values:
                return False
            if separator:
                value = attached
            else:
                i += 1
                if i == len(args):
                    return False
                value = args[i]
            if not value:
                return False
            values[key] = value
        elif word in {'--approve', '--request-changes'} and verb == 'review':
            return False
        elif word == '--comment' and resource == 'pr' and verb == 'review' and word not in flags:
            flags.add(word)
        elif word in {'--edit-last', '--create-if-none'} and verb == 'comment' and word not in flags:
            flags.add(word)
        elif not word.startswith('-') and target is None:
            target = word
        else:
            return None  # Unmodeled single-command flags keep the existing route.
        i += 1
    url = re.fullmatch(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/(issues|pull)/([0-9]+)', target or '')
    repository = values.get('repo', '')
    repo_match = re.fullmatch(r'(?:github\.com/)?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)', repository, re.I) if repository else None
    if repository and not repo_match:
        return False
    repository = repo_match[1].casefold() if repo_match else ''
    if url:
        if url[2] != ('issues' if resource == 'issue' else 'pull') or repository and repository != url[1].casefold():
            return False
        repository, target = url[1].casefold(), url[3]
    if verb == 'create':
        if target is not None or not values.get('title', '').strip():
            return None
    elif target is None or not re.fullmatch(r'#?\+?[0-9]+', target):
        return None  # Other existing target forms retain their original checks.
    if target is not None:
        # gh parses numeric selectors with an optional #/+ and leading zeros.
        # Canonicalize the identity, without changing the actual command bytes.
        target = target.removeprefix('#').removeprefix('+').lstrip('0')
        if not target:
            return False
    if 'body' in values and 'file' in values:
        return False
    if not ({'body', 'file'} & values.keys()):
        return None
    if verb == 'review' and '--comment' not in flags:
        return None
    if 'file' in values:
        if values['file'] == '-':
            return False
        path = Path(values['file'])
        if not path.is_absolute():
            path = Path(cwd or os.getcwd()) / path
        try:
            if not path.is_file() or str(path).startswith(('/dev/', '/proc/')):
                return False
            with path.open('rb'):
                pass
        except OSError:
            return False
    if details is not None:
        details.update(resource=resource, operation=verb, repository=repository, selector=target)
    return True
