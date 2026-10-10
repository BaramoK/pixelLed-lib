"""Real-time mirroring loop: render locally, push each frame to the panel."""

from __future__ import annotations

import time
from typing import Callable, Optional

from PIL import Image

from ..library.panel import Panel, use_panel
from ..library.render import render_bouncing_ball

Renderer = Callable[[float, int, int], Image.Image]


def run_mirror(
    address: str,
    fps: float = 10.0,
    duration: float = 0.0,
    brightness: Optional[int] = None,
    renderer: Renderer = render_bouncing_ball,
    on_stats: Optional[Callable[[float, int], None]] = None,
    panel: Optional[Panel] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> None:
    """Mirror locally rendered frames onto the panel until stopped.

    Args:
        address: Bluetooth MAC address of the panel.
        fps: Target refresh rate (frames per second).
        duration: Stop after this many seconds (0 = run until Ctrl+C).
        brightness: Optional brightness (0-100) applied on connect.
        renderer: Callable ``renderer(t, width, height) -> PIL.Image``.
        on_stats: Optional callback invoked after each frame with
            ``(measured_fps, frame_index)``.
        panel: Optional already connected panel to use instead of connecting;
            a borrowed panel is left open (see :func:`pixelplay.library.panel.use_panel`).
        should_stop: Optional predicate polled before each frame; the loop
            stops as soon as it returns True.
    """
    frame_interval = 1.0 / fps if fps > 0 else 0.0
    start = time.perf_counter()
    sent = 0

    with use_panel(address, brightness, panel) as panel:
        print(
            f"Connected to {panel.width}x{panel.height} panel "
            f"(LED type {panel.led_type})"
        )
        print(f"Mirroring at target {fps:g} fps - press Ctrl+C to stop.")
        try:
            while True:
                if should_stop is not None and should_stop():
                    break
                loop_start = time.perf_counter()
                elapsed = loop_start - start
                if duration > 0 and elapsed >= duration:
                    break

                frame = renderer(elapsed, panel.width, panel.height)
                panel.send_frame(frame)
                sent += 1

                if on_stats is not None:
                    measured = sent / (time.perf_counter() - start)
                    on_stats(measured, sent)

                # Throttle to the target frame rate.
                if frame_interval > 0:
                    sleep_for = frame_interval - (time.perf_counter() - loop_start)
                    if sleep_for > 0:
                        time.sleep(sleep_for)
        except KeyboardInterrupt:
            print("\nStopped by user.")

    total = time.perf_counter() - start
    effective = sent / total if total > 0 else 0.0
    print(f"Sent {sent} frames in {total:.2f}s -> {effective:.2f} fps effective.")
