"""A tiny 4x6 bitmap font drawn with PIL primitives.

The font is plain data, so it needs no font file and no extra dependency, and
it renders identically on every platform and Pillow version (``ImageFont``'s
built-in bitmap font is only scalable from Pillow 10.1 on, and this package
supports older releases). At 4x6 px a glyph plus its 1 px gap is 5 px wide, so
6 characters fit on a 32 px wide panel - enough for the launcher's labels -
and that fourth column is what makes letters such as M, W, R and S readable
instead of a blob.
"""

from __future__ import annotations

from PIL import ImageDraw

Color = tuple[int, int, int]

GLYPH_W = 4
GLYPH_H = 6
SPACING = 1

# Each glyph is 6 rows of 4 characters, top to bottom ('1' = lit pixel).
GLYPHS: dict[str, tuple[str, ...]] = {
    " ": ("0000", "0000", "0000", "0000", "0000", "0000"),
    "-": ("0000", "0000", "0000", "1111", "0000", "0000"),
    ".": ("0000", "0000", "0000", "0000", "0110", "0110"),
    ",": ("0000", "0000", "0000", "0110", "0110", "1100"),
    ":": ("0000", "0110", "0110", "0000", "0110", "0110"),
    "!": ("0100", "0100", "0100", "0100", "0000", "0100"),
    "?": ("0110", "1001", "0001", "0010", "0000", "0010"),
    "/": ("0001", "0010", "0010", "0100", "0100", "1000"),
    "+": ("0000", "0100", "0100", "1110", "0100", "0100"),
    "=": ("0000", "1111", "0000", "0000", "1111", "0000"),
    "_": ("0000", "0000", "0000", "0000", "0000", "1111"),
    "%": ("1001", "0001", "0010", "0100", "1000", "1001"),
    "#": ("1010", "1111", "1010", "1010", "1111", "1010"),
    "<": ("0010", "0100", "1000", "1000", "0100", "0010"),
    ">": ("0100", "0010", "0001", "0001", "0010", "0100"),
    "0": ("0110", "1001", "1001", "1001", "1001", "0110"),
    "1": ("0100", "1100", "0100", "0100", "0100", "1110"),
    "2": ("0110", "1001", "0001", "0010", "0100", "1111"),
    "3": ("1110", "0001", "0110", "0001", "1001", "0110"),
    "4": ("0010", "0110", "1010", "1111", "0010", "0010"),
    "5": ("1111", "1000", "1110", "0001", "1001", "0110"),
    "6": ("0110", "1000", "1110", "1001", "1001", "0110"),
    "7": ("1111", "0001", "0010", "0100", "0100", "0100"),
    "8": ("0110", "1001", "0110", "1001", "1001", "0110"),
    "9": ("0110", "1001", "1001", "0111", "0001", "0110"),
    "A": ("0110", "1001", "1001", "1111", "1001", "1001"),
    "B": ("1110", "1001", "1001", "1110", "1001", "1110"),
    "C": ("0110", "1001", "1000", "1000", "1001", "0110"),
    "D": ("1110", "1001", "1001", "1001", "1001", "1110"),
    "E": ("1111", "1000", "1110", "1000", "1000", "1111"),
    "F": ("1111", "1000", "1110", "1000", "1000", "1000"),
    "G": ("0110", "1001", "1000", "1011", "1001", "0111"),
    "H": ("1001", "1001", "1111", "1001", "1001", "1001"),
    "I": ("1110", "0100", "0100", "0100", "0100", "1110"),
    "J": ("0011", "0001", "0001", "0001", "1001", "0110"),
    "K": ("1001", "1010", "1100", "1100", "1010", "1001"),
    "L": ("1000", "1000", "1000", "1000", "1000", "1111"),
    "M": ("1001", "1111", "1111", "1001", "1001", "1001"),
    "N": ("1001", "1101", "1101", "1011", "1011", "1001"),
    "O": ("0110", "1001", "1001", "1001", "1001", "0110"),
    "P": ("1110", "1001", "1001", "1110", "1000", "1000"),
    "Q": ("0110", "1001", "1001", "1001", "1011", "0101"),
    "R": ("1110", "1001", "1001", "1110", "1010", "1001"),
    "S": ("0111", "1000", "0110", "0001", "0001", "1110"),
    "T": ("1111", "0100", "0100", "0100", "0100", "0100"),
    "U": ("1001", "1001", "1001", "1001", "1001", "0110"),
    "V": ("1001", "1001", "1001", "1001", "1010", "0100"),
    "W": ("1001", "1001", "1001", "1111", "1111", "1001"),
    "X": ("1001", "1001", "0110", "0110", "1001", "1001"),
    "Y": ("1001", "1001", "0110", "0100", "0100", "0100"),
    "Z": ("1111", "0001", "0010", "0100", "1000", "1111"),
}

# A character outside the table shows up as a solid block, so a typo in a label
# is obvious on the panel instead of silently rendering as a blank.
UNKNOWN: tuple[str, ...] = ("1111", "1111", "1111", "1111", "1111", "1111")


def glyph(char: str) -> tuple[str, ...]:
    """Return the 6 rows of ``char`` (case-insensitive); a block if unknown."""
    return GLYPHS.get(char.upper(), UNKNOWN)


def text_advance(scale: int = 1, spacing: int = SPACING) -> int:
    """Horizontal distance between two glyphs, in pixels."""
    return (GLYPH_W + max(0, int(spacing))) * max(1, int(scale))


def text_width(text: str, scale: int = 1, spacing: int = SPACING) -> int:
    """Width in pixels of ``text``, gap between glyphs included."""
    if not text:
        return 0
    scale = max(1, int(scale))
    spacing = max(0, int(spacing))
    return len(text) * text_advance(scale, spacing) - spacing * scale


def text_height(scale: int = 1) -> int:
    """Height in pixels of one line of text."""
    return GLYPH_H * max(1, int(scale))


def text_pitch(scale: int = 1, spacing: int = SPACING) -> int:
    """Vertical distance between two lines of text, in pixels."""
    return (GLYPH_H + max(0, int(spacing))) * max(1, int(scale))


def draw_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    color: Color,
    scale: int = 1,
    spacing: int = SPACING,
) -> None:
    """Draw ``text`` with its top-left corner at ``(x, y)``.

    Anything falling outside the target image is clipped by PIL, so callers
    can draw partially off-panel text without checking bounds themselves.
    """
    scale = max(1, int(scale))
    spacing = max(0, int(spacing))
    advance = (GLYPH_W + spacing) * scale
    cursor = x
    for char in text:
        rows = glyph(char)
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit != "1":
                    continue
                px = cursor + rx * scale
                py = y + ry * scale
                draw.rectangle(
                    [px, py, px + scale - 1, py + scale - 1], fill=color
                )
        cursor += advance
