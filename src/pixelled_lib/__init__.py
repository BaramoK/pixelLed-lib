"""pixelled_lib - real-time mirroring of local frames to iPixel Color LED panels.

This package embeds :mod:`pypixelcolor` as a library dependency and is split
into two parts:

- :mod:`pixelled_lib.library` : the reusable API.
  :class:`~pixelled_lib.library.panel.Panel` and
  :class:`~pixelled_lib.library.sender.FrameSender` are the only modules
  touching BLE; :mod:`~pixelled_lib.library.render`,
  :mod:`~pixelled_lib.library.control`, :mod:`~pixelled_lib.library.text`,
  :mod:`~pixelled_lib.library.keys` and :mod:`~pixelled_lib.library.menu` are
  pure and unit testable without hardware.
- :mod:`pixelled_lib.debug` : diagnostic / proof-of-concept tools run against a
  real panel (bench, mirror, play).

:mod:`pixelled_lib.launcher` is the on-panel launcher that ties the debug tools
together, and :mod:`pixelled_lib.cli` exposes everything on the command line.
Games live in the companion project ``pixelled_play``, which reuses
:mod:`pixelled_lib.library`.
"""

from .debug.play import run_play
from .launcher import run_launcher
from .library.control import Sprite
from .library.menu import Layout, Menu, MenuGroup, MenuItem, run_menu
from .library.panel import Panel
from .library.render import (
    RENDERERS,
    render_bars,
    render_bouncing_ball,
    render_gradient,
)

__version__ = "0.1.0"

__all__ = [
    "Layout",
    "Menu",
    "MenuGroup",
    "MenuItem",
    "Panel",
    "RENDERERS",
    "Sprite",
    "render_bars",
    "render_bouncing_ball",
    "render_gradient",
    "run_launcher",
    "run_menu",
    "run_play",
    "__version__",
]
