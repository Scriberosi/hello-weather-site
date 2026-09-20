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
