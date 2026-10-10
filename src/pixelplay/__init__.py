"""pixelplay - real-time mirroring of local frames to iPixel Color LED panels.

This package embeds :mod:`pypixelcolor` as a library dependency and is split
into three parts:

- :mod:`pixelplay.library` : the reusable API.
  :class:`~pixelplay.library.panel.Panel` and
  :class:`~pixelplay.library.sender.FrameSender` are the only modules touching
  BLE; :mod:`~pixelplay.library.render`, :mod:`~pixelplay.library.control`,
  :mod:`~pixelplay.library.text` and :mod:`~pixelplay.library.keys` are pure
  and unit testable without hardware.
- :mod:`pixelplay.debug` : diagnostic / proof-of-concept tools run against a
  real panel (bench, mirror, play).
- :mod:`pixelplay.games` : games rendered on the panel (breakout, tetris).

:mod:`pixelplay.menu` is the on-panel launcher that ties both tool sets
together, and :mod:`pixelplay.cli` exposes everything on the command line.
"""

from .debug.play import run_play
from .games.breakout import Breakout, run_breakout
from .games.tetris import Tetris, run_tetris
from .library.control import Sprite
from .library.panel import Panel
from .library.render import (
    RENDERERS,
    render_bars,
    render_bouncing_ball,
    render_gradient,
)
from .menu import Layout, Menu, MenuItem, run_menu

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
