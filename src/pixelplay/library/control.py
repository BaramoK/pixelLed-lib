"""A single controllable graphical element, decoupled from BLE.

The :class:`Sprite` is the element that can be moved/controlled from the
workstation. Like the renderers in :mod:`pixelplay.library.render` it is
deliberately
pure (no BLE, no I/O) so it can be unit tested without any hardware.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

Color = tuple[int, int, int]

# Colours cycled through by :meth:`Sprite.cycle_color`.
PALETTE: tuple[Color, ...] = (
    (0, 255, 0),
    (255, 0, 0),
    (0, 128, 255),
    (255, 255, 0),
    (255, 0, 255),
    (255, 255, 255),
)


def _clamp(value: int, low: int, high: int) -> int:
    """Return ``value`` constrained to ``[low, high]``."""
    return max(low, min(high, value))


class Sprite:
    """A controllable square drawn on a black frame.

    The position ``(x, y)`` is the centre of the element and is always kept
    inside the panel bounds. The sprite does not know the panel size itself:
    it is passed to :meth:`move`, :meth:`set_position`, :meth:`center` and
    :meth:`render`, which keeps the object easy to test at any size.

    Parameters
    ----------
    size:
        Half-size of the square in pixels (the square spans ``2*size+1``).
    color:
        Fill colour as an ``(r, g, b)`` tuple.
    """

    def __init__(self, size: int = 3, color: Color = PALETTE[0]):
        self.size = max(0, int(size))
        self.color = color
        self.x = 0
        self.y = 0

    def set_position(self, x: int, y: int, width: int, height: int) -> None:
        """Move the sprite to ``(x, y)`` clamped to the panel bounds."""
        self.x = _clamp(int(x), 0, max(0, width - 1))
        self.y = _clamp(int(y), 0, max(0, height - 1))

    def move(self, dx: int, dy: int, width: int, height: int) -> None:
        """Move the sprite by ``(dx, dy)`` clamped to the panel bounds."""
        self.set_position(self.x + dx, self.y + dy, width, height)

    def center(self, width: int, height: int) -> None:
        """Place the sprite at the centre of the panel."""
        self.set_position(width // 2, height // 2, width, height)

    def cycle_color(self) -> Color:
        """Advance to the next colour of :data:`PALETTE` and return it."""
        try:
            index = PALETTE.index(self.color)
        except ValueError:
            index = -1
        self.color = PALETTE[(index + 1) % len(PALETTE)]
        return self.color

    def render(self, width: int, height: int) -> Image.Image:
        """Return an ``RGB`` frame with the sprite on a black background."""
        img = Image.new("RGB", (width, height), (0, 0, 0))
        if width <= 0 or height <= 0:
            return img
        x = _clamp(self.x, 0, width - 1)
        y = _clamp(self.y, 0, height - 1)
        draw = ImageDraw.Draw(img)
        draw.rectangle(
            [x - self.size, y - self.size, x + self.size, y + self.size],
            fill=self.color,
        )
        return img
