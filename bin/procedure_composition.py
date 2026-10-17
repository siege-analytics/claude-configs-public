#!/usr/bin/env python3
"""Project-scoped procedure composition, shared by selection and rendering.

This graph selects content only. Policy, authorization and host capability
decisions are inputs owned elsewhere; replacing content cannot change them.
"""
from __future__ import annotations

import copy
from pathlib import PurePosixPath
import re

SLUG = re.compile(r"[a-z][a-z0-9-]*\Z")


def require(value, message):
    if not value:
        raise ValueError(message)


def fields(value, names, context):
    require(isinstance(value, dict) and set(value) == set(names), f"{context}: expected fields {sorted(names)}")


def identifier(value, context):
    require(isinstance(value, str) and SLUG.fullmatch(value), f"{context}: invalid qualified slug {value!r}")
    return value


def relative_path(value, context):
    require(isinstance(value, str) and value and "\\" not in value and "\x00" not in value, f"{context}: invalid path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts and str(path) == value, f"{context}: expected canonical relative path")
    return value


class ProcedureGraph:
    """Compile one selected project's bindings over an existing skill inventory.

    ``known`` is keyed by qualified slug and supplies source_path, package_path,
    project (None for parent skills). ``prerequisites`` is the selected scope's
    existing prerequisite map. Declarations name their source for diagnostics.
    Replacing a procedure replaces its own dependency set; callers' prerequisite
    edges still resolve through that replacement. Locked evidence requirements
    are policy constraints and must not be encoded as replaceable content edges.
    """

    def __init__(self, known, declarations, *, project, prerequisites=None):
        identifier(project, "project")
        fields(declarations, {"replacements", "extensions", "aliases"}, "composition")
        require(isinstance(known, dict), "known procedures must be an object")
        self.project = project
        self.known = copy.deepcopy(known)
        self.prerequisites = copy.deepcopy(prerequisites or {})
        self.replacements, self.extensions, self.aliases = {}, {}, {}
        sources = {}
        for slug, item in self.known.items():
            identifier(slug, "procedure")
            require(isinstance(item, dict), f"procedure {slug}: expected inventory entry")
            for name in ("source_path", "package_path"):
                relative_path(item.get(name), f"procedure {slug}.{name}")
            owner = item.get("project")
            require(owner is None or isinstance(owner, str) and SLUG.fullmatch(owner), f"procedure {slug}: invalid project")
            if owner is not None:
                require(item.get("publisher") is None, f"procedure {slug}: project scope and publisher ownership are distinct")
                require(slug.startswith(owner + "--"), f"procedure {slug}: qualification disagrees with project {owner}")
                require(item["source_path"].startswith(f"projects/{owner}/skills/"), f"procedure {slug}: source is outside declared project")
            elif item.get("publisher") is not None:
                publisher = identifier(item["publisher"], f"procedure {slug}.publisher")
                root = relative_path(item.get("publisher_root"), f"procedure {slug}.publisher_root")
                require(PurePosixPath(root).parts and PurePosixPath(root).parts[0] != "projects",
                        f"procedure {slug}: publisher cannot borrow project scope")
                qualified = item.get("publisher_qualified")
                require(type(qualified) is bool, f"procedure {slug}: publisher qualification must be explicit")
                local = identifier(item.get("publisher_local_slug"), f"procedure {slug}.publisher_local_slug")
                require(slug == (publisher + "--" + local if qualified else local),
                        f"procedure {slug}: qualification disagrees with publisher {publisher}")
                require(item["source_path"].startswith(root + "/"), f"procedure {slug}: source is outside declared publisher")
                source = PurePosixPath(item["source_path"])
                require(source.name == "SKILL.md", f"procedure {slug}: publisher source must be SKILL.md")
                relative = source.parent.relative_to(root)
                # Match source discovery, including its existing shelf namespace.
                source_local = source.parent.name
                require("--" not in source_local, f"procedure {slug}: publisher source directory must be unqualified")
                if len(relative.parts) > 1 and relative.parts[0] == "shelves":
                    source_local = "shelves--" + source_local
                require(local == source_local, f"procedure {slug}: local slug disagrees with declared publisher source")
            else:
                require(item["source_path"].startswith("skills/"), f"procedure {slug}: parent source must be under skills/")
            source = item["source_path"]
            require(source not in sources, f"same source declared as {sources.get(source)} and {slug}; use an explicit alias")
            sources[source] = slug
        for kind, keys in (
            ("replacements", {"target", "replacement", "source"}),
            ("extensions", {"target", "append", "source"}),
            ("aliases", {"alias", "target", "source"}),
        ):
            require(isinstance(declarations[kind], list), f"{kind}: expected declarations")
            for item in declarations[kind]:
                fields(item, keys, kind)
                require(isinstance(item["source"], str) and item["source"].strip(), f"{kind}: source is required")
                target = identifier(item["target"], kind + ".target")
                if kind == "aliases":
                    name = identifier(item["alias"], "alias")
                    require(name not in known, f"alias {name} would shadow an existing qualified procedure")
                    self._declare(self.aliases, name, target, item["source"], "alias")
                else:
                    self._visible(target)
                    if kind == "replacements":
                        replacement = identifier(item["replacement"], "replacement")
                        self._visible(replacement)
                        self._declare(self.replacements, target, replacement, item["source"], "replacement")
                    else:
                        append = item["append"]
                        require(isinstance(append, list) and append, f"extension {target}: expected ordered nonempty append list")
                        for slug in append:
                            self._visible(identifier(slug, "extension step"))
                        self._declare(self.extensions, target, append, item["source"], "ordered extension")
        require(isinstance(self.prerequisites, dict), "prerequisites must be an object")
        for target, dependencies in self.prerequisites.items():
            self._visible(target)
            require(isinstance(dependencies, list), f"prerequisites for {target}: expected list")
            for slug in dependencies:
                identifier(slug, "prerequisite")
                require(slug in self.aliases or slug in self.known, f"missing prerequisite reference: {slug}")
                if slug in self.known:
                    self._visible(slug)
        # Validate unused declarations too: an unreachable cycle is still an
        # invalid configuration, not a delayed runtime surprise.
        for slug in sorted(set(self.aliases) | set(self.replacements) | set(self.extensions) | set(self.prerequisites)):
            self.resolve([slug])

    @staticmethod
    def _declare(mapping, target, value, source, kind):
        if target in mapping:
            old = mapping[target]
            require(old["value"] == value, f"conflicting {kind} for {target}: {old['source']} versus {source}")
        else:
            mapping[target] = {"value": copy.deepcopy(value), "source": source}

    def _visible(self, slug):
        require(slug in self.known, f"missing procedure reference: {slug}")
        owner = self.known[slug].get("project")
        require(owner is None or owner == self.project, f"procedure {slug} belongs to project {owner}, not {self.project}")

    def resolve(self, requests):
        """Return one ordered load set, with every request using the same graph."""
        require(isinstance(requests, list), "requests must be an ordered list")
        selected = {}
        edges = set()

        def visit(slug, active, trace, root):
            identifier(slug, "requested procedure")
            require(slug not in active, "composition cycle: " + " -> ".join([*active, slug]))
            active = [*active, slug]
            if slug in self.aliases:
                edge = self.aliases[slug]
                return visit(edge["value"], active, [*trace, {"kind": "alias", "from": slug, **edge}], root)
            self._visible(slug)
            sequence = []
            if slug in self.replacements:
                edge = self.replacements[slug]
                sequence.extend(visit(edge["value"], active, [*trace, {"kind": "replacement", "from": slug, **edge}], root))
            else:
                for dependency in self.prerequisites.get(slug, []):
                    sequence.extend(visit(dependency, active, [*trace, {"kind": "prerequisite", "from": slug}], root))
                item = self.known[slug]
                if slug not in selected:
                    selected[slug] = {
                        "slug": slug, "source_path": item["source_path"], "load_path": item["package_path"],
                        "project": item.get("project"), "requested_by": [], "binding_traces": [],
                    }
                    if item.get("publisher") is not None:
                        selected[slug]["publisher"] = item["publisher"]
                entry = selected[slug]
                if root not in entry["requested_by"]:
                    entry["requested_by"].append(root)
                if trace not in entry["binding_traces"]:
                    entry["binding_traces"].append(trace)
                sequence.append(slug)
            if slug in self.extensions:
                edge = self.extensions[slug]
                for step in edge["value"]:
                    sequence.extend(visit(step, active, [*trace, {"kind": "extension", "from": slug, "source": edge["source"]}], root))
            sequence = list(dict.fromkeys(sequence))
            edges.update((left, right) for left, right in zip(sequence, sequence[1:]) if left != right)
            return sequence

        for requested in requests:
            visit(requested, [], [], requested)
        # Deduplication must not put an explicitly requested extension before
        # its base. Sort once over the union of all declared ordering edges.
        remaining, ordered = list(selected), []
        while remaining:
            ready = next((slug for slug in remaining if not any(right == slug and left in remaining for left, right in edges)), None)
            require(ready is not None, "conflicting composition order: " + " -> ".join(remaining))
            ordered.append(selected[ready]); remaining.remove(ready)
        return {"project": self.project, "selected": ordered, "authorization_effect": "none"}

    def link_targets(self, slug):
        """Ordered package paths for a skill token, including declared extensions."""
        return [item["load_path"] for item in self.resolve([slug])["selected"]]


def import_heading_overlay(text, mapping, *, source):
    """Import legacy level-two sections through an explicit stable-ID map.

    No heading implies precedence. Unknown/repeated headings or an unmapped
    preamble reject. Fenced code is retained verbatim, not parsed as headings.
    """
    require(isinstance(text, str) and isinstance(mapping, dict), "overlay text and explicit heading map required")
    require(all(isinstance(key, str) and key for key in mapping), "empty or invalid legacy heading")
    require(len({key.casefold() for key in mapping}) == len(mapping), "ambiguous case-folded heading mapping")
    for heading, entry in mapping.items():
        require(isinstance(heading, str) and heading, "empty legacy heading")
        fields(entry, {"id", "mode"}, f"legacy heading {heading}")
    sections, seen = [], set()
    heading, lines, fence = "__preamble__", [], None

    def save():
        content = "".join(lines).strip()
        if not content:
            return
        require(heading in mapping, f"{source}: unmapped legacy heading {heading!r}")
        key = heading.casefold()
        require(key not in seen, f"{source}: repeated/ambiguous legacy heading {heading!r}")
        seen.add(key)
        sections.append({**mapping[heading], "content": content, "source": source})

    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            if fence is None:
                fence = (marker[1][0], len(marker[1]))
            elif marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                fence = None
            lines.append(line)
            continue
        found = re.match(r"^ {0,3}##\s+(.+?)\s*#*\s*$", line) if fence is None else None
        if found:
            save()
            heading, lines = found[1], [line]
        else:
            lines.append(line)
    require(fence is None, f"{source}: unclosed code fence in legacy overlay")
    save()
    return sections


def graph_from_manifest(manifest, inventory, identity):
    """Read a derived consumer's content graph; this never authenticates policy.

    A composed package is specific to one exact repository identity. Using it
    elsewhere rejects, rather than silently falling back to a different scope.
    """
    config = manifest["procedure_composition"]
    fields(config, {"project", "identity", "bindings", "prerequisites"}, "procedure_composition")
    require(identity == config["identity"], "composed package repository identity differs from target")
    matches = [p for p in manifest["projects"] if p["id"] == config["project"] and p["repos"] == [identity]]
    require(len(matches) == 1, "composition project/identity differs from resolver project")
    known = {item["slug"]: item for item in inventory["items"] if item["kind"] in {"skill", "project-skill"}}
    return ProcedureGraph(known, config["bindings"], project=config["project"], prerequisites=config["prerequisites"])


def compose_resident(parent_blocks, overlays, *, project, max_characters, max_estimated_tokens):
    """Compose stable blocks under parent-declared content override points.

    Keep integrity/workflow blocks closed to prose overrides. The caller supplies
    their text from the accepted parent/policy; this function creates no policy.
    """
    identifier(project, "project")
    for name, value in (("max_characters", max_characters), ("max_estimated_tokens", max_estimated_tokens)):
        require(type(value) is int and value > 0, f"{name}: positive configured budget required")
    require(isinstance(parent_blocks, list) and isinstance(overlays, list), "resident blocks must be lists")
    result, modes = {}, {}
    for block in parent_blocks:
        fields(block, {"id", "content", "source", "allow"}, "parent resident block")
        ident = identifier(block["id"], "resident block")
        require(ident not in result, f"duplicate parent resident block ID: {ident}")
        require(isinstance(block["content"], str) and isinstance(block["source"], str) and block["source"], f"block {ident}: content/source required")
        require(isinstance(block["allow"], list) and set(block["allow"]) <= {"replace", "extend"}, f"block {ident}: unsupported composition mode")
        result[ident] = {"id": ident, "content": block["content"], "sources": [block["source"]]}
        modes[ident] = block["allow"]
    seen = set()
    for overlay in overlays:
        fields(overlay, {"id", "mode", "content", "source"}, "project resident overlay")
        ident = identifier(overlay["id"], "overlay block")
        require(ident not in seen, f"duplicate project resident block ID: {ident}")
        seen.add(ident)
        require(isinstance(overlay["content"], str) and isinstance(overlay["source"], str) and overlay["source"], f"overlay {ident}: content/source required")
        mode = overlay["mode"]
        require(mode in {"add", "replace", "extend"}, f"overlay {ident}: unknown mode")
        if mode == "add":
            require(ident not in result, f"overlay {ident}: add collides with existing block")
            require(ident.startswith(project + "--"), f"new resident block {ident} must be qualified for project {project}")
            result[ident] = {"id": ident, "content": overlay["content"], "sources": [overlay["source"]]}
        else:
            require(ident in modes, f"overlay {ident}: missing parent block")
            require(mode in modes[ident], f"overlay {ident}: parent does not permit {mode}")
            block = result[ident]
            block["content"] = overlay["content"] if mode == "replace" else block["content"] + "\n\n" + overlay["content"]
            block["sources"].append(overlay["source"])
    rendered = "\n\n".join(block["content"] for block in result.values())
    characters, tokens = len(rendered), (len(rendered) + 3) // 4
    require(characters <= max_characters and tokens <= max_estimated_tokens,
            f"composed resident exceeds configured budget: {characters} characters / {tokens} estimated tokens")
    return {"project": project, "blocks": list(result.values()), "rendered": rendered,
            "characters": characters, "estimated_tokens": tokens, "authorization_effect": "none"}
