#!/usr/bin/env bash
# Reproducible full-page screenshot capture for the public page.
#
# Point BASE at a running Hello Weather instance that serves both the API and
# the UI on one origin, and has a synced climate archive:
#
#   BASE=http://<host>:<port> CWEBP=/opt/homebrew/bin/cwebp tools/capture.sh
#
# These are dashboards, so every shot is the whole page, not the first
# viewport. Chrome only ever screenshots its viewport, so each page is
# rendered into a deliberately over-tall window and then cropped back to where
# the content actually ends -- tools/content_height.py finds that line by
# scanning up from the bottom for the first row that is not flat background.
#
# Mobile shots additionally render the app inside a 390px iframe. Chrome on
# macOS will not make a window narrower than 500 CSS px, so --window-size=390
# silently yields a 500px viewport, the app's max-width:480px rules never
# apply, and the result is a desktop layout cropped to phone size.
set -Eeuo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CWEBP="${CWEBP:-cwebp}"
BASE="${BASE:-http://localhost:5173}"
DESKTOP_W=1440
MOBILE_W=390
TALL_DESKTOP=9000
TALL_MOBILE=12000
QUALITY=80
# Optional tag appended to every output name, e.g. SUFFIX=-sunny.
SUFFIX="${SUFFIX:-}"
WAIT_MS=20000

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$HERE/.." && pwd)/assets/shots"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT"

echo "Capturing from $BASE"

crop_and_report() {
  local name="$1" width="$2" height="$3" tall="$4"
  if [ "$height" -ge "$((tall - 2))" ]; then
    echo "WARNING: $name filled the ${tall}px render window -- it is probably" \
         "clipped. Raise TALL_* and re-run." >&2
  fi
  "$CWEBP" -q "$QUALITY" -quiet -crop 0 0 "$width" "$height" \
    "$TMP/$name.png" -o "$OUT/${name}${SUFFIX}.webp"
  echo "${name}${SUFFIX}.webp ${width}x${height}"
}

shoot_desktop() {
  local name="$1" route="$2"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size="${DESKTOP_W},${TALL_DESKTOP}" \
    --virtual-time-budget="$WAIT_MS" \
    --screenshot="$TMP/$name.png" "$BASE/$route" 2>/dev/null
  local h
  h="$(python3 "$HERE/content_height.py" "$TMP/$name.png")"
  crop_and_report "$name" "$DESKTOP_W" "$h" "$TALL_DESKTOP"
}

shoot_mobile() {
  local name="$1" route="$2"
  cat > "$TMP/$name.html" <<HTML
<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;padding:0;background:#fff}
iframe{width:${MOBILE_W}px;height:${TALL_MOBILE}px;border:0;display:block}
</style></head><body>
<iframe src="${BASE}/${route}" title="app"></iframe>
</body></html>
HTML
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size="$((MOBILE_W + 260)),${TALL_MOBILE}" \
    --virtual-time-budget="$WAIT_MS" \
    --screenshot="$TMP/$name.png" "file://$TMP/$name.html" 2>/dev/null
  local h
  # Scan only the iframe's columns; the white wrapper beside it is not content.
  h="$(python3 "$HERE/content_height.py" "$TMP/$name.png" --width "$MOBILE_W")"
  crop_and_report "$name" "$MOBILE_W" "$h" "$TALL_MOBILE"
}

# The application picks light or dark from the weather code and daylight, not
# from the reader's operating system, so the dark capture can only be taken
# while the instance is actually rendering a night scheme. Check first:
#   curl -s "$BASE/api/weather" | python3 -c \
#     "import json,sys;print(json.load(sys.stdin)['current']['is_day'])"
# and run `tools/capture.sh dark` once that prints False.
if [ "${1:-}" = "dark" ]; then
  shoot_desktop climate-desktop-dark '#/climate'
  echo "Captured into $OUT"
  exit 0
fi

shoot_desktop dashboard-desktop '#/'
shoot_desktop history-desktop   '#/history?range=7d'
shoot_desktop climate-desktop   '#/climate'

# `tools/capture.sh desktop` stops here. The phone layout does not change with
# the weather theme, so capturing a theme variant only needs the desktop set.
if [ "${1:-}" = "desktop" ]; then
  echo "Captured into $OUT"
  exit 0
fi

shoot_mobile  dashboard-mobile  '#/'
shoot_mobile  history-mobile    '#/history?range=7d'
shoot_mobile  climate-mobile    '#/climate'

echo "Captured into $OUT"
