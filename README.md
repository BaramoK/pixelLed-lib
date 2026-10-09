# pixelplay

Real-time mirroring of locally rendered frames to **iPixel Color** LED matrix
panels. `pixelplay` embeds [`pypixelcolor`](https://pypi.org/project/pypixelcolor)
as a library and adds a small, testable layer on top of it:

- **Panel** — connected wrapper around `pypixelcolor.Client` that pushes frames.
- **Renderers** — pure PIL frame generators (no BLE, unit testable).
- **Mirror** — real-time loop that renders locally and mirrors each frame.
- **Bench** — measures the achievable frame rate on your hardware.
- **Play** — interactive window to control a graphical element on the panel from
  the workstation (manual end-to-end check of the offloading).
- **Breakout** — a small brick-breaker demo: the whole game (field + HUD) is
  drawn on the panel, while a minimal window only captures the keyboard. The
  wall is built from 2x2 px bricks packed edge to edge, the paddle is a 2 px
  bar and the ball is a single pixel.
- **Tetris** — a small Tetris demo, also played entirely on the panel: a 10
  block wide field of fixed 2x2 px blocks with a 12 px HUD band on its right
  (next piece preview, score bar, level bar). 7-bag randomizer, wall kicks,
  soft/hard drop, pause and restart, all from the keyboard.
- **Menu** — a launcher drawn on the panel (a 4x6 bitmap font, no extra
  dependency) that picks the tool to run and shares a single BLE connection
  with it. It scrolls by itself, so the panel is useful without a keyboard.

## Installation

The package is not published on PyPI yet, so install it from the repository
([github.com/BaramoK/iPixel-Play](https://github.com/BaramoK/iPixel-Play)):

```bash
git clone https://github.com/BaramoK/iPixel-Play.git
cd iPixel-Play
pip install -e .
```

Requires Python >= 3.9 and pulls `pypixelcolor>=0.5.0` and `Pillow`.

## Usage

```bash
# Show panel information
pixelplay info -a 30:E1:AF:BD:5F:D0

# Benchmark the achievable frame rate
pixelplay bench -a 30:E1:AF:BD:5F:D0 -n 60 --pattern bars

# Mirror an animated pattern in real time (Ctrl+C to stop)
pixelplay mirror -a 30:E1:AF:BD:5F:D0 --fps 8 --pattern ball

# Control an element on the panel from this workstation (q to quit)
pixelplay play -a 30:E1:AF:BD:5F:D0 --scale 12

# Play a brick-breaker demo entirely on the panel (q to quit)
pixelplay breakout -a 30:E1:AF:BD:5F:D0 --fps 15 --lives 3 --seed 42

# Play a Tetris demo entirely on the panel (q to quit)
pixelplay tetris -a 30:E1:AF:BD:5F:D0 --fps 10 --level 1 --seed 42

# Show a launcher on the panel and run the selected tool
pixelplay menu -a 30:E1:AF:BD:5F:D0
```

Or as a library:

```python
from pixelplay import Panel, render_bouncing_ball

with Panel("30:E1:AF:BD:5F:D0", brightness=60) as panel:
    panel.send_frame(render_bouncing_ball(0.0, panel.width, panel.height))
```

To mirror your own game/render, pass a callable `renderer(t, width, height)`
returning a `PIL.Image` in `RGB` at the panel size:

```python
from pixelplay.mirror import run_mirror

run_mirror("30:E1:AF:BD:5F:D0", fps=8, renderer=my_render_function)
```

## Notes and limitations

- Frame rate is limited by BLE throughput and the per-frame ACK; expect a few
  frames per second up to roughly 10-15 fps depending on panel size and content.
- For fluid local gameplay, render in a local window and mirror to the panel at
  a reduced rate.
- `send_image_hex` does not require "fun mode" (unlike per-pixel `set_pixel`).
- `pixelplay play` opens a `tkinter` window, so it needs a graphical display on
  the workstation running it.
- `pixelplay breakout` draws everything on the panel; its (minimal) window only
  captures the keyboard: arrows/`A`-`D` move the paddle, space launches, `r`
  replays a new random wall and `q`/Esc quits. The HUD lives on the panel's top
  row (green score bar on the left, remaining lives on the right); disable it
  with `--no-hud`. Bricks are 2x2 px blocks packed edge to edge (no gap), so the
  wall looks like the classic solid mass: `--density` is the probability for a
  2x2 cell to be filled, lower it (e.g. `--density 0.45`) for a lighter wall.
- `pixelplay tetris` also draws everything on the panel; its (minimal) window
  only captures the keyboard: arrows/`A`-`D` move the piece, up/`W`/`X` rotate
  clockwise, `Z` rotates counter-clockwise, down/`S` soft drops, space hard
  drops, `p` pauses, `r` replays a new game and `q`/Esc quits. A tap moves or
  drops the piece by exactly one block; hold a key to keep repeating it. The
  first piece starts falling on its own (1 row per second at the default 10
  fps), no key press is needed to begin. The field is 10 blocks wide, every
  block is exactly 2x2 px and a piece is made of 4 such blocks (so it spans 3x2
  blocks at most),
  so the same game looks the same on any panel: the block size is never scaled
  (a panel narrower than 20 px simply gets fewer columns). The 12 px band on the
  right holds the next piece preview, a green score bar (1 px per 100 points)
  and a yellow level bar (1 px per level); on a 32x32 panel field + band fill the
  matrix exactly (a 20x32 px field plus the band). Disable it with `--no-hud`.
  `--level` starts at a higher speed, `--seed` makes the piece sequence
  reproducible.
- `pixelplay menu` connects **once** and then lends that connection to every
  tool it starts, so switching between demos costs no reconnection. The
  launcher is grouped: the root menu lists the groups (`Games`: Breakout,
  Tetris; `Debug`: Info, Bench, Mirror, Play) and choosing one opens its
  sub-menu. It scrolls by itself (`--auto 2.0` = seconds per item, `0` starts
  in keyboard mode); the first arrow key takes over and auto-scrolling resumes
  after a few idle seconds. Keys: up/down or `W`/`S` move, `1`-`9` jump
  straight to an item, Enter/Space launches, `a` toggles auto-scrolling,
  `Esc`/Left/`b` returns from a group to the root and `q` quits (a launched
  demo goes back to its group when it exits). The menu uses a built-in 4x6
  bitmap font (`pixelplay.text`): labels are drawn 2x on panels of 64 px or
  more (4 rows of 12 px text) and a 32x32 matrix keeps single pixels (4 rows
  of 6 px text), scrolling the rest of the list. Unselected rows are slightly
  dimmed so the white band of the selection stands out.

## Tests

```bash
pytest
```

The renderer, control, text, menu, mirror, breakout, panel and tetris tests run
without any hardware.

## License

MIT. This is a third-party project, not affiliated with iPixel Color.
