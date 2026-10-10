# Implementation guide — `pixelplay.library`

## 1. Goal and scope

`pixelplay.library` groups the **reusable**, **application-agnostic** building
blocks: no diagnostic/POC tool (→ `pixelplay.debug`), no game
(→ `pixelplay.games`), no orchestration (→ `menu.py`, `cli.py`).

**Golden dependency rule:** arrows *always* point towards `library`.

```
debug/ ─┐
games/ ─┼──► library/
menu.py ┘
```

`library` must **never** import `debug`, `games`, `menu` or `cli`.

Two module families:

| Family | Modules | Requires hardware? |
|---|---|---|
| **I/O (BLE)** | `panel.py`, `sender.py` | yes |
| **Pure** | `render.py`, `control.py`, `text.py`, `keys.py` | no (unit testable) |

## 2. Technical constraints

- Python ≥ 3.9 (annotations `tuple[int, int]`).
- `from __future__ import annotations` at the top of **every** module.
- External dependencies: `Pillow` (everywhere) and `pypixelcolor` **only in
  `panel.py`**.
- Local alias `Color = tuple[int, int, int]` in the modules that handle colors.
- No I/O other than BLE: no `print` (the only exception being a transient error
  in the sender thread), no file, no network.

## 3. Layout

```
src/pixelplay/library/
├── __init__.py   # aggregates and re-exports the public API of the sub-package
├── panel.py      # Panel (connect + push one frame) and use_panel()
├── sender.py     # FrameSender ("last-write-wins" thread)
├── render.py     # pure renderers -> PIL.Image
├── control.py    # Sprite (movable element) + PALETTE
├── text.py       # 4x6 bitmap font + metrics + draw_text
└── keys.py       # KeyRepeater (keyboard auto-repeat)
```

## 4. Internal dependency graph

```
panel.py    ──► pypixelcolor
sender.py   ──► panel.py
render.py     (no internal import)
control.py    (no internal import)
text.py       (no internal import)
keys.py       (no internal import)
__init__.py ──► all
```

## 5. Module details

### 5.1 `panel.py` — hardware access

The only module that touches BLE (through `pypixelcolor.Client`). It does not
reimplement any low-level logic: it normalizes the frame and encodes it.

**`Panel(address, brightness=None)`**

- Connects immediately (`Client(address).connect()`).
- Fetches `get_device_info()`; on failure → `disconnect()` then re-raise (no
  leaked connection).
- Exposes `width`, `height`, `led_type`, `device_info`.
- Applies `brightness` (0-100) **after** connecting, when provided.

**Members:**

| Member | Purpose |
|---|---|
| `size` (property) | `(width, height)` |
| `describe()` | readable multi-line text (size, LED, device) |
| `send_png_bytes(png_bytes)` | `send_image_hex(bytes.hex(), ".png")` |
| `send_frame(img)` | converts to `RGB`, resizes when needed, encodes to an in-memory PNG, then `send_png_bytes` |
| `close()` | idempotent `disconnect()` (swallows exceptions) |
| `__enter__` / `__exit__` | context manager → `close()` on exit |

> **Key performance point:** `send_frame` produces an image already in the right
> format/size, so `pypixelcolor` **skips** its own resize/re-encode.

**`use_panel(address, brightness=None, panel=None)`** — context manager:

```python
@contextmanager
def use_panel(address, brightness=None, panel=None):
    if panel is not None:
        yield panel          # borrowed panel: never closed
        return
    with Panel(address, brightness=brightness) as owned:
        yield owned          # owned panel: closed on exit
```

> A **borrowed** panel (shared by the launcher) is never closed: its owner stays
> responsible for its lifecycle.

### 5.2 `sender.py` — asynchronous sending

`FrameSender(panel, fps)` is a **daemon** `threading.Thread` that pushes *the
latest submitted frame*.

- `fps <= 0` → send as fast as possible; otherwise an interval of `1/fps`.
- **Last-write-wins**: `submit()` replaces the pending frame (guarded by a
  `Lock` + `Event`).
- `stop()` requests the shutdown; `run()` loops until the stop event is set.
- `sent` counter (frames actually sent).
- Send errors are **printed**, never propagated (the thread survives transient
  errors).
- ⚠️ Do **not** name the event `_stop` (that would shadow `Thread._stop`).

API: `submit(img)`, `stop()`, `run()`, `sent` attribute.

### 5.3 `render.py` — pure renderers

Pure functions `(t, width, height, [color]) -> Image.Image` in `RGB` mode at the
requested size.

| Function | Description | Default color |
|---|---|---|
| `render_bars(t, w, h, color)` | scrolling vertical bars | `(0, 120, 255)` |
| `render_gradient(t, w, h)` | animated sinusoidal gradient | — |
| `render_bouncing_ball(t, w, h, color)` | bouncing ball | `(255, 64, 0)` |

Private helpers: `_new_frame(w, h, bg)` → `(Image, ImageDraw)`,
`_ping_pong(period, value)` → a `[0, 1]` value that goes back and forth.

Registry: `RENDERERS = {"bars": ..., "gradient": ..., "ball": ...}` (used by the
CLI and `bench`).

> A renderer is **deterministic**: same `t` ⇒ same image (essential to test
> motion *and* period repetition).

### 5.4 `control.py` — movable element

`Sprite(size=3, color=PALETTE[0])`: a square whose `(x, y)` is the **center**,
always clamped to the panel. The sprite **does not know** the panel size: it is
passed to the methods.

- Size: `size` = half-side (the square covers `2*size+1` px).
- `PALETTE`: 6 colors cycled by `cycle_color()`.

