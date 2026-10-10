"""Background frame sender shared by the interactive tools.

BLE writes are slow compared to UI/game ticks, so the interactive tools hand
frames to a :class:`FrameSender` thread which keeps pushing the *latest* frame.
If several frames are submitted while a send is in flight the older ones are
dropped, which keeps the UI responsive and avoids a growing backlog.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from PIL import Image

from .panel import Panel


class FrameSender(threading.Thread):
    """Thread pushing the most recently submitted frame to a panel.

    Parameters
    ----------
    panel:
        Connected panel to push frames to.
    fps:
        Target send rate (frames per second); ``<= 0`` sends as fast as possible.
    """

    def __init__(self, panel: Panel, fps: float):
        super().__init__(daemon=True)
        self._panel = panel
        self._interval = 1.0 / fps if fps > 0 else 0.0
        self._lock = threading.Lock()
        self._frame: Optional[Image.Image] = None
        self._has_frame = threading.Event()
        # NB: do not name this ``_stop`` - it would shadow ``Thread._stop``.
        self._stop_event = threading.Event()
        self.sent = 0

    def submit(self, img: Image.Image) -> None:
        """Store ``img`` as the next frame to send (replacing any pending one)."""
        with self._lock:
            self._frame = img
        self._has_frame.set()

    def stop(self) -> None:
        """Ask the thread to exit as soon as possible."""
        self._stop_event.set()
        self._has_frame.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            if not self._has_frame.wait(timeout=0.2):
                continue
            with self._lock:
                img = self._frame
                self._frame = None
                self._has_frame.clear()
            if img is None:
                continue
            started = time.perf_counter()
            try:
                self._panel.send_frame(img)
                self.sent += 1
            except Exception as exc:  # keep the caller alive on transient errors
                print(f"Send error: {exc}")
            remaining = self._interval - (time.perf_counter() - started)
            if remaining > 0:
                self._stop_event.wait(remaining)
