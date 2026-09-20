# hello-weather-site

The public page for Hello Weather, a private self-hosted weather dashboard.
Published to GitHub Pages from `main`. No build step: the repository root is
uploaded as-is.

## Verification

    python3 tools/check_page.py index.html
    python3 tools/check_contrast.py assets/site.css
    python3 -m unittest discover -s tools -p 'test_*.py'

## Screenshots

See "Capture recipe" below.

## One-time Pages setup

The deploy workflow cannot enable Pages by itself: the Actions token is not
permitted to create a Pages site. Enable it once as the repository owner:

    gh api -X POST repos/Scriberosi/hello-weather-site/pages -f build_type=workflow

## Pushing

This repository is owned by `Scriberosi`, but the default SSH key on the
development machine authenticates as a different account, so `origin` uses
HTTPS with `gh` as a repo-local credential helper:

    git remote set-url origin https://github.com/Scriberosi/hello-weather-site.git
    git config credential.helper '!gh auth git-credential'

`gh` must be on the `Scriberosi` account (`gh auth switch --user Scriberosi`)
with the `workflow` scope, which HTTPS pushes of files under
`.github/workflows/` require.

## Design token provenance

`assets/site.css` copies its tokens from `frontend/src/index.css` in the
private application repository (copied 2026-09-20). There is no shared build
step; when the application's palette changes, update the copy by hand and
re-run `python3 tools/check_contrast.py assets/site.css`.

## Capture recipe

Screenshots are captured by hand from a running local stack, not in CI: CI has
no database and no climate archive.

1. Start the local Compose stack. The UI must be on `http://localhost:5173`
   and the API on `http://localhost:8000`.
2. Confirm `curl -fsS http://localhost:8000/api/climate` succeeds. A `503`
   means the archive is still loading and the Climate captures would show a
   loading state.
3. Run `CWEBP=/opt/homebrew/bin/cwebp tools/capture.sh`.
4. Review every image against the privacy boundary in the design spec before
   committing: no coordinates, no address, no hostnames, no ports, no IPs, no
   System page content.
5. If a view was redesigned, update the `width`/`height` attributes in
   `index.html` to match — `tools/check_page.py` fails when they disagree.

Viewports: desktop 1440x900, mobile 390x844. Captures are viewport-sized, not
full-page, so each one reads as a real screen.

**Mobile captures go through an iframe on purpose.** Chrome on macOS will not
make a window narrower than 500 CSS px, so `--window-size=390,844` silently
produces a 500px viewport: the application's `max-width: 480px` rules never
apply and the result is a desktop layout cropped to phone size. `capture.sh`
renders the app inside a 390px iframe instead, which gives it a genuine 390px
viewport, then crops the screenshot back to the iframe's box. If a mobile shot
ever shows a multi-column detail grid clipped at the right edge, this is why.

The application's light/dark scheme follows the weather code and daylight, not
the reader's operating system, so the scheme in a capture is whatever the app
was showing at capture time. The dark Climate capture therefore has to be
taken after local sunset.