| Method | Effect |
|---|---|
| `set_position(x, y, w, h)` | places and **clamps** within `[0, w-1] × [0, h-1]` |
| `move(dx, dy, w, h)` | relative, clamps |
| `center(w, h)` | centers at `(w//2, h//2)` |
| `cycle_color()` | next color (wraps around) |
| `render(w, h)` | black `RGB` image with the sprite |

### 5.5 `text.py` — 4x6 bitmap font

The font is **pure data** (no file, no extra dependency, identical rendering
across platforms/Pillow versions).

- Constants: `GLYPH_W = 4`, `GLYPH_H = 6`, `SPACING = 1`.
- `GLYPHS: dict[str, tuple[str, ...]]`: 6 rows of 4 characters (`'1'` = lit
  pixel). Covers `A-Z`, `0-9` and a few symbols.
- `UNKNOWN`: a solid block — an untabulated character becomes **visible** (a
  typo stands out instead of silently disappearing).
- `glyph(char)`: case-insensitive lookup, `UNKNOWN` by default.

Metrics:

| Function | Meaning |
|---|---|
| `text_advance(scale, spacing)` | horizontal step between glyphs |
| `text_width(text, scale, spacing)` | width of one line (gaps included, no trailing gap) |
| `text_height(scale)` | height of one line |
| `text_pitch(scale, spacing)` | vertical step between lines |

Rendering: `draw_text(draw, x, y, text, color, scale=1, spacing=SPACING)` —
top-left corner at `(x, y)`. Out-of-image clipping is handled by PIL (no bounds
checking on the caller side).

### 5.6 `keys.py` — keyboard auto-repeat

`KeyRepeater(delay=REPEAT_DELAY, every=REPEAT_EVERY)` turns keyboard events into
**one action per key press**, then repeats.

- Constants: `REPEAT_DELAY = 3`, `REPEAT_EVERY = 1` (in ticks).
- `press(key)` → `True` on a new press, `False` on an OS auto-repeat (to ignore).
- `release(key)`, `clear()` (focus loss), `due()` → advances one tick and returns
  the keys to repeat.
- Counting is done in **ticks**, so it is independent of the exact event timing:
  a short press fires exactly once.

### 5.7 `__init__.py` — facade

Re-exports the public API of the sub-package and sets `__all__` (sorted). Usage
example:

```python
from pixelplay.library import Panel, FrameSender, Sprite, render_bouncing_ball
```

## 6. Invariants / contracts

- Any image produced or accepted is in **`RGB`**.
- `render_*` returns exactly `(width, height)`.
- `Sprite` always clamps its position to the panel.
- `FrameSender` never raises inside `run()`.
- `use_panel` never closes a borrowed panel.
- `library` never imports `debug`/`games`/`menu`/`cli`.

## 7. Adding a new renderer

1. Write `def render_xxx(t, width, height, color=...) -> Image.Image` in
   `render.py` using `_new_frame`.
2. Add it to the `RENDERERS` dict under a short key.
3. Export the function in `library/__init__.py` (`import` + `__all__`).
4. Add the parametrized test case: it will be picked up automatically by
   `@pytest.mark.parametrize("name", sorted(RENDERERS))`.

## 8. Testing without hardware — repository patterns

Test files live under `tests/library/` (`pytest.ini`: `testpaths = tests`,
`pythonpath = src`).

**Fake BLE** — inject a fake client via `Panel.__new__` (bypasses `__init__`,
which would open BLE):

```python
class FakeClient:
    def __init__(self):
        self.calls = []

    def send_image_hex(self, hex_string, extension, *args, **kwargs):
        self.calls.append((hex_string, extension))


def _make_panel(width=32, height=32):
    panel = Panel.__new__(Panel)
    panel._client = FakeClient()
    panel.width, panel.height = width, height
    panel.led_type, panel.device_info = "RGB", None
    return panel
```

The PNG is then decoded to check size/mode/pixels (`_decode`).

**`FrameSender` thread** — a `FakePanel` recording the `send_frame` calls, then a
deadline-based loop with `stop()`/`join()` and an
`assert not sender.is_alive()`.

**Renderers** — double `parametrize` (name × size) checking
`Image`/`RGB`/size; motion tests (`t=0` vs `t=0.1`) and repetition tests (`t=0`
vs `t=1.0`).

**Font** — shape validation of every glyph, case handling, `UNKNOWN`, `A-Z0-9`
coverage, metrics, lit pixels, scaling and clipping.

**Sprite** — starting at the origin, centering, clamping (set/move), color
cycling, pixel-by-pixel rendering, then the `render → send_frame` chain.

## 9. Checklist for a new `library` module

- [ ] `from __future__ import annotations` at the top.
- [ ] No import towards `debug`/`games`/`menu`/`cli`.
- [ ] Module docstring + NumPy-style "parameters" docstrings (like the others).
- [ ] Hardware I/O isolated (like `panel.py`).
- [ ] Export in `library/__init__.py` + entry in `__all__`.
- [ ] Tests added under `tests/library/` without hardware.
- [ ] Green `pytest` + public surface imports checked.

## 10. Test ↔ module mapping

| Module | Test file |
|---|---|
| `library/panel.py` | `tests/library/test_panel.py` |
| `library/render.py` | `tests/library/test_render.py` |
| `library/control.py` | `tests/library/test_control.py` |
| `library/text.py` | `tests/library/test_text.py` |
| `library/sender.py` | `tests/library/test_control.py` (thread test) |
| `library/keys.py` | covered indirectly (`tests/games/test_tetris.py`) |
