"""Tests for the shared tkinter window the interactive tools run on.

They need a real Tk interpreter (skipped where there is no display) but never
call ``mainloop``, so no window is ever shown. They guard the two properties a
session relies on: **one** interpreter for the whole process, and no callback
left behind by a window that was closed.
"""

import time

import pytest

# tkinter is imported first on purpose: importing the module under test imports
# it too, and a missing tkinter must skip (not error) the whole file.
tk = pytest.importorskip("tkinter")

from pixelled_lib.library import window as window_module  # noqa: E402


@pytest.fixture(scope="module")
def root():
    """Return the shared root, skipping the tests when there is no display."""
    try:
        return window_module.shared_root()
    except tk.TclError as exc:  # pragma: no cover - headless machine
        pytest.skip(f"no Tk display: {exc}")


def test_shared_root_is_created_once(root):
    assert window_module.shared_root() is root


def test_a_new_window_reuses_the_same_root(root):
    first = window_module.Window("first")
    first.close()
    second = window_module.Window("second")
    try:
        assert second.root is root
    finally:
        second.close()


def test_close_keeps_the_interpreter_alive(root):
    window = window_module.Window("temporary")
    window.close()

    assert window.closed
    # The root must survive: destroying it is what used to break the session
    # ("invalid command name ... ("after" script)") for the next window.
    assert root.winfo_exists()
    assert window_module.shared_root() is root


def test_close_is_idempotent(root):
    window = window_module.Window("temporary")
    window.close()
    window.close()  # must not raise
    assert window.closed


def test_close_drops_the_widgets_of_the_window(root):
    window = window_module.Window("temporary")
    assert window.label.winfo_exists()

    window.close()

    assert not window.label.winfo_exists()
    assert root.winfo_children() == []


def test_close_cancels_the_pending_callback(root):
    window = window_module.Window("temporary")
    calls = []
    window.schedule(1, lambda: calls.append(1))
    window.close()

    time.sleep(0.05)  # the timer would have fired long ago
    root.update()
    assert calls == []


def test_schedule_replaces_the_pending_callback(root):
    window = window_module.Window("temporary")
    calls = []
    try:
        window.schedule(1, lambda: calls.append("first"))
        window.schedule(1, lambda: calls.append("second"))
        time.sleep(0.05)
        root.update()
        assert calls == ["second"]
    finally:
        window.close()


def test_close_unbinds_the_keys(root):
    window = window_module.Window("temporary")
    seen = []
    window.bind("<KeyPress>", lambda event: seen.append(event.keysym))
    window.close()

    root.event_generate("<KeyPress>", keysym="q")
    assert seen == []
