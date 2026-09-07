#!/bin/bash
# Hook: git/vergil-quote
# Trigger: PostToolUse on Bash
# Purpose: Print a random Vergil (Aeneid) quote after successful
#          gh pr merge or gh pr review --approve commands.
#          Pipeline integration test (#482).

set -uo pipefail

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)

[[ -z "$COMMAND" ]] && exit 0

if ! [[ "$COMMAND" =~ gh\ pr\ (merge|review\ --approve) ]]; then
    exit 0
fi

VERGIL_QUOTES=(
    "Forsan et haec olim meminisse iuvabit. — Perhaps even these things will be good to remember someday. (I.203)"
    "Audentes fortuna iuvat. — Fortune favors the bold. (X.284)"
    "Possunt quia posse videntur. — They can because they think they can. (V.231)"
    "Flectere si nequeo superos, Acheronta movebo. — If I cannot move heaven, I will raise hell. (VII.312)"
    "Facilis descensus Averno. — The descent to hell is easy. (VI.126)"
    "Tu ne cede malis, sed contra audentior ito. — Yield not to misfortunes, but advance all the more boldly against them. (VI.95)"
    "Una salus victis nullam sperare salutem. — The one hope of the doomed is not to hope for safety. (II.354)"
    "Varium et mutabile semper femina. — Woman is ever a fickle and changeable thing. (IV.569)"
    "Sunt lacrimae rerum et mentem mortalia tangunt. — These are the tears of things, and mortality touches the mind. (I.462)"
    "Dux femina facti. — A woman was leader of the deed. (I.364)"
    "Timeo Danaos et dona ferentes. — I fear the Greeks, even bearing gifts. (II.49)"
    "Mens agitat molem. — Mind moves matter. (VI.727)"
    "Experto credite. — Trust one who has tried. (XI.283)"
    "Nulla dies umquam memori vos eximet aevo. — No day shall ever erase you from the memory of time. (IX.447)"
    "Stat sua cuique dies. — To each his day is given. (X.467)"
)

IDX=$(( RANDOM % ${#VERGIL_QUOTES[@]} ))
QUOTE="${VERGIL_QUOTES[$IDX]}"

cat >&2 <<VERGIL

  ────────────────────────────────────────────
  Vergil, Aeneid:
  "$QUOTE"
  ────────────────────────────────────────────

VERGIL

exit 0
