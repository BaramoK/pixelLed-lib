"""Frame renderers producing :class:`PIL.Image.Image` at panel size.

All functions are pure (no BLE, no I/O) so they can be unit tested without a
physical device. Each returns an ``RGB`` image of size ``(width, height)``.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

Color = tuple[int, int, int]


def _new_frame(
    width: int, height: int, bg: Color = (0, 0, 0)
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (width, height), bg)
    return img, ImageDraw.Draw(img)


def render_bars(
    t: float, width: int, height: int, color: Color = (0, 120, 255)
) -> Image.Image:
    """Vertical bars scrolling horizontally over time."""
    img, draw = _new_frame(width, height)
    bar_width = max(1, width // 8)
    offset = int(t * width) % width if width else 0
    x = -offset
    while x < width:
        draw.rectangle([x, 0, x + bar_width - 1, height - 1], fill=color)
        x += bar_width * 2
    return img


def render_gradient(t: float, width: int, height: int) -> Image.Image:
    """Smooth colour gradient animated over time."""
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    phase = t * 2.0
    for x in range(width):
        for y in range(height):
            r = int((math.sin(phase + x * 0.3) * 0.5 + 0.5) * 255)
            g = int((math.sin(phase + y * 0.3 + 2.0) * 0.5 + 0.5) * 255)
            b = int((math.sin(phase + (x + y) * 0.15 + 4.0) * 0.5 + 0.5) * 255)
            pixels[x, y] = (r, g, b)
    return img


def _ping_pong(period: float, value: float) -> float:
    """Return a value in ``[0, 1]`` that bounces back and forth over ``period``."""
    if period <= 0:
        return 0.0
    pos = (value % period) / period
    return pos * 2 if pos < 0.5 else (1 - pos) * 2


def render_bouncing_ball(
    t: float, width: int, height: int, color: Color = (255, 64, 0)
) -> Image.Image:
    """A small ball bouncing around the panel."""
    img, draw = _new_frame(width, height)
    radius = max(1, min(width, height) // 8)

    span_x = max(1, width - 2 * radius)
    span_y = max(1, height - 2 * radius)
    cx = radius + _ping_pong(2.0, t) * span_x
    cy = radius + _ping_pong(3.0, t) * span_y

    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)
    return img


RENDERERS = {
    "bars": render_bars,
    "gradient": render_gradient,
    "ball": render_bouncing_ball,
}
