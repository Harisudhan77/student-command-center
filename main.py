"""Student Command Center - main window with sidebar navigation.

Every menu lives inside this one window: the sidebar switches pages in a
QStackedWidget. Data is stored with store.py (SQLite in data/planner.db).
"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplashScreen,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, QTimer

import notify
import reminders
import store
from app_paths import base_dir
from dashboard import DashboardPage
from exams import ExamsPage
from planner import PlannerPage
from progress import ProgressPage
from settings import SettingsPage
from study_buddy import StudyBuddyWidget
from subjects import SubjectsPage
from tasks import TasksPage
from ui_theme import ACCENT, BG, BODY, BORDER, FAINT, MUTED, SIDEBAR, TEXT

app = QApplication(sys.argv)
app.setWindowIcon(QIcon(str(base_dir() / "assets" / "app_icon.png")))


class MainWindow(QMainWindow):
    """QMainWindow that minimizes to the system tray instead of quitting."""

    def __init__(self):
        super().__init__()
        self._quit_requested = False
        self._notifier = None

    def request_quit(self) -> None:
        self._quit_requested = True
        self.close()

    def closeEvent(self, event) -> None:
        keep_running = (
            not self._quit_requested
            and self._notifier is not None
            and store.get_setting("minimize_to_tray", "1") == "1"
        )
        if keep_running:
            event.ignore()
            self.hide()
            self._notifier.notify(
                "Student Command Centre",
                "Still running in the background — reminders stay active.\n"
                "Use the tray icon to reopen or quit.",
            )
            return
        event.accept()


main_window = MainWindow()
main_window.setWindowTitle("Student Command Center")
main_window.resize(1080, 700)
main_window.setMinimumSize(960, 620)

root_widget = QWidget()
root_widget.setObjectName("root")
root_widget.setStyleSheet(f"QWidget#root {{ background-color: {BG}; }}")
main_window.setCentralWidget(root_widget)

main_layout = QHBoxLayout()
main_layout.setContentsMargins(0, 0, 0, 0)
main_layout.setSpacing(0)
root_widget.setLayout(main_layout)

# ------------------------------------------------------------- sidebar
sidebar = QWidget()
sidebar.setFixedWidth(220)
sidebar.setStyleSheet(f"background-color: {SIDEBAR}; border-radius: 14px;")
sidebar_layout = QVBoxLayout(sidebar)
sidebar_layout.setContentsMargins(18, 25, 18, 18)

brand = QLabel("STUDY HUB")
brand.setStyleSheet(f"color: {TEXT}; font-size: 33px; font-weight: bold;")
sidebar_layout.addWidget(brand)
sidebar_layout.addSpacing(40)

def _separator():
    line = QLabel()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background-color: {BORDER};")
    return line

sidebar_layout.addWidget(_separator())
sidebar_layout.addSpacing(15)

menu_label = QLabel("MAIN MENU")
menu_label.setStyleSheet(f"color: {FAINT}; font-size: 11px; font-weight: bold; padding-left: 10px;")
sidebar_layout.addWidget(menu_label)
sidebar_layout.addSpacing(8)

AI_LABEL_STYLE = f"color: {FAINT}; font-size: 11px; font-weight: bold; padding-left: 10px;"

NAV = [
    ("dashboard_btn", "📊 Dashboard"),
    ("tasks_btn", "📋 Tasks"),
    ("subjects_btn", "📚 Subjects"),
    ("exams_btn", "🎯 Exams"),
    ("progress_btn", "📈 Progress"),
]

buttons: dict[str, QPushButton] = {}
for name, text in NAV:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedHeight(44)
    btn.setObjectName(name)
    buttons[name] = btn
    sidebar_layout.addWidget(btn)

sidebar_layout.addSpacing(18)
ai_label = QLabel("AI FEATURES")
ai_label.setStyleSheet(AI_LABEL_STYLE)
sidebar_layout.addWidget(ai_label)
sidebar_layout.addSpacing(8)

buttons["ai_btn"] = QPushButton("🤖 Study Buddy AI")
buttons["planner_btn"] = QPushButton("📆 Study Planner")
buttons["ai_btn"].setFixedHeight(44)
buttons["planner_btn"].setFixedHeight(44)
buttons["ai_btn"].setObjectName("ai_btn")
buttons["planner_btn"].setObjectName("planner_btn")
sidebar_layout.addWidget(buttons["ai_btn"])
sidebar_layout.addWidget(buttons["planner_btn"])
sidebar_layout.addStretch()

sidebar_layout.addWidget(_separator())
sidebar_layout.addSpacing(6)
buttons["settings_btn"] = QPushButton("⚙️ Settings")
buttons["settings_btn"].setFixedHeight(44)
buttons["settings_btn"].setObjectName("settings_btn")
sidebar_layout.addWidget(buttons["settings_btn"])

INACTIVE_BUTTON = f"""
    QPushButton {{
        color: {BODY}; background-color: transparent; border: none;
        border-radius: 9px; text-align: left; padding-left: 14px;
        font-size: 15px; font-weight: 500;
    }}
    QPushButton:hover {{ background-color: {ACCENT}; color: {TEXT}; }}
