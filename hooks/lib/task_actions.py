"""Bounded, non-executing shell reader classification and action paths (#1051).

Only positively recognized readers bypass task lookup. Unknown syntax remains
mutation-gated. This is intentionally not a shell interpreter: expansions,
subshells, eval and executable reader options are never certified as reads.
"""
from __future__ import annotations

import ast
import os
import re


class UnknownShape(ValueError):
    pass


def shell_tokens(command: str) -> list[tuple[str, bool]]:
    """Return (value, is_operator), preserving quoted operator literals."""
    tokens = []
    word = ""
    active = False
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
        elif c in "(){}":
            raise UnknownShape("shell group requires mutation handling")
        elif c.isspace() or c in ";&|<>":
            if active:
                tokens.append((word, False))
                word, active = "", False
            if c == "\n":
                tokens.append((";", True))
            elif not c.isspace():
                op = c
                if i + 1 < len(command) and command[i + 1] == c:
                    op += c
                    i += 1
                tokens.append((op, True))
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
        tokens.append((word, False))
    return tokens


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


def reader(args: list[str]) -> bool:
    if not args:
        return False
    cmd, rest = args[0], args[1:]
    if cmd in {"cat", "head", "tail", "less", "more", "wc", "file", "stat", "du", "df", "tree", "which", "readlink", "realpath", "md5", "sha256sum", "shasum", "xxd", "od", "hexdump", "ls", "cmp", "comm", "pwd", "dirname", "basename", "uname", "hostname", "whoami", "id", "true", "false", "test", "[", "echo", "printenv"}:
        # xxd -r reverses into an output file; file -C compiles a database.
        if cmd == "xxd" and any(a == "-r" or not a.startswith("-") and i == len(rest) - 1 and sum(not x.startswith("-") for x in rest) > 1 for i, a in enumerate(rest)):
            return False
        if cmd == "file" and any(a in {"-C", "--compile"} for a in rest):
            return False
        if cmd in {"less", "more"}:  # interactive shell escapes / LESSOPEN
            return False
        return True
    if cmd == "printf":
        return "-v" not in rest
    if cmd == "date":
        return not any(a in {"-s", "--set"} or a.startswith("--set=") or re.fullmatch(r"\d{8,}", a) for a in rest)
    if cmd == "env":
        return not rest  # env COMMAND executes; never certify that wrapper
    if cmd in {"grep", "egrep", "fgrep", "rg", "ag", "ack", "ripgrep"}:
        return not any(a.startswith(("--pre", "--hostname-bin")) for a in rest)
    if cmd == "find":
        return not any(a in {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"} for a in rest)
    if cmd == "diff":
        return not any(a.startswith(("--output", "--from-file")) for a in rest)
    if cmd == "jq":
        return True
    if cmd == "sed":
        return len(rest) == 3 and rest[0] == "-n" and bool(re.fullmatch(r"\d+(,\d+)?p", rest[1])) and not rest[2].startswith("-")
    if cmd in {"python", "python3"}:
        return _python_read(args)
    if cmd in {"pip", "pip3"}:
        return bool(rest) and rest[0] in {"list", "show", "freeze", "check"}
    if cmd == "git":
        while rest and rest[0] == "-C" and len(rest) >= 2:
            rest = rest[2:]
        if not rest:
            return False
        sub, opts = rest[0], rest[1:]
        if any(a.startswith(("--output", "--ext-diff", "--textconv", "--exec", "-o")) for a in opts):
            return False
        if sub in {"log", "status", "diff", "show", "rev-parse", "merge-base", "describe", "rev-list", "shortlog", "blame", "ls-tree", "ls-files", "cat-file", "name-rev", "for-each-ref"}:
            return True
        if sub in {"branch", "tag"}:
            return not opts or opts[0] in {"--list", "-l", "--show-current", "-v", "-vv", "-a", "-r"} and not any(a in {"-d", "-D", "-f", "-m", "-M", "-c", "-C"} or a.startswith(("--delete", "--force", "--move", "--copy", "--edit-description")) for a in opts)
        if sub == "remote":
            return not opts or opts[0] in {"-v", "--verbose", "show", "get-url"}
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


def action(command: str, cwd: str) -> dict:
    """Classify before gate lookup, and conservatively collect mutation targets."""
    try:
        tokens = shell_tokens(command)
    except UnknownShape as e:
        return {"read_only": False, "paths": [canonical(cwd)], "error": str(e)}
    paths = []
    reads = True
    args = []
    effective = canonical(cwd)
    binding = ""

    def finish():
        nonlocal args, effective, reads, binding
        if not args:
            return
        while args and args[0].startswith("CCP_TASK_ID="):
            value = args.pop(0).split("=", 1)[1]
            if binding and value != binding:
                raise UnknownShape("conflicting command task bindings")
            binding = value
        if not args:
            raise UnknownShape("missing command")
        if args[0] == "cd":
            if len(args) != 2 or args[1].startswith("-"):
                raise UnknownShape("unsupported cd")
            effective = canonical(args[1], effective)
        elif not reader(args):
            reads = False
            if args[0] in {'eval', 'exec', 'bash', 'sh', 'zsh', 'dash', 'ksh'} or args[0] in {'python', 'python3'} and any(x == '-c' or x.startswith('-c') for x in args[1:]):
                raise UnknownShape('opaque inline execution has unbounded mutation targets')
            local = effective
            operands = [x.split('=', 1)[-1] if '=' in x else x for x in args[1:]]
            if any(any(c in x for c in '*?[') or x.startswith('~') for x in operands):
                raise UnknownShape('expanded mutation targets require explicit concrete paths')
            if args[0] not in {'touch', 'mkdir', 'rm', 'rmdir', 'cp', 'mv', 'tee', 'chmod', 'chown', 'git'}:
                paths.extend(canonical(x, effective) for x in operands if '/' in x and '://' not in x and not x.startswith('-'))
            if args[0] == "git":
                i = 1
                while i + 1 < len(args) and args[i] == "-C":
                    local = canonical(args[i + 1], local)
                    i += 2
                paths.append(local)
                paths.extend(canonical(x, local) for x in args[i + 1:] if '/' in x and '://' not in x and not x.startswith('-'))
            elif args[0] in {"touch", "mkdir", "rm", "rmdir", "cp", "mv", "tee", "chmod", "chown", "patch"}:
                operands = []
                skip = False
                for token in args[1:]:
                    if skip:
                        skip = False
                        continue
                    if args[0] == 'touch' and token in {'-r', '--reference', '-d', '--date', '-t'}:
                        skip = True
                        continue
                    if not token.startswith('-'):
                        operands.append(token)
                if args[0] == 'cp':
                    # Common copy form: source(s) are reads, final operand writes.
                    if any(x in {'-t', '--target-directory'} or x.startswith('--target-directory=') for x in args):
                        raise UnknownShape('use explicit final copy destination')
                    operands = operands[-1:]
                elif args[0] in {'chmod', 'chown'}:
                    operands = operands[1:]
                paths.extend(canonical(x, effective) for x in operands)
                if not operands:
                    paths.append(local)
            else:
                paths.append(local)
                # Explicit paths cannot escape a task by borrowing CWD scope.
                paths.extend(canonical(x, effective) for x in args[1:] if x.startswith(("/", "./", "../")))
        args = []

    try:
        i = 0
        while i < len(tokens):
            value, op = tokens[i]
            if not op:
                args.append(value)
            elif value in {">", ">>"}:
                reads = False
                i += 1
                if i >= len(tokens) or tokens[i][1]:
                    raise UnknownShape("missing redirect target")
                paths.append(canonical(tokens[i][0], effective))
            elif value == "<":
                i += 1
                if i >= len(tokens) or tokens[i][1]:
                    raise UnknownShape("missing input target")
            elif value in {"&&", ";", "|", "||"}:
                finish()
            else:
                raise UnknownShape("unsupported shell operator")
            i += 1
        finish()
    except UnknownShape as e:
        return {"read_only": False, "paths": list(dict.fromkeys(paths + [effective])), "error": str(e), "binding": binding}
    return {"read_only": reads and bool(tokens), "paths": list(dict.fromkeys(paths or [effective])), "binding": binding}
