#!/usr/bin/env python3
"""AST scanner for writing-code:9 and writing-releases:3.

Invoked by scan.sh for .py files in the diff. Reports violations as
<file>:<line>:<rule>: <excerpt>. Exit 0 if clean, 1 if violations.

Usage:
  scan_ast.py [--config <path>] <file> [<file> ...]

This is a first-cut v2.2.0 implementation. Reports ALL violations in the
files passed (no diff-line filtering). Pre-existing violations are
flagged along with new ones; the rule bodies' grace-window language
documents the expectation. A v2.2.x patch may add diff-line filtering
if false-positive volume in pre-existing code becomes a problem.
"""

import ast
import re
import sys
from pathlib import Path


DEFAULT_ALLOW_DECORATORS = {
    "wraps", "functools.wraps",
    "contextmanager", "contextlib.contextmanager",
    "classmethod", "staticmethod", "property",
}

VERSION_RE = re.compile(r"v\d+\.\d+\.\d+")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
REMOVAL_KEYWORDS_RE = re.compile(
    r"\b(remove|removed|dropped|slated for|target|EOL)\b", re.IGNORECASE
)
DEPRECATION_WARNING_NAMES = {"DeprecationWarning", "PendingDeprecationWarning"}


def load_decorator_allowlist(config_path):
    if config_path is None or not Path(config_path).exists():
        return DEFAULT_ALLOW_DECORATORS
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return DEFAULT_ALLOW_DECORATORS
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    extra = set(config.get("scanner", {}).get("allow_decorators", []))
    return DEFAULT_ALLOW_DECORATORS | extra


def decorator_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    return ""


def collect_referenced(func_node):
    names = set()
    keywords = set()
    has_kwargs_spread = False
    for n in ast.walk(func_node):
        if isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.keyword):
            if n.arg is None:
                has_kwargs_spread = True
            else:
                keywords.add(n.arg)
    return names, keywords, has_kwargs_spread


def defaulted_args(func_node):
    out = []
    args = func_node.args
    if args.defaults:
        for arg, default in zip(args.args[-len(args.defaults):], args.defaults):
            if isinstance(default, ast.Constant) and default.value is None:
                continue
            out.append(arg.arg)
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is None:
            continue
        if isinstance(default, ast.Constant) and default.value is None:
            continue
        out.append(arg.arg)
    return out


def check_writing_code_9(tree, allow_decorators):
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(decorator_name(d) in allow_decorators for d in node.decorator_list):
            continue
        defaulted = defaulted_args(node)
        if not defaulted:
            continue
        has_kwarg_param = node.args.kwarg is not None
        names, keywords, has_kwargs_spread = collect_referenced(node)
        docstring = ast.get_docstring(node) or ""
        for arg_name in defaulted:
            if arg_name in names or arg_name in keywords:
                continue
            if has_kwarg_param and has_kwargs_spread:
                continue
            # Carve-out (c): if the docstring mentions the parameter name, treat as
            # documented no-op. Heuristic; loose by design — false negatives are
            # acceptable here and false positives are not. Tighter substring matches
            # (e.g. requiring "no-op" or "subclass" near the name) are a v2.2.x
            # candidate after fix-exercise evidence about real patterns.
            if arg_name in docstring:
                continue
            excerpt = (
                f"def {node.name}(...): parameter '{arg_name}' has a default "
                f"but is never referenced, not forwarded via **kwargs, and "
                f"not named in the docstring"
            )
            violations.append(
                (node.lineno,
                 f"writing-code-9-silently-dropped-param({arg_name})",
                 excerpt)
            )
    return violations


def flatten_string(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = flatten_string(node.left)
        right = flatten_string(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                return None
        return "".join(parts)
    return None


def deprecation_message_node(call_node):
    """Return the AST node carrying the deprecation message, or None.

    Handles three call shapes:
      - DeprecationWarning(msg) / PendingDeprecationWarning(msg)
      - warnings.warn(msg, DeprecationWarning) / warn(msg, PendingDeprecationWarning)
      - warnings.warn(msg, category=DeprecationWarning)
    """
    func = call_node.func
    func_name = ""
    if isinstance(func, ast.Name):
        func_name = func.id
    elif isinstance(func, ast.Attribute):
        func_name = func.attr
    if func_name in DEPRECATION_WARNING_NAMES and call_node.args:
        return call_node.args[0]
    if func_name == "warn" and call_node.args:
        category = None
        if len(call_node.args) >= 2:
            category = call_node.args[1]
        for kw in call_node.keywords:
            if kw.arg == "category":
                category = kw.value
        if category is None:
            return None
        cat_name = ""
        if isinstance(category, ast.Name):
            cat_name = category.id
        elif isinstance(category, ast.Attribute):
            cat_name = category.attr
        if cat_name in DEPRECATION_WARNING_NAMES:
            return call_node.args[0]
    return None


def check_writing_releases_3(tree):
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        msg_node = deprecation_message_node(node)
        if msg_node is None:
            continue
        msg = flatten_string(msg_node)
        if msg is None:
            continue
        has_anchor = bool(VERSION_RE.search(msg) or DATE_RE.search(msg))
        has_keyword = bool(REMOVAL_KEYWORDS_RE.search(msg))
        if has_anchor and has_keyword:
            continue
        missing = []
        if not has_anchor:
            missing.append("version-or-date")
        if not has_keyword:
            missing.append("removal-keyword")
        excerpt = msg.replace("\n", " ").strip()[:120]
        violations.append(
            (node.lineno,
             f"writing-releases-3-deprecation-no-removal-target(missing={'+'.join(missing)})",
             excerpt)
        )
    return violations


def scan_file(path, allow_decorators):
    try:
        source = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"{path}:0:scan-ast-error: {e}", file=sys.stderr)
        return []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        print(f"{path}:{e.lineno or 0}:scan-ast-syntax-error: {e.msg}",
              file=sys.stderr)
        return []
    return (check_writing_code_9(tree, allow_decorators)
            + check_writing_releases_3(tree))


def main(argv):
    config_path = None
    files = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--config":
            config_path = argv[i + 1]
            i += 2
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            files.append(a)
            i += 1
    if not files:
        return 0
    allow_decorators = load_decorator_allowlist(config_path)
    total = 0
    for path in files:
        if not path.endswith(".py"):
            continue
        for line, rule, excerpt in scan_file(path, allow_decorators):
            print(f"{path}:{line}:{rule}: {excerpt}")
            total += 1
    return 1 if total > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
