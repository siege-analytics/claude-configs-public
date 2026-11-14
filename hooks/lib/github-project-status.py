#!/usr/bin/env python3
"""Live membership proof for one source-granted project Status edit."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import sys

# GitHub's official Projects schema: ProjectV2Item.project/content and
# ProjectV2SingleSelectField.project/options, not caller-supplied attestations.
# https://docs.github.com/en/graphql/reference/projects
QUERY = '''query VerifyTaskStatus($item: ID!, $field: ID!) {
 item: node(id: $item) { __typename ... on ProjectV2Item {
  id isArchived
  project { id number owner { __typename ... on Organization { login } ... on User { login } }
   fields(first: 100) { pageInfo { hasNextPage } nodes {
    __typename ... on ProjectV2SingleSelectField { id name }
    ... on ProjectV2Field { id name } ... on ProjectV2IterationField { id name }
    ... on ProjectV2MultiSelectField { id name }
   } }
  }
  content { __typename ... on Issue { url number repository { nameWithOwner } } }
  status: fieldValueByName(name: "Status") { __typename ... on ProjectV2ItemFieldSingleSelectValue {
   optionId field { ... on ProjectV2SingleSelectField { id } }
  } }
 } }
 field: node(id: $field) { __typename ... on ProjectV2SingleSelectField {
  id name dataType project { id } options { id name }
 } }
}'''


def require(predicate, message):
    if not predicate:
        raise ValueError('live project Status proof: ' + message)


def unique(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate response key')
        result[key] = value
    return result


def verify(target, grants):
    """One bounded fixed query; failure never falls back to filesystem scope."""
    spec = importlib.util.spec_from_file_location('status_bounded_runner', Path(__file__).with_name('craft-settings-router.py'))
    runner = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(runner)
    command = shlex.join(['gh', 'api', 'graphql', '--hostname', 'github.com',
                          '-f', 'query=' + QUERY, '-f', 'item=' + target['item_id'],
                          '-f', 'field=' + target['field_id']])
    result, output, _error = runner.execute_hook(command, b'', dict(os.environ), 3.0)
    require(result == 0, 'GitHub lookup failed; verify read:project access and retry')
    require(len(output.encode()) <= 65536, 'response exceeds 64KiB')
    value = json.loads(output, object_pairs_hook=unique)
    try:
        require(isinstance(value, dict) and set(value) == {'data'}, 'missing or partial/error response')
        item, field = value['data']['item'], value['data']['field']
        require(item['__typename'] == 'ProjectV2Item' and item['id'] == target['item_id']
                and item['isArchived'] is False, 'item is missing, archived or another node type')
        project = item['project']
        require(project['id'] == target['project_id'] and type(project['number']) is int,
                'item is not in the requested project')
        owner = project['owner']
        require(owner['__typename'] in {'Organization', 'User'}, 'unsupported project owner')
        content = item['content']
        repo = content['repository']['nameWithOwner']
        issue = content['number']
        require(content['__typename'] == 'Issue' and type(issue) is int and issue > 0
                and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+', repo)
                and content['url'] == 'https://github.com/' + repo + '/issues/' + str(issue)
                and repo.split('/')[1] not in {'.', '..'}, 'item does not contain a canonical Issue')
        require(field['__typename'] == 'ProjectV2SingleSelectField' and field['id'] == target['field_id']
                and field['project']['id'] == project['id'] and field['name'] == 'Status'
                and field['dataType'] == 'SINGLE_SELECT', 'field is not this project\'s single-select Status')
        fields = project['fields']
        require(fields['pageInfo']['hasNextPage'] is False and isinstance(fields['nodes'], list)
                and len(fields['nodes']) <= 100, 'incomplete field membership')
        require(all(isinstance(f, dict) and f.get('__typename') in {'ProjectV2SingleSelectField', 'ProjectV2Field', 'ProjectV2IterationField', 'ProjectV2MultiSelectField'}
                    and isinstance(f.get('id'), str) and isinstance(f.get('name'), str) for f in fields['nodes']), 'invalid field membership shape')
        named = [f for f in fields['nodes'] if f.get('name') == 'Status']
        require(len(named) == 1 and named[0]['id'] == field['id'], 'Status field membership is ambiguous')
        options = field['options']
        require(isinstance(options, list) and len(options) <= 100, 'invalid option list')
        require(all(isinstance(o, dict) and isinstance(o.get('id'), str) and isinstance(o.get('name'), str) for o in options), 'invalid option shape')
        require(len({o['id'] for o in options}) == len(options) and len({o['name'] for o in options}) == len(options), 'ambiguous options')
        chosen = [o for o in options if o['id'] == target['option_id']]
        require(len(chosen) == 1, 'option does not belong to Status')
        status = item['status']
        if status is not None:
            require(status['__typename'] == 'ProjectV2ItemFieldSingleSelectValue'
                    and status['field']['id'] == field['id'], 'current Status is ambiguous')
            current = [o for o in options if o['id'] == status['optionId']]
            require(len(current) == 1 and current[0]['name'] != 'Done', 'operator-owned Done cannot be reset')
        issue_owner, repository = repo.split('/')
        permitted = [g for g in grants if g['operation'] == 'item-edit'
                     and g['owner'].lower() == owner['login'].lower() and g['project'] == project['number']
                     and g['issue_owner'].lower() == issue_owner.lower() and chosen[0]['name'] in g['values']]
        require(len(permitted) == 1, 'installed grant does not cover this project/issue/Status value')
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('live project Status proof: malformed relationship response') from error
    return {**target, 'owner':owner['login'], 'project':project['number'],
            'issue_owner':issue_owner, 'repository':repository, 'issue':issue}
