"""Unit tests for the launcher menu and its auto-scroll policy (no BLE)."""

import pytest

from pixelplay.menu import (
    MARGIN,
    MAX_CHARS,
    SELECTED_BG,
    SELECTED_FG,
    TEXT_COLOR,
    AutoPilot,
    Menu,
    MenuGroup,
    MenuItem,
    build_groups,
    chars_fit,
    display_scale,
    rows_fit,
)
from pixelplay.text import GLYPH_H, SPACING, text_width

LABELS = ["INFO", "BENCH", "MIRROR", "PLAY", "BRKOUT", "TETRIS"]
BLACK = (0, 0, 0)


def _items(count=len(LABELS)):
    return [
        MenuItem(label, f"run {label}", lambda panel: None)
        for label in LABELS[:count]
    ]


def _menu(index=0, count=len(LABELS)):
    return Menu(_items(count), index=index)


def _long_menu(index=0, count=12):
    items = [
        MenuItem(f"ITEM{i}", f"run item {i}", lambda panel: None)
        for i in range(1, count + 1)
    ]
    return Menu(items, index=index)


# -- selection --------------------------------------------------------------


def test_move_wraps_around_both_ways():
    menu = _menu()
    menu.move(-1)
    assert menu.index == len(LABELS) - 1
    menu.move(1)
    assert menu.index == 0
    menu.move(3)
    assert menu.selected.label == LABELS[3]


def test_jump_selects_a_1_based_item():
    menu = _menu()
    assert menu.jump(4) is True
    assert menu.index == 3
    assert menu.selected.label == "PLAY"


def test_jump_rejects_an_out_of_range_number():
    menu = _menu(index=2)
    assert menu.jump(0) is False
    assert menu.jump(len(LABELS) + 1) is False
    assert menu.index == 2  # unchanged


def test_an_empty_menu_is_rejected():
    with pytest.raises(ValueError):
        Menu([])


# -- geometry ---------------------------------------------------------------


def test_a_32x32_panel_shows_four_rows_and_scrolls():
    menu = _menu()

    assert display_scale(32, 32) == 1
    assert chars_fit(32, 1) == MAX_CHARS
    assert rows_fit(32, 1) == 4
    assert menu.rows(32, 32) == 4
    assert menu.viewport(32, 32) == (0, 3)  # the list scrolls


def test_a_large_panel_doubles_the_glyphs():
    menu = _menu()
    layout = menu.layout(64, 64)

    assert display_scale(64, 64) == 2
    assert chars_fit(64, 2) == MAX_CHARS
    assert layout.scale == 2
    assert layout.pitch == 2 * (GLYPH_H + SPACING)
    assert layout.glyph_h == 2 * GLYPH_H


def test_a_panel_too_narrow_for_6_characters_keeps_single_pixels():
    assert chars_fit(48, 2) == 4
    assert display_scale(48, 48) == 1
    assert chars_fit(48, 1) >= MAX_CHARS


def test_the_text_block_is_centred_on_the_panel():
    menu = _menu(index=0)
    layout = menu.layout(32, 32)

    assert layout.x == (32 - text_width(menu.longest)) // 2
    assert layout.y >= MARGIN
    assert layout.y + 3 * layout.pitch + layout.glyph_h <= 32 - MARGIN


def test_a_short_panel_shows_fewer_rows():
    assert rows_fit(16, 1) == 2
    assert _menu().rows(32, 16) == 2
    assert _menu().viewport(32, 16) == (0, 1)


def test_a_long_menu_scrolls_to_keep_the_selection_visible():
    assert _long_menu(index=0).viewport(32, 32) == (0, 3)
    assert _long_menu(index=3).viewport(32, 32) == (0, 3)
    assert _long_menu(index=4).viewport(32, 32) == (1, 4)
    assert _long_menu(index=11).viewport(32, 32) == (8, 11)


@pytest.mark.parametrize("index", range(12))
def test_the_selection_is_always_inside_the_viewport(index):
    menu = _long_menu(index=index)
    first, last = menu.viewport(32, 32)
    assert first <= index <= last


@pytest.mark.parametrize("size", [(32, 16), (32, 32), (64, 64), (8, 8)])
def test_render_matches_the_requested_size(size):
    width, height = size
    image = _menu().render(width, height)

    assert image.mode == "RGB"
    assert image.size == (width, height)


def test_the_selected_row_is_inverted():
    menu = _menu(index=0)
    layout = menu.layout(32, 32)
    image = menu.render(32, 32)

    assert image.getpixel((layout.x, layout.y)) == SELECTED_FG  # the glyph
    assert image.getpixel((31, layout.y)) == SELECTED_BG  # the band
    assert image.getpixel((31, 0)) == BLACK  # above the text block


