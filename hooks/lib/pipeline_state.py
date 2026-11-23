"""Current Task diagnostics; preparation prose never grants edit authority."""
import json
import sys

try:
    with open(sys.argv[1]) as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError('Task metadata must be an object')
except (OSError, ValueError, IndexError) as error:
    print(f'Task metadata unavailable: {error}. No preparation authority was derived.')
    sys.exit(0)

status = data.get('status', '')
if status not in ('disposed', 'done-awaiting-pr'):
    task = data.get('task_id') or data.get('ticket') or data.get('task', 'unknown')
    print(f'Task {json.dumps(task)}: status={status or "unknown"}. Ownership and physical scope are checked per action; review evidence is checked at publication.')
