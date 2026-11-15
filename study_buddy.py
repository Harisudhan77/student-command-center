"""Study Buddy AI - a Groq + GPT-OSS study assistant for the Student Command Center.

Run it on its own:
    python study_buddy.py

Or open it from the app with the "Study Buddy AI" sidebar button in main.py.

The AI logic (models, prompts, streaming) lives in ai_core.py so the web version
can share it. The API key is read from .env next to ai_core.py.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from web.ai_core import PRIMARY_MODEL, SYSTEM_PROMPT, AINotReady, ensure_ready, friendly_error, stream_reply

MAX_HISTORY_MESSAGES = 20


class ChatWorker(QThread):
    """Streams one assistant reply off the GUI thread."""

    chunk = Signal(str)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, messages: list[dict], parent=None):
        super().__init__(parent)
        self.messages = messages

    def run(self) -> None:
        received: list[str] = []
        try:
            for piece in stream_reply(self.messages):
                received.append(piece)
                self.chunk.emit(piece)
            self.done.emit("".join(received))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            self.failed.emit(friendly_error(exc))


class _InputBox(QPlainTextEdit):
    """Enter sends, Shift+Enter adds a new line."""

    submitted = Signal()

    def keyPressEvent(self, event) -> None:
        is_enter = event.key() in (Qt.Key_Return, Qt.Key_Enter)
        if is_enter and not (event.modifiers() & Qt.ShiftModifier):
            self.submitted.emit()
            return
        super().keyPressEvent(event)


USER_BUBBLE = """
    background-color: #6D5AE6;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 10px 13px;
    font-size: 14px;
"""

ASSISTANT_BUBBLE = """
    background-color: #172338;
    color: #E2E8F0;
    border: 1px solid #2B3A52;
    border-radius: 12px;
    padding: 10px 13px;
    font-size: 14px;
"""

ASSISTANT_BUBBLE_ERROR = """
    background-color: #2A1414;
    color: #FCA5A5;
    border: 1px solid #7F1D1D;
    border-radius: 12px;
    padding: 10px 13px;
    font-size: 14px;
