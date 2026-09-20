#!/usr/bin/env python3
"""Find where a screenshot's content ends. Standard library only.

A tall-viewport capture leaves the page background stretched below the last
element. Content is found by looking for sharp horizontal steps between
neighbouring pixels -- text edges, card borders, chart strokes. A smooth
background, including a large radial glow, changes only gradually across a
row and so never registers, which a simple lightest-minus-darkest test would
wrongly flag. The last row with a sharp step is the content height, and that
is what the screenshot is cropped to.

Run: python3 tools/content_height.py shot.png [--step N] [--width N]
Prints the height in pixels.
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

STEP = 12  # min jump (0-255) between neighbouring pixels to count as content


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def rows(png: bytes):
    """Yield each unfiltered scanline as bytes, top to bottom."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, ihdr = 8, bytearray(), None
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        kind = png[pos + 4 : pos + 8]
        body = png[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
        pos += 12 + length
    if ihdr is None:
        raise ValueError("no IHDR")
    width, height, depth, colour = ihdr[0], ihdr[1], ihdr[2], ihdr[3]
    if depth != 8 or colour not in (2, 6):
        raise ValueError(f"unsupported PNG: depth={depth} colour={colour}")
    channels = 3 if colour == 2 else 4
    stride = width * channels
    raw = zlib.decompress(bytes(idat))
    previous = bytearray(stride)
    at = 0
    for _ in range(height):
        filter_type = raw[at]
        line = bytearray(raw[at + 1 : at + 1 + stride])
        at += 1 + stride
        if filter_type == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                upleft = previous[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(left, previous[i], upleft)) & 0xFF
        previous = line
        yield bytes(line), width, channels


def content_height(png: bytes, step: int = STEP, scan_width: int | None = None) -> int:
    last = 0
    for index, (line, width, channels) in enumerate(rows(png)):
        limit = (min(scan_width, width) if scan_width else width) * channels
        sharp = False
        for c in range(3):
            column = line[c:limit:channels]
            if any(
                abs(a - b) >= step for a, b in zip(column, column[1:])
            ):
                sharp = True
                break
        if sharp:
            last = index
    return last + 1


def main() -> int:
    args = sys.argv[1:]
    step, scan_width = STEP, None
    for name, setter in (("--step", "step"), ("--width", "width")):
        if name in args:
            i = args.index(name)
            value = int(args[i + 1])
            del args[i : i + 2]
            if setter == "step":
                step = value
            else:
                scan_width = value
    if len(args) != 1:
        print(
            "usage: content_height.py <shot.png> [--step N] [--width N]",
            file=sys.stderr,
        )
        return 2
    print(content_height(Path(args[0]).read_bytes(), step, scan_width))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
