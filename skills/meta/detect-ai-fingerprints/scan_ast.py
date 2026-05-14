#!/usr/bin/env python3
"""AST scanner for writing-code:7, writing-code:9 and writing-releases:3.

Invoked by scan.sh for .py files in the diff. Reports violations as
<file>:<line>:<rule>: <excerpt>. Exit 0 if clean, 1 if violations.

Usage:
  scan_ast.py [--config <path>] <file> [<file> ...]

This is a first-cut v2.2.0 implementation extended at v2.3.1.1 to add
writing-code:7. Reports ALL violations in the files passed (no diff-line
filtering). Pre-existing violations are flagged along with new ones; the
rule bodies' grace-window language documents the expectation.

writing-code:7 detection covers the four base banned shapes (Pass,
Return None/False, Continue, log.X + Return/Continue) plus carve-outs
for Optional[T]+docstring, # noqa: writing-code-7, and ImportError +
flag-pattern (writing-code:8 territory). The TC5 alternative-return
and TC8 wrap-pure-logic enhancements are deferred to v2.3.2/v2.4.0.
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
            # documented no-op. Heuristic; loose by design - false negatives are
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


DOCSTRING_NONE_PATTERNS = (
    "or None if",
    "returns None when",
    "returning None if",
    "returning None when",
    "None if not found",
)

LOGGING_CALL_NAMES = {"debug", "info", "warning", "warn", "error", "critical", "exception",
                      "log_warning", "log_error", "log_info", "log_debug"}


def is_logging_call(stmt):
    """True if stmt is an Expr wrapping a Call to a logging-style function."""
    if not isinstance(stmt, ast.Expr):
        return False
    if not isinstance(stmt.value, ast.Call):
        return False
    func = stmt.value.func
    if isinstance(func, ast.Attribute):
        return func.attr in LOGGING_CALL_NAMES
    if isinstance(func, ast.Name):
        return func.id in LOGGING_CALL_NAMES
    return False


def is_silent_terminator(stmt):
    """True if stmt is one of the silent-terminator shapes (Pass / Return None / Return False / Continue)."""
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Continue):
        return True
    if isinstance(stmt, ast.Return):
        if stmt.value is None:
            return True
        if isinstance(stmt.value, ast.Constant) and stmt.value.value in (None, False):
            return True
    return False


def import_flag_pattern(handler):
    """True if the except handler body sets an availability flag (writing-code:8 territory).

    Matches:  except ImportError: <NAME>_AVAILABLE = False  (or = True/False).
    Body must be 1-2 simple Assign statements; carve-out for the optional-import idiom.
    """
    if not handler.type:
        return False
    type_name = ""
    if isinstance(handler.type, ast.Name):
        type_name = handler.type.id
    elif isinstance(handler.type, ast.Attribute):
        type_name = handler.type.attr
    if type_name != "ImportError":
        return False
    for stmt in handler.body:
        if not isinstance(stmt, ast.Assign):
            return False
        for target in stmt.targets:
            if not isinstance(target, ast.Name):
                return False
            if not (target.id.endswith("_AVAILABLE") or target.id.endswith("_INSTALLED")
                    or target.id.startswith("HAS_") or target.id.startswith("_HAS_")):
                return False
    return True


def has_noqa_writing_code_7(handler, source_lines):
    """True if the except handler line carries a `# noqa: writing-code-7` opt-out comment."""
    if handler.lineno < 1 or handler.lineno > len(source_lines):
        return False
    line = source_lines[handler.lineno - 1]
    return "noqa: writing-code-7" in line or "noqa:writing-code-7" in line


def function_returns_optional_with_documented_none(func_node):
    """True if function's return type is Optional/Union-with-None AND docstring documents None as outcome."""
    if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    rt = func_node.returns
    if rt is None:
        return False
    annotation_text = ast.unparse(rt) if hasattr(ast, "unparse") else ""
    has_optional_annotation = (
        "Optional" in annotation_text
        or "None" in annotation_text
        or annotation_text.endswith("?")
    )
    if not has_optional_annotation:
        return False
    docstring = ast.get_docstring(func_node) or ""
    return any(p in docstring for p in DOCSTRING_NONE_PATTERNS)


def enclosing_function(tree, target_node):
    """Find the FunctionDef/AsyncFunctionDef that contains target_node by lineno descent."""
    candidate = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = n.lineno
            end = getattr(n, "end_lineno", None) or start
            if start <= target_node.lineno <= end:
                if candidate is None or start > candidate.lineno:
                    candidate = n
    return candidate


def check_writing_code_7(tree, source_lines):
    """Yield violations for writing-code:7 (silent error swallowing).

    Detects four banned shapes per the rule body's banned-pattern list:
      - Pass
      - single Return None / Return False
      - single Continue
      - logging-call + Return/Continue (audit-log without typed-failure)

    Carve-outs:
      - # noqa: writing-code-7 inline opt-out on the except line
      - except ImportError + availability-flag-set body (writing-code:8 territory)
      - enclosing function returns Optional[T] AND docstring documents None as outcome
    """
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if has_noqa_writing_code_7(node, source_lines):
            continue
        if import_flag_pattern(node):
            continue
        body = node.body
        if not body:
            continue
        is_silent = False
        excerpt_shape = ""
        if len(body) == 1 and is_silent_terminator(body[0]):
            is_silent = True
            excerpt_shape = type(body[0]).__name__
        elif len(body) == 2 and is_logging_call(body[0]) and is_silent_terminator(body[1]):
            is_silent = True
            excerpt_shape = f"log+{type(body[1]).__name__}"
        if not is_silent:
            continue
        # Optional[T]+docstring carve-out applies only to Return None shape.
        if excerpt_shape in ("Return", "log+Return"):
            return_stmt = body[-1]
            if isinstance(return_stmt, ast.Return) and (
                return_stmt.value is None
                or (isinstance(return_stmt.value, ast.Constant) and return_stmt.value.value is None)
            ):
                func = enclosing_function(tree, node)
                if func is not None and function_returns_optional_with_documented_none(func):
                    continue
        # Build excerpt naming the exception type and the body shape.
        exc_name = "<bare>"
        if node.type is not None:
            if isinstance(node.type, ast.Name):
                exc_name = node.type.id
            elif isinstance(node.type, ast.Attribute):
                exc_name = node.type.attr
            elif isinstance(node.type, ast.Tuple):
                exc_name = "(" + ", ".join(
                    e.id if isinstance(e, ast.Name)
                    else (e.attr if isinstance(e, ast.Attribute) else "?")
                    for e in node.type.elts
                ) + ")"
        excerpt = f"except {exc_name}: <{excerpt_shape}>"
        violations.append(
            (node.lineno,
             f"writing-code-7-silent-swallow({excerpt_shape})",
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
    source_lines = source.splitlines()
    return (check_writing_code_7(tree, source_lines)
            + check_writing_code_9(tree, allow_decorators)
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
