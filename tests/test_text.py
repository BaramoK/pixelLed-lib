"""Unit tests for the tiny 4x6 bitmap font (no BLE / no device required)."""

from PIL import Image, ImageDraw

from pixelplay.text import (
    GLYPHS,
    GLYPH_H,
    GLYPH_W,
    SPACING,
    UNKNOWN,
    draw_text,
    glyph,
    text_advance,
    text_height,
    text_pitch,
    text_width,
)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def _canvas(width=32, height=32):
    image = Image.new("RGB", (width, height))
    return image, ImageDraw.Draw(image)


def _lit(image):
    """Coordinates of the non-black pixels of ``image``."""
    return {
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, y)) != BLACK
    }


def test_every_glyph_has_the_declared_shape():
    for char, rows in GLYPHS.items():
        assert len(rows) == GLYPH_H, char
        assert all(len(row) == GLYPH_W for row in rows), char
        assert set("".join(rows)) <= {"0", "1"}, char


def test_glyph_lookup_is_case_insensitive():
    assert glyph("a") == glyph("A")
    assert glyph("7") == GLYPHS["7"]


def test_an_unknown_character_is_a_solid_block():
    assert glyph("@") == UNKNOWN
    assert glyph("e") == GLYPHS["E"]
    assert all(row == "1" * GLYPH_W for row in UNKNOWN)


def test_the_font_covers_letters_and_digits():
    for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        assert char in GLYPHS


def test_no_visible_glyph_is_blank():
    for char, rows in GLYPHS.items():
        if char != " ":
            assert "1" in "".join(rows), char


def test_text_width_counts_the_gap_between_glyphs():
    assert text_width("") == 0
    assert text_width("A") == GLYPH_W
    assert text_width("AB") == 2 * GLYPH_W + SPACING


def test_text_width_scales():
    assert text_width("AB", scale=2) == 2 * text_width("AB")


def test_text_height_scales():
    assert text_height() == GLYPH_H
    assert text_height(2) == 2 * GLYPH_H


def test_text_advance_and_pitch_follow_the_glyph_size():
    assert text_advance() == GLYPH_W + SPACING
    assert text_advance(2) == 2 * (GLYPH_W + SPACING)
    assert text_pitch() == GLYPH_H + SPACING
    assert text_pitch(2, spacing=2) == 2 * (GLYPH_H + 2)


def test_draw_text_lights_the_glyph_pixels():
    image, draw = _canvas(8, 8)
    draw_text(draw, 0, 0, "1", WHITE)
    # '1' is (0100, 1100, 0100, 0100, 0100, 1110).
    assert image.getpixel((1, 0)) == WHITE
    assert image.getpixel((0, 0)) == BLACK
    assert image.getpixel((0, 1)) == WHITE
    assert image.getpixel((2, 1)) == BLACK
    assert image.getpixel((0, 5)) == WHITE
    assert image.getpixel((2, 5)) == WHITE
    assert image.getpixel((3, 5)) == BLACK


def test_draw_text_advances_by_the_glyph_pitch():
    image, draw = _canvas(16, 8)
    draw_text(draw, 0, 0, "11", WHITE)

    assert image.getpixel((GLYPH_W + SPACING + 1, 0)) == WHITE
    assert image.getpixel((GLYPH_W + SPACING, 0)) == BLACK


def test_draw_text_scales_every_glyph_pixel():
    image, draw = _canvas(16, 16)
    draw_text(draw, 0, 0, "1", WHITE, scale=2)

    for y in range(2):
        for x in range(2, 4):
            assert image.getpixel((x, y)) == WHITE


def test_draw_text_clips_at_the_image_border():
    image, draw = _canvas(8, 8)
    draw_text(draw, 6, 6, "T", WHITE)  # half of it is off-panel

    assert image.getpixel((7, 6)) == WHITE
    # ... and nothing wraps around to the opposite edge.
    assert image.getpixel((0, 6)) == BLACK
    assert image.getpixel((0, 7)) == BLACK


def test_a_space_leaves_a_blank_gap():
    image, draw = _canvas(16, 8)
    draw_text(draw, 0, 0, " A", WHITE)

    assert all(x >= GLYPH_W + SPACING for x, _ in _lit(image))
