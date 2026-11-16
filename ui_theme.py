"""Shared colors, stylesheets and small builders for every page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

BG = "#1D2130"
SIDEBAR = "#0B1220"
CARD = "#172338"
BORDER = "#2B3A52"
DEEP = "#0B1220"
ACCENT = "#6D5AE6"
ACCENT_HOVER = "#8170F0"
TEXT = "#F8FAFC"
BODY = "#CBD5E1"
MUTED = "#94A3B8"
FAINT = "#64748B"
ERROR_TEXT = "#FCA5A5"
ERROR_BORDER = "#7F1D1D"
ERROR_BG = "#2A1414"

WEEKDAYS = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]


def page_style(name: str) -> str:
    return f"QWidget#{name} {{ background-color: {BG}; }}"


def card(name: str = "") -> tuple[QFrame, QVBoxLayout]:
    """A rounded dark card. Set a unique objectName if you target it in CSS."""
    frame = QFrame()
    if name:
        frame.setObjectName(name)
    frame.setStyleSheet(
        f"QFrame#{name} {{ background-color: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; }}"
        if name else
        f"background-color: {CARD}; border: 1px solid {BORDER}; border-radius: 16px;"
    )
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(10)
    return frame, layout


def label(text: str, size: int = 14, color: str = TEXT, bold: bool = False) -> QLabel:
    label_ = QLabel(text)
    label_.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {'bold' if bold else 'normal'}; background: transparent; border: none;")
    label_.setWordWrap(True)
    return label_


def title_label(text: str) -> QLabel:
    return label(text, 18, TEXT, bold=True)


def small_label(text: str, color: str = MUTED) -> QLabel:
    return label(text, 12, color)


def page_header(title: str, subtitle: str) -> QWidget:
    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 4)
    layout.setSpacing(2)
    layout.addWidget(label(title, 24, TEXT, bold=True))
    layout.addWidget(label(subtitle, 13, FAINT))
    return holder


def button(text: str, kind: str = "ghost", height: int = 34) -> QPushButton:
    button_ = QPushButton(text)
    button_.setCursor(Qt.PointingHandCursor)
    button_.setFixedHeight(height)
    if kind == "primary":
        button_.setStyleSheet(
            f"QPushButton {{ color: #FFFFFF; background-color: {ACCENT}; border: none; "
            f"border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}"
            f"QPushButton:disabled {{ background-color: #334155; color: {MUTED}; }}"
        )
    elif kind == "danger":
        button_.setStyleSheet(
            "QPushButton { color: #FCA5A5; background-color: #2A1414; border: 1px solid #7F1D1D; "
            "border-radius: 8px; padding: 0 16px; font-size: 13px; }"
            "QPushButton:hover { background-color: #3B1A1A; }"
        )
    else:
        button_.setStyleSheet(
            f"QPushButton {{ color: {BODY}; background-color: {DEEP}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; padding: 0 16px; font-size: 13px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: #FFFFFF; }}"
            f"QPushButton:disabled {{ color: {FAINT}; }}"
        )
    return button_


def line_edit(placeholder: str = "", height: int = 34) -> "object":
    from PySide6.QtWidgets import QLineEdit

    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)
    edit.setFixedHeight(height)
    edit.setStyleSheet(
        f"QLineEdit {{ background-color: {DEEP}; color: {BODY}; border: 1px solid {BORDER}; "
        f"border-radius: 8px; padding: 0 10px; font-size: 13px; }}"
        f"QLineEdit:focus {{ border-color: {ACCENT}; }}"
    )
    return edit


def chip_button(text: str) -> QPushButton:
    button_ = QPushButton(text)
    button_.setCursor(Qt.PointingHandCursor)
    button_.setStyleSheet(
        f"QPushButton {{ color: #A5B4FC; background-color: {DEEP}; border: 1px solid {BORDER}; "
        f"border-radius: 14px; padding: 6px 12px; font-size: 11px; }}"
        f"QPushButton:hover {{ border-color: {ACCENT}; color: #FFFFFF; }}"
    )
    return button_


def empty_note(text: str) -> QLabel:
    return label(text, 13, MUTED)


def v_bar(value: int, maximum: int = 100) -> "object":
    from PySide6.QtWidgets import QProgressBar

    bar = QProgressBar()
    bar.setRange(0, maximum)
    bar.setValue(value)
    bar.setTextVisible(False)
    bar.setFixedSize(30, 110)
    bar.setStyleSheet(
        f"QProgressBar {{ background-color: {DEEP}; border: none; border-radius: 6px; }}"
        f"QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 6px; }}"
    )
    return bar