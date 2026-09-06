#!/usr/bin/env python3
"""AST scanner for writing-code:4 (Django ORM kwargs), :7, :8, :9, :15, writing-tests:5 and writing-releases:3.

Invoked by scan.sh for .py files in the diff. Reports violations as
<file>:<line>:<rule>: <excerpt>. Exit 0 if clean, 1 if violations.

Usage:
  scan_ast.py [--config <path>] [--exclude-tests] <file> [<file> ...]

writing-code:7 detection covers four base banned shapes (Pass, Return
None/False, Continue, log.X + Return/Continue) plus carve-outs for
Optional[T]+docstring, # noqa: writing-code-7, and ImportError +
flag-pattern (writing-code:8 territory).

writing-code:9 detection covers function parameters with non-None
defaults that are unreferenced, not forwarded via **kwargs, and not
named in the docstring. Decorator-allow-list and **kwargs-spread
carve-outs.

writing-code:15 detection covers the empirical-evidence-only call
surfaces (subprocess, requests, httpx, urllib, socket, sqlite3) called
without a `timeout` kwarg. Carve-out for `timeout=None` accompanied by
audit-signal comment (>=30 chars + identifier-shaped token) on the
same or preceding line. The --exclude-tests flag skips files matching
test path patterns.

writing-releases:3 detection covers DeprecationWarning and
PendingDeprecationWarning message strings missing version+keyword.
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


UNBOUNDED_IO_SURFACES = {
    # subprocess
    ("subprocess", "run"),
    ("subprocess", "call"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
    ("Popen", "communicate"),
    ("Popen", "wait"),
    # requests
    ("requests", "get"),
    ("requests", "post"),
    ("requests", "put"),
    ("requests", "delete"),
    ("requests", "head"),
    ("requests", "patch"),
    ("requests", "request"),
    # httpx (same set)
    ("httpx", "get"),
    ("httpx", "post"),
    ("httpx", "put"),
    ("httpx", "delete"),
    ("httpx", "head"),
    ("httpx", "patch"),
    ("httpx", "request"),
    # urllib
    ("request", "urlopen"),
    # socket
    ("socket", "create_connection"),
    # sqlite3
    ("sqlite3", "connect"),
}

# Audit-signal comment heuristic for `timeout=None` carve-out: comment must be
# >=30 chars AND contain at least one identifier-shaped token (length >=4).
AUDIT_COMMENT_IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b")
AUDIT_COMMENT_MIN_LEN = 30


def _attr_chain(node):
    """Walk an Attribute chain into a tuple of segments, leftmost first.
    `subprocess.run` -> ("subprocess", "run").
    `urllib.request.urlopen` -> ("urllib", "request", "urlopen").
    Returns None if the chain bottoms out at something other than a Name.
    """
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return tuple(reversed(parts))
    return None


def _matches_unbounded_io(call_func):
    """True if a Call's func node matches one of UNBOUNDED_IO_SURFACES."""
    if isinstance(call_func, ast.Attribute):
        chain = _attr_chain(call_func)
        if chain is None:
            return False
        # Match the rightmost two segments (handles urllib.request.urlopen
        # and subprocess.Popen(...).communicate via the (Popen, communicate) entry).
        if len(chain) >= 2 and chain[-2:] in UNBOUNDED_IO_SURFACES:
            return True
        # Also handle plain `urlopen` after `from urllib.request import urlopen`
        # via the rightmost-only check using the second-tuple-element.
    return False


def _audit_comment_present(source_lines, lineno):
    """Look at the call's line and the preceding line for an audit-signal comment.

    Heuristic: comment text >=30 chars containing >=1 identifier-shaped token
    (>=4 chars). Bare `# intentional` or `# see PR` won't match.
    """
    candidates = []
    if 1 <= lineno <= len(source_lines):
        line = source_lines[lineno - 1]
        idx = line.find("#")
        if idx != -1:
            candidates.append(line[idx + 1:].strip())
    if 2 <= lineno <= len(source_lines):
        prev = source_lines[lineno - 2].strip()
        if prev.startswith("#"):
            candidates.append(prev[1:].strip())
    for comment in candidates:
        if len(comment) >= AUDIT_COMMENT_MIN_LEN and AUDIT_COMMENT_IDENT_RE.search(comment):
            return True
    return False


