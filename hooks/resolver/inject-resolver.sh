#!/bin/bash
# UserPromptSubmit hook: inject the compact kernel and a deterministic task/project load set.
set -euo pipefail
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
CANONICAL_KERNEL="$REPO_ROOT/skills/KERNEL.md"
KERNEL="${CLAUDE_KERNEL_PATH:-$CANONICAL_KERNEL}"
SELECTOR="$REPO_ROOT/bin/resolve-load-set.py"
block_invalid_kernel() {
  printf '%s\n' '{"continue":false,"systemMessage":"BLOCKED: mandatory compact safety kernel is unavailable or invalid; restore the canonical KERNEL.md before continuing."}'
  exit 0
}
# A caller-controlled path may be useful for packaging tests, but it must not
# change the invariant policy surface. Accept only byte-identical kernel
# content within the source-bound budget; never treat arbitrary content as the
# kernel merely because an environment variable points to it.
[[ -f "$CANONICAL_KERNEL" && -f "$KERNEL" ]] || block_invalid_kernel
[[ "$(wc -c < "$KERNEL" | tr -d ' ')" -le 80000 ]] || block_invalid_kernel
cmp -s "$CANONICAL_KERNEL" "$KERNEL" || block_invalid_kernel
PAYLOAD="$(cat || true)"
# Buffer the complete delivery, including optional plan warnings, before stdout.
# Keep the original descriptor available for a sole structured failure response.
exec 8>&1
block_delivery() {
  printf '%s\n' '{"continue":false,"systemMessage":"BLOCKED: complete mandatory policy cannot be delivered within the declared delivery byte limit; restore compact canonical KERNEL.md and writable temporary storage."}' >&8
  exit 0
}
DELIVERY_FILE="$(mktemp "${TMPDIR:-/tmp}/craft-hook-output.XXXXXX" 2>/dev/null)" ||
  DELIVERY_FILE="$(mktemp /tmp/craft-hook-output.XXXXXX 2>/dev/null)" || block_delivery
trap 'rm -f -- "$DELIVERY_FILE"' EXIT
trap 'block_delivery' ERR
COMPOSED_ENVELOPE=0
{
MODE="${CLAUDE_PROGRESSIVE_LOADING:-on}"
if [[ "$MODE" == "off" || "$MODE" == "kernel-only" ]]; then
  cat <<EOF
<skill-kernel mode="kernel-only">
$(cat "$KERNEL")
</skill-kernel>
<progressive-load-set>
state: disabled
project: none
diagnostic: selector disabled by canary control; kernel only
</progressive-load-set>
EOF
elif [[ ! -x "$(command -v python3 || true)" || ! -f "$SELECTOR" ]]; then
  cat <<EOF
<skill-kernel mode="$MODE">
$(cat "$KERNEL")
</skill-kernel>
<progressive-loading-warning>Selector unavailable; kernel-only mode. No broad fallback was loaded.</progressive-loading-warning>
EOF
else
  RENDER_MODE="on"
  [[ "$MODE" != "canary" ]] || RENDER_MODE="canary"
  # One interpreter per prompt: the selector reads prompt and cwd from the
  # payload itself. Interpreter startup dominates this hook's latency (#1064).
  if RESULT="$(printf '%s' "$PAYLOAD" | python3 "$SELECTOR" --payload-stdin --render-hook --mode "$RENDER_MODE" 2>/dev/null)"; then
    # This leading envelope is emitted only after resident identity/bytes validate.
    if [[ "$RESULT" == '<project-resident>'$'\n'* ]]; then COMPOSED_ENVELOPE=1; fi
  else
    RESULT=""
  fi
  cat <<EOF
<skill-kernel mode="$MODE">
$(cat "$KERNEL")
</skill-kernel>
EOF
  if [[ -n "$RESULT" ]]; then
    printf '%s\n' "$RESULT"
  else
    printf '%s\n' '<progressive-load-set>' 'state: error' 'diagnostic: selector unavailable; kernel only' '</progressive-load-set>'
  fi
fi

# Preparation notes are optional task context, not prompt-time edit prerequisites.

} > "$DELIVERY_FILE"
DELIVERY_BYTES="$(LC_ALL=C wc -c < "$DELIVERY_FILE")"
DELIVERY_LIMIT=10000
# The checked composed resident has an existing 80000-byte budget of its own.
if [[ "$COMPOSED_ENVELOPE" == 1 ]]; then DELIVERY_LIMIT=$((10000 + 80000)); fi
if [[ "$DELIVERY_BYTES" -ge "$DELIVERY_LIMIT" ]]; then
  # Required composed context must never be silently replaced by generic policy.
  if [[ "$COMPOSED_ENVELOPE" == 1 ]]; then block_delivery; fi
  {
    printf '%s\n' '<skill-kernel mode="kernel-only">'
    cat "$CANONICAL_KERNEL"
    printf '%s\n' '</skill-kernel>' '<progressive-load-set>' 'state: over-budget' 'project: none' 'diagnostic: final hook output exceeds inline byte limit; kernel only' '</progressive-load-set>'
  } > "$DELIVERY_FILE"
  DELIVERY_BYTES="$(LC_ALL=C wc -c < "$DELIVERY_FILE")"
  [[ "$DELIVERY_BYTES" -lt 10000 ]] || block_delivery
fi
# The decision is complete: never append structured failure output after publish.
trap - ERR
cat "$DELIVERY_FILE"
