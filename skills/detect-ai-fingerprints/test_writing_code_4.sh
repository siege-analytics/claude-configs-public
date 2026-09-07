#!/bin/bash
# Test: writing-code:4 detector — Django ORM kwarg validation (#771 m-1)
#
# Same-file model resolution: kwargs to filter/get/create/update etc must be
# declared field names on the model. Unknown kwargs fire. Cross-file model
# calls are silently skipped.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCAN="$SCRIPT_DIR/scan_ast.py"

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); FAILED+=("$1"); printf '  [FAIL] %s\n' "$1"; printf '         %s\n' "$2"; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

fires_wc4() {
    echo "$1" | grep -q "writing-code-4"
}

# (a) filter kwarg matches declared field — silent
cat > "$TMP/a.py" <<'EOF'
from django.db import models
class Widget(models.Model):
    name = models.CharField(max_length=32)
    active = models.BooleanField()

def go():
    Widget.objects.filter(name="x", active=True)
EOF
OUT=$(python3 "$SCAN" "$TMP/a.py" 2>&1)
if ! fires_wc4 "$OUT"; then
    ok "(a) filter with declared fields — silent"
else
    bad "(a) declared fields false-fire" "out=$OUT"
fi

# (b) filter kwarg on undeclared field — fires
cat > "$TMP/b.py" <<'EOF'
from django.db import models
class Widget(models.Model):
    name = models.CharField(max_length=32)

def go():
    Widget.objects.filter(nonexistent_field="x")
EOF
OUT=$(python3 "$SCAN" "$TMP/b.py" 2>&1)
if fires_wc4 "$OUT"; then
    ok "(b) unknown kwarg — fires"
else
    bad "(b) unknown kwarg" "out=$OUT"
fi

# (c) get with lookup suffix — silent (field__gt decomposes to field)
cat > "$TMP/c.py" <<'EOF'
from django.db import models
class Widget(models.Model):
    count = models.IntegerField()

def go():
    Widget.objects.filter(count__gt=5, count__lt=100)
EOF
OUT=$(python3 "$SCAN" "$TMP/c.py" 2>&1)
if ! fires_wc4 "$OUT"; then
    ok "(c) declared field with lookup suffix — silent"
else
    bad "(c) lookup suffix" "out=$OUT"
fi

# (d) get_or_create defaults={} with unknown key — fires
cat > "$TMP/d.py" <<'EOF'
from django.db import models
class Widget(models.Model):
    name = models.CharField(max_length=32)

def go():
    Widget.objects.get_or_create(name="x", defaults={"nonexistent": True})
EOF
OUT=$(python3 "$SCAN" "$TMP/d.py" 2>&1)
if fires_wc4 "$OUT"; then
    ok "(d) get_or_create defaults with unknown field — fires"
else
    bad "(d) defaults unknown" "out=$OUT"
fi

# (e) non-field kwargs like 'using' — silent (in _NON_FIELD_KWARGS)
cat > "$TMP/e.py" <<'EOF'
from django.db import models
class Widget(models.Model):
    name = models.CharField(max_length=32)

def go():
    Widget.objects.filter(name="x", using="other_db")
EOF
OUT=$(python3 "$SCAN" "$TMP/e.py" 2>&1)
if ! fires_wc4 "$OUT"; then
    ok "(e) 'using' non-field kwarg — silent"
else
    bad "(e) using kwarg" "out=$OUT"
fi

# (f) cross-file model — silent (model not defined here)
cat > "$TMP/f.py" <<'EOF'
def go():
    from other_app.models import Widget
    Widget.objects.filter(anything_at_all="x")
EOF
OUT=$(python3 "$SCAN" "$TMP/f.py" 2>&1)
if ! fires_wc4 "$OUT"; then
    ok "(f) cross-file model — silent (v1 scope)"
else
    bad "(f) cross-file false fire" "out=$OUT"
fi

# (g) non-django class — silent (not a Model subclass)
cat > "$TMP/g.py" <<'EOF'
class Foo:
    def do(self):
        return self.filter(bogus_kwarg=1)

def go():
    Foo().do()
EOF
OUT=$(python3 "$SCAN" "$TMP/g.py" 2>&1)
if ! fires_wc4 "$OUT"; then
    ok "(g) non-Django class .filter() call — silent"
else
    bad "(g) non-Django class" "out=$OUT"
fi

# (h) create with unknown kwarg — fires
cat > "$TMP/h.py" <<'EOF'
from django.db import models
class Widget(models.Model):
    name = models.CharField(max_length=32)

def go():
    Widget.objects.create(name="x", bogus=1)
EOF
OUT=$(python3 "$SCAN" "$TMP/h.py" 2>&1)
if fires_wc4 "$OUT"; then
    ok "(h) create with unknown kwarg — fires"
else
    bad "(h) create unknown" "out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
