#!/usr/bin/env python3
"""Build bounded, project-specific content packages using the #848 selection.

This produces configured content evidence only. It does not install packages or
change policy, permissions, required evidence, or host enforcement.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
from html import unescape
from html.parser import HTMLParser
import importlib.util
import json
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'bin' / filename)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


composition = module('procedure_composition', 'procedure_composition.py')
build = module('composition_build', 'build.py')
effective = module('composition_policy', 'effective_policy.py')


def raw_link_targets(content):
    """Read Markdown destinations and HTML href/src without interpreting prose.

    This is a conservative package validator, not a Markdown renderer: even
    local link examples in code must name packaged content. Destination parsing
    handles angle brackets, escapes and balanced parentheses; external schemes
    and same-document anchors are classified by the caller.
    """
    def destination(offset):
        while offset < len(content) and content[offset].isspace():
            offset += 1
        angled = offset < len(content) and content[offset] == '<'
        if angled:
            offset += 1
        result, depth = [], 0
        while offset < len(content):
            char = content[offset]
            if char == '\\' and offset + 1 < len(content):
                result.append(content[offset + 1]); offset += 2; continue
            if angled:
                if char == '>':
                    return ''.join(result)
                composition.require(char not in '\r\n', 'unsupported multiline angle link destination')
            else:
                if char.isspace() or char == ')' and depth == 0:
                    composition.require(depth == 0, 'unbalanced raw link destination')
                    return ''.join(result)
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
            result.append(char); offset += 1
        composition.require(not angled and depth == 0, 'unclosed raw link destination')
        return ''.join(result)

    targets = [destination(match.end()) for match in re.finditer(r'\]\(', content)]
    # Reference definitions are checked even if unused. Labels may contain
    # escaped brackets; whitespace before the destination may include a newline.
    definitions = re.finditer(r'(?m)^[ \t]{0,3}\[(?:\\.|[^\]\\]){1,999}\]:', content)
    targets.extend(destination(match.end()) for match in definitions)

    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for name, value in attrs:
                if name in {'href', 'src'} and value is not None:
                    targets.append(value)

    parser = Links(convert_charrefs=True)
    parser.feed(content)
    parser.close()
    return targets


def validate_packaged_links(files):
    for name, data in files.items():
        if not name.endswith('.md'):
            continue
        for link in raw_link_targets(data.decode()):
            parsed = urlsplit(unescape(link))
            if parsed.scheme:
                composition.require(parsed.scheme in {'http', 'https', 'mailto'},
                                    f'{name}: unsupported link scheme {parsed.scheme!r}; local-resource URLs are outside package scope')
                if parsed.scheme in {'http', 'https'}:
                    composition.require(bool(parsed.hostname), f'{name}: web link requires an external host: {link}')
                else:
                    composition.require(bool(parsed.path) and not parsed.netloc, f'{name}: mailto link requires a recipient: {link}')
                continue
            if not parsed.path and not parsed.netloc:
                continue
            path = unquote(parsed.path)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), path))
            composition.require(not parsed.netloc and not path.startswith('/') and target in files,
                                f'{name}: missing or out-of-scope packaged link {link}; use a qualified skill/rule token')


def package(source, destination, identity, *, policy_root=ROOT):
    """Render both supported layouts from one parent and explicit project inputs.

    ``source`` follows the existing skills/ and projects/ source convention.
    Destination must be new so a stale output cannot masquerade as a current
    composition. Parent source and parent packages are never rewritten.
    """
    source = source.resolve()
    composition.require(not destination.resolve().is_relative_to(source), 'composition output must be outside the source tree')
    contract, policy, selection = effective.load_inputs(policy_root)
    resolved = effective.explain(contract, policy, selection, effective.default_context(identity, []), {'type': 'review-procedure'})
    composition.require(resolved['state'] == 'resolved', 'cannot compose: ' + resolved.get('diagnostic', 'unknown identity'))
    canonical_identity = '/'.join(resolved['repository_identity'][key] for key in ('host', 'owner', 'repository'))
    project = resolved['project']
    project_root = source / 'projects' / project
    # Check the bounded source tree before any content reads. No symlink may
    # borrow a private or foreign project's files into a generated package.
    for tree in (source / 'skills', project_root):
        current = source
        for part in tree.relative_to(source).parts:
            current = current / part
            composition.require(not current.is_symlink(), f'symlink composition source is unsupported: {current}')
        for path in [tree, *tree.rglob('*')]:
            composition.require(not path.is_symlink(), f'symlink composition source is unsupported: {path}')
    config = effective.read_json(project_root / 'composition.json')
    composition.fields(config, {'bindings', 'heading_map', 'resident_budget'}, 'project composition')
    composition.fields(config['resident_budget'], {'max_characters', 'max_estimated_tokens'}, 'resident_budget')
    bindings = copy.deepcopy(config['bindings'])
    composition.fields(bindings, {'replacements', 'extensions', 'aliases'}, 'bindings')
    # The logical review capability points to the accepted procedure identifier.
    # A project may replace its content; it cannot replace the selected policy.
    bindings['aliases'].append({'alias': 'review', 'target': resolved['values']['review-procedure-binding']['procedure'], 'source': resolved['approved_policy']['source']})
    parent_skills = build.find_skills(source / 'skills')
    sources = {slug: Path('skills') / path / 'SKILL.md' for slug, path in sorted(parent_skills.items())}
    for entry in sorted((project_root / 'skills').glob('*/SKILL.md')):
        slug = project + '--' + entry.parent.name
        composition.require(slug not in sources, f'duplicate qualified skill {slug}')
        sources[slug] = entry.relative_to(source)
    rules = {slug: Path('skills') / path for slug, path in sorted(build.find_rules(source / 'skills').items())}
    if (project_root / '_rules.md').is_file():
        rules[project + '--rules'] = (project_root / '_rules.md').relative_to(source)
    procedure = resolved['values']['review-procedure-binding']['procedure']
    workflow = resolved['resident_workflow'].replace(f'Run `{procedure}`', 'Run [skill:review]')
    parent_blocks = [
        {'id': 'integrity', 'content': '## Integrity\n\nRequired evidence and permissions remain independent of procedure content. Configuration is not enforcement proof.', 'source': 'parent:composition-integrity', 'allow': []},
        {'id': 'workflow', 'content': '## Workflow\n\n' + workflow, 'source': resolved['approved_policy']['source'], 'allow': []},
        {'id': 'conventions', 'content': '## Shared conventions\n\nRecord observed results.', 'source': 'parent:composition-conventions', 'allow': ['extend', 'replace']},
    ]
    legacy = project_root / 'CLAUDE.md'
    overlays = composition.import_heading_overlay(legacy.read_text(), config['heading_map'], source=legacy.relative_to(source).as_posix())
    resident = composition.compose_resident(parent_blocks, overlays, project=project, **config['resident_budget'])
    composition.require(not destination.exists(), f'composition destination already exists: {destination}')
    outputs = {}
    # Validate and render everything in memory before any destination writes.
    for layout in ('nested', 'flat'):
        known = {}
        for slug, path in sources.items():
            owner = project if path.parts[0] == 'projects' else None
            directory = slug if owner or layout == 'flat' and not build.is_router(parent_skills[slug], parent_skills) else str(parent_skills[slug])
            content = (source / path).read_text()
            known[slug] = {'slug': slug, 'project': owner, 'kind': 'project-skill' if owner else 'skill', 'source_path': path.as_posix(), 'package_path': f'skills/{directory}/SKILL.md', 'characters': len(content), 'estimated_tokens': (len(content) + 3) // 4}
        graph = composition.ProcedureGraph(known, bindings, project=project, prerequisites={'code-review': ['review']})
        selected = graph.resolve(list(known))['selected']
        files = {}
        rule_paths = {slug: f'_{slug}.md' for slug in rules}
        for entry in selected:
            src_dir = (source / entry['source_path']).parent
            dst_dir = Path(entry['load_path']).parent
            child_skills = {p.parent for p in src_dir.rglob('SKILL.md') if p.parent != src_dir}
            for asset in sorted(src_dir.rglob('*')):
                composition.require(not asset.is_symlink(), f'symlink skill asset not supported: {asset}')
                if not asset.is_file():
                    continue
                # Routers do not own their child skills. Otherwise copying a
                # router's assets can restore an omitted replacement target.
                if any(asset.is_relative_to(child) for child in child_skills):
                    continue
                target = dst_dir / asset.relative_to(src_dir)
                if asset.suffix == '.md':
                    content = asset.read_text()
                    for match in build.RULE_TOKEN.finditer(content):
                        composition.require(match['slug'] in rule_paths, f'missing scoped rule: {match["slug"]}')
                    text = build.resolve_tokens(content, layout, {}, rule_paths, target.relative_to('skills'), composition=graph)
                    files[target.as_posix()] = text.encode()
                else:
                    files[target.as_posix()] = asset.read_bytes()
        for slug, path in rules.items():
            target = Path('skills') / rule_paths[slug]
            content = (source / path).read_text()
            for match in build.RULE_TOKEN.finditer(content):
                composition.require(match['slug'] in rule_paths, f'missing scoped rule: {match["slug"]}')
            files[target.as_posix()] = build.resolve_tokens(content, layout, {}, rule_paths, target.relative_to('skills'), composition=graph).encode()
        bundle = '\n\n'.join(files['skills/' + rule_paths[slug]].decode() for slug in sorted(rules))
        # Rule links are rendered at skills/ so the on-demand bundle lives there.
        files['skills/RULES_BUNDLE.md'] = bundle.encode()
        # Resident overlays use the same token resolver and are budgeted after
        # expansion, including longer effective project paths.
        for match in build.RULE_TOKEN.finditer(resident['rendered']):
            composition.require(match['slug'] in rule_paths, f'missing scoped rule: {match["slug"]}')
        rendered_resident = build.resolve_tokens(resident['rendered'], layout, {}, rule_paths, Path('RESIDENT.md'), composition=graph)
        final_chars = len(rendered_resident)
        composition.require(final_chars <= config['resident_budget']['max_characters'] and (final_chars + 3) // 4 <= config['resident_budget']['max_estimated_tokens'], 'rendered resident exceeds configured budget')
        files['skills/RESIDENT.md'] = rendered_resident.encode()
        manifest = {
            'schema_version': 1, 'kernel': 'skills/RESIDENT.md',
            'routes': [{'id': 'review-procedure', 'priority': 100, 'terms': ['review candidate'], 'skills': [resolved['values']['review-procedure-binding']['procedure']]}],
            'projects': [{'id': project, 'repos': [canonical_identity], 'always': [], 'routes': []}],
            'explicit_stacks': {},
            'procedure_composition': {'project': project, 'identity': canonical_identity, 'bindings': bindings, 'prerequisites': {'code-review': ['review']}},
            'known': known,
        }
        for entry in selected:
            item = known[entry['slug']]
            item['characters'] = len(files[entry['load_path']].decode())
            item['estimated_tokens'] = (item['characters'] + 3) // 4
        files['catalog/resolver-manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
        files['catalog/skills-inventory.json'] = (json.dumps({'items': list(known.values())}, indent=2) + '\n').encode()
        for filename in ('resolve-load-set.py', 'procedure_composition.py'):
            files['bin/' + filename] = (ROOT / 'bin' / filename).read_bytes()
        parent_digest = effective.digest({p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((source / 'skills').rglob('*')) if p.is_file()})
        receipt = {'project': project, 'identity': canonical_identity, 'layout': layout, 'parent_content_sha256': parent_digest, 'policy': resolved, 'composition': graph.resolve(['review']), 'resident': {**resident, 'rendered': rendered_resident, 'characters': final_chars, 'estimated_tokens': (final_chars + 3) // 4}, 'evidence_state': 'configured', 'authorization_effect': 'none'}
        files['composition.json'] = (json.dumps(receipt, indent=2) + '\n').encode()
        # A pre-existing Markdown link must not resurrect the replaced default
        # or escape into another consumer. Tokens are rebound; unsupported raw
        # references reject with a concrete path instead of shipping broken.
        validate_packaged_links(files)
        outputs[layout] = files
    for layout, files in outputs.items():
        for relative, data in files.items():
            path = destination / layout / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return {'project': project, 'layouts': list(outputs), 'evidence_state': 'configured', 'authorization_effect': 'none'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'examples/composition')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--identity', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(package(args.source, args.output, args.identity), sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({'state': 'error', 'diagnostic': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
