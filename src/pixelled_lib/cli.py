"""Command line interface for pixelled_lib."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from . import __version__
from .debug.bench import run_bench
from .debug.mirror import run_mirror
from .debug.play import run_play
from .launcher import run_launcher
from .library.panel import Panel
from .library.render import RENDERERS, render_bouncing_ball


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-a",
        "--address",
        required=True,
        help="Bluetooth MAC address of the panel (e.g. 30:E1:AF:BD:5F:D0).",
    )
    parser.add_argument(
        "-b",
        "--brightness",
        type=int,
        default=None,
        help="Brightness 0-100 applied on connect.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pixelled-lib",
        description=(
            "Mirror locally rendered frames to an iPixel Color LED matrix "
            "panel (built on pypixelcolor)."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"pixelled-lib {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="Connect and print panel information.")
    _add_common(p_info)

    p_bench = sub.add_parser("bench", help="Benchmark the achievable frame rate.")
    _add_common(p_bench)
    p_bench.add_argument(
        "-n", "--frames", type=int, default=60, help="Number of frames (default 60)."
    )
    p_bench.add_argument(
        "--pattern", choices=sorted(RENDERERS), default="bars", help="Test pattern."
    )

    p_mirror = sub.add_parser(
        "mirror", help="Mirror a locally rendered animation in real time."
    )
    _add_common(p_mirror)
    p_mirror.add_argument(
        "--fps", type=float, default=10.0, help="Target frames per second (default 10)."
    )
    p_mirror.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Stop after N seconds (0 = until Ctrl+C).",
    )
    p_mirror.add_argument(
        "--pattern",
        choices=sorted(RENDERERS),
        default="ball",
        help="Animation pattern.",
    )

    p_play = sub.add_parser(
        "play",
        help="Interactively control an element on the panel from this workstation.",
    )
    _add_common(p_play)
    p_play.add_argument(
        "--scale",
        type=int,
        default=12,
        help="Preview magnification, screen pixels per LED (default 12).",
    )
    p_play.add_argument(
        "--fps", type=float, default=10.0, help="Target frames per second (default 10)."
    )
    p_play.add_argument(
        "--size", type=int, default=3, help="Element half-size in pixels (default 3)."
    )

    p_menu = sub.add_parser(
        "menu",
        help="Show a launcher on the panel and run the selected tool.",
    )
    _add_common(p_menu)
    p_menu.add_argument(
        "--fps", type=float, default=10.0, help="Menu refresh rate (default 10)."
    )
    p_menu.add_argument(
        "--scale",
        type=int,
        default=12,
        help="Preview magnification for 'play' (default 12).",
    )
    p_menu.add_argument(
        "--auto",
        type=float,
        default=2.0,
        help="Seconds per item while auto-scrolling (0 = off, default 2).",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "info":
        with Panel(args.address, brightness=args.brightness) as panel:
            print(panel.describe())
        return 0

    if args.command == "bench":
        run_bench(
            args.address,
            frames=args.frames,
            pattern=args.pattern,
            brightness=args.brightness,
        )
        return 0

    if args.command == "mirror":
        renderer = RENDERERS.get(args.pattern, render_bouncing_ball)
        run_mirror(
            args.address,
            fps=args.fps,
            duration=args.duration,
            brightness=args.brightness,
            renderer=renderer,
        )
        return 0

    if args.command == "play":
        run_play(
            args.address,
            brightness=args.brightness,
            scale=args.scale,
            fps=args.fps,
            size=args.size,
        )
        return 0

    if args.command == "menu":
        run_launcher(
            args.address,
            brightness=args.brightness,
            fps=args.fps,
            scale=args.scale,
            auto=args.auto,
        )
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
