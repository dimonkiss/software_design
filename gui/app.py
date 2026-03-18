"""
Application entry point.  Creates the root window and starts the event loop.
"""

from __future__ import annotations

from gui.main_window import MainWindow


class Application:
    """Thin wrapper that owns the root :class:`MainWindow` lifetime."""

    def __init__(self) -> None:
        self._window = MainWindow()

    def run(self) -> None:
        self._window.mainloop()