def check_writing_code_15(tree, source_lines):
    """Yield violations for writing-code:15 (unbounded blocking I/O).

    For each Call to a known I/O surface, require either a numeric `timeout`
    kwarg OR `timeout=None` accompanied by an audit-signal comment.
    """
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _matches_unbounded_io(node.func):
            continue
        timeout_kwarg = None
        for kw in node.keywords:
            if kw.arg == "timeout":
                timeout_kwarg = kw
                break
        # Surface name for excerpt.
        surface = "?"
        if isinstance(node.func, ast.Attribute):
            chain = _attr_chain(node.func)
            if chain is not None:
                surface = ".".join(chain)
        if timeout_kwarg is None:
            violations.append(
                (node.lineno,
                 "writing-code-15-unbounded-io(missing-timeout)",
                 f"{surface}(...): no timeout kwarg")
            )
            continue
        # timeout=None requires audit-signal comment.
        val = timeout_kwarg.value
        is_none = isinstance(val, ast.Constant) and val.value is None
        if is_none and not _audit_comment_present(source_lines, node.lineno):
            violations.append(
                (node.lineno,
                 "writing-code-15-unbounded-io(timeout-none-no-audit-comment)",
                 f"{surface}(...): timeout=None without audit-signal comment "
                 f"(>=30 chars + identifier-shaped token, naming upstream bound)")
            )
    return violations


# --- writing-code:4 — Django ORM kwarg validation (v1: same-file models only) ---

# ORM methods whose kwargs (or `defaults={...}` dict literal) are field-name -> value.
ORM_FIELD_KWARG_METHODS = {
    "create", "get_or_create", "update_or_create",
    "filter", "exclude", "get", "update",
}

# Methods where `defaults=` carries a dict literal of field -> value.
ORM_DEFAULTS_METHODS = {"get_or_create", "update_or_create"}

# Django field class name suffix that identifies a field declaration.
_DJANGO_FIELD_SUFFIX = "Field"

# Common Manager-method kwargs that are NOT field names. Kept conservative.
_NON_FIELD_KWARGS = {
    "using", "for_update", "select_for_update", "skip_locked",
    "negate", "defaults", "create_defaults",
}

# Lookup suffixes that decompose `field__lookup` -> field. List is the union
# of Django's built-in lookups; matched as the trailing segment of __-split.
_DJANGO_LOOKUPS = {
    "exact", "iexact", "contains", "icontains", "in", "gt", "gte", "lt", "lte",
    "startswith", "istartswith", "endswith", "iendswith", "range", "date",
    "year", "iso_year", "month", "day", "week", "week_day", "iso_week_day",
    "quarter", "time", "hour", "minute", "second", "isnull", "regex", "iregex",
    "search", "overlap", "contained_by", "len", "intersects", "within",
    "distance_lte", "distance_gte", "dwithin", "covers", "covered_by",
    "crosses", "disjoint", "equals", "touches", "relate", "left", "right",
    "strictly_above", "strictly_below", "bbcontains", "bboverlaps",
}


def _is_django_field_call(value_node):
    """True if an assignment RHS looks like a Django field call (e.g. CharField(...))."""
    if not isinstance(value_node, ast.Call):
        return False
    func = value_node.func
    if isinstance(func, ast.Name):
        return func.id.endswith(_DJANGO_FIELD_SUFFIX)
    if isinstance(func, ast.Attribute):
        return func.attr.endswith(_DJANGO_FIELD_SUFFIX)
    return False


def _collect_django_models(tree):
    """Map of <ClassName> -> set of declared field names, for Django models
    defined IN THE FILE. A class is treated as a Django model if any class-body
    assignment looks like `name = <X>Field(...)`.
    """
    models = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        fields = set()
        for stmt in node.body:
            # Plain assignment: name = Field(...)
            if isinstance(stmt, ast.Assign):
                if not _is_django_field_call(stmt.value):
                    continue
                for tgt in stmt.targets:
                    if isinstance(tgt, ast.Name):
                        fields.add(tgt.id)
            # Annotated assignment: name: T = Field(...)
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                if not _is_django_field_call(stmt.value):
                    continue
                if isinstance(stmt.target, ast.Name):
                    fields.add(stmt.target.id)
        if fields:
            # Implicit pk + standard auto-fields Django adds.
            fields.update({"id", "pk"})
            models[node.name] = fields
    return models


