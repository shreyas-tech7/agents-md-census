"""Draw docs/social-preview.png (1280 x 640) with the standard library only.

Text uses a small built-in 5x7 pixel font. The bars come from
results/summary.json, so the picture never shows a typed number.
"""

from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W, H = 1280, 640
BG, FG, MUTED, BAR, TRACK = (
    (13, 17, 23),
    (230, 237, 243),
    (145, 152, 161),
    (68, 147, 248),
    (48, 54, 61),
)

FONT = {
    "A": "01110100011000111111100011000110001",
    "B": "11110100011111010001100011000111110",
    "C": "01110100011000010000100001000101110",
    "D": "11110100011000110001100011000111110",
    "E": "11111100001111010000100001000011111",
    "F": "11111100001111010000100001000010000",
    "G": "01110100011000010111100011000101111",
    "H": "10001100011111110001100011000110001",
    "I": "01110001000010000100001000010001110",
    "J": "00111000100001000010000101001001100",
    "K": "10001100101010011000101001001010001",
    "L": "10000100001000010000100001000011111",
    "M": "10001110111010110101100011000110001",
    "N": "10001110011010110011100011000110001",
    "O": "01110100011000110001100011000101110",
    "P": "11110100011000111110100001000010000",
    "Q": "01110100011000110001101011001001101",
    "R": "11110100011000111110101001001010001",
    "S": "01111100001000001110000010000111110",
    "T": "11111001000010000100001000010000100",
    "U": "10001100011000110001100011000101110",
    "V": "10001100011000110001100010101000100",
    "W": "10001100011000110101101011010101010",
    "X": "10001100010101000100010101000110001",
    "Y": "10001100010101000100001000010000100",
    "Z": "11111000010001000100010001000011111",
    "0": "01110100011001110101110011000101110",
    "1": "00100011000010000100001000010001110",
    "2": "01110100010000100010001000100011111",
    "3": "11111000100010000010000011000101110",
    "4": "00010001100101010010111110001000010",
    "5": "11111100001111000001000011000101110",
    "6": "00110010001000011110100011000101110",
    "7": "11111000010001000100010000100001000",
    "8": "01110100011000101110100011000101110",
    "9": "01110100011000101111000010001001100",
    " ": "0" * 35,
    "-": "00000000000000011111000000000000000",
    ".": "0" * 30 + "01100",
    "%": "11001110010001000100010001001110011",
    ",": "0" * 25 + "0110000100",
}


def text(px, x, y, s, scale, color):
    for ch in s.upper():
        glyph = FONT.get(ch, FONT[" "])
        for i, bit in enumerate(glyph[:35]):
            if bit == "1":
                gx, gy = x + (i % 5) * scale, y + (i // 5) * scale
                rect(px, gx, gy, scale, scale, color)
        x += 6 * scale


def rect(px, x, y, w, h, color):
    for yy in range(max(0, y), min(H, y + h)):
        row = px[yy]
        for xx in range(max(0, x), min(W, x + w)):
            row[xx] = color


def png(px) -> bytes:
    raw = b"".join(b"\x00" + bytes(c for p in row for c in p) for row in px)

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def draw(summary: dict) -> bytes:
    px = [[BG] * W for _ in range(H)]
    text(px, 80, 70, "agents-md-census", 10, FG)
    text(px, 80, 170, "how public repos write instructions for ai coding agents", 3, MUTED)
    heads = {p["label"]: p for p in summary["headline"]}
    rows = [
        ("any agent file", heads["Repos with at least one agent instruction file"]),
        ("agents.md", heads["Repos with AGENTS.md"]),
        ("claude.md", heads["Repos with CLAUDE.md"]),
        ("files with drift", heads["Files with at least one drifted command"]),
    ]
    y = 260
    for name, p in rows:
        text(px, 80, y, name, 4, FG)
        rect(px, 520, y, 560, 28, TRACK)
        rect(px, 520, y, int(560 * (p["pct"] or 0) / 100), 28, BAR)
        text(px, 1100, y, f"{p['pct']}%", 4, FG)
        y += 70
    text(px, 80, 560, f"n {summary['n_repos']} repos, 95% wilson intervals in the report", 3, MUTED)
    return png(px)


def main(argv) -> int:
    summary = json.loads((ROOT / "results/summary.json").read_text())
    data = draw(summary)
    out = ROOT / "docs/social-preview.png"
    if "--check" in argv:
        w, h = struct.unpack(">II", out.read_bytes()[16:24])
        ok = (w, h) == (W, H) and out.read_bytes() == data
        print("social preview", "current" if ok else "stale or wrong size", f"{w}x{h}")
        return 0 if ok else 1
    out.write_bytes(data)
    print(f"wrote {out.relative_to(ROOT)} {W}x{H}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
