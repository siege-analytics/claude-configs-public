#!/bin/bash
# Older host registrations may still invoke this retired preparation callback.
# Missing or malformed optional investigation evidence cannot grant authority
# or create a universal stop; per-action Task checks are tested separately.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 - "$ROOT/hooks/resolver/investigate-gate-guard.sh" <<'PROBE'
import json, subprocess, sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    marker = root / 'investigate-gate.json'
    for contents in (None, '{broken', '{"findings": []}'):
        if contents is not None:
            marker.write_text(contents)
        before = {p.name: p.read_bytes() for p in root.iterdir()}
        result = subprocess.run(['bash', sys.argv[1]], input=json.dumps({'cwd': folder}),
                                text=True, capture_output=True, cwd=root, timeout=10)
        assert result.returncode == 0 and not result.stdout and not result.stderr, result
        assert {p.name: p.read_bytes() for p in root.iterdir()} == before
print('Legacy investigation callback: 3 optional-evidence cases passed; no writes or blocking output.')
PROBE