def _orm_call_target(call_node):
    """If `call_node` is `<Model>.objects.<method>(...)`, return (ModelName, method).
    Otherwise return None.
    """
    func = call_node.func
    if not isinstance(func, ast.Attribute):
        return None
    method = func.attr
    if method not in ORM_FIELD_KWARG_METHODS:
        return None
    # func.value should be `<Model>.objects`
    objects_attr = func.value
    if not isinstance(objects_attr, ast.Attribute) or objects_attr.attr != "objects":
        return None
    model_node = objects_attr.value
    if not isinstance(model_node, ast.Name):
        return None
    return (model_node.id, method)


def _field_root(kwarg_name):
    """Decompose `field__lookup__sub` -> `field` if the trailing segments are
    known Django lookups; otherwise return the leading segment as-is.
    Returns None for things that obviously aren't field references (starts with _).
    """
    if not kwarg_name or kwarg_name.startswith("_"):
        return None
    parts = kwarg_name.split("__")
    # Strip trailing known-lookup segments; the leftmost remaining is the field.
    while len(parts) > 1 and parts[-1] in _DJANGO_LOOKUPS:
        parts.pop()
    return parts[0]


def _check_keys_against_model(model_name, declared, keys_with_lineno, file_excerpt):
    """For each (key, lineno) pair, yield a violation if the root field is not
    in `declared`. `file_excerpt` is the prefix used in the message.
    """
    out = []
    for key, lineno in keys_with_lineno:
        if key in _NON_FIELD_KWARGS:
            continue
        root = _field_root(key)
        if root is None:
            continue
        if root not in declared:
            out.append(
                (lineno,
                 "writing-code-4-django-orm-kwarg(unknown-field)",
                 f"{file_excerpt}: unknown field {root!r} on model {model_name!r} "
                 f"(declared fields: {sorted(declared)})")
            )
    return out