"""
ACTIVE_BUTTON = f"""
    QPushButton {{
        color: {TEXT}; background-color: {ACCENT}; border: none;
        border-radius: 9px; text-align: left; padding-left: 14px;
        font-size: 15px; font-weight: bold;
    }}
"""

# ------------------------------------------------------------- pages
stack = QStackedWidget()
pages = {
    "dashboard_btn": DashboardPage(),
    "tasks_btn": TasksPage(),
    "subjects_btn": SubjectsPage(),
    "exams_btn": ExamsPage(),
    "progress_btn": ProgressPage(),
    "ai_btn": StudyBuddyWidget(),
    "planner_btn": PlannerPage(),
    "settings_btn": SettingsPage(),
}
for page in pages.values():
    stack.addWidget(page)

dashboard_scroll = QScrollArea()
dashboard_scroll.setWidgetResizable(True)
dashboard_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
dashboard_scroll.setWidget(pages["dashboard_btn"])

page_wrappers = {
    "dashboard_btn": dashboard_scroll,
    "tasks_btn": pages["tasks_btn"],
    "subjects_btn": pages["subjects_btn"],
    "exams_btn": pages["exams_btn"],
    "progress_btn": pages["progress_btn"],
    "ai_btn": pages["ai_btn"],
    "planner_btn": pages["planner_btn"],
    "settings_btn": pages["settings_btn"],
}
for widget in page_wrappers.values():
    stack.addWidget(widget)

def activate(name: str) -> None:
    for btn_name, btn in buttons.items():
        btn.setStyleSheet(ACTIVE_BUTTON if btn_name == name else INACTIVE_BUTTON)
    stack.setCurrentWidget(page_wrappers[name])
    page = pages[name]
    if hasattr(page, "refresh"):
        page.refresh()

for name, btn in buttons.items():
    btn.clicked.connect(lambda _=False, n=name: activate(n))

main_layout.addWidget(sidebar)
main_layout.addWidget(stack, 1)

# clean shutdown if a Study Buddy request is still running when quitting
app.aboutToQuit.connect(pages["ai_btn"].shutdown)

# ------------------------------------------------------------- start
ASSETS = base_dir() / "assets"
splash_pixmap = QPixmap(str(ASSETS / "logo_lockup.png")).scaledToWidth(520, Qt.SmoothTransformation)
splash = QSplashScreen(splash_pixmap)
splash.showMessage("Loading your study hub…", Qt.AlignHCenter | Qt.AlignBottom, QColor("#94A3B8"))
splash.show()
app.processEvents()

store.get_setting("student_name")  # touch the database so data/planner.db exists up front
activate("dashboard_btn")

def _start() -> None:
    main_window.show()
    splash.finish(main_window)

QTimer.singleShot(1200, _start)  # let the splash breathe for a moment

# --------------------------------------------------------- tray + reminders
notifier = notify.init_notifier(main_window)
main_window._notifier = notifier

checker = reminders.ReminderChecker()

def _check_reminders() -> None:
    for title, message in checker.run_once(QDateTime.currentDateTime().toPython()):
        notifier.notify(title, message)

reminder_timer = QTimer(main_window)
reminder_timer.timeout.connect(_check_reminders)
reminder_timer.start(60_000)          # check every minute
QTimer.singleShot(15_000, _check_reminders)  # first nudge shortly after startup

sys.exit(app.exec())