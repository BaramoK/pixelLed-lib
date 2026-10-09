"""pixelplay - real-time mirroring of local frames to iPixel Color LED panels.

This package embeds :mod:`pypixelcolor` as a library dependency and adds a
small, testable layer on top of it:

- :class:`pixelplay.panel.Panel` : connected panel wrapper.
- :mod:`pixelplay.render` : pure frame renderers (no BLE, unit testable).
- :mod:`pixelplay.control` : controllable element (no BLE, unit testable).
- :mod:`pixelplay.mirror` : real-time mirroring loop.
- :mod:`pixelplay.bench` : frame-rate benchmark.
- :mod:`pixelplay.play` : interactive keyboard control of an element on the panel.
- :mod:`pixelplay.breakout` : brick-breaker demo rendered on the panel.
- :mod:`pixelplay.tetris` : Tetris demo rendered on the panel.
- :mod:`pixelplay.text` : tiny 4x6 bitmap font drawn with PIL.
- :mod:`pixelplay.menu` : launcher drawn on the panel (auto-scrolling).
"""

from .breakout import Breakout, run_breakout
from .control import Sprite
from .menu import Layout, Menu, MenuItem, run_menu
from .panel import Panel
from .play import run_play
from .render import (
    RENDERERS,
    render_bars,
    render_bouncing_ball,
    render_gradient,
)
from .tetris import Tetris, run_tetris

__version__ = "0.1.0"

__all__ = [
    "Breakout",
    "Layout",
    "Menu",
    "MenuItem",
    "Panel",
    "RENDERERS",
    "Sprite",
    "Tetris",
    "render_bars",
    "render_bouncing_ball",
    "render_gradient",
    "run_breakout",
    "run_menu",
    "run_play",
    "run_tetris",
    "__version__",
]