def test_the_other_rows_are_dimmed_text_on_black():
    menu = _menu(index=0)
    layout = menu.layout(32, 32)
    image = menu.render(32, 32)
    second = layout.y + layout.pitch

    assert image.getpixel((layout.x, second)) == TEXT_COLOR  # 'B' of BENCH
    assert image.getpixel((31, second)) == BLACK
    assert TEXT_COLOR != SELECTED_BG  # the selection must stand out


def test_moving_the_selection_moves_the_inverted_row():
    layout = _menu(index=0).layout(32, 32)
    second = layout.y + layout.pitch
    top = _menu(index=0).render(32, 32)
    down = _menu(index=1).render(32, 32)

    assert top.tobytes() != down.tobytes()
    assert top.getpixel((31, layout.y)) == SELECTED_BG
    assert top.getpixel((31, second)) == BLACK
    assert down.getpixel((31, layout.y)) == BLACK
    assert down.getpixel((31, second)) == SELECTED_BG


def test_every_label_fits_a_32px_wide_panel():
    for item in _items():
        assert len(item.label) <= MAX_CHARS
        assert text_width(item.label) <= 32 - 2 * MARGIN


# -- items ------------------------------------------------------------------


def test_build_groups_exposes_games_and_debug():
    groups = build_groups("00:11:22:33:44:55")

    assert [group.label for group in groups] == ["GAMES", "DEBUG"]
    assert [item.label for item in groups[0].items] == ["BRKOUT", "TETRIS"]
    assert [item.label for item in groups[1].items] == [
        "INFO",
        "BENCH",
        "MIRROR",
        "PLAY",
    ]
    assert all(isinstance(group, MenuGroup) for group in groups)
    assert all(group.title for group in groups)
    assert all(item.title for group in groups for item in group.items)
    assert all(callable(item.action) for group in groups for item in group.items)


def test_every_group_label_fits_a_32px_wide_panel():
    for group in build_groups("00:11:22:33:44:55"):
        assert len(group.label) <= MAX_CHARS
        assert text_width(group.label) <= 32 - 2 * MARGIN


def test_every_group_has_at_least_one_item():
    for group in build_groups("00:11:22:33:44:55"):
        assert group.items


def test_the_root_menu_lists_the_groups():
    groups = build_groups("00:11:22:33:44:55")
    root = Menu(
        [MenuItem(group.label, group.title, lambda panel: None) for group in groups]
    )

    assert [item.label for item in root.items] == ["GAMES", "DEBUG"]
    assert root.render(32, 32).size == (32, 32)


def test_a_group_opens_as_a_regular_menu():
    games = build_groups("00:11:22:33:44:55")[0]
    menu = Menu(games.items)

    assert [item.label for item in menu.items] == ["BRKOUT", "TETRIS"]
    assert menu.render(32, 32).size == (32, 32)


# -- auto-scroll ------------------------------------------------------------


def test_auto_pilot_moves_every_delay_ticks():
    pilot = AutoPilot(delay=3, auto=True)

    assert [pilot.tick() for _ in range(6)] == [
        False,
        False,
        True,
        False,
        False,
        True,
    ]


def test_a_key_press_takes_over_from_the_auto_scroll():
    pilot = AutoPilot(delay=1, resume=5, auto=True)

    pilot.key()
    assert pilot.auto is False
    # Four idle ticks, then auto-scrolling resumes *and* moves.
    assert [pilot.tick() for _ in range(5)] == [
        False,
        False,
        False,
        False,
        True,
    ]
    assert pilot.auto is True


def test_a_key_press_restarts_the_idle_countdown():
    pilot = AutoPilot(delay=1, resume=3, auto=False)

    pilot.tick()
    pilot.tick()
    pilot.key()

    assert [pilot.tick() for _ in range(3)] == [False, False, True]


def test_auto_scroll_never_comes_back_without_a_resume_delay():
    pilot = AutoPilot(delay=1, resume=0, auto=True)

    pilot.key()

    assert [pilot.tick() for _ in range(20)] == [False] * 20
    assert pilot.auto is False


def test_the_toggle_flips_the_mode_and_returns_it():
    pilot = AutoPilot(delay=2, resume=0, auto=False)

    assert pilot.toggle() is True
    assert [pilot.tick() for _ in range(4)] == [False, True, False, True]
    assert pilot.toggle() is False
