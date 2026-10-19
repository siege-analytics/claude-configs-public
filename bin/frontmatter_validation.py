#!/usr/bin/env python3
"""Validate Markdown YAML frontmatter with a real YAML parser.

Self-contained and vendorable: the standard library plus PyYAML, with no
repository layout assumptions. Callers pass text or file paths and a kind.

A frontmatter block is the text between a leading ``---`` line and the next
``---`` line. The block must parse with ``yaml.safe_load`` semantics, reject
duplicate keys, and produce a mapping. Required metadata must be non-empty,
non-whitespace ``str``. A narrow compatibility lint rejects plain scalars that
a YAML 1.1 parser (PyYAML) and a YAML 1.2 core-schema parser resolve
differently, such as unquoted ``yes``/``no``/``on``/``off``, so validation here
agrees with 1.2 hosts on every accepted file.

PyYAML is imported lazily so that importing this module never fails. Every
validation entry point fails closed with FrontmatterDependencyError when
PyYAML is unavailable; there is no fallback parser.

CLI:  python3 frontmatter_validation.py [--kind skill|rule] FILE...
      python3 frontmatter_validation.py --check-dependency
Exit: 0 all valid, 1 any invalid, 2 PyYAML unavailable (or, for
--check-dependency, not the pinned version).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

PYYAML_REQUIREMENT = "PyYAML==6.0.3"

# Kind policy. Skills must carry a block with name and description. Rule files
# may omit the block; when present, these fields must be well-formed strings.
KINDS: dict[str, dict[str, Any]] = {
    "skill": {"require_block": True, "required": ("name", "description")},
    "rule": {"require_block": False, "required": ()},
}
STRING_FIELDS = ("name", "description")

_YAML_STR = "tag:yaml.org,2002:str"
_YAML_MERGE = "tag:yaml.org,2002:merge"

# YAML 1.2 core schema implicit resolution (YAML 1.2.2 spec, section 10.3.2).
_CORE_12 = (
    ("tag:yaml.org,2002:null", re.compile(r"^(?:~|null|Null|NULL|)$")),
    ("tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")),
    ("tag:yaml.org,2002:int", re.compile(r"^(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$")),
    ("tag:yaml.org,2002:float", re.compile(
        r"^(?:[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?"
        r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$"
    )),
)
# Same int tag in both schemas but a different value: 1.1 reads a leading zero
# as octal, 1.2 core reads it as decimal.
_LEADING_ZERO_INT = re.compile(r"^[-+]?0[0-9]+$")


class FrontmatterError(ValueError):
    """Frontmatter is missing, unparseable, or violates the metadata contract."""


class FrontmatterDependencyError(FrontmatterError):
    """PyYAML is unavailable; validation cannot run and must not pass."""


_LOADER = None


def _yaml():
    try:
        import yaml
    except ImportError as exc:
        raise FrontmatterDependencyError(
            f"PyYAML is required for frontmatter validation and is not importable by "
            f"{sys.executable}; install the pinned validation dependency "
            f"({PYYAML_REQUIREMENT}), for example: "
            f"{Path(sys.executable).name} -m pip install '{PYYAML_REQUIREMENT}'"
        ) from exc
    return yaml


def _loader():
    """Return a SafeLoader subclass that rejects duplicate mapping keys."""
    global _LOADER
    if _LOADER is None:
        yaml = _yaml()

        class UniqueKeySafeLoader(yaml.SafeLoader):
            def construct_mapping(self, node, deep=False):
                if isinstance(node, yaml.MappingNode):
                    seen = set()
                    for key_node, _ in node.value:
                        if key_node.tag == _YAML_MERGE:
                            continue
                        key = self.construct_object(key_node, deep=True)
                        try:
                            duplicate = key in seen
                        except TypeError:
                            raise yaml.constructor.ConstructorError(
                                "while constructing a mapping", node.start_mark,
                                "found unhashable key", key_node.start_mark,
                            ) from None
                        if duplicate:
                            raise yaml.constructor.ConstructorError(
                                "while constructing a mapping", node.start_mark,
                                f"found duplicate key {key!r}", key_node.start_mark,
                            )
                        seen.add(key)
                return super().construct_mapping(node, deep=deep)

        _LOADER = UniqueKeySafeLoader
    return _LOADER


def split_frontmatter(text: str) -> str | None:
    """Return the raw frontmatter block, or None when the text has no block.

    The block opens with a first line of exactly ``---`` and closes at the next
    ``\\n---\\n``, the delimiter convention other frontmatter readers share.
    A byte-order mark or CRLF opening is rejected rather than silently read as
    "no frontmatter"; so is an opening delimiter without a closing one.
    """
    if text.startswith(("﻿", "---\r\n")):
        raise FrontmatterError("frontmatter must start with '---' and LF line endings, without a byte-order mark")
    if not text.startswith("---\n"):
        # A near-miss delimiter ('--- ', or '---' after blank lines) would
        # otherwise read as "no frontmatter" and ship its header unvalidated.
        first = text.lstrip("\r\n").split("\n", 1)[0]
        if first.strip() == "---":
            raise FrontmatterError("frontmatter delimiter must be exactly '---' on the first line")
        return None
    end = text.find("\n---\n", 3)
    if end < 0:
        raise FrontmatterError("frontmatter opening '---' has no closing '---' line")
    return text[4:end] if end >= 4 else ""


def _core_12_tag(value: str) -> str:
    for tag, pattern in _CORE_12:
        if pattern.match(value):
            return tag
    return _YAML_STR


def _plain_scalars(node, yaml):
    stack = [node]
    seen = set()
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, yaml.ScalarNode):
            if current.style is None:
                yield current
        elif isinstance(current, yaml.SequenceNode):
            stack.extend(current.value)
        elif isinstance(current, yaml.MappingNode):
            for key_node, value_node in current.value:
                stack.extend((key_node, value_node))


def compatibility_problems(block: str) -> list[str]:
    """Constructs that YAML 1.1 and YAML 1.2 core parsers may read differently.

    Anchors, aliases, explicit tags, and merge keys are rejected outright:
    metadata never needs them, and 1.1-only types (!!set, !!omap, merge) hide
    behind them. Plain scalars must resolve to the same type under both.
    """
    yaml = _yaml()
    problems = []
    for token in yaml.scan(block, Loader=_loader()):
        construct = {
            yaml.AnchorToken: "anchor", yaml.AliasToken: "alias", yaml.TagToken: "explicit tag",
        }.get(type(token))
        if construct:
            problems.append(f"line {token.start_mark.line + 2}: {construct} not allowed in frontmatter")
    node = yaml.compose(block, Loader=_loader())
    if node is None:
        return problems
    for scalar in _plain_scalars(node, yaml):
        if scalar.tag == _YAML_MERGE:
            problems.append(f"line {scalar.start_mark.line + 2}: merge key '<<' is YAML 1.1 only")
            continue
        core = _core_12_tag(scalar.value)
        line = scalar.start_mark.line + 2  # +1 for 1-based, +1 for the opening '---'
        if scalar.tag != core:
            problems.append(
                f"line {line}: unquoted {scalar.value!r} resolves as {scalar.tag.rsplit(':', 1)[-1]} "
                f"under YAML 1.1 but {core.rsplit(':', 1)[-1]} under YAML 1.2; quote it"
            )
        elif core == "tag:yaml.org,2002:int" and _LEADING_ZERO_INT.match(scalar.value):
            problems.append(
                f"line {line}: unquoted {scalar.value!r} is octal under YAML 1.1 but decimal "
                f"under YAML 1.2; quote it"
            )
    return problems


def _location(problem: Any) -> str:
    mark = getattr(problem, "problem_mark", None)
    if mark is None:
        return ""
    return f" at line {mark.line + 2}, column {mark.column + 1}"


def parse_frontmatter(block: str) -> dict[str, Any]:
    """Parse a frontmatter block into a mapping, rejecting duplicates and lint failures."""
    yaml = _yaml()
    try:
        data = yaml.load(block, Loader=_loader())
    except yaml.YAMLError as exc:
        reason = getattr(exc, "problem", None) or str(exc).splitlines()[0]
        raise FrontmatterError(f"invalid YAML: {reason}{_location(exc)}") from None
    if not isinstance(data, dict):
        raise FrontmatterError(f"frontmatter must be a YAML mapping, got {type(data).__name__}")
    problems = compatibility_problems(block)
    if problems:
        raise FrontmatterError("YAML 1.1/1.2 incompatible frontmatter: " + "; ".join(problems))
    return data


def validate_text(text: str, kind: str = "skill", source: str = "<text>") -> dict[str, Any] | None:
    """Validate one document's frontmatter. Return the parsed mapping, or None
    for a rule without a block. Raise FrontmatterError naming ``source``."""
    if kind not in KINDS:
        raise ValueError(f"unknown frontmatter kind {kind!r}; expected one of {sorted(KINDS)}")
    policy = KINDS[kind]
    _yaml()  # Fail closed even for documents that would need no parse.
    try:
        block = split_frontmatter(text)
        if block is None:
            if policy["require_block"]:
                raise FrontmatterError("missing frontmatter block")
            return None
        data = parse_frontmatter(block)
        missing = [field for field in policy["required"] if field not in data]
        if missing:
            raise FrontmatterError(f"missing required {', '.join(missing)}")
        for field in STRING_FIELDS:
            if field not in data:
                continue
            value = data[field]
            if not isinstance(value, str):
                raise FrontmatterError(
                    f"{field} must be a non-empty string, got {type(value).__name__} {value!r}"
                )
            if not value.strip():
                raise FrontmatterError(f"{field} must be a non-empty string, got blank")
    except FrontmatterDependencyError:
        raise
    except FrontmatterError as exc:
        raise FrontmatterError(f"{kind} frontmatter invalid in {source}: {exc}") from None
    return data


def validate_file(path: Path | str, kind: str = "skill", source: str | None = None) -> dict[str, Any] | None:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FrontmatterError(f"{kind} frontmatter unreadable in {source or path}: {exc}") from None
    return validate_text(text, kind=kind, source=source or str(path))


def check_dependency() -> str:
    """Return the installed PyYAML version when it matches the pin; else raise."""
    yaml = _yaml()
    pinned = PYYAML_REQUIREMENT.split("==", 1)[1]
    installed = getattr(yaml, "__version__", "unknown")
    if installed != pinned:
        raise FrontmatterDependencyError(
            f"PyYAML {installed} is importable by {sys.executable}, but the pinned validation "
            f"dependency is {PYYAML_REQUIREMENT}"
        )
    return installed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--kind", choices=sorted(KINDS), default="skill")
    parser.add_argument("--check-dependency", action="store_true",
                        help=f"exit 0 only if {PYYAML_REQUIREMENT} is importable by this interpreter")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args(argv)
    if args.check_dependency:
        try:
            installed = check_dependency()
        except FrontmatterDependencyError as exc:
            print(f"frontmatter validation unavailable: {exc}", file=sys.stderr)
            return 2
        print(f"frontmatter validation dependency: PyYAML {installed} ({sys.executable})")
        return 0
    if not args.paths:
        parser.error("at least one path is required unless --check-dependency is given")
    failures = 0
    for path in args.paths:
        try:
            validate_file(path, kind=args.kind)
        except FrontmatterDependencyError as exc:
            print(f"frontmatter validation unavailable: {exc}", file=sys.stderr)
            return 2
        except FrontmatterError as exc:
            failures += 1
            print(exc, file=sys.stderr)
    if failures:
        print(f"frontmatter validation: {failures} of {len(args.paths)} file(s) invalid", file=sys.stderr)
        return 1
    print(f"frontmatter validation: {len(args.paths)} file(s) valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
