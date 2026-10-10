# pixelled-lib

Real-time mirroring of locally rendered frames to **iPixel Color** LED matrix
panels, plus the debug tooling built around it. `pixelled-lib` embeds
[`pypixelcolor`](https://pypi.org/project/pypixelcolor) as a library and adds a
small, testable layer on top of it:

- **Panel** — connected wrapper around `pypixelcolor.Client` that pushes frames.
- **Renderers** — pure PIL frame generators (no BLE, unit testable).
- **Mirror** — real-time loop that renders locally and mirrors each frame.
- **Bench** — measures the achievable frame rate on your hardware.
- **Play** — interactive window to control a graphical element on the panel from
  the workstation (manual end-to-end check of the offloading).
- **Launcher** — a menu drawn on the panel (a 4x6 bitmap font, no extra
  dependency) that picks the tool to run and shares a single BLE connection with
  it. It scrolls by itself, so the panel is useful without a keyboard.

The games (Breakout, Tetris) live in the companion project
[`pixelled-play`](https://github.com/BaramoK/pixelLed-play), which depends on
this package.

## Layout

The package is split into three parts:

- `pixelled_lib.library` — the reusable API. `Panel` and `FrameSender` are the
  only modules touching BLE; `render`, `control`, `text`, `keys` and `menu` are
  pure and unit testable without hardware.
- `pixelled_lib.debug` — diagnostic / proof-of-concept tools run against a real
  panel (`bench`, `mirror`, `play`).
- `pixelled_lib.launcher` — the on-panel launcher that ties the debug tools
  together, built on the generic engine in `pixelled_lib.library.menu`.

`pixelled_lib.cli` exposes everything on the command line. The top-level
`pixelled_lib` namespace re-exports the public API, so
`from pixelled_lib import Panel, render_bouncing_ball` keeps working.

The [`docs/library.md`](docs/library.md) guide documents the internals of
`pixelled_lib.library` (module responsibilities, dependency rules, contracts and
testing patterns) for anyone extending it.

## Installation

The package is not published on PyPI yet, so install it from the repository
([github.com/BaramoK/pixelLed-lib](https://github.com/BaramoK/pixelLed-lib)):

```bash
git clone https://github.com/BaramoK/pixelLed-lib.git
cd pixelLed-lib
pip install -e .
```

Requires Python >= 3.9 and pulls `pypixelcolor>=0.5.0` and `Pillow`.

## Usage

```bash
# Show panel information
pixelled-lib info -a 30:E1:AF:BD:5F:D0

# Benchmark the achievable frame rate
pixelled-lib bench -a 30:E1:AF:BD:5F:D0 -n 60 --pattern bars

# Mirror an animated pattern in real time (Ctrl+C to stop)
pixelled-lib mirror -a 30:E1:AF:BD:5F:D0 --fps 8 --pattern ball

# Control an element on the panel from this workstation (q to quit)
pixelled-lib play -a 30:E1:AF:BD:5F:D0 --scale 12

# Show a launcher on the panel and run the selected tool
pixelled-lib menu -a 30:E1:AF:BD:5F:D0
```

Or as a library:

```python
from pixelled_lib import Panel, render_bouncing_ball

with Panel("30:E1:AF:BD:5F:D0", brightness=60) as panel:
    panel.send_frame(render_bouncing_ball(0.0, panel.width, panel.height))
```

`run_mirror` accepts any callable returning a `PIL.Image` in `RGB` at the panel
size:

```python
from pixelled_lib.debug.mirror import run_mirror

run_mirror("30:E1:AF:BD:5F:D0", fps=8, renderer=my_render_function)
```

## Notes and limitations

- Frame rate is limited by BLE throughput and the per-frame ACK; expect a few
  frames per second up to roughly 10-15 fps depending on panel size and content.
- For fluid local gameplay, render in a local window and mirror to the panel at
  a reduced rate.
- `send_image_hex` does not require "fun mode" (unlike per-pixel `set_pixel`).
- `pixelled-lib play` opens a `tkinter` window, so it needs a graphical display
  on the workstation running it.
- `pixelled-lib menu` connects **once** and then lends that connection to every
  tool it starts, so switching between tools costs no reconnection. It shows the
  debug group (Info, Bench, Mirror, Play) and scrolls by itself (`--auto 2.0` =
  seconds per item, `0` starts in keyboard mode); the first arrow key takes over
  and auto-scrolling resumes after a few idle seconds. Keys: up/down or `W`/`S`
  move, `1`-`9` jump straight to an item, Enter/Space launches, `a` toggles
  auto-scrolling, `Esc`/Left/`b` returns from the group to the root and `q`
  quits (a launched tool goes back to its group when it exits). The menu uses a
  built-in 4x6 bitmap font (`pixelled_lib.library.text`): labels are drawn 2x on
  panels of 64 px or more (4 rows of 12 px text) and a 32x32 matrix keeps single
  pixels (4 rows of 6 px text), scrolling the rest of the list. Unselected rows
  are slightly dimmed so the white band of the selection stands out.
- The games are in the companion project
  [`pixelled-play`](https://github.com/BaramoK/pixelLed-play).

## Tests

```bash
pytest
```

The renderer, control, text, keys, menu, mirror and panel tests run without any
hardware.

## Troubleshooting

### `Fatal error in launcher: Unable to create process using ...`

This error means the virtual environment was moved or renamed: a venv is not
relocatable. Its `pyvenv.cfg`, the editable install `.pth` files and every
console script launcher (`pixelled-lib.exe`, `pip.exe`, `pytest.exe`, ...) store
absolute paths recorded when the environment was created, so the launcher tries
to start a `python.exe` that no longer exists (on a localized Windows the
message ends with something like *Le fichier spécifié est introuvable*). The
venv's own `python.exe` keeps working, which is why `python -m pytest` still
runs while `pixelled-lib` fails.

Recreate the environment:

```bash
deactivate                       # or open a fresh terminal
rm -rf .venv                     # PowerShell: Remove-Item -Recurse -Force .venv
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install -e ".[dev]"
```

Then check that the console script is healthy again:

```bash
.venv/Scripts/pixelled-lib --version
.venv/Scripts/python -m pytest
```

To run something right away without touching the venv, use the module form
(`.venv/Scripts/python -m pixelled_lib ...`), which bypasses the launcher. Keep
`.venv/` inside the project and avoid renaming the project folder once the
environment exists.

## License

MIT. This is a third-party project, not affiliated with iPixel Color.
