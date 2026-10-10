"""Benchmark how fast frames can be pushed to the panel."""

from __future__ import annotations

import io
import time
from typing import Optional

from ..library.panel import Panel, use_panel
from ..library.render import RENDERERS, render_bars


def run_bench(
    address: str,
    frames: int = 60,
    pattern: str = "bars",
    brightness: Optional[int] = None,
    panel: Optional[Panel] = None,
) -> None:
    """Measure per-frame timing and the effective achievable frame rate.

    Args:
        address: Bluetooth MAC address of the panel.
        frames: Number of frames to send.
        pattern: One of the keys of ``render.RENDERERS``.
        brightness: Optional brightness (0-100) applied on connect.
        panel: Optional already connected panel to use instead of connecting;
            a borrowed panel is left open (see :func:`pixelplay.library.panel.use_panel`).
    """
    renderer = RENDERERS.get(pattern, render_bars)
    encode_timings: list[float] = []
    send_timings: list[float] = []

    with use_panel(address, brightness, panel) as panel:
        print(
            f"Connected to {panel.width}x{panel.height} panel "
            f"(LED type {panel.led_type})"
        )
        print(f"Benchmarking '{pattern}' over {frames} frames...")

        for i in range(frames):
            t = i / 10.0
            frame = renderer(t, panel.width, panel.height)

            # Measure PNG encoding separately from the BLE transfer.
            t0 = time.perf_counter()
            buf = io.BytesIO()
            frame.save(buf, format="PNG")
            encode_timings.append(time.perf_counter() - t0)

            payload = buf.getvalue()
            t1 = time.perf_counter()
            panel.send_png_bytes(payload)
            send_timings.append(time.perf_counter() - t1)

    if not send_timings:
        print("No frames sent.")
        return

    avg_encode = sum(encode_timings) / len(encode_timings)
    avg_send = sum(send_timings) / len(send_timings)
    avg_total = avg_encode + avg_send

    print("")
    print(f"Frames sent      : {len(send_timings)}")
    print(f"Avg encode (PNG) : {avg_encode * 1000:.1f} ms")
    print(f"Avg send (BLE)   : {avg_send * 1000:.1f} ms")
    print(f"Min send         : {min(send_timings) * 1000:.1f} ms")
    print(f"Max send         : {max(send_timings) * 1000:.1f} ms")
    print(f"Effective rate   : {1.0 / avg_total:.2f} fps")
