#!/bin/bash
# Test: writing-code:8 detector in scan_ast.py (#57)

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

# (a) unguarded callsite: fires
cat > "$TMP/a.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    return shapely.geometry.Polygon(coords)
EOF
# Isolate writing-code:8 by grepping specifically for that rule token.
# Other rules (writing-tests-5, writing-code-7) may also fire on these
# fixtures — those are covered by their own test suites; we only care
# whether writing-code-8 fires or stays silent here.

fires_wc8() {
    echo "$1" | grep -q "writing-code-8"
}

OUT=$(python3 "$SCAN" "$TMP/a.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(a) unguarded callsite: writing-code-8 fires"
else
    bad "(a) unguarded callsite" "out=$OUT"
fi

# (b) early-return guard: no fire
cat > "$TMP/b.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    if not SHAPELY_AVAILABLE:
        raise RuntimeError("required")
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/b.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(b) early-return guard: writing-code-8 silent"
else
    bad "(b) early-return guard" "out=$OUT"
fi

# (c) if-body-guard: no fire
cat > "$TMP/c.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    if SHAPELY_AVAILABLE:
        return shapely.geometry.Polygon(coords)
    return None
EOF
OUT=$(python3 "$SCAN" "$TMP/c.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(c) if-body-guard: writing-code-8 silent"
else
    bad "(c) if-body-guard" "out=$OUT"
fi

# (d) inside try body: no fire (flag can't be False in the try that set it)
cat > "$TMP/d.py" <<'EOF'
try:
    import shapely
    _ = shapely.geometry.Polygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
EOF
OUT=$(python3 "$SCAN" "$TMP/d.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(d) inside try body: writing-code-8 silent"
else
    bad "(d) inside try body" "out=$OUT"
fi

# (e) private helper documents flag: no fire
cat > "$TMP/e.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def _make_polygon_impl(coords):
    """Caller must check SHAPELY_AVAILABLE before calling."""
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/e.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(e) private helper documents flag: writing-code-8 silent"
else
    bad "(e) private helper documents flag" "out=$OUT"
fi

# (f) no optional-import pattern present: no fire (the file just imports shapely regularly)
cat > "$TMP/f.py" <<'EOF'
import shapely

def make_polygon(coords):
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/f.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(f) no optional-import pattern: writing-code-8 silent"
else
    bad "(f) no optional-import" "out=$OUT"
fi

# --- Codex hostile-review F2-F5 lock-in fixtures (issue #760) ---

# (g) F2: use INSIDE `if not FLAG:` body -- that IS the unavailable branch, must fire
cat > "$TMP/g.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    if not SHAPELY_AVAILABLE:
        return shapely.geometry.Polygon(coords)
    return None
EOF
OUT=$(python3 "$SCAN" "$TMP/g.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(g) F2 use inside 'if not FLAG:' body: writing-code-8 fires"
else
    bad "(g) F2 use inside 'if not FLAG:' body" "out=$OUT"
fi

# (h) F3: `if FLAG: return` followed by use -- fallthrough means FLAG false, must fire
cat > "$TMP/h.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    if SHAPELY_AVAILABLE:
        return None
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/h.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(h) F3 positive-early-return doesn't establish truthy: writing-code-8 fires"
else
    bad "(h) F3 positive early return" "out=$OUT"
fi

# (i) F4: compound `if FLAG and other: return` doesn't prove FLAG, must fire
cat > "$TMP/i.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords, other):
    if SHAPELY_AVAILABLE and other:
        return None
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/i.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(i) F4 compound test doesn't establish truthy: writing-code-8 fires"
else
    bad "(i) F4 compound establish" "out=$OUT"
fi

# (j) F5: private helper docstring mentions flag but no caller-contract phrase, must fire
cat > "$TMP/j.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def _make_polygon_impl(coords):
    """SHAPELY_AVAILABLE is a module-level flag."""
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/j.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(j) F5 private helper bare flag mention: writing-code-8 fires"
else
    bad "(j) F5 bare docstring mention" "out=$OUT"
fi

# (k) F5 counterpart: docstring names flag AND has caller-contract phrase, silent
cat > "$TMP/k.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def _make_polygon_impl(coords):
    """Caller must check SHAPELY_AVAILABLE before invoking."""
    return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/k.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(k) F5 private helper w/ caller-contract phrase: writing-code-8 silent"
else
    bad "(k) F5 with caller contract" "out=$OUT"
fi

# (l) F2 counterpart: else-branch of `if not FLAG:` IS guarded (flag truthy there)
cat > "$TMP/l.py" <<'EOF'
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def make_polygon(coords):
    if not SHAPELY_AVAILABLE:
        return None
    else:
        return shapely.geometry.Polygon(coords)
EOF
OUT=$(python3 "$SCAN" "$TMP/l.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(l) F2 counterpart else-branch of 'if not FLAG:': writing-code-8 silent"
else
    bad "(l) F2 counterpart else-branch" "out=$OUT"
fi

# --- R5-F1 (#802) lock-in: multi-import + multi-flag in one try block ---

# (m) R5-F1: two imports + two flags, both correctly guarded — silent
cat > "$TMP/m.py" <<'EOF'
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    GEOPANDAS_AVAILABLE = False

def use_pd():
    if not PANDAS_AVAILABLE:
        raise RuntimeError("install pandas")
    return pd.DataFrame()

def use_gpd():
    if not GEOPANDAS_AVAILABLE:
        raise RuntimeError("install geopandas")
    return gpd.GeoDataFrame()
EOF
OUT=$(python3 "$SCAN" "$TMP/m.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(m) R5-F1 two imports two flags both guarded: silent"
else
    bad "(m) R5-F1 two-import mis-mapping" "out=$OUT"
fi

# (n) R5-F1: two imports two flags, pd guarded but gpd unguarded — only gpd fires
cat > "$TMP/n.py" <<'EOF'
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    GEOPANDAS_AVAILABLE = False

def use_pd():
    if not PANDAS_AVAILABLE:
        raise RuntimeError("install pandas")
    return pd.DataFrame()

def use_gpd():
    return gpd.GeoDataFrame()
EOF
OUT=$(python3 "$SCAN" "$TMP/n.py" 2>&1)
if echo "$OUT" | grep -q "writing-code-8" && echo "$OUT" | grep -q "gpd" && ! echo "$OUT" | grep -q "'pd'"; then
    ok "(n) R5-F1 pd guarded, gpd unguarded: only gpd fires"
else
    bad "(n) R5-F1 selective firing" "out=$OUT"
fi

# --- R6-F1 (#804) lock-in: grouped-imports-then-flags shape ---

# (o) R6-F1: grouped imports+flags, correctly guarded — silent
cat > "$TMP/o.py" <<'EOF'
try:
    import pandas
    import geopandas
    PANDAS_AVAILABLE = True
    GEOPANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    GEOPANDAS_AVAILABLE = False

def use_gpd():
    if not GEOPANDAS_AVAILABLE:
        raise RuntimeError("gpd")
    return geopandas.GeoDataFrame()
EOF
OUT=$(python3 "$SCAN" "$TMP/o.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(o) R6-F1 grouped imports+flags correctly guarded: silent"
else
    bad "(o) R6-F1 grouped correct" "out=$OUT"
fi

# (p) R6-F1: grouped imports+flags, guarded with WRONG flag — fires on truly-unguarded name with correct suggested flag
cat > "$TMP/p.py" <<'EOF'
try:
    import pandas
    import geopandas
    PANDAS_AVAILABLE = True
    GEOPANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    GEOPANDAS_AVAILABLE = False

def use_gpd():
    if not PANDAS_AVAILABLE:
        raise RuntimeError("wrong flag")
    return geopandas.GeoDataFrame()
EOF
OUT=$(python3 "$SCAN" "$TMP/p.py" 2>&1)
# Should fire on geopandas + suggest GEOPANDAS_AVAILABLE (not PANDAS_AVAILABLE)
if fires_wc8 "$OUT" && echo "$OUT" | grep -q "geopandas" && echo "$OUT" | grep -q "GEOPANDAS_AVAILABLE"; then
    ok "(p) R6-F1 grouped wrong-flag: fires on geopandas with correct GEOPANDAS_AVAILABLE suggestion"
else
    bad "(p) R6-F1 grouped wrong-flag" "out=$OUT"
fi

# (q) R6-F1: 3 imports + 3 flags grouped
cat > "$TMP/q.py" <<'EOF'
try:
    import shapely
    import fiona
    import rasterio
    SHAPELY_AVAILABLE = True
    FIONA_AVAILABLE = True
    RASTERIO_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    FIONA_AVAILABLE = False
    RASTERIO_AVAILABLE = False

def use_shp():
    if not SHAPELY_AVAILABLE:
        raise RuntimeError("shp")
    return shapely.geometry.Polygon()

def use_f():
    if not FIONA_AVAILABLE:
        raise RuntimeError("f")
    return fiona.open("x")

def use_r():
    if not RASTERIO_AVAILABLE:
        raise RuntimeError("r")
    return rasterio.open("x")
EOF
OUT=$(python3 "$SCAN" "$TMP/q.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(q) R6-F1 3+3 grouped all correctly guarded: silent"
else
    bad "(q) R6-F1 3+3 grouped" "out=$OUT"
fi

# (r) R6-F1: positional-fallback case — aliases whose stems don't match
cat > "$TMP/r.py" <<'EOF'
try:
    import pandas as pd
    import geopandas as gpd
    PANDAS_AVAILABLE = True
    GEOPANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    GEOPANDAS_AVAILABLE = False

def use_pd():
    if not PANDAS_AVAILABLE:
        raise RuntimeError("pd")
    return pd.DataFrame()

def use_gpd():
    if not GEOPANDAS_AVAILABLE:
        raise RuntimeError("gpd")
    return gpd.GeoDataFrame()
EOF
OUT=$(python3 "$SCAN" "$TMP/r.py" 2>&1)
# `pd` doesn't match PANDAS_AVAILABLE by whole-word; `gpd` doesn't match either.
# Positional fallback pairs pd -> PANDAS_AVAILABLE, gpd -> GEOPANDAS_AVAILABLE.
if ! fires_wc8 "$OUT"; then
    ok "(r) R6-F1 aliased imports positional fallback: silent"
else
    bad "(r) R6-F1 positional fallback" "out=$OUT"
fi

# --- R7-F1 (#806) lock-in: reversed flag order + underscore-aware stem match ---

# (s) R7-F1: flags declared in REVERSED order relative to imports
cat > "$TMP/s.py" <<'EOF'
try:
    import pandas
    import geopandas
    GEOPANDAS_AVAILABLE = True
    PANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    PANDAS_AVAILABLE = False

def use_pd():
    if not PANDAS_AVAILABLE:
        raise RuntimeError("pd")
    return pandas.DataFrame()

def use_gpd():
    if not GEOPANDAS_AVAILABLE:
        raise RuntimeError("gpd")
    return geopandas.GeoDataFrame()
EOF
OUT=$(python3 "$SCAN" "$TMP/s.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(s) R7-F1 reversed flag order correctly stem-paired: silent"
else
    bad "(s) R7-F1 reversed flag order" "out=$OUT"
fi

# (t) R7-F1: numpy + numpy_financial with matching flags
cat > "$TMP/t.py" <<'EOF'
try:
    import numpy
    import numpy_financial
    NUMPY_AVAILABLE = True
    NUMPY_FINANCIAL_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    NUMPY_FINANCIAL_AVAILABLE = False

def use_np():
    if not NUMPY_AVAILABLE:
        raise RuntimeError("np")
    return numpy.array([])

def use_npf():
    if not NUMPY_FINANCIAL_AVAILABLE:
        raise RuntimeError("npf")
    return numpy_financial.rate(1, 2, 3, 4)
EOF
OUT=$(python3 "$SCAN" "$TMP/t.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(t) R7-F1 numpy + numpy_financial correctly stem-paired: silent"
else
    bad "(t) R7-F1 numpy family" "out=$OUT"
fi

# --- R7-F2 (#806) lock-in: single-flag stem-mismatch fails open ---

# (u) R7-F2: import re + MRE_AVAILABLE (single flag doesn't stem-match import)
cat > "$TMP/u.py" <<'EOF'
try:
    import re
    MRE_AVAILABLE = True
except ImportError:
    MRE_AVAILABLE = False

def compile_pat(pat):
    return re.compile(pat)
EOF
OUT=$(python3 "$SCAN" "$TMP/u.py" 2>&1)
# Should fail open with scan-ast-warning; no writing-code:8 emission
if ! fires_wc8 "$OUT" && echo "$OUT" | grep -q "scan-ast-warning"; then
    ok "(u) R7-F2 single-flag stem-mismatch fails open + warns: silent + warning"
else
    bad "(u) R7-F2 single-flag mismatch" "out=$OUT"
fi

# --- R8 (#808) lock-in: source_module-based pairing for aliased + from-imports ---

# (v) R8-F1: `import numpy as np` + NUMPY_AVAILABLE unguarded -- fires
cat > "$TMP/v.py" <<'EOF'
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

arr = np.array([1, 2, 3])
EOF
OUT=$(python3 "$SCAN" "$TMP/v.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(v) R8-F1 numpy as np unguarded: fires"
else
    bad "(v) R8-F1 aliased" "out=$OUT"
fi

# (w) R8-F1 counterpart: `import numpy as np` + NUMPY_AVAILABLE guarded -- silent
cat > "$TMP/w.py" <<'EOF'
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

def go():
    if not NUMPY_AVAILABLE:
        raise RuntimeError("numpy")
    return np.array([1, 2, 3])
EOF
OUT=$(python3 "$SCAN" "$TMP/w.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(w) R8-F1 numpy as np guarded: silent"
else
    bad "(w) R8-F1 aliased guarded" "out=$OUT"
fi

# (x) R8-F2: `from PIL import Image` + PIL_AVAILABLE unguarded -- fires
cat > "$TMP/x.py" <<'EOF'
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

img = Image.new("RGB", (1, 1))
EOF
OUT=$(python3 "$SCAN" "$TMP/x.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(x) R8-F2 from PIL import Image unguarded: fires"
else
    bad "(x) R8-F2 from-import" "out=$OUT"
fi

# (y) R8-F2 counterpart: `from PIL import Image` + PIL_AVAILABLE guarded -- silent
cat > "$TMP/y.py" <<'EOF'
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def open_img():
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL")
    return Image.new("RGB", (1, 1))
EOF
OUT=$(python3 "$SCAN" "$TMP/y.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(y) R8-F2 from PIL import Image guarded: silent"
else
    bad "(y) R8-F2 from-import guarded" "out=$OUT"
fi

# (z) R8-F3: `from lxml import etree as _et` + LXML_AVAILABLE guarded -- silent
cat > "$TMP/z2.py" <<'EOF'
try:
    from lxml import etree as _et
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

def parse(s):
    if not LXML_AVAILABLE:
        raise RuntimeError("lxml")
    return _et.fromstring(s)
EOF
OUT=$(python3 "$SCAN" "$TMP/z2.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(z2) R8-F3 from lxml import etree as _et guarded: silent"
else
    bad "(z2) R8-F3 asname from-import" "out=$OUT"
fi

# --- R9 (#810) lock-in: dotted source + source-group binding + gated positional fallback ---

# (z3) R9-F1: `from foo.bar import baz` + FOO_BAR_AVAILABLE unguarded -- fires
cat > "$TMP/z3.py" <<'EOF'
try:
    from foo.bar import baz
    FOO_BAR_AVAILABLE = True
except ImportError:
    FOO_BAR_AVAILABLE = False

def use_baz():
    return baz()
EOF
OUT=$(python3 "$SCAN" "$TMP/z3.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(z3) R9-F1 dotted source from foo.bar import baz: fires"
else
    bad "(z3) R9-F1 dotted source" "out=$OUT"
fi

# (z4) R9-F2: `import numpy; import numpy as np` + NUMPY_AVAILABLE, np unguarded -- fires on np
cat > "$TMP/z4.py" <<'EOF'
try:
    import numpy
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

def use_np():
    return np.array([])
EOF
OUT=$(python3 "$SCAN" "$TMP/z4.py" 2>&1)
if fires_wc8 "$OUT"; then
    ok "(z4) R9-F2 source-group both bind to NUMPY_AVAILABLE: np fires"
else
    bad "(z4) R9-F2 source-group" "out=$OUT"
fi

# (z5) R9-F3: no-stem-match with correct guards -- fails open, no wrong-flag suggestion
cat > "$TMP/z5.py" <<'EOF'
try:
    import numpy
    import pandas
    DATAFRAME_AVAILABLE = True
    ARRAY_AVAILABLE = True
except ImportError:
    DATAFRAME_AVAILABLE = False
    ARRAY_AVAILABLE = False

def use_np():
    if not ARRAY_AVAILABLE:
        raise RuntimeError("array")
    return numpy.array([])

def use_pd():
    if not DATAFRAME_AVAILABLE:
        raise RuntimeError("dataframe")
    return pandas.DataFrame()
EOF
OUT=$(python3 "$SCAN" "$TMP/z5.py" 2>&1)
if ! fires_wc8 "$OUT" && echo "$OUT" | grep -q "scan-ast-warning"; then
    ok "(z5) R9-F3 no-stem-match fails open with warning: silent"
else
    bad "(z5) R9-F3 no-stem-match" "out=$OUT"
fi

# --- PR D / #827 R11 INVALIDATING shape repairs ---

# (z6) I1: flag assigned in try/except/else must be detected; unguarded use fires
cat > "$TMP/z6.py" <<'EOF'
try:
    import numpy as np
except ImportError:
    np = None
    NUMPY_AVAILABLE = False
else:
    NUMPY_AVAILABLE = True

def arr():
    return np.array([1, 2, 3])
EOF
OUT=$(python3 "$SCAN" "$TMP/z6.py" 2>&1)
if fires_wc8 "$OUT" && echo "$OUT" | grep -q "np" && echo "$OUT" | grep -q "NUMPY_AVAILABLE"; then
    ok "(z6) #827 I1 try/except/else flag assignment: unguarded use fires"
else
    bad "(z6) #827 I1 else-clause flag" "out=$OUT"
fi

# (z7) I2: dotted-source prefix flag must pair matplotlib.pyplot -> MATPLOTLIB_AVAILABLE
cat > "$TMP/z7.py" <<'EOF'
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

def draw():
    return plt.figure()
EOF
OUT=$(python3 "$SCAN" "$TMP/z7.py" 2>&1)
if fires_wc8 "$OUT" && echo "$OUT" | grep -q "plt" && echo "$OUT" | grep -q "MATPLOTLIB_AVAILABLE"; then
    ok "(z7) #827 I2 matplotlib.pyplot prefix flag: unguarded use fires"
else
    bad "(z7) #827 I2 dotted-source prefix" "out=$OUT"
fi

# (z8) I3: one PYSPARK_AVAILABLE flag covers multiple PySpark imports; unguarded function import fires
cat > "$TMP/z8.py" <<'EOF'
try:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import udf, pandas_udf, col
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False

def make_udf():
    return udf(lambda x: x)
EOF
OUT=$(python3 "$SCAN" "$TMP/z8.py" 2>&1)
if fires_wc8 "$OUT" && echo "$OUT" | grep -q "udf" && echo "$OUT" | grep -q "PYSPARK_AVAILABLE"; then
    ok "(z8) #827 I3 one-flag/N-import PySpark: unguarded use fires"
else
    bad "(z8) #827 I3 one-flag N-import" "out=$OUT"
fi

# (z9) I1/I2/I3 guarded counterparts are silent.
cat > "$TMP/z9.py" <<'EOF'
try:
    import matplotlib.pyplot as plt
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import udf, pandas_udf, col
    MATPLOTLIB_AVAILABLE = True
    PYSPARK_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    PYSPARK_AVAILABLE = False

def draw():
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError("matplotlib")
    return plt.figure()

def make_udf():
    if not PYSPARK_AVAILABLE:
        raise RuntimeError("pyspark")
    return udf(lambda x: x)
EOF
OUT=$(python3 "$SCAN" "$TMP/z9.py" 2>&1)
if ! fires_wc8 "$OUT"; then
    ok "(z9) #827 guarded dotted-prefix and one-flag/N-import counterparts: silent"
else
    bad "(z9) #827 guarded counterparts" "out=$OUT"
fi

echo
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    for n in "${FAILED[@]}"; do printf '  - %s\n' "$n"; done
    exit 1
fi
exit 0
