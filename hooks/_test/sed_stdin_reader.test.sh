#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$ROOT/hooks/_test/sed_stdin_reader.py"
