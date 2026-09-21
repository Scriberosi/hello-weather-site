#!/usr/bin/env python3
"""Regenerate the issue index and the Atom feed from the issues directory.

The directory is the source of truth: adding an issue file and re-running this
is the whole publishing step.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from html import escape, unescape
from pathlib import Path

_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
_DESCRIPTION = re.compile(r'<meta name="description" content="(.*?)"')
_TAGS = re.compile(r"<[^>]+>")

SITE_TITLE = "Hello Weather — Climate Magazine"
# Atom requires an author; entries inherit this feed-level one (RFC 4287 §4.2.1).
FEED_AUTHOR = SITE_TITLE
# A feed with no issues still needs a stable <updated>; the clock must never
# reach the output or every rebuild would differ byte-for-byte.
_EMPTY_FEED_UPDATED = "1970-01-01T00:00:00Z"

# Month names are fixed rather than locale-derived: the page is lang="en" and
# strftime("%B") would follow the build machine's LC_TIME instead.
_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def issue_title(path: Path) -> str:
    match = _H1.search(path.read_text(encoding="utf-8"))
    if not match:
        return path.stem
    # Strip tags, then decode entities exactly once. The caller escapes on
    # output, so decoding here prevents a double-escape (&amp; -> &amp;amp;).
    return unescape(_TAGS.sub("", match.group(1))).strip()


def issue_summary(path: Path) -> str:
    match = _DESCRIPTION.search(path.read_text(encoding="utf-8"))
    # The meta description is attribute-encoded; decode once so the caller's
    # escape() single-encodes it on output.
    return unescape(match.group(1)).strip() if match else ""


def _month_label(stem: str) -> str:
    parsed = datetime.strptime(stem, "%Y-%m")  # validates the YYYY-MM stem
    return f"{_MONTHS[parsed.month - 1]} {parsed.year}"


def _sorted_newest_first(paths: list[Path]) -> list[Path]:
    return sorted((p for p in paths if p.stem != "index"), key=lambda p: p.stem,
                  reverse=True)


def _archive_row(path: Path) -> str:
    # The summary sits inside the <a> so the whole card is a single hit target,
    # matching the "one large hit target" contract in magazine.css. A blank
    # summary is omitted rather than left as an empty, still-padded element.
    summary = issue_summary(path)
    summary_html = (
        f'<span class="archive__summary">{escape(summary)}</span>' if summary else ""
    )
    return (
        f'<li><a href="{escape(path.name)}">'
        f'<span class="archive__month">{escape(_month_label(path.stem))}</span>'
        f'<span class="archive__title">{escape(issue_title(path))}</span>'
        f"{summary_html}</a></li>"
    )


def build_index(issue_paths: list[Path], out_path: Path) -> None:
    rows = [_archive_row(path) for path in _sorted_newest_first(issue_paths)]
    if rows:
        listing = f'<ul class="archive__list">\n{chr(10).join(rows)}\n</ul>\n'
    else:
        listing = '<p class="archive__empty">No issues yet.</p>\n'
    out_path.write_text(
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(SITE_TITLE)}</title>\n"
        '<link rel="stylesheet" href="../assets/site.css">\n'
        '<link rel="stylesheet" href="../assets/magazine.css">\n'
        '<link rel="alternate" type="application/atom+xml" href="../feed.xml">\n'
        "</head>\n<body>\n"
        '<main class="archive">\n'
        f"<h1>{escape(SITE_TITLE)}</h1>\n"
        '<p class="archive__lede">One issue a month about the weather and '
        "climate of a single location, built from a daily archive that starts "
        "in 1940.</p>\n"
        f"{listing}"
        '<p class="archive__back"><a href="../index.html">'
        "About this project</a></p>\n"
        "</main>\n</body>\n</html>\n",
        encoding="utf-8",
    )


def build_feed(issue_paths: list[Path], out_path: Path, site_url: str) -> None:
    site_url = site_url.rstrip("/")
    ordered = _sorted_newest_first(issue_paths)
    # Derive <updated> from the newest issue, not the clock, so an unchanged set
    # of issues always rebuilds to identical bytes.
    updated = f"{ordered[0].stem}-01T00:00:00Z" if ordered else _EMPTY_FEED_UPDATED
    entries = []
    for path in ordered:
        url = f"{site_url}/issues/{path.name}"
        published = f"{path.stem}-01T00:00:00Z"
        entries.append(
            "<entry>\n"
            f"<title>{escape(issue_title(path))}</title>\n"
            f'<link href="{escape(url)}"/>\n'
            f"<id>{escape(url)}</id>\n"
            f"<updated>{published}</updated>\n"
            f"<summary>{escape(issue_summary(path))}</summary>\n"
            "</entry>"
        )
    body = f"{chr(10).join(entries)}\n" if entries else ""
    out_path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f"<title>{escape(SITE_TITLE)}</title>\n"
        f'<link href="{escape(site_url)}/issues/index.html"/>\n'
        f'<link rel="self" href="{escape(site_url)}/feed.xml"/>\n'
        f"<id>{escape(site_url)}/</id>\n"
        f"<author><name>{escape(FEED_AUTHOR)}</name></author>\n"
        f"<updated>{updated}</updated>\n"
        f"{body}"
        "</feed>\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issues", default="issues", type=Path)
    parser.add_argument(
        "--site-url", default="https://scriberosi.github.io/hello-weather-site"
    )
    parser.add_argument("--feed", default="feed.xml", type=Path)
    arguments = parser.parse_args()

    paths = sorted(arguments.issues.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].html"))
    build_index(paths, arguments.issues / "index.html")
    build_feed(paths, arguments.feed, arguments.site_url)
    print(f"built index and feed from {len(paths)} issues")


if __name__ == "__main__":
    main()
