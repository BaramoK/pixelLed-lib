"""The on-panel launcher for the library's debug tools.

The launcher engine lives in :mod:`pixelled_lib.library.menu`; this module only
describes *which* tools the library ships (info, bench, mirror, play) and wires
them to the engine. Games live in their own project and provide their own
launcher.
"""

from __future__ import annotations

from typing import Optional

from .debug.bench import run_bench
from .debug.mirror import run_mirror
from .debug.play import run_play
from .library.menu import AUTO_DELAY_S, MenuGroup, MenuItem, run_menu
from .library.panel import Panel
from .library.render import render_bouncing_ball

# Frame count used when the launcher starts the benchmark.
_BENCH_FRAMES = 60


def build_debug_groups(
    address: str,
    fps: float = 10.0,
    scale: int = 12,
) -> list[MenuGroup]:
    """Build the debug launcher groups; each action borrows the panel it is given."""

    def show_info(panel: Panel) -> None:
        print(panel.describe())

    debug = [
        MenuItem("INFO", "show the panel information", show_info),
        MenuItem(
            "BENCH",
            "benchmark the achievable frame rate",
            lambda panel: run_bench(
                address, frames=_BENCH_FRAMES, pattern="bars", panel=panel
            ),
        ),
        MenuItem(
            "MIRROR",
            "mirror the bouncing ball until a key is pressed",
            lambda panel: _mirror_until_key(address, panel, fps),
        ),
        MenuItem(
            "PLAY",
            "control an element with the keyboard",
            lambda panel: run_play(address, scale=scale, fps=fps, panel=panel),
        ),
    ]
    return [MenuGroup("DEBUG", "debug tools", debug)]


def _mirror_until_key(address: str, panel: Panel, fps: float) -> None:
    """Mirror the default animation until any key is pressed.

    ``run_mirror`` blocks the thread that calls it, so the tiny window pumps
    its own event queue from ``should_stop`` to stay responsive.
    """
    from .library.window import Window

    state = {"stop": False}
    window = Window("pixelled mirror")
    window.label.config(
        text="mirroring the bouncing ball - press any key to stop"
    )

    def stop(_event=None) -> None:
        state["stop"] = True

    def should_stop() -> bool:
        window.root.update()  # the mirror loop blocks this thread: pump it here
        return state["stop"]

    window.bind("<Key>", stop)
    window.on_close(stop)
    window.show()
    print("Press any key in the mirror window to stop.")
    try:
        run_mirror(
            address,
            fps=fps,
            renderer=render_bouncing_ball,
            panel=panel,
            should_stop=should_stop,
        )
    finally:
        window.close()


def run_launcher(
    address: str,
    brightness: Optional[int] = None,
    fps: float = 10.0,
    scale: int = 12,
    auto: float = AUTO_DELAY_S,
) -> None:
    """Show the debug launcher on the panel and run the selected tool.

    Args:
        address: Bluetooth MAC address of the panel.
        brightness: Optional brightness (0-100) applied on connect.
        fps: Menu refresh rate (frames per second) and tool rate.
        scale: Preview magnification passed on to ``play``.
        auto: Seconds between two automatic moves (``0`` starts in keyboard
            mode; ``a`` still toggles auto-scrolling on).
    """
    with Panel(address, brightness=brightness) as panel:
        run_menu(
            panel,
            build_debug_groups(address, fps=fps, scale=scale),
            fps=fps,
            auto=auto,
            title="pixelled debug launcher",
        )
