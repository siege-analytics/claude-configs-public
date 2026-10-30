"""Bounded shell classification and canonical action paths (#1051).

Pure readers and explicitly approved diagnostics have separate early-allow
flags. Candidate commands are never executed; Git ownership uses a bounded
read-only toplevel query. Unknown syntax remains mutation-gated or fails closed.
Substitutions, subshells, eval and executable reader options are not pure reads.
Only bounded pure-reader/pytest grammars admit pathname globs, with a literal
non-option prefix or a genuine -- terminator; quoted patterns do not expand.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess


class UnknownShape(ValueError):
    pass


def shell_tokens(command: str) -> list[tuple[str, bool, tuple[int, ...]]]:
    """Preserve operators and positions of unquoted glob characters.

    Reader/diagnostic classification decides whether a glob word is safe;
    mutation operands still require explicit concrete paths.
    """
    tokens = []
    word = ""
    globs = []
    active = False
    fd_literal = True  # only adjacent, wholly unquoted ASCII digits are IO_NUMBER
    quote = ""
    i = 0
    while i < len(command):
        c = command[i]
        if quote == "'":
            if c == quote:
                quote = ""
            else:
                word += c
        elif c == "\\" and quote != "'":
            i += 1
            if i >= len(command) or command[i] == "\n":
                raise UnknownShape("escaped newline or incomplete escape")
            word += command[i]
            active = True
            fd_literal = False
        elif c in "$`" and quote != "'":
            raise UnknownShape("shell expansion requires mutation handling")
        elif quote == '"':
            if c == quote:
                quote = ""
            else:
                word += c
        elif c in "'\"":
            quote = c
            active = True
            fd_literal = False
        elif c in "(){}":
            raise UnknownShape("shell group requires mutation handling")
        elif c in "*?[" and not (c == "[" and not active and i + 1 < len(command) and command[i + 1].isspace()):
            globs.append(len(word))
            word += c
            active = True
        elif c.isspace() or c in ";&|<>":
            fd = ""
            if active:
                if c in "<>" and fd_literal and re.fullmatch(r"[0-9]+", word):
                    fd = word
                else:
                    tokens.append((word, False, tuple(globs)))
                word, active, globs, fd_literal = "", False, [], True
            if c == "\n":
                tokens.append((";", True, ()))
            elif not c.isspace():
                # Longest redirect first: &>> is not background + append,
                # and >&/<& consume their ampersand, not a shell separator.
                if c in "<>" or command.startswith("&>", i):
                    op = next(op for op in ("&>>", "&>", ">>", ">&", "<&", ">|", "<<", ">", "<")
                              if command.startswith(op, i))
                    i += len(op) - 1
                    op = fd + op
                else:
                    op = c
                    if i + 1 < len(command) and command[i + 1] == c:
                        op += c
                        i += 1
                tokens.append((op, True, ()))
        elif c == "#" and not active:
            # Comments/markers are deliberately not interpreted as authorization.
            raise UnknownShape("shell comment requires mutation handling")
        else:
            word += c
            active = True
        i += 1
    if quote:
        raise UnknownShape("unclosed quote")
    if active:
        tokens.append((word, False, tuple(globs)))
    return tokens


def _reader_globs(args: list[str], positions: list[tuple[int, ...]]) -> None:
    """V2: expansion only in bounded pure-reader/pytest argument grammars.

    Mixed commands (find/tree/sort, interpreters, fixing linters, etc.) keep
    concrete paths even when their write/exec switch is absent. The bounded
    options below also distinguish a real -- from an option VALUE of --.
    Quoted patterns have no expansion positions and retain existing handling.
    """
    if not any(positions):
        return
    cmd, start = args[0], 1
    if cmd == 'git':
        while start + 1 < len(args) and args[start] == '-C':
            if positions[start + 1]:
                raise UnknownShape('Git targeting requires an explicit concrete path')
            start += 2
        if start >= len(args) or args[start] not in {'diff', 'log'}:
            raise UnknownShape('globbed Git arguments require pure diff/log paths')
        cmd = 'git-' + args[start]
        start += 1
    elif cmd in {'python', 'python3'} and args[1:3] == ['-m', 'pytest']:
        cmd, start = 'pytest', 3
    elif cmd == 'gh' and args[1:2] == ['api']:
        cmd, start = 'gh-api', 2
    grammars = {
        'ls': ('-a -A -l -h -d -R -t -r -S -1 -F -p -i -n -s --all --almost-all --human-readable --recursive --directory --color --group-directories-first', '--color --sort --format --time --time-style --quoting-style --block-size --ignore --hide'),
        'cat': ('-n -b -s -v -e -E -t -T -u -A --number --number-nonblank --squeeze-blank --show-all --show-ends --show-tabs --show-nonprinting', ''),
        'head': ('-q -v --quiet --silent --verbose', '-n --lines -c --bytes'),
        'tail': ('-q -v -f -F --quiet --silent --verbose --follow --retry', '-n --lines -c --bytes --follow --pid --sleep-interval --max-unchanged-stats'),
        'grep': ('-n -r -R -i -l -L -c -v -w -x -q -s -h -H -E -F -G -P -o -a -I -z -Z --line-number --recursive --ignore-case --files-with-matches --count --invert-match --only-matching --no-messages --fixed-strings --extended-regexp --quiet', '-e --regexp -f --file -m --max-count -A -B -C --after-context --before-context --context --include --exclude --exclude-dir --binary-files --color --colour --directories --devices --label'),
        'rg': ('-n -i -l -L -c -v -w -x -q -s -o -a -u -F -P --hidden --files --no-ignore --json --line-number --count --invert-match --quiet --ignore-case --fixed-strings --pcre2 --only-matching --no-line-number --no-heading --heading', '-e --regexp -f --file -m --max-count -A -B -C --after-context --before-context --context -g --glob --iglob -t --type -T --type-not --color --colors -r --replace'),
        'wc': ('-l -w -c -m -L --lines --words --bytes --chars --max-line-length', ''),
        'file': ('-b -i -L -h -k -N --brief --mime --mime-type --mime-encoding --dereference --no-dereference --keep-going --no-pad', '-m --magic-file -f --files-from -F --separator -e --exclude --exclude-quiet -P --parameter'),
        'stat': ('-l -x -n -q -r -s -L --dereference --file-system --terse', '-f -t -c --format --printf --cached'),
        'diff': ('-u -q -r -s -N -a -b -B -w -i -y --unified --brief --recursive --report-identical-files --new-file --text --ignore-space-change --ignore-all-space --side-by-side', '-U -C -I --ignore-matching-lines --exclude --exclude-from --label --unified'),
        'git-diff': ('-p -u --patch --stat --name-only --name-status --check --cached --staged --no-index --no-ext-diff --no-textconv --exit-code --quiet --raw --numstat --shortstat --color --no-color --full-index --binary', '-U --unified --src-prefix --dst-prefix --word-diff-regex'),
        'git-log': ('--oneline --stat --name-only --name-status --no-merges --first-parent --all --graph --decorate --no-decorate --no-color --date-order --reverse --abbrev-commit', '-n --max-count --since --until --author --grep --format --pretty --date'),
        'pytest': ('-q -qq -v -vv -x -s --collect-only --disable-warnings --strict-markers --strict-config --no-header --no-summary', '-k -m --maxfail --tb --color'),
        'gh-api': ('--paginate --slurp --silent --include --verbose', '-H --header --hostname -q --jq -t --template'),
    }
    if cmd in {'egrep', 'fgrep'}:
        cmd = 'grep'
    if cmd not in grammars:
        raise UnknownShape('this command keeps the explicit concrete-path rule for glob expansions')
    flags, values = (set(s.split()) for s in grammars[cmd])
    literal, expecting = False, ''

    def shape(word, globs, offset=0, *, pattern=False):
        if not globs:
            return
        if not word or any(p < offset for p in globs):
            raise UnknownShape('globbed option key: prefix ./ or quote the pattern')
        # An attached fixed grep --include= key survives expansion verbatim.
        if pattern:
            return
        forbidden = '-*?[{$`~' if not literal else '{$`~'
        if word[0] in forbidden:
            raise UnknownShape('leading glob argument: prefix ./ or quote the pattern')

    for index in range(start, len(args)):
        word, globs = args[index], positions[index]
        if expecting:
            if cmd == 'pytest' and globs:
                raise UnknownShape('pytest globs are selection paths, not option values')
            shape(word, globs)
            expecting = ''
        elif not literal and word == '--':
            literal = True
        elif not literal and word.startswith('-') and word != '-':
            key, equals, value = word.partition('=')
            if equals and key in values:
                if cmd == 'pytest' and globs:
                    raise UnknownShape('pytest globs are selection paths, not option values')
                shape(value, globs, len(key) + 1, pattern=cmd == 'grep' and key == '--include')
            elif word in flags:
                pass
            elif word in values:
                expecting = word
            elif word.startswith('-') and not word.startswith('--') and len(word) > 2 and all('-' + c in flags for c in word[1:]):
                pass  # known no-value short flag cluster, never -e/-f/etc.
            elif not word.startswith('--') and word[:2] in values and len(word) > 2:
                shape(word[2:], globs, 2)
            else:
                raise UnknownShape('unbounded glob reader option: prefix ./ or quote the pattern')
        else:
            shape(word, globs)
    if expecting:
        raise UnknownShape('missing glob reader option value')


def _python_read(args: list[str]) -> bool:
    # Isolation prevents local json.py / ast.py from executing on import.
    if not args or args[0] not in {"python", "python3"}:
        return False
    if "-I" not in args or "-c" not in args:
        return False
    pos = args.index("-c")
    if set(args[1:pos]) - {"-I", "-B"} or pos + 2 != len(args):
        return False
    try:
        tree = ast.parse(args[pos + 1])
    except (ValueError, SyntaxError):
        return False
    bound = set()
    modules = set()
    reserved = {"open", "print", "len", "str", "int", "sorted", "list", "dict", "tuple", "bool"}

    def expr(n):
        if isinstance(n, ast.Constant):
            return isinstance(n.value, (str, bytes, int, float, bool, type(None)))
        if isinstance(n, ast.Name):
            return n.id in bound  # callable/module values cannot be passed around
        if isinstance(n, (ast.List, ast.Tuple, ast.Set)):
            return all(expr(x) for x in n.elts)
        if isinstance(n, ast.Dict):
            return all(k is not None and expr(k) and expr(v) for k, v in zip(n.keys, n.values))
        if isinstance(n, ast.Subscript):
            return expr(n.value) and expr(n.slice)
        if isinstance(n, ast.Slice):
            return all(x is None or expr(x) for x in (n.lower, n.upper, n.step))
        if not isinstance(n, ast.Call) or any(k.arg is None for k in n.keywords):
            return False
        if not all(expr(x) for x in n.args) or not all(expr(k.value) for k in n.keywords):
            return False
        f = n.func
        if isinstance(f, ast.Name):
            if f.id == "open":
                return (1 <= len(n.args) <= 2 and isinstance(n.args[0], ast.Constant)
                        and isinstance(n.args[0].value, str)
                        and (len(n.args) == 1 or isinstance(n.args[1], ast.Constant)
                             and n.args[1].value in {"r", "rb", "rt"})
                        and all(k.arg in {"encoding", "errors"} for k in n.keywords))
            return f.id in reserved - {"open"} and not n.keywords
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            allowed = {"json": {"load", "loads", "dumps"}, "ast": {"parse", "literal_eval", "dump"}}
            return f.value.id in modules and f.attr in allowed.get(f.value.id, set()) and not n.keywords
        if isinstance(f, ast.Attribute) and f.attr in {"read", "readline", "readlines"}:
            return isinstance(f.value, ast.Call) and isinstance(f.value.func, ast.Name) and f.value.func.id == "open" and expr(f.value) and not n.keywords
        return False

    for n in tree.body:
        if isinstance(n, ast.Import):
            if any(a.name not in {"json", "ast"} or a.asname for a in n.names):
                return False
            modules.update(a.name for a in n.names)
        elif isinstance(n, ast.Assign):
            if not expr(n.value) or any(not isinstance(t, ast.Name) or t.id in reserved | modules for t in n.targets):
                return False
            bound.update(t.id for t in n.targets)
        elif not isinstance(n, ast.Expr) or not expr(n.value):
            return False
    return bool(tree.body)


def _options(args: list[str], flags=(), values=(), *, minimum=0, maximum=None) -> bool:
    """Bounded CLI grammar: unknown switches/option values are not certified."""
    operands, i, literal = 0, 0, False
    while i < len(args):
        token = args[i]
        if not literal and token == "--":
            literal = True
        elif not literal and token.startswith("-") and token != "-":
            option, equals, value = token.partition("=")
            if option in values:
                if not equals:
                    i += 1
                    if i >= len(args) or args[i].startswith("-"):
                        return False
                elif not value:
                    return False
            elif token not in flags:
                return False
        else:
            operands += 1
        i += 1
    return operands >= minimum and (maximum is None or operands <= maximum)


def investigation(args: list[str]) -> bool:
    """Approved diagnostic execution, NOT a proof of side-effect-free code.

    Only bounded diagnostic forms qualify. Test modules/plugins and compilers
    can execute code or write files and require a separately scoped runner;
    their executable names alone are not investigation authority.
    """
    if not args:
        return False
    cmd, rest = args[0], args[1:]
    # Test modules and plugins execute arbitrary project code; py_compile writes
    # bytecode. A command-line selection is not a scoped execution authority.
    if cmd == "pytest" or cmd in {"python", "python3"} and rest[:1] == ["-m"]:
        return False
    if cmd in {"bash", "sh", "zsh", "dash", "ksh"}:
        return bool(rest) and rest[0] == "-n" and _options(rest[1:], minimum=1)
    if cmd == "shellcheck":
        return _options(rest, flags={"-x", "--external-sources", "--norc", "--check-sourced"}, values={"-s", "--shell", "-S", "--severity", "-f", "--format", "-e", "--exclude", "-i", "--include"}, minimum=1)
    if cmd == "ruff":
        return bool(rest) and rest[0] == "check" and _options(rest[1:], flags={"--no-fix", "--no-cache", "-q", "--quiet", "-v", "--verbose", "--statistics", "--diff"}, values={"--select", "--ignore", "--extend-select", "--extend-ignore", "--output-format"})
    if cmd in {"flake8", "mypy", "pylint"}:
        return _options(rest, flags={"-q", "--quiet", "-v", "--verbose", "--show-error-codes", "--strict", "--ignore-missing-imports"}, values={"--select", "--ignore", "--disable", "--enable", "--max-line-length"}, minimum=1)
    if cmd in {"black", "isort"}:
        checks = {"--check"} if cmd == "black" else {"--check", "--check-only"}
        return bool(set(rest) & checks) and _options(rest, flags=checks | {"--diff", "-q", "--quiet", "--no-cache"}, values={"--line-length"}, minimum=1)
    if cmd == "git":
        while len(rest) >= 2 and rest[0] == "-C":
            rest = rest[2:]
        return (bool(rest) and rest[0] == "fetch"
                and _options(rest[1:], flags={"--all", "--prune", "--tags", "--no-tags", "--dry-run", "-q", "--quiet", "-v", "--verbose", "--no-recurse-submodules"}, values={"--depth", "--deepen"}, maximum=1)
                and all(t.startswith('-') or re.fullmatch(r'[A-Za-z0-9_./-]+', t) for t in rest[1:]))  # no destination refspecs/helper URLs
    return False


def _long_option_matches(token: str, names) -> bool:
    """GNU accepts any unambiguous prefix of a long option (`--lin` is --link)."""
    name = token.split('=', 1)[0]
    return len(name) > 2 and any(full.startswith(name) for full in names)


def _cp_link_copy(tokens) -> bool:
    """cp -l/-s and their long forms make the destination another name (#1100)."""
    for t in tokens:
        if t == '--':
            break
        if t.startswith('--'):
            if _long_option_matches(t, ('--link', '--symbolic-link')):
                return True
        elif t.startswith('-') and t != '-' and ('l' in t[1:] or 's' in t[1:]):
            return True
    return False


def _cp_keeps_symlinks(tokens) -> bool:
    """Options under which cp copies a symlink as a symlink."""
    for t in tokens:
        if t == '--':
            break
        if t.startswith('--'):
            if _long_option_matches(t, ('--no-dereference', '--recursive', '--archive')) or (
                    _long_option_matches(t, ('--preserve',)) and ('links' in t or 'all' in t)):
                return True
        elif t.startswith('-') and t != '-' and any(c in t[1:] for c in 'PdrRa'):
            return True
    return False


def _has_symlink(path: str, limit: int = 2000) -> bool:
    """A symlink at or under path; past `limit` entries, assume one."""
    if os.path.islink(path):
        return True
    if not os.path.isdir(path):
        return False
    seen = 0
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            seen += 1
            if seen > limit or os.path.islink(os.path.join(root, name)):
                return True
    return False


def _git_toplevel(directory: str) -> str:
    try:
        return canonical(subprocess.check_output(["git", "-C", directory, "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.DEVNULL, timeout=3).strip())
    except (subprocess.SubprocessError, OSError):
        raise UnknownShape("cannot resolve repository toplevel for Git mutation")


def reader(args: list[str]) -> bool:
    if not args:
        return False
    cmd, rest = args[0], args[1:]
    if cmd in {"cat", "head", "tail", "less", "more", "wc", "file", "stat", "du", "df", "which", "readlink", "realpath", "md5", "sha256sum", "shasum", "xxd", "od", "hexdump", "ls", "cmp", "comm", "pwd", "dirname", "basename", "uname", "whoami", "id", "true", "false", "test", "[", "echo", "printenv"}:
        # xxd -r reverses into an output file; file -C compiles a database.
        if cmd == "xxd":
            return _options(rest, flags={"-a", "-b", "-e", "-p", "-ps", "-u", "-v"}, values={"-c", "-g", "-l", "-o", "-s"}, maximum=1)
        if cmd == "file" and any(a.startswith('--compile') or a.startswith('-') and not a.startswith('--') and 'C' in a for a in rest):
            return False
        if cmd in {"less", "more"}:  # interactive shell escapes / LESSOPEN
            return False
        return True
    if cmd == "hostname":
        return _options(rest, flags={"-f", "-s", "-d", "-i", "-I", "-a", "-A", "--fqdn", "--short", "--domain", "--ip-address", "--all-ip-addresses", "--all-fqdns", "--alias", "--help", "--version"}, maximum=0)
    if cmd == "type":
        return _options(rest, flags={"-a", "-t", "-p", "-P", "-f"}, minimum=1)
    if cmd == "tree":
        return _options(rest, flags={"-a", "-d", "-f", "-i", "-l", "-n", "-N", "-q", "-p", "-u", "-g", "-s", "-h", "-D", "-F", "-t", "-r", "-U", "-C", "--noreport", "--dirsfirst"}, values={"-L", "-P", "-I", "--sort", "--filelimit"})
    if cmd == "markitdown":
        return _options(rest, flags={"--help", "--version"}, minimum=1, maximum=1)
    if cmd in {"pdf-tool", "xlsx-tool", "pptx-tool", "ical-tool"}:
        forms = {"pdf-tool": {"info", "extract"}, "xlsx-tool": {"read", "info"}, "pptx-tool": {"info"}, "ical-tool": {"read"}}
        return bool(rest) and rest[0] in forms[cmd] and _options(rest[1:], flags={"--json", "--text"}, values={"--pages", "--sheet", "--range"}, minimum=1, maximum=1)
    if cmd == "doc-diff":
        return _options(rest, flags={"--json"}, minimum=2, maximum=2)
    if cmd in {"npm", "yarn", "pnpm"}:
        if not rest or rest[0] not in {"list", "ls", "info", "view", "outdated", "audit"}:
            return False
        return _options(rest[1:], flags={"--json", "--global", "-g", "--all", "--long", "--parseable", "--production", "--dev"}, values={"--depth"}, maximum=0 if rest[0] == "audit" else None)
    if cmd in {"brew", "apt", "dnf", "yum"}:
        return bool(rest) and rest[0] in {"list", "info", "search", "show"} and _options(rest[1:], flags={"--versions", "--formula", "--cask", "--installed", "--available", "--pinned", "-l", "-1", "-r"})
    if cmd == "printf":
        fmt = rest[1] if len(rest) > 1 and rest[0] == '--' else rest[0] if rest else ''
        # Bash printf also assigns through -vNAME and the %n conversion.
        return not any(a.startswith('-v') for a in rest) and not re.search(r'%[^%a-zA-Z]*[hlLjztq]*n', fmt)
    if cmd == "date":
        flags = {'-u', '--utc', '--universal', '-j', '-R', '--rfc-email', '--rfc-2822', '--help', '--version', '--debug', '-I', '--iso-8601'}
        flags |= {'--iso-8601=' + unit for unit in ('date', 'hours', 'minutes', 'seconds', 'ns')}
        values = {'-d', '--date', '-r', '--reference', '-f', '--file'}
        if not _options(rest, flags=flags, values=values, maximum=2):
            return False
        i, literal = 0, False
        while i < len(rest):
            token = rest[i]
            if not literal and token == '--':
                literal = True
            elif not literal and token.partition('=')[0] in values:
                if '=' not in token:
                    i += 1
            elif not literal and token.startswith('-'):
                pass
            elif not token.startswith('+') and '-j' not in rest:
                return False  # bare dates can set the BSD clock
            i += 1
        return True
    if cmd == "env":
        return not rest  # env COMMAND executes; never certify that wrapper
    if cmd in {"grep", "egrep", "fgrep", "rg", "ag", "ack", "ripgrep"}:
        return not any(a.startswith(("--pre", "--hostname-bin", "--pager", "--output")) for a in rest)
    if cmd == "find":
        return not any(a in {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"} for a in rest)
    if cmd == "diff":
        return not any(a.startswith(("--output", "--from-file")) for a in rest)
    if cmd == "jq":
        return True
    if cmd == "sed":
        return len(rest) == 3 and rest[0] == "-n" and bool(re.fullmatch(r"\d+(,\d+)?p", rest[1])) and not rest[2].startswith("-")
    if cmd in {"python", "python3"}:
        return (_python_read(args) or len(rest) >= 3 and rest[:2] == ["-m", "pip"] and reader(["pip"] + rest[2:]))
    if cmd in {"pip", "pip3"}:
        if not rest or rest[0] not in {"list", "show", "freeze", "check"}:
            return False
        return _options(rest[1:], flags={"--all", "--outdated", "--uptodate", "--editable", "--local", "--user", "--not-required", "--include-editable", "--exclude-editable", "--pre", "--files", "-f", "-v", "--verbose", "-q", "--quiet", "--disable-pip-version-check", "--no-cache-dir"}, values={"--format", "--exclude", "--path"}, maximum=0 if rest[0] == "check" else None)
    if cmd == "git":
        while rest and rest[0] == "-C" and len(rest) >= 2:
            rest = rest[2:]
        if not rest:
            return False
        sub, opts = rest[0], rest[1:]
        if any(a.startswith(("--output", "--ext-diff", "--textconv", "--exec", "-o")) for a in opts):
            return False
        if sub == "reflog":
            return not any(a in {"expire", "delete", "drop", "write"} for a in opts)
        if sub in {"log", "status", "diff", "show", "rev-parse", "merge-base", "describe", "rev-list", "shortlog", "blame", "ls-tree", "ls-files", "cat-file", "name-rev", "for-each-ref"}:
            return True
        if sub == "branch":
            if opts == ["--show-current"]:
                return True
            list_flags = {"--list", "-l", "-v", "-vv", "--verbose", "-a", "--all", "-r", "--remotes"}
            return _options(opts, flags=list_flags, maximum=None if set(opts) & {"--list", "-l"} else 0)
        if sub == "tag":
            return not opts or opts[0] in {"--list", "-l"} and _options(opts, flags={"--list", "-l"})
        if sub == "remote":
            if not opts or opts in (["-v"], ["--verbose"]):
                return True
            if opts[0] == "show":
                return _options(opts[1:], flags={"-n", "--no-query"}, minimum=1, maximum=1)
            return opts[0] == "get-url" and _options(opts[1:], flags={"--push", "--all"}, minimum=1, maximum=1)
        if sub == "config":
            return bool(opts) and opts[0] in {"--get", "--get-all", "--get-regexp", "--list", "-l"} and not any(a.startswith(("--unset", "--add", "--replace", "--edit")) for a in opts)
        return sub in {"stash", "worktree"} and bool(opts) and opts[0] == "list"
    if cmd == "gh" and rest:
        if rest[0] == "api":
            return not any(a in {"-X", "--method", "--input", "--raw-field", "--field", "-f", "-F"} or a.startswith(("-X", "-f", "-F", "--method=", "--input=", "--field=", "--raw-field=")) for a in rest[1:])
        return len(rest) >= 2 and (rest[0], rest[1]) in {(x, y) for x in {"issue", "pr", "release", "run"} for y in {"view", "list", "checks", "diff", "status"}} | {("repo", "view")}
    return False


def canonical(path: str, cwd: str = "") -> str:
    return os.path.realpath(path if os.path.isabs(path) else os.path.join(cwd or os.getcwd(), path))


_RELEASED_READS = None


def released_read_verdict(command: str) -> int:
    """Verdict of the released read classifier (hooks/lib/read-only-command.py,
    #1057): 0 proven read, 3 veto (writes or runs a program), 1/4 unproven.
    One classifier decides what is a read on main and here (#846, #1051 slim)."""
    global _RELEASED_READS
    if _RELEASED_READS is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "read_only_command", os.path.join(os.path.dirname(os.path.abspath(__file__)), "read-only-command.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _RELEASED_READS = module
    try:
        return int(_RELEASED_READS.main(command))
    except Exception:
        return 1


def action(command: str, cwd: str) -> dict:
    """Classify before gate lookup, and conservatively collect mutation targets."""
    verdict = released_read_verdict(command)
    if verdict == 0:
        return {"read_only": True, "investigation": False, "self_management": False, "paths": [],
                "binding": "", "proven_by": "read-only-command"}
    result = _action(command, cwd)
    if verdict == 3:
        # A veto is never a read or an investigation, whatever the local reader
        # thinks; the targets found below still pick the owning task's gate.
        result.update(read_only=False, investigation=False, self_management=False,
                      veto="read-only-command: option writes or runs a program")
        result["paths"] = result.get("paths") or [canonical(cwd)]
    return result


def _action(command: str, cwd: str) -> dict:
    try:
        tokens = shell_tokens(command)
    except UnknownShape as e:
        return {"read_only": False, "paths": [canonical(cwd)], "error": str(e)}
    paths = []
    reads = True
    diagnostic = False
    self_managed = True
    directory_paths = []
    directory_removals = []
    file_removals = []  # rm operands: unlinking a name never writes the file (#1100)
    file_paths = []
    args = []
    arg_globs = []
    effective = canonical(cwd)
    binding = ""

    def finish():
        nonlocal args, arg_globs, effective, reads, binding, diagnostic, self_managed
        if not args:
            return
        while args and args[0].startswith("CCP_TASK_ID="):
            if arg_globs.pop(0):
                raise UnknownShape('globbed task binding requires an explicit identity')
            value = args.pop(0).split("=", 1)[1]
            if binding and value != binding:
                raise UnknownShape("conflicting command task bindings")
            binding = value
        if not args:
            raise UnknownShape("missing command")
        if arg_globs[0]:
            raise UnknownShape('globbed command requires an explicit executable')
        if args[0] == "cd":
            if len(args) != 2 or args[1].startswith("-") or arg_globs[1]:
                raise UnknownShape("unsupported cd; use an explicit concrete path")
            effective = canonical(args[1], effective)
        elif investigation(args):
            _reader_globs(args, arg_globs)
            diagnostic = True
        elif reader(args):
            _reader_globs(args, arg_globs)
        else:
            if any(arg_globs):
                raise UnknownShape('expanded mutation targets require explicit concrete paths')
            reads = False
            self_managed = self_managed and args[0] in {"touch", "mkdir", "rm", "rmdir", "cp", "mv", "tee", "chmod", "chown", "ln"}
            if args[0] in {'eval', 'exec', 'bash', 'sh', 'zsh', 'dash', 'ksh'} or args[0] in {'python', 'python3'} and any(x == '-c' or x.startswith('-c') for x in args[1:]):
                raise UnknownShape('opaque inline execution has unbounded mutation targets')
            local = effective
            operands = [x.split('=', 1)[-1] if '=' in x else x for x in args[1:]]
            if any(any(c in x for c in '*?[') or x.startswith('~') for x in operands):
                raise UnknownShape('expanded mutation targets require explicit concrete paths')
            if args[0] not in {'touch', 'mkdir', 'rm', 'rmdir', 'cp', 'mv', 'tee', 'chmod', 'chown', 'git'}:
                paths.extend(canonical(x, effective) for x in operands if '/' in x and '://' not in x and not x.startswith('-'))
            if os.path.basename(args[0]) == "git" or args[0] in {"env", "command"}:
                # The operation-policy guards use this same literal boundary.
                # A valid task does not turn an unresolved alias into authority.
                from git_command import prefix
                operation = prefix(args, local)
                if not operation:
                    raise UnknownShape("unsupported Git mutation options")
                if any(_long_option_matches(a, ('--textconv', '--ext-diff', '--exec', '--open-files-in-pager',
                                                   '--upload-pack', '--receive-pack')) for a in operation["args"][1:]):
                    raise UnknownShape("Git helper execution has unbounded effects; use --no-textconv/--no-ext-diff for inspection")
                local = operation["cwd"]
                paths.append(_git_toplevel(local))
                git_operands = [x.split('=', 1)[-1] if '=' in x else x for x in operation["args"][1:]]
                paths.extend(canonical(x, local) for x in git_operands if '/' in x and '://' not in x and not x.startswith('-'))
            elif args[0] in {"touch", "mkdir", "rm", "rmdir", "cp", "mv", "tee", "chmod", "chown", "patch"}:
                # Options that take the next token as their value. Without this,
                # `cp SRC DST -S .bak` made `.bak` the copy destination (#1051
                # review): GNU tools permute options, so values can trail.
                value_options = {
                    'touch': {'-r', '--reference', '-d', '--date', '-t'},
                    'cp': {'-S', '--suffix'}, 'mv': {'-S', '--suffix'},
                    'chmod': {'--reference'}, 'chown': {'--reference'},
                }.get(args[0], set())
                operands = []
                option_paths = []
                has_reference = False
                skip = False
                end_of_options = False
                for token in args[1:]:
                    if skip:
                        skip = False
                        continue
                    if end_of_options or not token.startswith('-') or token == '-':
                        operands.append(token)
                        continue
                    if token == '--':
                        end_of_options = True
                        continue
                    if args[0] in {'cp', 'mv'} and (token == '-t' or _long_option_matches(token, ('--target-directory',))
                                                   or (not token.startswith('--') and 't' in token[1:])):
                        raise UnknownShape('use explicit final copy destination')
                    if token == '--reference' or token.startswith('--reference='):
                        has_reference = True
                    elif '/' in token:
                        # A path attached to an option (`-o/abs`, `--out=/abs`)
                        # is a potential target: count it, never drop it.
                        option_paths.append(token.split('=', 1)[1] if token.startswith('--') and '=' in token else token[token.index('/'):])
                    if token in value_options or args[0] in {'cp', 'mv'} and _long_option_matches(token, ('--suffix',)) and '=' not in token:
                        skip = True
                    elif args[0] in {'cp', 'mv'} and not token.startswith('--') and token.endswith('S'):
                        skip = True  # a short cluster such as -aS takes the next token
                if args[0] == 'cp' and not _cp_link_copy(args[1:]) and not (
                        _cp_keeps_symlinks(args[1:])
                        and any(_has_symlink(os.path.join(effective, x)) for x in operands[:-1])):
                    # Common copy form: source(s) are reads, final operand writes.
                    # A link copy, or a copy that carries a symlink across, makes
                    # the destination reach the source, so every operand is a
                    # target (#1100).
                    operands = operands[-1:]
                elif args[0] in {'chmod', 'chown'} and not has_reference:
                    operands = operands[1:]  # the first operand is the mode/owner
                operands = operands + option_paths
                paths.extend(canonical(x, effective) for x in operands)
                if args[0] in {"mkdir", "rmdir"}:
                    directory_paths.extend(canonical(x, effective) for x in operands)
                    if args[0] == 'rmdir':
                        directory_removals.extend(canonical(x, effective) for x in operands)
                else:
                    file_paths.extend(canonical(x, effective) for x in operands)
                    if args[0] == 'rm':
                        file_removals.extend(canonical(x, effective) for x in operands)
                if not operands:
                    paths.append(local)
            elif args[0] == 'ln':
                # Both ends of a link are targets (#1100): writing through the
                # link writes the source.
                # A target directory can ride on an option (`--target-directory=d`,
                # `--targ=d`, `-td`), so option values count as operands too.
                link_operands = []
                target_dir = None  # -t DIR / -tDIR / --target-directory=DIR
                ended = False
                expect_dir = False
                for x in args[1:]:
                    if expect_dir:
                        target_dir = x
                        link_operands.append(x)
                        expect_dir = False
                    elif ended or not x.startswith('-') or x == '-':
                        link_operands.append(x)
                    elif x == '--':
                        ended = True
                    elif x.startswith('--'):
                        if '=' in x:
                            link_operands.append(x.split('=', 1)[1])
                            if '--target-directory'.startswith(x.split('=', 1)[0]):
                                target_dir = x.split('=', 1)[1]
                        elif len(x) > 2 and '--target-directory'.startswith(x):
                            expect_dir = True
                    elif 't' in x[1:]:
                        rest = x[x.index('t', 1) + 1:]
                        if rest:
                            target_dir = rest
                            link_operands.append(rest)
                        else:
                            expect_dir = True
                if not link_operands:
                    paths.append(local)
                # A relative symlink target resolves from the link's directory,
                # not the cwd (#1109): `ln -s x sub/link` points at sub/x. Count
                # both readings of every relative operand.
                # With -t the links live in that directory, so every source
                # resolves from it.
                if target_dir is not None:
                    tdir = os.path.join(effective, target_dir)
                    for t in [x for x in link_operands if x != target_dir]:
                        if not t.startswith('/'):
                            link_operands.append(os.path.join(tdir, t))
                elif len(link_operands) >= 2:
                    link_dir = os.path.join(effective, link_operands[-1])
                    for t in link_operands[:-1]:
                        if not t.startswith('/'):
                            for base in (os.path.dirname(link_dir), link_dir):
                                link_operands.append(os.path.join(base, t))
                paths.extend(canonical(x, effective) for x in link_operands)
                file_paths.extend(canonical(x, effective) for x in link_operands)
            else:
                paths.append(local)
                # Explicit paths cannot escape a task by borrowing CWD scope.
                paths.extend(canonical(x, effective) for x in args[1:] if x.startswith(("/", "./", "../")))
                # Paths attached to options (`-o/abs`, `--out=/abs`) cannot
                # escape either.
                for x in args[1:]:
                    if x.startswith('-') and '/' in x:
                        value = x.split('=', 1)[1] if x.startswith('--') and '=' in x else x[x.index('/'):]
                        if value.startswith(("/", "./", "../")):
                            paths.append(canonical(value, effective))
        args = []
        arg_globs = []

    try:
        i = 0
        while i < len(tokens):
            value, op, globs = tokens[i]
            if not op:
                args.append(value)
                arg_globs.append(globs)
            elif re.fullmatch(r"[0-9]*(?:>>|>&|<&|>\||>|<)|&>>|&>", value):
                redirect = re.sub(r"^[0-9]+", "", value)
                i += 1
                if i >= len(tokens) or tokens[i][1]:
                    raise UnknownShape("missing redirect target")
                target = tokens[i][0]
                if tokens[i][2] or target.startswith('~'):
                    raise UnknownShape('redirection requires an explicit concrete path')
                if redirect in {">&", "<&"} and (re.fullmatch(r"[0-9]+", target) or target == "-"):
                    pass  # duplicate/close descriptors; no filesystem target
                elif redirect == "<&":
                    raise UnknownShape("input fd duplication requires a descriptor or -")
                elif redirect != "<" and target != "/dev/null":
                    # Only the literal sink is exempt: aliases/symlinks still
                    # require ownership. Earlier file writes are never erased
                    # by a later duplication or /dev/null redirect.
                    reads = False
                    paths.append(canonical(target, effective))
                    file_paths.append(canonical(target, effective))
            elif value in {"&&", ";", "|", "||"}:
                finish()
            else:
                raise UnknownShape("unsupported shell operator")
            i += 1
        finish()
    except UnknownShape as e:
        return {"read_only": False, "paths": list(dict.fromkeys(paths + [effective])), "error": str(e), "binding": binding}
    return {"read_only": reads and not diagnostic and bool(tokens), "investigation": reads and diagnostic,
            "self_managed_shape": self_managed and not diagnostic, "directory_paths": [p for p in directory_paths if p not in file_paths], "directory_removals": directory_removals,
            # A path only removed, never also written in the same command (#1100).
            "file_removals": [p for p in file_removals if paths.count(p) == file_removals.count(p)],
            "paths": list(dict.fromkeys(paths or [effective])), "binding": binding}
