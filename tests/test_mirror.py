"""Unit tests for the mirroring loop (no BLE / no device required).

A fake panel records the frames, so the loop can be driven by a
``should_stop`` predicate instead of a real clock or hardware.
"""

from PIL import Image

from pixelplay.mirror import run_mirror

ADDRESS = "00:00:00:00:00:00"


class FakePanel:
    """Records the frames it is asked to push instead of talking to hardware."""

    def __init__(self, width=32, height=32):
        self.width = width
        self.height = height
        self.led_type = "RGB"
        self.device_info = None
        self.frames = []
        self.closed = False

    def send_frame(self, img):
        self.frames.append(img)

    def close(self):
        self.closed = True


def _solid(color=(1, 2, 3)):
    def renderer(t, width, height):
        return Image.new("RGB", (width, height), color)

    return renderer


def _stop_after(panel, count):
    return lambda: len(panel.frames) >= count


def _run(panel, stop_after=1, renderer=None, **kwargs):
    """Drive the mirror loop with the fake panel until ``stop_after`` frames."""
    run_mirror(
        ADDRESS,
        panel=panel,
        fps=0,
        renderer=renderer or _solid(),
        should_stop=_stop_after(panel, stop_after),
        **kwargs,
    )


def test_a_borrowed_panel_is_used_and_left_open():
    panel = FakePanel()

    _run(panel, stop_after=0)

    assert panel.frames == []
    assert panel.closed is False  # the owner closes it, not the mirror loop


def test_frames_are_pushed_until_should_stop_is_true():
    panel = FakePanel()

    _run(panel, stop_after=3)

    assert len(panel.frames) == 3


def test_the_renderer_receives_the_panel_size():
    panel = FakePanel(width=16, height=8)
    seen = []

    def renderer(t, width, height):
        seen.append((width, height))
        return Image.new("RGB", (width, height))

    _run(panel, stop_after=2, renderer=renderer)

    assert seen == [(16, 8), (16, 8)]
    assert panel.frames[0].size == (16, 8)


def test_on_stats_reports_the_frame_count():
    panel = FakePanel()
    counts = []

    _run(
        panel,
        stop_after=3,
        on_stats=lambda measured, sent: counts.append(sent),
    )

    assert counts == [1, 2, 3]


def test_the_loop_stops_by_itself_after_duration():
    panel = FakePanel()

    run_mirror(ADDRESS, panel=panel, fps=0, duration=0.1, renderer=_solid())

    assert len(panel.frames) >= 1