"""

STARTER_PROMPTS = [
    "Explain photosynthesis like I'm 10",
    "Make a 7-day study plan for my exams",
    "Quiz me on quadratic equations",
]


class StudyBuddyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Study Buddy AI")
        self.resize(860, 680)
        self.setMinimumSize(560, 440)

        self.history: list[dict] = []
        self.ready = False
        self._worker: ChatWorker | None = None
        self._stream_label: QLabel | None = None
        self._stream_text = ""
        self._bubbles: list[QLabel] = []

        self._build_ui()
        self._init_client()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.setStyleSheet("QDialog { background-color: #1D2130; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(2)

        title = QLabel("🤖  Study Buddy")
        title.setStyleSheet("color: #FFFFFF; font-size: 19px; font-weight: bold;")
        subtitle = QLabel(f"GPT-OSS via Groq · {PRIMARY_MODEL}")
        subtitle.setStyleSheet("color: #64748B; font-size: 11px;")

        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header.addLayout(title_column)
        header.addStretch()

        self.new_chat_btn = QPushButton("New chat")
        self.new_chat_btn.setCursor(Qt.PointingHandCursor)
        self.new_chat_btn.setFixedHeight(32)
        self.new_chat_btn.setStyleSheet(
            """
            QPushButton {
                color: #CBD5E1;
                background-color: #0B1220;
                border: 1px solid #2B3A52;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12px;
            }
            QPushButton:hover { border-color: #6D5AE6; color: #FFFFFF; }
            """
        )
        self.new_chat_btn.clicked.connect(self.reset_chat)
        header.addWidget(self.new_chat_btn)
        root.addLayout(header)

        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet(
            """
            background-color: #2A1414;
            color: #FCA5A5;
            border: 1px solid #7F1D1D;
            border-radius: 8px;
            padding: 9px 12px;
            font-size: 12px;
            """
        )
        self.banner.hide()
        root.addWidget(self.banner)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: #1D2130; }")

        self.transcript = QWidget()
        self.transcript.setStyleSheet("background-color: #1D2130;")
        self.transcript_layout = QVBoxLayout(self.transcript)
        self.transcript_layout.setContentsMargins(4, 4, 4, 4)
        self.transcript_layout.setSpacing(10)
        self.transcript_layout.addStretch()

        self.scroll.setWidget(self.transcript)
        root.addWidget(self.scroll, 1)

        self.starters = QHBoxLayout()
        self.starters.setSpacing(8)
        for prompt in STARTER_PROMPTS:
            button = QPushButton(prompt)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(
                """
                QPushButton {
                    color: #A5B4FC;
                    background-color: #0B1220;
                    border: 1px solid #2B3A52;
                    border-radius: 14px;
                    padding: 6px 12px;
                    font-size: 11px;
                    text-align: left;
                }
                QPushButton:hover { border-color: #6D5AE6; color: #FFFFFF; }
                """
            )
            button.clicked.connect(lambda _=False, p=prompt: self._use_starter(p))
            self.starters.addWidget(button)
        root.addLayout(self.starters)
        self._starter_widgets = [
            self.starters.itemAt(i).widget() for i in range(self.starters.count())
        ]

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.input = _InputBox()
        self.input.setPlaceholderText(
            "Ask anything about your studies…  (Enter to send, Shift+Enter for a new line)"
        )
        self.input.setFixedHeight(66)
        self.input.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #0B1220;
                color: #E2E8F0;
                border: 1px solid #2B3A52;
                border-radius: 10px;
                padding: 8px 10px;
                font-size: 14px;
            }
            QPlainTextEdit:focus { border-color: #6D5AE6; }
            """
        )
        self.input.submitted.connect(self.send_message)
        input_row.addWidget(self.input, 1)

        self.send_btn = QPushButton("Send")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setFixedSize(84, 66)
        self.send_btn.setStyleSheet(
            """
            QPushButton {
                color: #FFFFFF;
                background-color: #6D5AE6;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8170F0; }
            QPushButton:disabled { background-color: #334155; color: #94A3B8; }
            """
        )
        self.send_btn.clicked.connect(self.send_message)
        input_row.addWidget(self.send_btn)

        root.addLayout(input_row)

        self.status = QLabel("")
        self.status.setStyleSheet("color: #64748B; font-size: 11px;")
        root.addWidget(self.status)

    def _init_client(self) -> None:
        try:
            ensure_ready()
            self.ready = True
        except AINotReady as exc:
            self._disable(str(exc))

    def _disable(self, message: str) -> None:
        self.banner.setText(message)
        self.banner.show()
        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.status.setText("Study Buddy is not ready yet.")

    # -------------------------------------------------------------- helpers
    def _fit_bubble(self, label: QLabel, text: str) -> None:
        """Give a word-wrapped bubble an explicit width (QLabel's own sizeHint is capped)."""
        available = max(220, int(self.width() * 0.74))
        metrics = label.fontMetrics()
        widest = max(
            (metrics.horizontalAdvance(line) for line in (text or " ").splitlines()),
            default=0,
        )
        width = min(max(widest + 36, 150), available)
        label.setFixedWidth(width)
        label.setFixedHeight(label.heightForWidth(width) + 2)

    def _add_bubble(self, text: str, role: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.MarkdownText)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setStyleSheet(USER_BUBBLE if role == "user" else ASSISTANT_BUBBLE)

        row = QHBoxLayout()
        if role == "user":
            row.addStretch(1)
            row.addWidget(label, 0, Qt.AlignTop)
        else:
            row.addWidget(label, 0, Qt.AlignTop)
            row.addStretch(1)

        # Keep the stretch spacer at the very end of the transcript.
        self.transcript_layout.insertLayout(self.transcript_layout.count() - 1, row)
        self._fit_bubble(label, text)
        self._bubbles.append(label)
        return label

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        for label in self._bubbles:
            self._fit_bubble(label, label.text())

    def _scroll_to_bottom(self) -> None:
        def _apply():
            bar = self.scroll.verticalScrollBar()
            bar.setValue(bar.maximum())

        _apply()
        QTimer.singleShot(0, _apply)

    def _use_starter(self, prompt: str) -> None:
        self.input.setPlainText(prompt)
        self.input.setFocus()
        self.input.moveCursor(self.input.textCursor().End)

    def _hide_starters(self) -> None:
        for widget in self._starter_widgets:
            widget.hide()

    def _set_busy(self, busy: bool) -> None:
        self.send_btn.setEnabled(not busy)
        self.send_btn.setText("…" if busy else "Send")
        self.new_chat_btn.setEnabled(not busy)
        self.input.setReadOnly(busy)
        self.status.setText("Study Buddy is thinking…" if busy else "")

    # ---------------------------------------------------------------- flow
    def reset_chat(self) -> None:
        if self._worker is not None:
            return
        self.history.clear()
        self._bubbles.clear()
        while self.transcript_layout.count() > 1:
            item = self.transcript_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget() is not None:
                        child.widget().deleteLater()
                item.layout().deleteLater()
        for widget in self._starter_widgets:
            widget.show()
        self.status.setText("")
        self.input.clear()

    def send_message(self) -> None:
        if not self.ready or self._worker is not None:
            return

        text = self.input.toPlainText().strip()
        if not text:
            return

        self.input.clear()
        self._hide_starters()
        self._add_bubble(text, "user")
        self.history.append({"role": "user", "content": text})
        if len(self.history) > MAX_HISTORY_MESSAGES:
            self.history = self.history[-MAX_HISTORY_MESSAGES:]

        self._stream_text = ""
        self._stream_label = self._add_bubble("", "assistant")
        self._set_busy(True)
        self._scroll_to_bottom()

        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.history]

        self._worker = ChatWorker(messages, parent=self)
        self._worker.chunk.connect(self._on_chunk)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def _on_chunk(self, piece: str) -> None:
        self._stream_text += piece
        if self._stream_label is not None:
            self._stream_label.setText(self._stream_text)
            self._fit_bubble(self._stream_label, self._stream_text)
        self._scroll_to_bottom()

    def _on_done(self, full_text: str) -> None:
        if self._stream_label is not None:
            self._stream_label.setText(full_text or "_No answer came back. Try again._")
            self._fit_bubble(self._stream_label, self._stream_label.text())
        if full_text:
            self.history.append({"role": "assistant", "content": full_text})
        self._finish_stream()

    def _on_failed(self, message: str) -> None:
        if self._stream_label is not None:
            self._stream_label.setStyleSheet(ASSISTANT_BUBBLE_ERROR)
            self._stream_label.setText(f"⚠️  {message}")
            self._fit_bubble(self._stream_label, self._stream_label.text())
        # Drop the unanswered question so the next send starts from clean context.
        if self.history and self.history[-1]["role"] == "user":
            self.history.pop()
        self._finish_stream()

    def _finish_stream(self) -> None:
        self._stream_text = ""
        self._stream_label = None
        self._set_busy(False)
        self.input.setFocus()
        self._scroll_to_bottom()

    def _cleanup_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def closeEvent(self, event) -> None:
        if self._worker is not None:
            self._worker.wait(2000)
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = StudyBuddyDialog()
    dialog.show()
    sys.exit(app.exec())
