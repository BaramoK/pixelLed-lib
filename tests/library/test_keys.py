"""Unit tests for the keyboard auto-repeat helper (no window, no BLE)."""

from pixelled_lib.library.keys import KeyRepeater


def test_a_key_tap_fires_exactly_once():
    repeater = KeyRepeater()
    assert repeater.press("right") is True  # the tap itself
    repeater.release("right")  # released before the next frame
    assert [repeater.due() for _ in range(20)] == [[]] * 20


def test_the_os_auto_repeat_does_not_double_a_press():
    repeater = KeyRepeater()
    assert repeater.press("right") is True
    assert repeater.press("right") is False  # the OS re-sent KeyPress
    assert repeater.press("right") is False
    repeater.release("right")
    assert repeater.press("right") is True  # a new, real press works again


def test_a_held_key_repeats_after_the_delay_then_every_tick():
    repeater = KeyRepeater()
    repeater.press("left")
    for _ in range(repeater.delay - 1):
        assert repeater.due() == []  # not long enough to repeat yet
    assert repeater.due() == ["left"]  # held: it starts repeating
    assert repeater.due() == ["left"]  # and keeps repeating every tick


def test_the_repeat_interval_is_honoured():
    repeater = KeyRepeater(delay=2, every=3)
    repeater.press("left")
    assert repeater.due() == []
    assert repeater.due() == ["left"]  # after the delay
    assert repeater.due() == []
    assert repeater.due() == []
    assert repeater.due() == ["left"]  # every 3 ticks


def test_release_stops_the_repeat():
    repeater = KeyRepeater()
    repeater.press("right")
    repeater.due()
    repeater.due()
    repeater.release("right")
    assert [repeater.due() for _ in range(10)] == [[]] * 10


def test_losing_the_focus_does_not_leave_a_key_stuck():
    repeater = KeyRepeater()
    repeater.press("right")
    repeater.clear()  # no KeyRelease is delivered on FocusOut
    assert repeater.due() == []
    assert repeater.press("right") is True
