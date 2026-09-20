#!/usr/bin/env bash
# Reproducible screenshot capture for the public page.
#
# Requires the local Hello Weather stack running (Vite dev server on :5173,
# API on :8000) with a synced climate archive, plus Chrome and cwebp.
#
# Usage: tools/capture.sh
#
# Why mobile captures go through an iframe: Chrome on macOS refuses to make a
# window narrower than 500 CSS px, so `--window-size=390,844` yields a 500px
# viewport and the application's `max-width: 480px` rules never apply -- the
# result is a desktop layout cropped to phone size. Rendering the app inside a
# 390px iframe gives it a genuine 390px viewport, and the shot is then cropped
# back to the iframe's box.
set -Eeuo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CWEBP="${CWEBP:-cwebp}"
BASE="${BASE:-http://localhost:5173}"
OUT="$(cd "$(dirname "$0")/.." && pwd)/assets/shots"
TOOLS="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$OUT"

report() {
  TOOLS="$TOOLS" python3 - "$1" <<'PYDIM'
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ["TOOLS"])
from check_page import webp_size  # noqa: E402

path = Path(sys.argv[1])
print("%s %dx%d" % (path.name, *webp_size(path.read_bytes())))
PYDIM
}

# Desktop: the viewport is wider than Chrome's 500px floor, so shoot directly.
shoot_desktop() {
  local name="$1" route="$2" width="$3" height="$4"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size="${width},${height}" \
    --virtual-time-budget=15000 \
    --screenshot="$TMP/$name.png" \
    "$BASE/$route" 2>/dev/null
  "$CWEBP" -q 82 -quiet "$TMP/$name.png" -o "$OUT/$name.webp"
  report "$OUT/$name.webp"
}

# Mobile: render inside an iframe of the target size, then crop to it.
shoot_mobile() {
  local name="$1" route="$2" width="$3" height="$4"
  cat > "$TMP/$name.html" <<HTML
<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;padding:0;background:#fff}
iframe{width:${width}px;height:${height}px;border:0;display:block}
</style></head><body>
<iframe src="${BASE}/${route}" title="app"></iframe>
</body></html>
HTML
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size="$((width + 210)),$((height + 60))" \
    --virtual-time-budget=15000 \
    --screenshot="$TMP/$name.png" \
    "file://$TMP/$name.html" 2>/dev/null
  "$CWEBP" -q 82 -quiet -crop 0 0 "$width" "$height" \
    "$TMP/$name.png" -o "$OUT/$name.webp"
  report "$OUT/$name.webp"
}

shoot_desktop dashboard-desktop '#/'                  1440 900
shoot_desktop history-desktop   '#/history?range=7d'  1440 900
shoot_desktop climate-desktop   '#/climate'           1440 900
shoot_mobile  dashboard-mobile  '#/'                  390  844
shoot_mobile  history-mobile    '#/history?range=7d'  390  844
shoot_mobile  climate-mobile    '#/climate'           390  844

echo "Captured into $OUT"
