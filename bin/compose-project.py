#!/usr/bin/env python3
"""Build bounded project content from explicit content and approved policy inputs.

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
    # Conservatively inspect definitions anywhere, including inside nested
    # blockquotes/lists and unused definitions. A top-level line anchor would
    # miss valid container definitions. Labels cannot contain bare brackets.
    definitions = re.finditer(r'\[(?:\\.|[^\[\]\\]){1,999}\]:', content)
    targets.extend(destination(match.end()) for match in definitions)

    # CommonMark 0.31.2 section 6.5: URI autolinks are destinations too, not
    # HTML attributes. Feed them through the same scheme policy. Email
    # autolinks intentionally resolve to mailto, as in CommonMark.
    targets.extend(re.findall(r'<([A-Za-z][A-Za-z0-9+.-]{1,31}:[^\x00-\x20\x7f<>]*)>', content))
    email = (r"[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
             r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
             r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*')
    targets.extend('mailto:' + address for address in re.findall('<(' + email + ')>', content))

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


def selected_content(value, source, resolved):
    """Expand declared content inputs without adopting policy or capabilities.

    The bounded policy substitutions render the separately verified selection. They
    are not an expression language and cannot modify its values or authority.
    Publisher ownership is independent of the selected project's scope.
    """
    composition.fields(value, {'schema_version', 'publishers', 'policy_aliases', 'prerequisites',
                               'routes', 'resident_blocks'}, 'content selection')
    composition.require(type(value['schema_version']) is int and value['schema_version'] == 1,
                        'unsupported content selection schema')
    composition.require(isinstance(value['publishers'], list), 'publishers must be an ordered list')
    publishers, roots = {}, []
    for entry in value['publishers']:
        composition.fields(entry, {'id', 'skills_root', 'qualified'}, 'publisher')
        ident = composition.identifier(entry['id'], 'publisher')
        composition.require(ident not in publishers, f'duplicate publisher {ident}')
        relative = composition.relative_path(entry['skills_root'], f'publisher {ident} source')
        path = Path(relative)
        composition.require(path.parts and path.parts[0] != 'projects', 'publisher source cannot borrow project scope')
        composition.require(type(entry['qualified']) is bool, 'publisher qualification must be explicit')
        composition.require(not any(path.is_relative_to(prior) or prior.is_relative_to(path) for prior in roots),
                            f'overlapping publisher source {relative}')
        current = source
        for part in path.parts:
            current /= part
            composition.require(not current.is_symlink(), f'symlink publisher source: {current}')
        composition.require(current.is_dir(), f'missing selected publisher source: {relative}')
        for asset in current.rglob('*'):
            composition.require(not asset.is_symlink(), f'symlink publisher asset: {asset}')
        roots.append(path)
        publishers[ident] = copy.deepcopy(entry)
    aliases = value['policy_aliases']
    composition.require(isinstance(aliases, list), 'policy_aliases must be a list')
    for alias in aliases:
        composition.identifier(alias, 'policy alias')
    composition.require(len(set(aliases)) == len(aliases), 'duplicate policy alias')
    composition.require(isinstance(value['routes'], list), 'routes must be a list')
    procedure = resolved['values']['review-procedure-binding']['procedure']
    route_ids, routes = set(), copy.deepcopy(value['routes'])
    for route in routes:
        composition.fields(route, {'id', 'priority', 'terms', 'skills'}, 'content route')
        ident = composition.identifier(route['id'], 'route')
        composition.require(ident not in route_ids, f'duplicate route {ident}')
        route_ids.add(ident)
        composition.require(type(route['priority']) is int, f'route {ident}: priority must be an integer')
        composition.require(isinstance(route['terms'], list) and route['terms']
                            and all(isinstance(term, str) and term.strip() for term in route['terms']),
                            f'route {ident}: nonempty terms required')
        composition.require(isinstance(route['skills'], list) and route['skills'], f'route {ident}: skills required')
        route['skills'] = [procedure if slug == '${policy.review_procedure}' else slug for slug in route['skills']]
        for slug in route['skills']:
            composition.identifier(slug, 'route skill')
    review_reference = aliases[0] if aliases else procedure
    workflow = resolved['resident_workflow'].replace(f'Run `{procedure}`', f'Run [skill:{review_reference}]')
    composition.require(isinstance(value['resident_blocks'], list), 'resident_blocks must be a list')
    blocks = copy.deepcopy(value['resident_blocks'])
    for block in blocks:
        composition.fields(block, {'id', 'content', 'source', 'allow'}, 'resident block')
        composition.require(isinstance(block['content'], str) and isinstance(block['source'], str),
                            'resident block content/source must be strings')
        block['content'] = block['content'].replace('${policy.resident_workflow}', workflow)
        block['source'] = block['source'].replace('${policy.source}', resolved['approved_policy']['source'])
        composition.require('${policy.' not in block['content'] and '${policy.' not in block['source'],
                            'unknown policy substitution in resident block')
    return publishers, blocks, routes


def package(source, destination, identity, *, policy_root=ROOT,
            policy_registration_source=None, policy_registration_sha256=None,
            content_selection=None):
    """Render both layouts through one graph and renderer for every selection.

    ``source`` contains declared publisher roots and projects/ source inputs.
    Omitted arguments select the explicit Siege compatibility descriptors.
    Explicit content selection never establishes the policy registration pin.
    Destination must be new so a stale output cannot masquerade as a current
    composition. Parent source and parent packages are never rewritten.
    """
    source = source.resolve()
    composition.require(not destination.resolve().is_relative_to(source), 'composition output must be outside the source tree')
    if policy_registration_source is None and policy_registration_sha256 is None:
        contract, policy, selection = effective.load_inputs(policy_root)
        selection_source = 'catalog/effective-policy-selection.json'
    else:
        composition.require(policy_registration_source is not None and policy_registration_sha256 is not None,
                            'policy registration source and independent digest must be supplied together')
        loaded = effective.load_registered_inputs(policy_root, registration_source=policy_registration_source,
                                                  registration_sha256=policy_registration_sha256)
        contract, policy, selection = (loaded[key] for key in ('contract', 'policy', 'selection'))
        selection_source = loaded['registration']['selection_source']
    resolved = effective.explain(contract, policy, selection, effective.default_context(identity, []),
                                 {'type': 'review-procedure'}, selection_source=selection_source)
    composition.require(resolved['state'] == 'resolved', 'cannot compose: ' + resolved.get('diagnostic', 'unknown identity'))
    canonical_identity = '/'.join(resolved['repository_identity'][key] for key in ('host', 'owner', 'repository'))
    project = resolved['project']
    project_root = source / 'projects' / project
    # Check the bounded source tree before any content reads. No symlink may
    # borrow a private or foreign project's files into a generated package.
    for tree in (project_root,):
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
    if content_selection is None:
        # Explicit Siege compatibility input; the generic path never reads it.
        content_selection = effective.read_json(effective._gate_contract_module().repository_path(
            policy_root, 'bundles/siege/composition-inputs.json', 'Siege composition input'))
    publishers, parent_blocks, routes = selected_content(content_selection, source, resolved)
    procedure = resolved['values']['review-procedure-binding']['procedure']
    for alias in content_selection['policy_aliases']:
        bindings['aliases'].append({'alias': alias, 'target': procedure, 'source': resolved['approved_policy']['source']})
    sources, source_owners, parent_skills, rules = {}, {}, {}, {}
    for publisher, declaration in publishers.items():
        root = Path(declaration['skills_root'])
        discovered = build.find_skills(source / root)
        for local, path in sorted(discovered.items()):
            slug = publisher + '--' + local if declaration['qualified'] else local
            composition.require(slug not in sources, f'duplicate qualified skill {slug}; declare an explicit alias')
            sources[slug] = root / path / 'SKILL.md'
            source_owners[slug] = declaration
            parent_skills[slug] = (path, build.is_router(path, discovered))
        for local, path in sorted(build.find_rules(source / root).items()):
            slug = publisher + '--' + local if declaration['qualified'] else local
            composition.require(slug not in rules, f'duplicate qualified rule {slug}')
            rules[slug] = root / path
    for entry in sorted((project_root / 'skills').glob('*/SKILL.md')):
        slug = project + '--' + entry.parent.name
        composition.require(slug not in sources, f'duplicate qualified skill {slug}')
        sources[slug] = entry.relative_to(source)
    if (project_root / '_rules.md').is_file():
        composition.require(project + '--rules' not in rules, f'duplicate qualified rule {project}--rules')
        rules[project + '--rules'] = (project_root / '_rules.md').relative_to(source)
    legacy = project_root / 'CLAUDE.md'
    overlays = composition.import_heading_overlay(legacy.read_text(), config['heading_map'], source=legacy.relative_to(source).as_posix())
    resident = composition.compose_resident(parent_blocks, overlays, project=project, **config['resident_budget'])
    composition.require(resident['rendered'].strip(), 'selected resident composition must not be empty')
    composition.require(not destination.exists(), f'composition destination already exists: {destination}')
    outputs = {}
    # Validate and render everything in memory before any destination writes.
    for layout in ('nested', 'flat'):
        known = {}
        for slug, path in sources.items():
            owner = project if path.parts[0] == 'projects' else None
            publisher = source_owners.get(slug)
            directory = slug if owner or publisher['qualified'] or layout == 'flat' and not parent_skills[slug][1] else str(parent_skills[slug][0])
            content = (source / path).read_text()
            known[slug] = {'slug': slug, 'project': owner, 'kind': 'project-skill' if owner else 'skill', 'source_path': path.as_posix(), 'package_path': f'skills/{directory}/SKILL.md', 'characters': len(content), 'estimated_tokens': (len(content) + 3) // 4}
            if publisher:
                known[slug].update(publisher=publisher['id'], publisher_root=publisher['skills_root'],
                                   publisher_qualified=publisher['qualified'])
        graph = composition.ProcedureGraph(known, bindings, project=project, prerequisites=content_selection['prerequisites'])
        for route in routes:
            graph.resolve(route['skills'])
            composition.require(all(slug in known for slug in route['skills']),
                                f'route {route["id"]}: name concrete procedures; use policy.review_procedure for the selected binding')
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
            'routes': routes,
            'projects': [{'id': project, 'repos': [canonical_identity], 'always': [], 'routes': []}],
            'explicit_stacks': {},
            'procedure_composition': {'project': project, 'identity': canonical_identity, 'bindings': bindings, 'prerequisites': copy.deepcopy(content_selection['prerequisites'])},
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
        publisher_files = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                           for declaration in publishers.values()
                           for p in sorted((source / declaration['skills_root']).rglob('*')) if p.is_file()}
        parent_digest = effective.digest(publisher_files)
        review_request = content_selection['policy_aliases'][0] if content_selection['policy_aliases'] else procedure
        receipt = {'project': project, 'identity': canonical_identity, 'layout': layout, 'parent_content_sha256': parent_digest, 'policy': resolved, 'composition': graph.resolve([review_request]), 'resident': {**resident, 'rendered': rendered_resident, 'characters': final_chars, 'estimated_tokens': (final_chars + 3) // 4}, 'evidence_state': 'configured', 'authorization_effect': 'none',
                   'content_selection_sha256': effective.digest(content_selection),
                   'publishers': [{'id': name, 'skills_root': entry['skills_root'], 'qualified': entry['qualified'],
                                   'content_sha256': effective.digest({path: sha for path, sha in publisher_files.items() if Path(path).is_relative_to(entry['skills_root'])})}
                                  for name, entry in publishers.items()]}
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
    parser.add_argument('--policy-root', type=Path, default=ROOT)
    parser.add_argument('--policy-inputs', type=Path)
    parser.add_argument('--policy-inputs-sha256')
    parser.add_argument('--content-selection', type=Path, help='content-only selection relative to --source')
    args = parser.parse_args()
    try:
        content = None if args.content_selection is None else effective.read_json(effective._gate_contract_module().repository_path(
            args.source, args.content_selection.as_posix(), 'content selection'))
        print(json.dumps(package(args.source, args.output, args.identity, policy_root=args.policy_root,
                                 policy_registration_source=args.policy_inputs,
                                 policy_registration_sha256=args.policy_inputs_sha256,
                                 content_selection=content), sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError, build.BuildError) as exc:
        print(json.dumps({'state': 'error', 'diagnostic': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
