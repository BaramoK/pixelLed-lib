"""Reusable, application-agnostic building blocks (the public API layer).

Modules here contain no CLI and no application wiring. :class:`Panel` and
:class:`FrameSender` are the only ones touching BLE; everything else
(:mod:`render`, :mod:`control`, :mod:`text`, :mod:`keys`) is pure and can be
unit tested without a physical panel.
"""

from .control import PALETTE, Sprite
from .keys import KeyRepeater
from .panel import Panel, use_panel
from .render import (
    RENDERERS,
    render_bars,
    render_bouncing_ball,
    render_gradient,
)
from .sender import FrameSender
from .text import (
    GLYPH_H,
    GLYPH_W,
    SPACING,
    draw_text,
    text_height,
    text_pitch,
    text_width,
)

__all__ = [
    "FrameSender",
    "GLYPH_H",
    "GLYPH_W",
    "KeyRepeater",
    "PALETTE",
    "Panel",
    "RENDERERS",
    "SPACING",
    "Sprite",
    "draw_text",
    "render_bars",
    "render_bouncing_ball",
    "render_gradient",
    "text_height",
    "text_pitch",
    "text_width",
    "use_panel",
]
