"""Keyboard auto-repeat helper shared by the interactive tools.

The interactive tools (the launcher, ``play`` and the games) run a periodic
tick and bind ``<KeyPress>``/``<KeyRelease>``. Doing both naively
double-applies an action: the key press acts once *and* the held key is acted
upon again on the next tick. :class:`KeyRepeater` centralizes the fix, and it
is pure Python so it can be unit tested without a window.
"""

from __future__ import annotations

REPEAT_DELAY = 3  # ticks a key must be held before it starts repeating
REPEAT_EVERY = 1  # ticks between two repeats, once started


class KeyRepeater:
    """Turn key events into exactly one action per press, then auto-repeat.

    A tap fires exactly once; holding a key fires again after ``delay`` ticks
    and then every ``every`` tick. The repeat deadline is counted in ticks, so
    it does not depend on whether the key event lands just before or just after
    the frame: a press shorter than ``delay`` ticks always fires exactly once.
    The auto-repeat of the OS itself - which re-sends ``KeyPress`` while a key
    is held - is filtered out, so it can never double an action either.
    """

    def __init__(
        self, delay: int = REPEAT_DELAY, every: int = REPEAT_EVERY
    ) -> None:
        self.delay = max(1, int(delay))
        self.every = max(1, int(every))
        self.held: set[str] = set()
        self._ticks = 0
        self._due_at: dict[str, int] = {}

    def press(self, key: str) -> bool:
        """Record a press; return True when it is a fresh press.

        A False return means the key is already held, i.e. the event is an
        auto-repeat from the OS and must be ignored.
        """
        if key in self.held:
            return False
        self.held.add(key)
        self._due_at[key] = self._ticks + self.delay
        return True

    def release(self, key: str) -> None:
        """Stop repeating ``key``."""
        self.held.discard(key)
        self._due_at.pop(key, None)

    def clear(self) -> None:
        """Forget every held key (e.g. when the window loses the focus)."""
        self.held.clear()
        self._due_at.clear()

    def due(self) -> list[str]:
        """Advance one tick; return the held keys that repeat right now."""
        self._ticks += 1
        fired = []
        for key in sorted(self.held):
            if self._ticks >= self._due_at[key]:
                self._due_at[key] = self._ticks + self.every
                fired.append(key)
        return fired
