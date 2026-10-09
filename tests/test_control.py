"""Unit tests for the controllable sprite (no BLE / no device required).

``Panel.__new__`` is used to bypass the constructor (which would open a real
Bluetooth connection) and inject a fake client that records the payloads, so
the whole "control -> frame -> panel" chain can be checked without hardware.
"""

import io
import time

from PIL import Image

from pixelplay.control import PALETTE, Sprite
from pixelplay.panel import Panel
from pixelplay.play import _Sender


class FakeClient:
    """Records calls to ``send_image_hex`` instead of talking to hardware."""

    def __init__(self):
        self.calls = []

    def send_image_hex(self, hex_string, extension, *args, **kwargs):
        self.calls.append((hex_string, extension))


def _make_panel(width=32, height=32):
    panel = Panel.__new__(Panel)  # bypass __init__ (no BLE)
    panel._client = FakeClient()
    panel.width = width
    panel.height = height
    panel.led_type = "RGB"
    panel.device_info = None
    return panel


def _decode(hex_string):
    return Image.open(io.BytesIO(bytes.fromhex(hex_string))).convert("RGB")


def test_sprite_starts_at_origin():
    sprite = Sprite()
    assert (sprite.x, sprite.y) == (0, 0)


def test_center_places_sprite_in_the_middle():
    sprite = Sprite()
    sprite.center(32, 16)
    assert (sprite.x, sprite.y) == (16, 8)


def test_set_position_clamps_to_bounds():
    sprite = Sprite()
    sprite.set_position(99, -5, 32, 16)
    assert (sprite.x, sprite.y) == (31, 0)


def test_move_clamps_to_bounds():
    sprite = Sprite()
    sprite.center(32, 16)  # (16, 8)
    sprite.move(-1000, -1000, 32, 16)
    assert (sprite.x, sprite.y) == (0, 0)

    sprite.move(1000, 1000, 32, 16)
    assert (sprite.x, sprite.y) == (31, 15)


def test_cycle_color_advances_and_wraps_palette():
    sprite = Sprite(color=PALETTE[0])
    assert sprite.cycle_color() == PALETTE[1]

    for _ in range(len(PALETTE) - 1):
        sprite.cycle_color()
    assert sprite.color == PALETTE[0]


def test_render_places_element_at_position():
    sprite = Sprite(size=1, color=(0, 255, 0))
    sprite.set_position(5, 7, 32, 16)

    img = sprite.render(32, 16)
    assert img.mode == "RGB"
    assert img.size == (32, 16)
    assert img.getpixel((5, 7)) == (0, 255, 0)
    # a corner away from the element stays black
    assert img.getpixel((0, 0)) == (0, 0, 0)


def test_render_background_is_black_around_a_single_pixel():
    sprite = Sprite(size=0, color=(255, 255, 255))
    sprite.set_position(1, 1, 8, 8)

    img = sprite.render(8, 8)
    assert img.getpixel((1, 1)) == (255, 255, 255)
    assert img.getpixel((5, 5)) == (0, 0, 0)


def test_send_frame_pushes_controlled_element_to_panel():
    panel = _make_panel(32, 16)
    sprite = Sprite(size=1, color=(0, 255, 0))
    sprite.set_position(3, 4, panel.width, panel.height)

    panel.send_frame(sprite.render(panel.width, panel.height))

    assert len(panel._client.calls) == 1
    hex_string, extension = panel._client.calls[0]
    assert extension == ".png"
    decoded = _decode(hex_string)
    assert decoded.size == (32, 16)
    assert decoded.getpixel((3, 4)) == (0, 255, 0)


def test_move_then_send_updates_element_position():
    panel = _make_panel(16, 16)
    # size=0 keeps the element to a single pixel so positions do not overlap.
    sprite = Sprite(size=0, color=(0, 255, 0))
    sprite.center(panel.width, panel.height)
    panel.send_frame(sprite.render(panel.width, panel.height))

    sprite.move(1, 0, panel.width, panel.height)
    panel.send_frame(sprite.render(panel.width, panel.height))

    assert len(panel._client.calls) == 2
    first = _decode(panel._client.calls[0][0])
    second = _decode(panel._client.calls[1][0])
    assert first.getpixel((8, 8)) == (0, 255, 0)
    assert second.getpixel((9, 8)) == (0, 255, 0)
    assert second.getpixel((8, 8)) == (0, 0, 0)


def test_sender_thread_pushes_frames_and_stops_cleanly():
    class FakePanel:
        def __init__(self):
            self.frames = []

        def send_frame(self, img):
            self.frames.append(img)

    panel = FakePanel()
    sender = _Sender(panel, fps=100)
    sender.start()
    try:
        sender.submit(Image.new("RGB", (4, 4), (0, 255, 0)))
        deadline = time.time() + 2.0
        while not panel.frames and time.time() < deadline:
            time.sleep(0.01)
    finally:
        sender.stop()
        sender.join(timeout=1.0)

    assert len(panel.frames) >= 1
    assert not sender.is_alive()
