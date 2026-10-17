#!/usr/bin/env python3
"""Validate canonical terminology, its artifact bindings and generated wiki page."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "catalog/ontology.json"
BINDINGS = "catalog/ontology-bindings.json"
WIKI = "wiki/Ontology.md"
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
VALUE_TYPES = {"string": str, "object": dict, "array": list, "boolean": bool, "integer": int}
# A bounded vocabulary invariant, not runtime permission. Maintenance ownership
# may extend protection, but can never qualify a new subject or allowed edge.
AUTHORITY_TERMS = frozenset({"authorization-record", "authorization-scope"})
AUTHORITY_RELATIONSHIPS = frozenset({("authorization-record", "binds", "authorization-scope")})


def fail(message: str) -> None:
    raise ValueError(message)


def object_fields(value: Any, fields: set[str], context: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        fail(f"{context}: expected exactly {sorted(fields)}")


def text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        fail(f"{context}: expected nonempty text without surrounding whitespace")
    return value


def items(value: Any, context: str, *, empty: bool = False) -> list:
    if not isinstance(value, list) or (not value and not empty):
        fail(f"{context}: expected {'a' if empty else 'a nonempty'} list")
    return value


def identifier(value: Any, context: str) -> str:
    value = text(value, context)
    if not ID.fullmatch(value):
        fail(f"{context}: expected a lowercase hyphenated identifier")
    return value


def normalized(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def repository_path(root: Path, relative: str) -> Path:
    text(relative, "artifact path")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        fail(f"artifact path must stay within the repository: {relative}")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        fail(f"artifact path escapes the repository: {relative}")
    component = root.resolve()
    for part in path.parts:
        component = component / part
        if component.is_symlink():
            fail(f"artifact path contains a symlink: {relative}")
    return resolved


def validate_registry(data: Any) -> dict[str, dict]:
    object_fields(data, {"schema_version", "ontology_version", "terms", "relationships", "aliases"}, REGISTRY)
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        fail("unsupported ontology schema_version; expected integer 1")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", text(data["ontology_version"], "ontology_version")):
        fail("ontology_version must be a numeric major.minor.patch version")
    terms: dict[str, dict] = {}
    names: dict[str, str] = {}
    for term in items(data["terms"], "terms"):
        object_fields(term, {"id", "label", "definition", "owner", "examples", "distinguished_from", "references"}, "term")
        ident = identifier(term["id"], "term id")
        if ident in terms:
            fail(f"duplicate term id: {ident}")
        for field in ("label", "definition", "owner"):
            text(term[field], f"{ident}.{field}")
        for field in ("examples", "distinguished_from", "references"):
            values = items(term[field], f"{ident}.{field}", empty=field == "distinguished_from")
            for value in values:
                text(value, f"{ident}.{field}")
            if len(set(values)) != len(values):
                fail(f"{ident}.{field}: duplicate values")
        for name in {normalized(ident), normalized(term["label"])}:
            if name in names:
                fail(f"term label/id collision: {ident} with {names[name]}")
            names[name] = ident
        terms[ident] = term
    missing_authority_terms = AUTHORITY_TERMS - terms.keys()
    if missing_authority_terms:
        fail(f"missing required authority terms: {', '.join(sorted(missing_authority_terms))}")
    protected_terms = AUTHORITY_TERMS | {
        ident for ident, term in terms.items() if normalized(term["owner"]) == "authority"
    }
    for ident, term in terms.items():
        for other in term["distinguished_from"]:
            if other not in terms or other == ident:
                fail(f"{ident}: invalid distinguished_from term {other}")
    edges = set()
    triples = set()
    for edge in items(data["relationships"], "relationships"):
        object_fields(edge, {"id", "subject", "verb", "object", "definition"}, "relationship")
        ident = identifier(edge["id"], "relationship id")
        for field in ("subject", "object"):
            if text(edge[field], f"{ident}.{field}") not in terms:
                fail(f"{ident}: unknown {field} term {edge[field]}")
        identifier(edge["verb"], f"{ident}.verb")
        text(edge["definition"], f"{ident}.definition")
        triple = (edge["subject"], edge["verb"], edge["object"])
        if ident in edges or triple in triples:
            fail(f"duplicate relationship: {ident}")
        if protected_terms.intersection((edge["subject"], edge["object"])) and triple not in AUTHORITY_RELATIONSHIPS:
            fail(f"{ident}: unsupported authority relationship: {' '.join(triple)}; "
                 "only authorization-record binds authorization-scope is permitted; "
                 "review changes to the authority invariant in bin/ontology.py")
        edges.add(ident)
        triples.add(triple)
    for triple in sorted(AUTHORITY_RELATIONSHIPS - triples):
        fail(f"missing required authority relationship: {' '.join(triple)}")
    for alias in items(data["aliases"], "aliases", empty=True):
        object_fields(alias, {"name", "status", "targets"}, "alias")
        name = normalized(text(alias["name"], "alias name"))
        if name in names:
            fail(f"alias collision: {alias['name']} with {names[name]}")
        if alias["status"] not in ("ambiguous", "deprecated"):
            fail(f"{alias['name']}: invalid alias status")
        targets = items(alias["targets"], f"{alias['name']}.targets")
        for target in targets:
            if text(target, "alias target") not in terms:
                fail(f"{alias['name']}: unknown alias target {target}")
        if len(set(targets)) != len(targets):
            fail(f"{alias['name']}: duplicate alias targets")
        if (alias["status"] == "deprecated" and len(targets) != 1) or (alias["status"] == "ambiguous" and len(targets) < 2):
            fail(f"{alias['name']}: deprecated aliases need one target; ambiguous aliases need alternatives")
        names[name] = alias["name"]
    return terms


def canonical_term(value: Any, registry: dict, terms: dict[str, dict]) -> str:
    value = text(value, "term reference")
    if value in terms:
        return value
    for alias in registry["aliases"]:
        if normalized(value) == normalized(alias["name"]):
            fail(f"{alias['status']} term '{value}'; use an explicit canonical ID: {', '.join(alias['targets'])}")
    suggestions = [ident for ident, term in terms.items() if normalized(value) in (normalized(ident), normalized(term["label"]))]
    fail(f"unknown canonical term '{value}'" + (f"; use {suggestions[0]}" if suggestions else ""))


def pointer_values(data: Any, pointer: str) -> list[Any]:
    """Resolve JSON Pointer tokens, with '*' selecting every child; every branch must match."""
    if not isinstance(pointer, str) or not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        fail(f"invalid artifact pointer: {pointer!r}")
    current = [data]
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        next_values = []
        for value in current:
            if token == "*" and isinstance(value, (dict, list)) and value:
                next_values.extend(value.values() if isinstance(value, dict) else value)
            elif token != "*" and isinstance(value, dict) and token in value:
                next_values.append(value[token])
            elif isinstance(value, list) and token.isascii() and token.isdigit() and str(int(token)) == token and int(token) < len(value):
                next_values.append(value[int(token)])
            else:
                fail(f"missing or empty bound field: {pointer} (at {token!r})")
        current = next_values
    return current


def validate_bindings(data: Any, registry: dict, root: Path) -> int:
    """Check semantic references without executing or changing the referenced artifacts."""
    terms = validate_registry(registry)
    object_fields(data, {"schema_version", "ontology_version", "bindings"}, "bindings")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        fail("unsupported bindings schema_version; expected integer 1")
    if data["ontology_version"] != registry["ontology_version"]:
        fail("bindings ontology_version differs from the registry; review and update the binding")
    seen = set()
    count = 0
    for binding in items(data["bindings"], "bindings"):
        object_fields(binding, {"artifact", "fields"}, "artifact binding")
        artifact = repository_path(root, binding["artifact"])
        if artifact in seen:
            fail(f"duplicate artifact binding: {binding['artifact']}")
        seen.add(artifact)
        content = read_json(artifact)
        pointers = set()
        for field in items(binding["fields"], "bound fields"):
            object_fields(field, {"pointer", "term", "value_type"}, "field binding")
            canonical_term(field["term"], registry, terms)
            pointer = text(field["pointer"], "bound pointer")
            if pointer in pointers:
                fail(f"duplicate field binding: {binding['artifact']} {pointer}")
            pointers.add(pointer)
            value_type = text(field["value_type"], "value_type")
            if value_type not in VALUE_TYPES:
                fail(f"unknown value_type: {value_type}")
            for value in pointer_values(content, pointer):
                if type(value) is not VALUE_TYPES[value_type]:
                    fail(f"{binding['artifact']} {pointer}: expected {value_type}, got {type(value).__name__}")
                count += 1
    return count


def render_wiki(registry: dict, bindings: dict) -> str:
    digest = hashlib.sha256(json.dumps(registry, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    lines = ["# Shared ontology", "", "<!-- Generated by bin/ontology.py --write. Edit catalog/ontology.json, not this page. -->", "",
             f"Ontology version: **{registry['ontology_version']}**. Canonical registry SHA-256: `{digest}`.", "",
             "The versioned registry defines the shared vocabulary. This page is its generated, on-demand reference; it is not globally injected resident context.", "",
             "## Use and authority", "",
             "Structured semantic references must use exact canonical IDs. Aliases require an explicit migration choice; the validator never silently rewrites them. Existing field names can retain a checked binding while their owning contract is migrated.", "",
             "A binding checks its canonical term reference, field presence and JSON type. It does not prove that the chosen meaning is correct or that a program implements the definition. Relationships describe the model; they are not executable permission rules, a reasoner or authorization evidence. Owners identify maintenance responsibility, not permission to authorize an operation.", "",
             "The validator seals relationships involving `authorization-record`, `authorization-scope` or any term maintained by the `authority` owner. The only permitted signature is `authorization-record binds authorization-scope`, and that relationship and its two terms are required. All other incoming or outgoing edges fail regardless of the verb, including configuration or skill replacement creating authorization. Changing an owner cannot unprotect the two canonical terms or qualify a new subject. Adding a relationship at this boundary requires a reviewed change to the explicit allowlist in `bin/ontology.py`; non-authority relationships remain extensible. This is a structural vocabulary constraint, not proof about arbitrary prose or runtime authorization.", "",
             "Configuration, artifact checks, runtime observation and protected acceptance are separate claims. Always name the target, revision, boundary and evidence relevant to a claim. A skill replacement, label or configured flag cannot manufacture authorization or live enforcement.", "",
             "## Canonical terms", ""]
    for term in sorted(registry["terms"], key=lambda item: item["id"]):
        lines.extend([f"<a id=\"{term['id']}\"></a>", f"### {term['label']}", "", f"ID: `{term['id']}` · Owner: `{term['owner']}` · Work: {', '.join(term['references'])}", "", term["definition"], ""])
        lines.extend(f"- Example: {example}" for example in term["examples"])
        if term["distinguished_from"]:
            lines.append("- Distinguish from: " + ", ".join(f"[{other}](#{other})" for other in term["distinguished_from"]) + ".")
        lines.append("")
    lines.extend(["## Relationships", ""])
    for edge in sorted(registry["relationships"], key=lambda item: item["id"]):
        lines.append(f"- `{edge['id']}`: [{edge['subject']}](#{edge['subject']}) **{edge['verb']}** [{edge['object']}](#{edge['object']}). {edge['definition']}")
    lines.extend(["", "## Ambiguous and former names", "", "These spellings are rejected as machine term references. The prose linter only advises; context determines the intended replacement.", ""])
    for alias in sorted(registry["aliases"], key=lambda item: item["name"]):
        lines.append(f"- `{alias['name']}` ({alias['status']}): " + ", ".join(f"`{target}`" for target in alias["targets"]) + ".")
    lines.extend(["", "## Checked artifact bindings", "", "These bindings annotate existing fields without changing their runtime schema. In particular, a legacy `blocking` boolean describes configuration, not observed protected acceptance.", ""])
    for binding in bindings["bindings"]:
        lines.append(f"- `{binding['artifact']}`:")
        for field in binding["fields"]:
            lines.append(f"  - `{field['pointer']}` → `{field['term']}` ({field['value_type']}).")
    lines.extend(["", "## Consumer compatibility", "",
                  "Synthetic consumer A preserves parent-owned content and adds a declared project layer. Synthetic consumer B imports an explicit legacy native-shadow declaration as a skill replacement. Both use the same parent definitions and explicit resident composition; neither makes its local workflow a universal default.", "",
                  "An ambiguous local term needs a scoped mapping chosen by its owner. Do not add project-specific meanings to a canonical ID or guess that every local override is the same operation. Private consumer source and operational evidence remain in their authorized private locations.", "",
                  "## Maintenance and publication", "", "```sh", "python3 bin/build.py --layout both", "python3 bin/ontology.py --write", "python3 bin/ontology.py --check", "python3 bin/ontology.py --explain host-capability", "python3 bin/ontology.py --validate-bindings catalog/ontology-bindings.json", "python3 bin/ontology.py --lint docs/design-note.md", "```", "",
                  "Change definitions and bindings in the same reviewed PR. Additive terms increment the minor ontology version; editorial clarification increments the patch version; incompatible meanings require a new ID and an explicit migration, with a major version when compatibility breaks. Update the binding version after reviewing that change.", "",
                  "CI validates the registry, opted-in bindings and this generated page. Unregistered interfaces are not claimed as covered. Prose lint is optional and advisory; it does not gate agent tool use.", "",
                  "The repository-backed wiki is reviewable with its source. A separate GitHub Wiki mirror must copy the generated page from an approved source revision, identify that revision, preserve unrelated pages, and avoid hand-editing definitions. If the wiki remote is unavailable, report publication as pending; do not claim this checked-in page is already mirrored.", ""])
    return "\n".join(lines)


def lint_prose(content: str, registry: dict) -> list[str]:
    phrases = {value for term in registry["terms"] for value in (term["id"], term["label"])}
    masked = content
    for phrase in sorted(phrases, key=len, reverse=True):
        masked = re.sub(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", lambda match: " " * len(match[0]), masked, flags=re.I)
    warnings = []
    for line, value in enumerate(masked.splitlines(), 1):
        for alias in registry["aliases"]:
            if re.search(r"(?<!\w)" + re.escape(alias["name"]) + r"(?!\w)", value, flags=re.I):
                warnings.append(f"{line}: {alias['status']} '{alias['name']}'; choose from {', '.join(alias['targets'])}")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="validate registry/bindings and generated freshness (default)")
    modes.add_argument("--write", action="store_true", help="regenerate the wiki after validating bindings")
    modes.add_argument("--validate-bindings", metavar="FILE", help="check an additional repository-local binding manifest")
    modes.add_argument("--explain", metavar="TERM", help="print a canonical term definition")
    modes.add_argument("--lint", nargs="+", metavar="FILE", help="advisory prose warnings; ambiguity does not fail")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        registry = read_json(repository_path(root, REGISTRY))
        terms = validate_registry(registry)
        if args.explain:
            ident = canonical_term(args.explain, registry, terms)
            print(json.dumps(terms[ident], indent=2))
        elif args.lint:
            for name in args.lint:
                for warning in lint_prose(repository_path(root, name).read_text(encoding="utf-8"), registry):
                    print(f"ADVISORY {name}:{warning}")
        else:
            bindings = read_json(repository_path(root, args.validate_bindings or BINDINGS))
            count = validate_bindings(bindings, registry, root)
            if not args.validate_bindings:
                expected = render_wiki(registry, bindings)
                wiki = repository_path(root, WIKI)
                if args.write:
                    wiki.parent.mkdir(parents=True, exist_ok=True)
                    wiki.write_text(expected, encoding="utf-8")
                elif not wiki.is_file() or wiki.read_text(encoding="utf-8") != expected:
                    fail(f"stale or missing {WIKI}; run python3 bin/ontology.py --write")
            print(f"ontology {registry['ontology_version']}: {len(terms)} terms; {count} bound values validated")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ONTOLOGY ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
