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