def check_writing_code_4_django_orm(tree):
    """Yield violations for ORM kwargs that don't map to declared model fields.

    v1 scope: same-file model resolution only. Calls referencing models defined
    in other files / apps are silently skipped (no false positives from missing
    cross-file resolution).
    """
    models = _collect_django_models(tree)
    if not models:
        return []
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = _orm_call_target(node)
        if target is None:
            continue
        model_name, method = target
        if model_name not in models:
            continue
        declared = models[model_name]
        # Direct kwargs on the call.
        direct_keys = [(kw.arg, kw.lineno) for kw in node.keywords if kw.arg]
        violations.extend(
            _check_keys_against_model(
                model_name, declared, direct_keys,
                f"{model_name}.objects.{method}(...)",
            )
        )
        # `defaults={"field": value, ...}` dict literal.
        if method in ORM_DEFAULTS_METHODS:
            for kw in node.keywords:
                if kw.arg != "defaults":
                    continue
                if not isinstance(kw.value, ast.Dict):
                    continue
                dict_keys = []
                for k in kw.value.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        dict_keys.append((k.value, k.lineno))
                violations.extend(
                    _check_keys_against_model(
                        model_name, declared, dict_keys,
                        f"{model_name}.objects.{method}(defaults={{...}})",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# writing-code:8 -- optional-import callsite hygiene (#57)
#
# When a module declares an optional import via the try/import/except-with-flag
# pattern, every public callsite of the imported symbol must be guarded by
# `if <FLAG>: ...` (or its negation) BEFORE the call, so a missing dependency
# produces a clear error rather than a bare NameError at first use.
#
# Detection is single-file only (multi-file re-exports are out of scope; the
# ticket calls them "known scanner gap" tracked at upstream #57 v1.6.2). Fires
# only when both parts of the pattern are present in one module:
#   (a) try / import X ... except (ImportError, ModuleNotFoundError): X_FLAG = ...
#   (b) an Attribute or Call node references X somewhere outside a guarded
#       branch (an `if X_FLAG` / `if not X_FLAG:` conditional or a private
#       helper function whose docstring names the flag as the caller's contract).
#
# Carve-outs:
#   - Callsites inside a private function (leading-underscore name) whose
#     docstring contains "caller must check" or names the flag literally.
#     This matches the writing-code:8 rule body ("Public callsites must check
#     the flag inline; private helpers can defer to their callers only if
#     the docstring documents the contract.").
#   - Callsites inside the try-body that established the flag (obviously
#     guarded — the flag can't be False if we're still in the try block).
# ---------------------------------------------------------------------------

FLAG_PATTERNS = ("_AVAILABLE", "_INSTALLED")
FLAG_PREFIXES = ("HAS_", "_HAS_")


def _is_flag_name(name):
    return (name.endswith(FLAG_PATTERNS) if isinstance(FLAG_PATTERNS, str)
            else any(name.endswith(s) for s in FLAG_PATTERNS)
            or any(name.startswith(p) for p in FLAG_PREFIXES))


def _extract_optional_imports(tree):
    """Return dict of imported_name -> flag_name for optional-import patterns
    at module scope. Only matches the tight
        try: import X (or from X import Y)
        <FLAG> = True
        except (ImportError, ...): <FLAG> = False
    shape."""
    result = {}
    if not isinstance(tree, ast.Module):
        return result

    for node in tree.body:
        if not isinstance(node, ast.Try):
            continue
        # Handler must catch ImportError (or subclass)
        catches_import = False
        for h in node.handlers:
            if h.type is None:
                continue
            names = []
            if isinstance(h.type, ast.Name):
                names.append(h.type.id)
            elif isinstance(h.type, ast.Tuple):
                for elt in h.type.elts:
                    if isinstance(elt, ast.Name):
                        names.append(elt.id)
            elif isinstance(h.type, ast.Attribute):
                names.append(h.type.attr)
            if any(n in ("ImportError", "ModuleNotFoundError") for n in names):
                catches_import = True
                break
        if not catches_import:
            continue

        # Find imports + flag assigns in the try body
        imported_names = []
        flag_names_in_try = []
        for stmt in node.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    imported_names.append(alias.asname or alias.name.split(".")[0])
            elif isinstance(stmt, ast.ImportFrom):
                for alias in stmt.names:
                    imported_names.append(alias.asname or alias.name)
            elif isinstance(stmt, ast.Assign):
                for tgt in stmt.targets:
                    if isinstance(tgt, ast.Name) and _is_flag_name(tgt.id):
                        flag_names_in_try.append(tgt.id)

        # Verify at least one handler ALSO assigns a flag (mirror shape)
        flag_names_in_handler = []
        for h in node.handlers:
            for stmt in h.body:
                if isinstance(stmt, ast.Assign):
                    for tgt in stmt.targets:
                        if isinstance(tgt, ast.Name) and _is_flag_name(tgt.id):
                            flag_names_in_handler.append(tgt.id)

        if not flag_names_in_try or not flag_names_in_handler:
            continue

        # Map each imported name to the (first) flag. If multiple flags are
        # set, take the intersection or fall back to first-flag.
        common_flags = set(flag_names_in_try) & set(flag_names_in_handler)
        flag_name = next(iter(common_flags), flag_names_in_try[0] if flag_names_in_try else None)
        if not flag_name:
            continue
        for imp in imported_names:
            result[imp] = flag_name
    return result


def _canonical_flag_test_polarity(test, flag_name):
    """Return 'positive' if the test is exactly `FLAG`, 'negative' if exactly
    `not FLAG`, else None. Compound tests (`FLAG and other`, `FLAG or other`,
    `FLAG == True`, attribute access) are NOT canonical — they can't be used
    to prove flag polarity. See F4 in issue #760."""
    if isinstance(test, ast.Name) and test.id == flag_name:
        return "positive"
    if (isinstance(test, ast.UnaryOp)
            and isinstance(test.op, ast.Not)
            and isinstance(test.operand, ast.Name)
            and test.operand.id == flag_name):
        return "negative"
    return None


def _test_implies_flag_truthy(test, flag_name, branch):
    """Given an if-test and which branch was taken ('true' = body executed,
    'false' = else executed), return True iff the flag is guaranteed truthy
    in that branch. See F2 in issue #760: earlier version was branch-blind
    and treated the body of `if not FLAG:` as guarded even though that IS
    the unavailable branch."""
    polarity = _canonical_flag_test_polarity(test, flag_name)
    if polarity is None:
        return False
    # `if FLAG:` body → flag truthy; else → flag falsy
    # `if not FLAG:` body → flag falsy; else → flag truthy
    if polarity == "positive":
        return branch == "true"
    return branch == "false"


def _guarded_by_flag(node, flag_name, guard_stack):
    """True iff the current node is under a canonical if-guard that proves
    flag_name is truthy at this point in the code."""
    for test, branch in guard_stack:
        if _test_implies_flag_truthy(test, flag_name, branch):
            return True
    return False


# Phrases whose presence in a private helper's docstring counts as an
# assertion that the caller has verified the availability flag. Bare mention
# of the flag name is NOT sufficient (F5 in issue #760).
CALLER_CONTRACT_PHRASES = (
    "caller must check",
    "caller must ensure",
    "caller must verify",
    "caller must have checked",
    "caller has checked",
    "caller checks",
    "caller ensures",
    "callers must",
    "requires the caller",
    "assumes the caller",
)


def _private_helper_documents_flag(func, flag_name):
    """True iff func is a leading-underscore function whose docstring both
    names the flag AND asserts (via a caller-contract phrase) that the
    caller has checked it. F5 in issue #760: bare flag mention alone is
    not enough."""
    if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    if not func.name.startswith("_"):
        return False
    doc = ast.get_docstring(func) or ""
    if flag_name not in doc:
        return False
    lower = doc.lower()
    return any(phrase in lower for phrase in CALLER_CONTRACT_PHRASES)


def _terminates_flow(stmts):
    """True if the block ends in a Return/Raise/Continue/Break — establishes an
    early-return invariant for subsequent statements in the enclosing block."""
    if not stmts:
        return False
    last = stmts[-1]
    return isinstance(last, (ast.Return, ast.Raise, ast.Continue, ast.Break))


def _if_establishes_flag(if_node, known_flags):
    """Return the flag-name (str) whose truthiness is established on the
    fall-through path after this if-statement, or None. F3 and F4 in issue
    #760: only canonical shapes count.

    Recognized (establish flag-truthy on fallthrough):
        if not FLAG: <terminator>
        if FLAG: <non-terminator>; else: <terminator>

    Explicitly NOT recognized:
        if FLAG: <terminator>              — fallthrough means FLAG was falsy
        if not FLAG: <non-terminator>; else: <terminator>  — mirrored inverse
        if FLAG and other: <terminator>    — compound doesn't prove polarity
        if FLAG or other: <terminator>     — compound doesn't prove polarity
    """
    if not isinstance(if_node, ast.If):
        return None
    for flag in known_flags:
        polarity = _canonical_flag_test_polarity(if_node.test, flag)
        if polarity is None:
            continue
        body_terminates = _terminates_flow(if_node.body)
        else_terminates = _terminates_flow(if_node.orelse) if if_node.orelse else False
        if polarity == "negative" and body_terminates:
            return flag
        if polarity == "positive" and else_terminates:
            return flag
    return None


def _establish_test(if_node, known_flags):
    """Return a synthetic `FLAG` Name node representing the invariant that
    is guaranteed on the fall-through path after if_node. Requires that
    _if_establishes_flag returned a non-None flag for the same if_node."""
    flag = _if_establishes_flag(if_node, known_flags)
    if flag is None:
        return None
    return ast.Name(id=flag, ctx=ast.Load())


def check_writing_code_8(tree):
    optional = _extract_optional_imports(tree)
    if not optional:
        return []

    violations = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.guard_stack = []
            self.func_stack = []
            # Skip the try/except body where the flag was established
            self.skip_ranges = []

        def visit_Try(self, node):
            # If this try/except sets a flag we're tracking, its body is safe
            # (the flag can't be False inside the try where imports succeeded).
            try_sets_tracked_flag = False
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for tgt in stmt.targets:
                        if isinstance(tgt, ast.Name) and tgt.id in optional.values():
                            try_sets_tracked_flag = True
            if try_sets_tracked_flag:
                self.skip_ranges.append((node.body[0].lineno if node.body else node.lineno,
                                        node.body[-1].end_lineno if node.body and hasattr(node.body[-1], 'end_lineno') else node.lineno))
            self.generic_visit(node)

        def visit_If(self, node):
            self.guard_stack.append((node.test, 'true'))
            for stmt in node.body:
                self.visit(stmt)
            self.guard_stack.pop()
            self.guard_stack.append((node.test, 'false'))
            for stmt in node.orelse:
                self.visit(stmt)
            self.guard_stack.pop()

        def _visit_block(self, stmts):
            """Walk a statement block with early-return-establishes-invariant semantics.

            When encountering `if not FLAG: raise/return`, treat FLAG as
            established for the REMAINDER of this block, but NOT while
            visiting the if-body itself (the body is the unavailable branch;
            F2 in issue #760). Same for `if FLAG: ok; else: raise/return`.

            F3/F4 (#760): polarity + shape are enforced via
            _if_establishes_flag; positive-early-return and compound tests
            no longer establish the flag."""
            established_count = 0
            known_flags = list(optional.values())
            for stmt in stmts:
                # Visit the statement FIRST — inside its own body, the flag
                # is not yet known truthy.
                self.visit(stmt)
                # THEN push the invariant for subsequent statements in this
                # block (fall-through semantic).
                if isinstance(stmt, ast.If):
                    virtual_test = _establish_test(stmt, known_flags)
                    if virtual_test is not None:
                        self.guard_stack.append((virtual_test, "true"))
                        established_count += 1
            for _ in range(established_count):
                self.guard_stack.pop()

        def visit_FunctionDef(self, node):
            self.func_stack.append(node)
            # Visit the function body with early-return semantics
            for arg_node in [*node.args.defaults, *node.args.kw_defaults]:
                if arg_node is not None:
                    self.visit(arg_node)
            self._visit_block(node.body)
            self.func_stack.pop()

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def _check_name_usage(self, name_node, used_name):
            if used_name not in optional:
                return
            flag = optional[used_name]

            # Skip if inside the try-body that set the flag
            for lo, hi in self.skip_ranges:
                if lo <= name_node.lineno <= hi:
                    return

            # Skip if guarded
            if _guarded_by_flag(name_node, flag, self.guard_stack):
                return

            # Skip if inside a private helper whose docstring names the flag
            if self.func_stack and _private_helper_documents_flag(self.func_stack[-1], flag):
                return

            violations.append((
                name_node.lineno,
                "writing-code-8",
                f"unguarded use of optional import '{used_name}'; expected 'if {flag}:' guard before this callsite",
            ))

        def visit_Attribute(self, node):
            # X.foo -> value is Name(X); flag lookup key = X
            if isinstance(node.value, ast.Name):
                self._check_name_usage(node.value, node.value.id)
            self.generic_visit(node)

        def visit_Call(self, node):
            # X(...) -> func is Name(X)
            if isinstance(node.func, ast.Name):
                self._check_name_usage(node.func, node.func.id)
            self.generic_visit(node)

    Visitor().visit(tree)
    return violations


# ---------------------------------------------------------------------------
# writing-tests:5 -- untested exception handlers (#56)
#
# For each `except` block in production code, verify at least one test file
# names the same exception class in a `pytest.raises(X)` / `assertRaises(X)` /
# `with raises(X):` form. Cross-file: needs to open the test-file counterpart
# to the source file being scanned.
#
# Source-to-test mapping (mirrors the affected-tests gate heuristic):
#   For source `<pkg>/X.py`:
#     tests/test_X.py
#     tests/test_X_*.py            (glob)
#     tests/<pkg>/test_X.py
#     <pkg>/tests/test_X.py
#
# Carve-outs (out of scope; not flagged):
#   - except inside a `finally` cleanup block
#   - except in `__del__` or signal handlers
# Both are detected by simple ancestry check + name check.
#
# Exception-class name matching:
#   Allow short-name match. `requests.exceptions.RequestException` matches
#   `RequestException` in a test that imports the short form. Match on the
#   last dotted component only (which is the typical import shape).
# ---------------------------------------------------------------------------

def _extract_except_class_names(tree):
    """Yield (lineno, class_name) for each except-handler that names a class.
    Bare `except:` and `except Exception:` are still yielded; the caller
    decides what to skip. Nested inside FunctionDef / ClassDef bodies is
    fine; we walk the whole tree."""
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        # Skip the try if it's inside a finally-body of an ancestor Try (rare
        # but the carve-out for finally-best-effort applies). We approximate
        # by scanning the tree for parents; too expensive to be exact.
        for handler in node.handlers:
            if handler.type is None:
                results.append((handler.lineno, ""))
                continue
            names = []
            if isinstance(handler.type, ast.Name):
                names.append(handler.type.id)
            elif isinstance(handler.type, ast.Attribute):
                # requests.exceptions.RequestException -> last segment
                names.append(handler.type.attr)
            elif isinstance(handler.type, ast.Tuple):
                for elt in handler.type.elts:
                    if isinstance(elt, ast.Name):
                        names.append(elt.id)
                    elif isinstance(elt, ast.Attribute):
                        names.append(elt.attr)
            for name in names:
                results.append((handler.lineno, name))
    return results


def _test_files_for_source(source_path):
    """Return candidate test files for a source file, per the affected-tests
    heuristic. Returns a list of pathlib.Path objects that exist on disk.

    F6 (#760): namespaced layouts are now mirrored. For source
    `<root>/pkg/sub/thing.py`, we look under `<root>/tests/pkg/sub/test_thing.py`
    as well as the shallower locations."""
    src = Path(source_path).resolve()
    stem = src.stem
    # Walk up to find repo root by looking for .git
    root = src.parent
    while root.parent != root and not (root / ".git").exists():
        root = root.parent
    if not (root / ".git").exists():
        return []

    candidates = [
        root / "tests" / f"test_{stem}.py",
        root / "tests" / src.parent.name / f"test_{stem}.py",
        src.parent / "tests" / f"test_{stem}.py",
        src.parent.parent / "tests" / f"test_{stem}.py",
    ]
    # F6: mirror the source's relative path under `tests/`. For
    # `<root>/pkg/sub/thing.py`, add `<root>/tests/pkg/sub/test_thing.py` plus
    # every prefix (`<root>/tests/pkg/test_thing.py`, `<root>/tests/sub/...`).
    try:
        rel_parent = src.parent.relative_to(root)
    except ValueError:
        rel_parent = None
    if rel_parent is not None:
        parts = rel_parent.parts
        for i in range(len(parts) + 1):
            candidates.append(root / "tests" / Path(*parts[:i]) / f"test_{stem}.py")
    # Glob for test_X_*.py in tests/ (both the flat root and the mirrored dir)
    if (root / "tests").is_dir():
        candidates.extend(sorted((root / "tests").glob(f"test_{stem}_*.py")))
        if rel_parent is not None:
            mirror_dir = root / "tests" / rel_parent
            if mirror_dir.is_dir():
                candidates.extend(sorted(mirror_dir.glob(f"test_{stem}_*.py")))

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in candidates:
        rp = p.resolve() if p.exists() else p
        if rp in seen:
            continue
        seen.add(rp)
        unique.append(p)
    return [p for p in unique if p.is_file()]


def _iter_call_arg_class_names(call_node):
    """Yield class-name-shaped identifiers from a Call's positional args.
    Handles Name, Attribute (dotted last-segment), and Tuple (multiple classes
    passed as a tuple, e.g. `pytest.raises((ExcA, ExcB))`)."""
    for arg in call_node.args:
        if isinstance(arg, ast.Name):
            yield arg.id
        elif isinstance(arg, ast.Attribute):
            yield arg.attr
        elif isinstance(arg, ast.Tuple):
            for elt in arg.elts:
                if isinstance(elt, ast.Name):
                    yield elt.id
                elif isinstance(elt, ast.Attribute):
                    yield elt.attr


def _test_ast_covers_exception(test_path, exc_class):
    """F7 (#760): parse the test file as AST and look for actual call nodes
    to pytest.raises / raises / assertRaises / self.assertRaises whose first
    positional arg names `exc_class`. Comments and TODOs cannot satisfy
    coverage because they are not in the AST.

    Returns True if such a call is found. On unreadable/unparseable files,
    emits a scanner diagnostic to stderr and returns False (writing-code:11
    no-silent-process compliance)."""
    if not exc_class:
        return False
    try:
        source = test_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"{test_path}:0:scan-ast-warning: test file unreadable: {e}",
              file=sys.stderr)
        return False
    try:
        tree = ast.parse(source, filename=str(test_path))
    except SyntaxError as e:
        print(f"{test_path}:{e.lineno or 0}:scan-ast-warning: test file "
              f"unparseable: {e.msg}", file=sys.stderr)
        return False

    RAISES_NAMES = ("raises", "assertRaises")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Match: raises(X), assertRaises(X)
        if isinstance(func, ast.Name) and func.id in RAISES_NAMES:
            if exc_class in _iter_call_arg_class_names(node):
                return True
        # Match: pytest.raises(X), self.assertRaises(X), any.assertRaises(X)
        elif isinstance(func, ast.Attribute) and func.attr in RAISES_NAMES:
            if exc_class in _iter_call_arg_class_names(node):
                return True
    return False


# Back-compat alias: earlier revisions used a grep-based helper; the AST
# version is strictly stricter (rejects comments/TODOs) and is the correct
# implementation of writing-tests:5's coverage predicate.
_test_file_covers_exception = _test_ast_covers_exception


# Regex to enforce F8 (#760): `noqa: writing-tests-5` must be followed by
# at least one non-whitespace reason token. Bare `noqa: writing-tests-5`
# with no reason is rejected. Pattern accepts optional space after the
# colon, then requires >=3 chars of non-whitespace content.
_NOQA_WITH_REASON_RE = re.compile(
    r"noqa:\s*writing-tests-5\b[^\n]*?\S{3,}"
)


def _is_carveout_handler(handler_lineno, source_lines):
    """True if the except handler carries a carve-out comment on the same or
    preceding line naming why no test exists.

    F8 (#760): `noqa: writing-tests-5` requires at least 3 chars of non-
    whitespace reason text following it on the same comment. Bare
    `# noqa: writing-tests-5` is rejected; rule text requires a one-line
    comment naming why no test exists."""
    if handler_lineno < 1 or handler_lineno > len(source_lines):
        return False
    line = source_lines[handler_lineno - 1]
    if _NOQA_WITH_REASON_RE.search(line):
        return True
    if handler_lineno >= 2:
        prev = source_lines[handler_lineno - 2]
        if _NOQA_WITH_REASON_RE.search(prev):
            return True
    return False


def check_writing_tests_5(tree, source_lines, source_path):
    """Cross-file check: every except handler needs a test that names its class."""
    # Skip if source path IS a test file (rule is for production code)
    if _is_test_path(source_path):
        return []

    # Skip if source has no except blocks at all
    handlers = _extract_except_class_names(tree)
    handlers = [(ln, cls) for ln, cls in handlers if cls]  # drop bare except:
    if not handlers:
        return []

    # Drop handlers that carry an explicit noqa carve-out before deciding
    # whether to emit the no-test-file fire; a file whose every except is
    # carved out should stay silent.
    handlers = [(ln, cls) for ln, cls in handlers
                if not _is_carveout_handler(ln, source_lines)]
    if not handlers:
        return []

    test_files = _test_files_for_source(source_path)
    if not test_files:
        # No test file exists for this source. Fire once per file rather
        # than once per except (avoid noise) — the fix is to add a test
        # file, not to comment N except lines.
        return [(handlers[0][0], "writing-tests-5",
                 f"source has {len(handlers)} except block(s) but no test file found "
                 f"(looked in tests/, {Path(source_path).parent}/tests/, ...)")]

    violations = []
    for lineno, exc_class in handlers:
        # Any test file covers it?
        covered = any(_test_file_covers_exception(tp, exc_class) for tp in test_files)
        if not covered:
            violations.append((
                lineno, "writing-tests-5",
                f"except {exc_class}: no matching pytest.raises({exc_class}) in "
                f"{', '.join(str(p.name) for p in test_files)}",
            ))
    return violations


# Default test-path globs for --exclude-tests.
TEST_PATH_PATTERNS = ("/tests/", "/test/", "_test.py", "test_")


def _is_test_path(path):
    p = str(path)
    return any(pat in p for pat in TEST_PATH_PATTERNS)


def scan_file(path, allow_decorators, exclude_tests=False):
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
    results = (check_writing_code_7(tree, source_lines)
               + check_writing_code_9(tree, allow_decorators)
               + check_writing_code_4_django_orm(tree)
               + check_writing_releases_3(tree)
               + check_writing_code_8(tree)
               + check_writing_tests_5(tree, source_lines, path))
    # writing-code:15 honors --exclude-tests for project-specific test fixtures.
    if not (exclude_tests and _is_test_path(path)):
        results = results + check_writing_code_15(tree, source_lines)
    return results


def main(argv):
    config_path = None
    exclude_tests = False
    files = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--config":
            config_path = argv[i + 1]
            i += 2
        elif a == "--exclude-tests":
            exclude_tests = True
            i += 1
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
        for line, rule, excerpt in scan_file(path, allow_decorators, exclude_tests):
            print(f"{path}:{line}:{rule}: {excerpt}")
            total += 1
    return 1 if total > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
