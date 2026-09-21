#!/usr/bin/env python3
"""WCAG-AA contrast gate for the copied design tokens. Standard library only.

Text on this site sits on a translucent white card over a gradient backdrop, so
each text colour is checked against the card composited over both gradient
endpoints, and the worse result is the one that must pass. This mirrors
frontend/src/theme.contrast.test.ts in the application repository.

Run: python3 tools/check_contrast.py assets/site.css
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

BODY_MIN = 4.5
Rgb = tuple[int, int, int]

# The palette tokens this gate reasons about. The stylesheet that defines them
# (assets/site.css) is checked strictly; a stylesheet that only references them
# (an extension such as assets/magazine.css) is checked with --extension, which
# treats a token-less file as a no-op because the contrast it inherits is gated
# on the file that owns the tokens.
_CONTRAST_TOKENS = ("--surface-alpha", "--bg-from", "--bg-to", "--text",
                    "--text-muted")


def hex_to_rgb(value: str) -> Rgb:
    v = value.lstrip("#")
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))


def relative_luminance(rgb: Rgb) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: Rgb, b: Rgb) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def overlay_white(bg: Rgb, alpha: float) -> Rgb:
    return tuple(round(255 * alpha + c * (1 - alpha)) for c in bg)  # type: ignore[return-value]


def _scheme_blocks(css: str) -> dict[str, str]:
    """Split the stylesheet into a light and a dark token block."""
    dark = re.search(r"prefers-color-scheme:\s*dark.*", css, re.S)
    return {
        "light": css[: dark.start()] if dark else css,
        "dark": dark.group(0) if dark else "",
    }


def _token(block: str, name: str) -> str | None:
    match = re.search(rf"{name}:\s*([^;]+);", block)
    return match.group(1).strip() if match else None


def check_contrast(css: str, *, is_extension: bool = False) -> list[str]:
    # Only an explicitly declared extension may skip the check when it defines
    # no palette tokens. A primary stylesheet that is missing its palette is a
    # real defect and must still be reported, not silently accepted.
    if is_extension and not any(_token(css, name) for name in _CONTRAST_TOKENS):
        return []
    problems: list[str] = []
    for scheme, block in _scheme_blocks(css).items():
        if not block.strip():
            continue
        alpha_raw = _token(block, "--surface-alpha")
        if alpha_raw is None:
            problems.append(f"{scheme}: --surface-alpha is not defined")
            continue
        alpha = float(alpha_raw)
        backdrops = []
        for name in ("--bg-from", "--bg-to"):
            raw = _token(block, name)
            if raw is None:
                problems.append(f"{scheme}: {name} is not defined")
            else:
                backdrops.append(hex_to_rgb(raw))
        if len(backdrops) != 2:
            continue
        surfaces = [overlay_white(bg, alpha) for bg in backdrops]
        for name in ("--text", "--text-muted"):
            raw = _token(block, name)
            if raw is None:
                problems.append(f"{scheme}: {name} is not defined")
                continue
            fg = hex_to_rgb(raw)
            worst = min(contrast_ratio(fg, surface) for surface in surfaces)
            if worst < BODY_MIN:
                problems.append(
                    f"{scheme}: {name.lstrip('-')} contrast is {worst:.2f}:1, "
                    f"below the {BODY_MIN}:1 minimum"
                )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="WCAG-AA contrast gate")
    parser.add_argument("stylesheet", type=Path)
    parser.add_argument(
        "--extension",
        action="store_true",
        help="a token-less extension stylesheet (e.g. assets/magazine.css) is "
        "a no-op; without this flag a stylesheet must define the palette",
    )
    args = parser.parse_args()
    problems = check_contrast(
        args.stylesheet.read_text(encoding="utf-8"), is_extension=args.extension
    )
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
