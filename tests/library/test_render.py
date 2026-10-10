"""Unit tests for the frame renderers (no BLE / no device required)."""

import pytest
from PIL import Image

from pixelled_lib import render_bars, render_bouncing_ball, render_gradient
from pixelled_lib.library.render import RENDERERS

SIZES = [(32, 16), (32, 32), (64, 64)]


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("name", sorted(RENDERERS))
def test_renderer_returns_rgb_at_size(name, size):
    width, height = size
    img = RENDERERS[name](0.0, width, height)
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    assert img.size == (width, height)


def test_bars_change_over_time():
    # The scroll period equals the width, so a full period (t=1.0) repeats:
    # use a sub-period delta to observe movement.
    a = render_bars(0.0, 32, 32)
    b = render_bars(0.1, 32, 32)
    assert a.tobytes() != b.tobytes()


def test_bars_repeat_after_a_full_period():
    a = render_bars(0.0, 32, 32)
    b = render_bars(1.0, 32, 32)
    assert a.tobytes() == b.tobytes()


def test_bouncing_ball_moves():
    a = render_bouncing_ball(0.0, 64, 64)
    b = render_bouncing_ball(1.0, 64, 64)
    assert a.tobytes() != b.tobytes()


def test_gradient_is_not_uniform():
    img = render_gradient(0.5, 32, 32)
    colors = img.getcolors(maxcolors=1 << 16)
    assert colors is None or len(colors) > 1
