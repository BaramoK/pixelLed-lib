"""Unit tests for the Panel frame-pushing logic (no BLE required).

``Panel.__new__`` is used to bypass the constructor (which would open a real
Bluetooth connection) and inject a fake client that records the payloads.
"""

import io

from PIL import Image

from pixelplay.panel import Panel

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


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
    return Image.open(io.BytesIO(bytes.fromhex(hex_string)))


def test_send_frame_pushes_png_hex():
    panel = _make_panel(32, 16)
    panel.send_frame(Image.new("RGBA", (32, 16), (255, 0, 0, 255)))

    assert len(panel._client.calls) == 1
    hex_string, extension = panel._client.calls[0]
    assert extension == ".png"
    assert bytes.fromhex(hex_string)[:8] == PNG_MAGIC


def test_send_frame_resizes_to_panel_size():
    panel = _make_panel(32, 32)
    panel.send_frame(Image.new("RGB", (100, 100), (0, 255, 0)))

    hex_string, _ = panel._client.calls[0]
    decoded = _decode(hex_string)
    assert decoded.size == (32, 32)
    assert decoded.mode == "RGB"


def test_send_frame_converts_mode_and_preserves_pixels():
    panel = _make_panel(64, 64)
    panel.send_frame(Image.new("RGB", (64, 64), (10, 20, 30)))

    hex_string, _ = panel._client.calls[0]
    decoded = _decode(hex_string)
    assert decoded.size == (64, 64)
    assert decoded.getpixel((0, 0)) == (10, 20, 30)


def test_send_png_bytes_hex_encodes():
    panel = _make_panel(8, 8)
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (1, 2, 3)).save(buf, format="PNG")

    panel.send_png_bytes(buf.getvalue())

    hex_string, extension = panel._client.calls[0]
    assert extension == ".png"
    assert bytes.fromhex(hex_string) == buf.getvalue()


def test_describe_reports_size_led_type_and_device():
    panel = _make_panel(64, 32)

    assert panel.describe() == (
        "Size     : 64x32\nLED type : RGB\nDevice   : None"
    )
