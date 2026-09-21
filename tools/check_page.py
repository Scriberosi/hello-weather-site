#!/usr/bin/env python3
"""Structural checks for the single-page site. Standard library only.

Run: python3 tools/check_page.py index.html
Exits 1 and prints one line per problem. Silent and exits 0 when sound.
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

REQUIRED_ANCHORS = {
    "dashboard",
    "history",
    "climate",
    "built",
    "rivers",
    "air-quality",
    "forecast-quality",
    "climate-change",
    "sources",
}

# Markers for the magazine documents. An issue page (`<article class="issue">`)
# and the archive index (`<main class="archive">`) are separate documents from
# the single-page site; they legitimately carry none of its landmark anchors.
# The generic structural checks (one h1, no heading skips, no dangling
# fragments, alt text, on-origin resources) still apply to them.
_MAGAZINE_MARKERS = ('class="issue"', 'class="archive"')


def _required_for(html: str) -> set[str]:
    """Which landmark anchors this document must carry.

    The single-page reference site must carry all of REQUIRED_ANCHORS; a
    magazine issue or archive page requires none of them.
    """
    if any(marker in html for marker in _MAGAZINE_MARKERS):
        return set()
    return REQUIRED_ANCHORS


def webp_size(data: bytes) -> tuple[int, int]:
    """Width and height from a WebP byte string (VP8, VP8L, or VP8X)."""
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a WebP file")
    chunk = data[12:16]
    if chunk == b"VP8X":
        return (
            int.from_bytes(data[24:27], "little") + 1,
            int.from_bytes(data[27:30], "little") + 1,
        )
    if chunk == b"VP8 ":
        return (
            int.from_bytes(data[26:28], "little") & 0x3FFF,
            int.from_bytes(data[28:30], "little") & 0x3FFF,
        )
    if chunk == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    raise ValueError(f"unknown WebP chunk {chunk!r}")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.fragments: list[str] = []
        self.images: list[dict[str, str]] = []
        self.headings: list[int] = []
        self.resources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and a.get("href", "").startswith("#"):
            self.fragments.append(a["href"][1:])
        if tag == "img":
            self.images.append(a)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))
        if tag == "script" and a.get("src"):
            self.resources.append(a["src"])
        if tag == "link" and "stylesheet" in a.get("rel", ""):
            self.resources.append(a.get("href", ""))


def check_page(
    html_path: Path, root: Path, required: set[str] | None = None
) -> list[str]:
    required = REQUIRED_ANCHORS if required is None else required
    parser = PageParser()
    parser.feed(Path(html_path).read_text(encoding="utf-8"))
    problems: list[str] = []

    for fragment in parser.fragments:
        if fragment and fragment not in parser.ids:
            problems.append(f"link to #{fragment} has no matching id")

    for anchor in sorted(required - parser.ids):
        problems.append(f"required anchor id missing: {anchor}")

    if parser.headings.count(1) != 1:
        problems.append(f"expected exactly one h1, found {parser.headings.count(1)}")
    previous = 0
    for level in parser.headings:
        if previous and level > previous + 1:
            problems.append(f"heading level skips from h{previous} to h{level}")
        previous = level

    for image in parser.images:
        src = image.get("src", "")
        if not image.get("alt", "").strip():
            problems.append(f"image {src} has no alt text")
        if not image.get("width") or not image.get("height"):
            problems.append(f"image {src} is missing width/height attributes")
        path = Path(root) / src
        if not path.is_file():
            problems.append(f"image file missing: {src}")
            continue
        if path.suffix == ".webp" and image.get("width") and image.get("height"):
            try:
                width, height = webp_size(path.read_bytes())
            except ValueError as exc:
                problems.append(f"image {src} is not readable as WebP: {exc}")
                continue
            declared = (int(image["width"]), int(image["height"]))
            if declared != (width, height):
                problems.append(
                    f"image {src} declares {declared[0]}x{declared[1]} "
                    f"but the file is {width}x{height}"
                )

    for resource in parser.resources:
        if resource.startswith(("http://", "https://", "//")):
            problems.append(f"off-origin resource is not allowed: {resource}")

    return problems


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_page.py <index.html>", file=sys.stderr)
        return 2
    html_path = Path(sys.argv[1]).resolve()
    required = _required_for(html_path.read_text(encoding="utf-8"))
    problems = check_page(html_path, html_path.parent, required=required)
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
