"""A launcher menu drawn on the LED panel.

The panel has no buttons, so the menu is *displayed* on the matrix and driven
from the workstation keyboard through a minimal tkinter window - the same
pattern as the demos. It also scrolls by itself, so the panel is useful
without a keyboard at all: the first arrow key takes over, and auto-scrolling
resumes once the keyboard has been idle for a few seconds.

:class:`Menu` (state + rendering) and :class:`AutoPilot` (auto-scroll policy)
are pure - no BLE, no tkinter - and therefore unit tested; :func:`run_menu` is
the only part that opens a window and talks to hardware. The whole session
shares a single BLE connection: every tool borrows the panel opened here (see
:func:`pixelplay.library.panel.use_panel`) instead of reconnecting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence, Union

from PIL import Image, ImageDraw

from .debug.bench import run_bench
from .debug.mirror import run_mirror
from .debug.play import run_play
from .games.breakout import run_breakout
from .games.tetris import run_tetris
from .library.keys import KeyRepeater
from .library.panel import Panel
from .library.render import render_bouncing_ball
from .library.sender import FrameSender
from .library.text import (
    SPACING,
    draw_text,
    text_advance,
    text_height,
    text_pitch,
    text_width,
)

Color = tuple[int, int, int]

# Unselected rows are slightly dimmed: on a real matrix full white bleeds into
# the neighbouring LEDs and the whole list turns into a blob, while the white
# band of the selected row keeps the maximum contrast.
TEXT_COLOR: Color = (200, 200, 200)
SELECTED_BG: Color = (255, 255, 255)
SELECTED_FG: Color = (0, 0, 0)

MARGIN = 1  # black pixels kept around the text, unscaled
MIN_ROWS = 3  # a zoom that leaves fewer rows than this is not worth it
MAX_CHARS = 6  # longest label the launcher uses
AUTO_DELAY_S = 2.0  # seconds between two automatic moves
AUTO_RESUME_S = 5.0  # idle seconds after which auto-scrolling resumes

# Per-tool settings used when the launcher starts a tool.
_BENCH_FRAMES = 60
_BREAKOUT_FPS = 15.0
_TETRIS_FPS = 10.0

_HELP = (
    "up/down or W/S: move   1-9: jump   Enter: launch\n"
    "a: auto-scroll   Esc/Left/b: back   q: quit"
)


def chars_fit(width: int, scale: int) -> int:
    """How many characters fit on one line of ``width`` px at ``scale``."""
    usable = width - 2 * MARGIN + SPACING * scale
    return max(1, usable // text_advance(scale))


def rows_fit(height: int, scale: int) -> int:
    """How many rows fit in ``height`` px at ``scale``, gaps included."""
    usable = height - 2 * MARGIN - text_height(scale)
    return max(1, 1 + usable // text_pitch(scale))


def display_scale(width: int, height: int, chars: int = MAX_CHARS) -> int:
    """Return the biggest glyph scale that stays readable on that panel.

    A 4x6 glyph is still small when it is the only thing on a large matrix, so
    the scale is doubled as soon as the panel can show ``chars`` characters
    and MIN_ROWS rows at that size. A 32x32 matrix keeps single pixels, which
    is already 4x6 px per glyph and 6 characters per line.
    """
    for scale in (2, 1):
        if chars_fit(width, scale) >= chars and rows_fit(height, scale) >= MIN_ROWS:
            return scale
    return 1


def _fit(label: str, width: int, scale: int) -> str:
    """Uppercase ``label``, truncated so that it fits in ``width`` pixels."""
    return label.upper()[:chars_fit(width, scale)]


@dataclass(frozen=True)
class Layout:
    """Where the text goes on a given panel (all values in pixels).

    Attributes:
        scale: Glyph magnification (1 = 4x6 px per glyph).
        rows: How many items are drawn at once.
        pitch: Vertical distance between two rows.
        glyph_h: Height of one line of text.
        x: Left edge of the text block.
        y: Top edge of the first row.
    """

    scale: int
    rows: int
    pitch: int
    glyph_h: int
    x: int
    y: int


@dataclass(frozen=True)
class MenuItem:
    """One entry of the launcher.

    Attributes:
        label: Short uppercase label drawn on the panel (6 chars max).
        title: Human-readable description shown in the terminal.
        action: Called with the connected panel when the item is launched.
    """

    label: str
    title: str
    action: Callable[[Panel], None]


@dataclass(frozen=True)
class MenuGroup:
    """A named section of the launcher that opens its own sub-menu.

    Attributes:
        label: Short uppercase label drawn on the panel (6 chars max).
        title: Human-readable description shown in the terminal.
        items: The items of the group, shown when the group is opened.
    """

    label: str
    title: str
    items: Sequence[MenuItem]


class _Back:
    """Sentinel returned by :func:`_choose` when the user goes back a level."""


# Returned by _choose() when Esc/Left/b is pressed inside a group sub-menu.
_BACK = _Back()


def _noop(_panel: Panel) -> None:
    """Placeholder action for a group entry: opening the group does the work."""


class Menu:
    """Selection state of the launcher and its on-panel rendering.

    The menu is a pure object: it knows which item is selected and how to draw
    itself at a given size. All geometry adapts to the panel, so the same
    instance renders correctly on a 32x32 and on a 64x64 matrix.
    """

    def __init__(self, items: Sequence[MenuItem], index: int = 0) -> None:
        if not items:
            raise ValueError("a menu needs at least one item")
        self.items = list(items)
        self.index = int(index) % len(self.items)

    def move(self, delta: int) -> None:
        """Move the selection by ``delta`` items, wrapping around."""
        self.index = (self.index + delta) % len(self.items)

    def jump(self, number: int) -> bool:
        """Select the ``number``-th item (1-based); False when out of range."""
        if 1 <= number <= len(self.items):
            self.index = number - 1
            return True
        return False

    @property
    def selected(self) -> MenuItem:
        """The currently selected item."""
        return self.items[self.index]

    @property
    def longest(self) -> str:
        """Longest label of the menu; it drives the horizontal geometry."""
        return max((item.label for item in self.items), key=len)

    def rows(self, width: int, height: int) -> int:
        """Number of items drawn at once on that panel."""
        scale = display_scale(width, height, len(self.longest))
        return min(len(self.items), rows_fit(height, scale))

    def viewport(self, width: int, height: int) -> tuple[int, int]:
        """Return the inclusive ``(first, last)`` item indices to draw.

        The list scrolls only as far as it must, so the selection stays
        visible and a menu that fits does not move at all.
        """
        rows = self.rows(width, height)
        if rows >= len(self.items):
            return 0, len(self.items) - 1
        first = max(0, min(self.index - rows + 1, len(self.items) - rows))
        return first, first + rows - 1

    def layout(self, width: int, height: int) -> Layout:
        """Compute where the text goes on a ``width`` x ``height`` panel.

        Labels are left-aligned on a block that is centred, so the rows stay
        aligned with each other while the list scrolls.
        """
        scale = display_scale(width, height, len(self.longest))
        rows = self.rows(width, height)
        pitch = text_pitch(scale)
        glyph_h = text_height(scale)
        block_h = (rows - 1) * pitch + glyph_h
        block_w = text_width(_fit(self.longest, width, scale), scale)
        return Layout(
            scale=scale,
            rows=rows,
            pitch=pitch,
            glyph_h=glyph_h,
            x=max(0, (width - block_w) // 2),
            y=max(0, (height - block_h) // 2),
        )

    def render(self, width: int, height: int) -> Image.Image:
        """Draw the menu as an image of ``width`` x ``height`` pixels.

        The selected row is inverted (white band, black text).
        """
        layout = self.layout(width, height)
        first, last = self.viewport(width, height)
        image = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(image)
        padding = (layout.pitch - layout.glyph_h) // 2
        y = layout.y

        for index in range(first, last + 1):
            label = _fit(self.items[index].label, width, layout.scale)
            if index == self.index:
                top = max(0, y - padding)
                bottom = min(height - 1, top + layout.pitch - 1)
                draw.rectangle([0, top, width - 1, bottom], fill=SELECTED_BG)
                color = SELECTED_FG
            else:
                color = TEXT_COLOR
            draw_text(draw, layout.x, y, label, color, scale=layout.scale)
            y += layout.pitch

        return image


class AutoPilot:
    """Decide when the launcher moves on its own.

    The menu scrolls by itself so that the panel is useful without a keyboard.
    Any navigation key gives the keyboard control (:meth:`key`) and
    auto-scrolling resumes once the keyboard has been idle for ``resume``
    ticks. Both ``delay`` and ``resume`` are counted in ticks (the tools tick
    at ``--fps``), which keeps the policy independent from wall-clock jitter.
    """

    def __init__(self, delay: int, resume: int = 0, auto: bool = False) -> None:
        self.delay = max(1, int(delay))
        self.resume = max(0, int(resume))
        self.auto = bool(auto)
        self._ticks = 0
        self._idle = 0

    def key(self) -> None:
        """A navigation key was pressed: the keyboard takes over."""
        self.auto = False
        self._idle = 0
        self._ticks = 0

    def toggle(self) -> bool:
        """Flip auto-scrolling; return the new state."""
        self.auto = not self.auto
        self._idle = 0
        self._ticks = 0
        return self.auto

    def tick(self) -> bool:
        """Advance one tick; return True when the menu must move by one."""
        self._ticks += 1
        if self.auto:
            if self._ticks >= self.delay:
                self._ticks = 0
                return True
            return False
        if self.resume > 0 and self._idle < self.resume:
            self._idle += 1
            if self._idle >= self.resume:
                # The keyboard has been idle long enough: auto-scrolling takes
                # over again, and this very tick is a move.
                self._idle = 0
                self._ticks = 0
                self.auto = True
                return True
        return False


def _ticks(seconds: float, fps: float) -> int:
    """Convert a duration in seconds into a number of ticks (at least 1)."""
    return max(1, int(round(seconds * fps)))


def build_groups(
    address: str,
    fps: float = 10.0,
    scale: int = 12,
    seed: Optional[int] = None,
) -> list[MenuGroup]:
    """Build the launcher groups; each action borrows the panel it is given."""

    def show_info(panel: Panel) -> None:
        print(panel.describe())

    games = [
        MenuItem(
            "BRKOUT",
            "play the brick-breaker demo",
            lambda panel: run_breakout(
                address, fps=_BREAKOUT_FPS, seed=seed, panel=panel
            ),
        ),
        MenuItem(
            "TETRIS",
            "play the Tetris demo",
            lambda panel: run_tetris(
                address, fps=_TETRIS_FPS, seed=seed, panel=panel
            ),
        ),
    ]
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
    return [
        MenuGroup("GAMES", "games", games),
        MenuGroup("DEBUG", "debug tools", debug),
    ]


def _mirror_until_key(address: str, panel: Panel, fps: float) -> None:
    """Mirror the default animation until any key is pressed.

    ``run_mirror`` blocks the thread that calls it, so the tiny window pumps
    its own event queue from ``should_stop`` to stay responsive.
    """
    import tkinter as tk

    state = {"stop": False}
    root = tk.Tk()
    root.title("pixelplay mirror")
    tk.Label(
        root,
        font=("Consolas", 9),
        text="mirroring the bouncing ball - press any key to stop",
    ).pack(padx=10, pady=10)

    def stop(_event=None) -> None:
        state["stop"] = True
        try:
            root.destroy()
        except tk.TclError:
            pass

    def should_stop() -> bool:
        try:
            root.update()
        except tk.TclError:
            return True  # the window is gone: stop the loop
        return state["stop"]

    root.bind("<Key>", stop)
    root.protocol("WM_DELETE_WINDOW", stop)
    root.focus_force()
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
        try:
            root.destroy()
        except tk.TclError:
            pass


def run_menu(
    address: str,
    brightness: Optional[int] = None,
    fps: float = 10.0,
    scale: int = 12,
    seed: Optional[int] = None,
    auto: float = AUTO_DELAY_S,
) -> None:
    """Show the launcher on the panel and run whichever tool is selected.

    The launcher is grouped: the root menu lists the groups (Games, Debug)
    and choosing one opens its sub-menu. The panel is connected once for the
    whole session: the selected tool borrows that connection, and its group
    comes back when the tool exits (Esc/Left/``b`` returns to the root).

    Args:
        address: Bluetooth MAC address of the panel.
        brightness: Optional brightness (0-100) applied on connect.
        fps: Menu refresh rate (frames per second) and tool rate.
        scale: Preview magnification passed on to ``play``.
        seed: Optional RNG seed passed on to the games.
        auto: Seconds between two automatic moves (``0`` starts in keyboard
            mode; ``a`` still toggles auto-scrolling on).
    """
    groups = build_groups(address, fps=fps, scale=scale, seed=seed)
    by_label = {group.label: group for group in groups}
    root = Menu([MenuItem(group.label, group.title, _noop) for group in groups])

    with Panel(address, brightness=brightness) as panel:
        print(panel.describe())
        if auto > 0:
            print(f"pixelplay launcher (auto-scroll: {auto:g}s per item)")
        else:
            print("pixelplay launcher (auto-scroll off)")
        print(_HELP)
        delay = _ticks(auto if auto > 0 else AUTO_DELAY_S, fps)
        resume = _ticks(AUTO_RESUME_S, fps) if auto > 0 else 0
        while True:
            group = _choose(
                panel, root, fps, delay=delay, resume=resume, auto=auto > 0
            )
            if group is None:
                print("Bye.")
                return
            menu = Menu(by_label[group.label].items)
            print(f"--- {by_label[group.label].title} ---")
            while True:
                item = _choose(
                    panel,
                    menu,
                    fps,
                    delay=delay,
                    resume=resume,
                    auto=auto > 0,
                    allow_back=True,
                )
                if item is None:
                    print("Bye.")
                    return
                if item is _BACK:
                    break
                print(f"--- {item.title} ---")
                item.action(panel)
                print("--- back to the launcher ---")


def _choose(
    panel: Panel,
    menu: Menu,
    fps: float,
    delay: int,
    resume: int,
    auto: bool,
    allow_back: bool = False,
) -> Union[MenuItem, _Back, None]:
    """Run the launcher window; return the chosen item, or None to quit.

    When ``allow_back`` is set (a group sub-menu), Esc/Left/``b`` returns
    :data:`_BACK` so the caller can go back up one level instead of quitting.

    Only the keyboard is displayed on screen - the whole point is the panel -
    so the window is a single label with the help text.
    """
    import tkinter as tk

    interval = max(1, int(round(1000 / fps))) if fps > 0 else 100
    repeater = KeyRepeater()
    pilot = AutoPilot(delay=delay, resume=resume, auto=auto)
    sender = FrameSender(panel, fps)
    sender.start()
    choice: Optional[MenuItem] = None
    back = False
    alive = True

    root = tk.Tk()
    root.title("pixelplay launcher - keyboard")
    label = tk.Label(root, anchor="w", justify="left", font=("Consolas", 9))
    label.pack(padx=10, pady=10)

    def redraw() -> None:
        mode = "auto" if pilot.auto else "keyboard"
        label.config(
            text=(
                f"[{menu.index + 1}/{len(menu.items)}] {menu.selected.title}"
                f"   mode: {mode}\n{_HELP}"
            )
        )
        sender.submit(menu.render(panel.width, panel.height))

    def close() -> None:
        """Tear the window down, once (idempotent)."""
        nonlocal alive
        if not alive:
            return
        alive = False
        root.destroy()

    def launch() -> None:
        nonlocal choice
        choice = menu.selected
        close()

    def go_back() -> None:
        """Ask the caller to go back up one level, once (idempotent)."""
        nonlocal back
        back = True
        close()

    def handle(key: str) -> bool:
        """Apply one key press; return True when the display changed."""
        if key in ("up", "w", "k"):
            pilot.key()
            menu.move(-1)
            return True
        if key in ("down", "s", "j"):
            pilot.key()
            menu.move(1)
            return True
        if len(key) == 1 and key in "123456789":
            if menu.jump(int(key)):
                pilot.key()
                return True
            return False
        if key == "a":
            pilot.toggle()
            return True
        if allow_back and key in ("escape", "left", "b"):
            go_back()
            return False
        if key in ("q", "escape"):
            close()
        return False

    def on_press(event) -> None:
        key = event.keysym.lower()
        if not repeater.press(key):
            return  # OS auto-repeat: the tick already repeats held keys
        if key in ("return", "kp_enter", "space"):
            launch()
            return
        if handle(key):
            redraw()

    def on_release(event) -> None:
        repeater.release(event.keysym.lower())

    def on_focus_out(_event) -> None:
        repeater.clear()  # no KeyRelease is delivered when the focus is lost

    def tick() -> None:
        if not alive:
            return
        changed = False
        for key in repeater.due():
            changed = handle(key) or changed
        if alive and pilot.tick():
            menu.move(1)
            changed = True
        if alive and changed:
            redraw()
        if alive:
            root.after(interval, tick)

    root.bind("<KeyPress>", on_press)
    root.bind("<KeyRelease>", on_release)
    root.bind("<FocusOut>", on_focus_out)
    root.protocol("WM_DELETE_WINDOW", close)
    root.focus_force()
    redraw()
    root.after(interval, tick)
    try:
        root.mainloop()
    finally:
        sender.stop()
        sender.join(timeout=1.0)
    return _BACK if back else choice
