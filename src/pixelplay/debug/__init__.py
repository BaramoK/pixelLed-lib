"""Diagnostic and proof-of-concept tools run against a real panel.

These are the manual end-to-end checks of the display offloading:
:mod:`bench` measures the achievable frame rate, :mod:`mirror` streams a
locally rendered animation and :mod:`play` controls an element from the
workstation. Unlike :mod:`pixelplay.library` they talk to hardware.
"""

from .bench import run_bench
from .mirror import run_mirror
from .play import run_play

__all__ = ["run_bench", "run_mirror", "run_play"]
