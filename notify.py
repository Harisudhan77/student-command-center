"""System-tray notifications (real Windows toasts) with the app's robot icon."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

ICON_PATH = Path(__file__).resolve().parent / "assets" / "app_icon.png"

_notifier = None


class Notifier:
    """Thin wrapper around QSystemTrayIcon so any module can send a toast."""

    def __init__(self, window=None):
        self.tray = QSystemTrayIcon(QIcon(str(ICON_PATH)))
        self.tray.setToolTip("Student Command Centre")

        menu = QMenu()
        if window is not None:
            open_action = menu.addAction("Open Student Command Centre")
            open_action.triggered.connect(self._reopen)
            menu.addSeparator()
            quit_action = menu.addAction("Quit")
            quit_action.triggered.connect(window.request_quit)
        self.tray.setContextMenu(menu)

        self.available = self.tray.isSystemTrayAvailable()
        self.tray.show()
        self.window = window

    def _reopen(self) -> None:
        if self.window is not None:
            self.window.showNormal()
            self.window.activateWindow()

    def notify(self, title: str, message: str, msecs: int = 7000) -> bool:
        if not self.available:
            return False
        self.tray.showMessage(title, message, QSystemTrayIcon.Information, msecs)
        return True


def init_notifier(window) -> Notifier:
    global _notifier
    _notifier = Notifier(window)
    return _notifier


def get_notifier() -> Notifier | None:
    return _notifier