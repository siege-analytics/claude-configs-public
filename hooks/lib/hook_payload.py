"""Bounded identity/action metadata; semantic hook input stays on its input stream."""
from __future__ import annotations

import json
import sys

INPUT_LIMIT = 1024 * 1024
METADATA_LIMIT = 98304
COMMAND_LIMIT = 65536
IDENTITY_KEYS = (
    'session_id', 'sessionId', 'sessionID', 'id', 'craftSessionId',
    'craft_session_id', 'transcript_path', 'transcriptPath', 'cwd',
    'hook_event_name', 'tool_name', 'tool_use_id', 'task_id',
)
IDENTITY_CONTAINERS = ('session', 'conversation', 'metadata')


def metadata_environment(payload: dict) -> str:
    """Preserve decision-bearing fields, excluding arbitrary tool/prompt bodies."""
    if not isinstance(payload, dict):
        raise ValueError('hook payload must be a JSON object')

    def identity(value):
        if not isinstance(value, dict):
            return value
        result = {key: value[key] for key in IDENTITY_KEYS if key in value}
        for key in IDENTITY_CONTAINERS:
            if key in value:
                result[key] = identity(value[key])
        return result

    metadata = identity(payload)
    if 'prompt' in payload:
        prompt = payload['prompt']
        metadata['prompt'] = prompt if isinstance(prompt, str) and len(prompt) <= 4096 else ''
    if 'tool_input' in payload:
        tool_input = payload['tool_input']
        if isinstance(tool_input, dict):
            selected = {key: tool_input[key] for key in ('command', 'file_path', 'notebook_path', 'path') if key in tool_input}
            for key in ('content', 'old_string', 'new_string'):
                if key in tool_input:
                    selected[key] = ''
            if 'edits' in tool_input:
                selected['edits'] = []
            metadata['tool_input'] = selected
        else:
            metadata['tool_input'] = tool_input
    command = (payload.get('tool_input') or {}).get('command') if isinstance(payload.get('tool_input'), dict) else None
    if payload.get('tool_name') == 'Bash' and not isinstance(command, str):
        raise ValueError('Bash command metadata must be a string')
    if isinstance(command, str) and len(command.encode('utf-8', 'surrogatepass')) > COMMAND_LIMIT:
        raise ValueError('Bash command exceeds its 64 KiB transport bound')
    encoded = json.dumps(metadata, ensure_ascii=True, allow_nan=False)
    if len(encoded.encode('utf-8')) > METADATA_LIMIT:
        raise ValueError('required hook metadata exceeds its 96 KiB environment bound')
    return encoded


def _unique(pairs):
    value = {}
    for key, field in pairs:
        if key in value:
            raise ValueError('duplicate hook payload keys')
        value[key] = field
    return value


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(INPUT_LIMIT + 1)
        if len(raw) > INPUT_LIMIT:
            raise ValueError('hook input exceeds its 1 MiB bound')
        payload = json.loads(raw, object_pairs_hook=_unique,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite hook value')))
        print(metadata_environment(payload))
        return 0
    except ValueError as error:
        print('Hook metadata unavailable: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
