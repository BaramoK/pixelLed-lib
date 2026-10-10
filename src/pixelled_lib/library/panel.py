"""Thin wrapper around :class:`pypixelcolor.Client` used to push frames.

This module intentionally contains no low-level BLE logic: it reuses
``pypixelcolor`` as a library and only handles frame normalization/encoding.
"""

from __future__ import annotations

import io
from contextlib import contextmanager
from typing import Iterator, Optional

from PIL import Image

from pypixelcolor import Client


@contextmanager
def use_panel(
    address: str,
    brightness: Optional[int] = None,
    panel: Optional["Panel"] = None,
) -> Iterator["Panel"]:
    """Yield a panel, connecting to ``address`` only when none was given.

    The interactive tools accept an optional, already connected panel (the
    launcher shares a single BLE connection with everything it runs). A panel
    that was *borrowed* is never closed: the owner stays in charge of it.
    """
    if panel is not None:
        yield panel
        return
    with Panel(address, brightness=brightness) as owned:
        yield owned


class Panel:
    """A connected LED matrix panel.

    Parameters
    ----------
    address:
        Bluetooth MAC address of the device (e.g. ``"30:E1:AF:BD:5F:D0"``).
    brightness:
        Optional brightness (0-100) applied right after connecting.
    """

    def __init__(self, address: str, brightness: Optional[int] = None):
        self._client = Client(address)
        self._client.connect()
        try:
            info = self._client.get_device_info()
        except Exception:
            self._client.disconnect()
            raise
        self.width = info.width
        self.height = info.height
        self.led_type = info.led_type
        self.device_info = info
        if brightness is not None:
            self._client.set_brightness(int(brightness))

    @property
    def size(self) -> tuple[int, int]:
        """Return the panel size as ``(width, height)``."""
        return (self.width, self.height)

    def describe(self) -> str:
        """Return a short human-readable description of the connected device."""
        return (
            f"Size     : {self.width}x{self.height}\n"
            f"LED type : {self.led_type}\n"
            f"Device   : {self.device_info}"
        )

    def send_png_bytes(self, png_bytes: bytes) -> None:
        """Send raw PNG bytes to the panel via ``send_image_hex``."""
        self._client.send_image_hex(png_bytes.hex(), ".png")

    def send_frame(self, img: Image.Image) -> None:
        """Send a single frame to the panel.

        The image is converted to ``RGB`` and resized to the exact panel
        size when needed, then PNG-encoded in memory and pushed. Because the
        image already matches the panel size/mode, ``pypixelcolor`` skips its
        own resize/re-encode step.
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        if img.size != (self.width, self.height):
            img = img.resize((self.width, self.height))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        self.send_png_bytes(buf.getvalue())

    def close(self) -> None:
        """Disconnect from the device (idempotent)."""
        try:
            self._client.disconnect()
        except Exception:
            pass

    def __enter__(self) -> "Panel":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
