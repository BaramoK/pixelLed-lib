"""Interactive harness to test display offloading from the workstation.

Opens a local ``tkinter`` window showing a magnified preview of the panel and
lets you move a controllable element (:class:`pixelplay.control.Sprite`) with
the keyboard. Every change is mirrored to the physical panel, so you can check
end-to-end that what you control locally is displayed remotely.

Mirroring runs in a small background thread that keeps pushing the latest frame;
the window therefore stays responsive even though BLE is slow.
"""

from __future__ import annotations

from typing import Optional

from PIL import Image

from .control import Sprite
from .panel import Panel, use_panel
from .sender import FrameSender

# Backwards-compatible alias: ``_Sender`` used to live in this module.
_Sender = FrameSender

_HELP = "arrows/WASD: move   c: colour   r: recentre   q/Esc: quit"


def run_play(
    address: str,
    brightness: Optional[int] = None,
    scale: int = 12,
    fps: float = 10.0,
    size: int = 3,
    panel: Optional[Panel] = None,
) -> None:
    """Control a graphical element on the panel from this workstation.

    Args:
        address: Bluetooth MAC address of the panel.
        brightness: Optional brightness (0-100) applied on connect.
        scale: Preview magnification factor (screen pixels per LED).
        fps: Target send rate (frames per second).
        size: Half-size of the controlled element in pixels.
        panel: Optional already connected panel to use instead of connecting;
            a borrowed panel is left open (see :func:`pixelplay.panel.use_panel`).
    """
    import tkinter as tk

    from PIL import ImageTk

    scale = max(1, int(scale))
    with use_panel(address, brightness, panel) as panel:
        print(
            f"Connected to {panel.width}x{panel.height} panel "
            f"(LED type {panel.led_type})"
        )
        print(f"Preview scale x{scale}. {_HELP}")

        sprite = Sprite(size=size)
        sprite.center(panel.width, panel.height)

        sender = FrameSender(panel, fps)
        sender.start()

        view_w = panel.width * scale
        view_h = panel.height * scale

        root = tk.Tk()
        root.title(f"pixelplay play - {panel.width}x{panel.height} @ {address}")
        canvas = tk.Canvas(
            root, width=view_w, height=view_h, highlightthickness=0, bg="black"
        )
        canvas.pack()
        status = tk.Label(root, anchor="w", font=("Consolas", 9))
        status.pack(fill="x")

        photo = None  # keep a reference so Tk does not garbage-collect it

        def redraw() -> None:
            nonlocal photo
            img = sprite.render(panel.width, panel.height)
            preview = img.resize((view_w, view_h), Image.NEAREST) if scale > 1 else img
            photo = ImageTk.PhotoImage(preview)
            canvas.delete("all")
            canvas.create_image(0, 0, image=photo, anchor="nw")
            status.config(
                text=f"pos=({sprite.x},{sprite.y})  sent={sender.sent}  |  {_HELP}"
            )
            sender.submit(img)

        def on_key(event) -> None:
            key = event.keysym.lower()
            if key in ("up", "w"):
                sprite.move(0, -1, panel.width, panel.height)
            elif key in ("down", "s"):
                sprite.move(0, 1, panel.width, panel.height)
            elif key in ("left", "a"):
                sprite.move(-1, 0, panel.width, panel.height)
            elif key in ("right", "d"):
                sprite.move(1, 0, panel.width, panel.height)
            elif key == "c":
                sprite.cycle_color()
            elif key == "r":
                sprite.center(panel.width, panel.height)
            elif key in ("q", "escape"):
                root.destroy()
                return
            else:
                return
            redraw()

        root.bind("<Key>", on_key)
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.focus_force()
        redraw()
        try:
            root.mainloop()
        finally:
            sender.stop()
            sender.join(timeout=1.0)

        print(f"Sent {sender.sent} frames.")
