"""The single tkinter window the interactive tools read the keyboard from.

The panel has no buttons, so the launcher and the games display themselves on
the matrix and are driven from the workstation keyboard through a *minimal*
window (a title plus one status line). A session runs several of those windows
one after another - the launcher, the game it starts, the launcher again - and
creating a ``tk.Tk()`` / ``root.destroy()`` pair per window is **not** supported
by Tcl:

* destroying a window while its periodic ``after`` timer is still pending
  leaves that timer queued in Tcl's notifier; the *next* window runs it and Tcl
  reports ``invalid command name "..." while executing "..." ("after" script)``
  because the callback of the destroyed window no longer exists;
* tearing interpreters down over and over ends up aborting the process with
  ``Tcl_AsyncDelete: async handler deleted by the wrong thread``.

:func:`shared_root` therefore creates **one** interpreter for the whole process,
and :class:`Window` only shows and hides that root: no interpreter is ever
created twice nor destroyed early, and :meth:`Window.close` cancels the pending
callback, so a timer can never outlive the window it belongs to.

The tools import this module lazily (``import tkinter`` stays out of the import
path of the pure, unit tested modules).
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

# The one and only root of the process, created on first use and never destroyed.
_root: Optional[tk.Tk] = None


def shared_root() -> tk.Tk:
    """Return the process-wide Tk root, created (and hidden) on first use.

    Reusing a single root is what keeps the tools alive for a whole session: a
    new interpreter per window leaves the timers of the previous one behind
    (see the module docstring).
    """
    global _root
    if _root is not None:
        try:
            if _root.winfo_exists():
                return _root
        except tk.TclError:
            pass  # the interpreter is gone: fall through and build a new one
    _root = tk.Tk()
    _root.withdraw()
    return _root


class Window:
    """A minimal window on the shared root: one status line and key bindings.

    Only one window is ever open at a time, which is what makes reusing the
    root possible: :meth:`close` destroys the widgets the session created (the
    status line included) and hides the window again.

    Attributes:
        root: The shared :class:`tkinter.Tk` root.
        label: The status/help line, packed by the constructor unless the
            caller wants to place it itself (``pack_label=False``).
    """

    def __init__(self, title: str, pack_label: bool = True) -> None:
        self.root = shared_root()
        self.root.title(title)
        self.label = tk.Label(
            self.root, anchor="w", justify="left", font=("Consolas", 9)
        )
        if pack_label:
            self.label.pack(padx=10, pady=10)
        self._timer: Optional[str] = None
        self._bindings: list[str] = []
        self._closed = False

    @property
    def closed(self) -> bool:
        """True once :meth:`close` has been called."""
        return self._closed

    def bind(self, sequence: str, callback: Callable) -> None:
        """Bind ``sequence`` on the window, forgetting it again on close."""
        self.root.bind(sequence, callback)
        self._bindings.append(sequence)

    def on_close(self, callback: Callable) -> None:
        """Call ``callback`` when the window manager close button is used."""
        self.root.protocol("WM_DELETE_WINDOW", callback)

    def schedule(self, interval_ms: int, callback: Callable[[], None]) -> None:
        """Run ``callback`` in ``interval_ms`` ms, replacing any pending call.

        The id is remembered so :meth:`close` can cancel it: a callback of a
        closed window must never run (the widget it would update is gone).
        """
        self.cancel()
        self._timer = self.root.after(interval_ms, callback)

    def cancel(self) -> None:
        """Cancel the callback registered through :meth:`schedule`, if any."""
        if self._timer is not None:
            self.root.after_cancel(self._timer)
            self._timer = None

    def show(self) -> None:
        """Make the window visible and give it the keyboard focus."""
        self.root.deiconify()
        self.root.focus_force()

    def mainloop(self) -> None:
        """Show the window and run the event loop until :meth:`close`."""
        self.show()
        self.root.mainloop()

    def close(self) -> None:
        """Tear the window down, once (idempotent).

        The pending callback is cancelled and the widgets are destroyed, but
        the root - and therefore the Tcl interpreter - stays alive: the next
        window of the session reuses it.
        """
        if self._closed:
            return
        self._closed = True
        self.cancel()
        for sequence in self._bindings:
            self.root.unbind(sequence)
        self._bindings.clear()
        self.root.protocol("WM_DELETE_WINDOW", "")
        for child in self.root.winfo_children():
            child.destroy()
        self.root.withdraw()
        self.root.quit()
