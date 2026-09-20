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

Screenshots are captured by hand from a running instance, not in CI: CI has no
database and no climate archive.

These are dashboards, so every shot is the **whole page**, not the first
viewport. Chrome only screenshots its viewport, so each page is rendered into a
deliberately over-tall window and cropped back to where the content ends.
`tools/content_height.py` finds that line by scanning up from the bottom for
the first row containing a sharp step between neighbouring pixels. It looks for
sharp steps rather than light-versus-dark spread because the app paints a large
radial glow that scales with viewport height; a spread test follows the glow
instead of the content and returns the same wrong height for every page.

1. Start an instance that serves the API and the UI on one origin, with a
   synced climate archive.
2. Confirm `curl -fsS "$BASE/api/climate"` succeeds. A `503` means the archive
   is still loading and the Climate captures would show a loading state.
3. Run it, passing the instance address (never commit that address — this
   repository is public):

       BASE=http://<host>:<port> CWEBP=/opt/homebrew/bin/cwebp tools/capture.sh

4. Review every image against the privacy boundary in the design spec before
   committing: no coordinates, no address, no hostnames, no ports, no IPs, no
   System page content.
5. Update the `width`/`height` attributes in `index.html` to the sizes the
   script prints — `tools/check_page.py` fails when they disagree.

If the script warns that a page filled its render window, raise `TALL_DESKTOP`
or `TALL_MOBILE` and re-run; that page was clipped.

Viewports: desktop 1440 wide, mobile 390 wide.

**Mobile captures go through an iframe on purpose.** Chrome on macOS will not
make a window narrower than 500 CSS px, so `--window-size=390,...` silently
produces a 500px viewport: the application's `max-width: 480px` rules never
apply and the result is a desktop layout cropped to phone size. `capture.sh`
renders the app inside a 390px iframe instead, then crops back to it. If a
mobile shot ever shows a multi-column detail grid clipped at the right edge,
this is why.

Phone captures run to three or four thousand pixels. The page caps their
displayed height and fades them out; the committed file is still the full page.

The application's light/dark scheme follows the weather code and daylight, not
the reader's operating system, so the scheme in a capture is whatever the app
was showing at capture time. A dark capture has to be taken after local sunset.
