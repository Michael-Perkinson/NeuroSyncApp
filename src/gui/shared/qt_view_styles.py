from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt

_ARROW_DOWN = str(Path(__file__).parent / "assets" / "arrow_down.svg").replace("\\", "/")

APP_FONT_FAMILY = "DejaVu Sans"
MONO_FONT_FAMILY = "DejaVu Sans Mono"
APP_FONT_POINT_SIZE = 9

PALETTE = {
    "app_bg": "#EDF3F8",
    "panel_bg": "#F7FAFD",
    "card_bg": "#FFFFFF",
    "card_alt_bg": "#EEF5FA",
    "border": "#CCD8E4",
    "border_strong": "#A9BBCD",
    "text": "#17324D",
    "muted": "#62758B",
    "accent": "#0F766E",
    "accent_hover": "#0C5E58",
    "accent_soft": "#D7EEEB",
    "button_bg": "#EEF4F9",
    "button_hover": "#E1EBF4",
}

APP_TABS_STYLESHEET = f"""
QTabWidget::pane {{
    border: 1px solid {PALETTE["border"]};
    border-radius: 8px;
    background: {PALETTE["panel_bg"]};
    top: -1px;
}}
QTabBar::tab {{
    background: {PALETTE["button_bg"]};
    color: {PALETTE["muted"]};
    border: 1px solid {PALETTE["border"]};
    padding: 5px 10px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    color: {PALETTE["text"]};
    background: {PALETTE["card_bg"]};
    border-color: {PALETTE["border_strong"]};
}}
"""


def panel_stylesheet(object_name: str) -> str:
    return f"""
#{object_name} {{
    background: {PALETTE["panel_bg"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 10px;
}}
#{object_name} QLabel {{
    color: {PALETTE["text"]};
}}
#{object_name} QLineEdit,
#{object_name} QComboBox,
#{object_name} QPlainTextEdit {{
    background: {PALETTE["card_bg"]};
    color: {PALETTE["text"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 6px;
    padding: 3px 6px;
}}
#{object_name} QLineEdit:focus,
#{object_name} QComboBox:focus,
#{object_name} QPlainTextEdit:focus {{
    border-color: {PALETTE["accent"]};
}}
#{object_name} QComboBox::drop-down {{
    width: 24px;
    border: 0;
}}
#{object_name} QComboBox::down-arrow {{
    image: url({_ARROW_DOWN});
    width: 10px;
    height: 6px;
}}
#{object_name} QCheckBox {{
    color: {PALETTE["text"]};
    spacing: 6px;
}}
#{object_name} QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {PALETTE["border_strong"]};
    background: {PALETTE["card_bg"]};
}}
#{object_name} QCheckBox::indicator:checked {{
    background: {PALETTE["accent"]};
    border-color: {PALETTE["accent"]};
}}
#{object_name} QScrollArea {{
    border: 0;
    background: {PALETTE["panel_bg"]};
}}
#{object_name} QScrollArea > QWidget > QWidget {{
    background: {PALETTE["panel_bg"]};
}}
#{object_name} QTreeView,
#{object_name} QTableView {{
    background: {PALETTE["card_bg"]};
    alternate-background-color: {PALETTE["card_alt_bg"]};
    color: {PALETTE["text"]};
    border: 1px solid {PALETTE["border"]};
    gridline-color: {PALETTE["border"]};
}}
#{object_name} QTreeView::item,
#{object_name} QTableView::item {{
    padding: 4px;
}}
#{object_name} QHeaderView::section {{
    background: {PALETTE["button_bg"]};
    color: {PALETTE["text"]};
    border: 1px solid {PALETTE["border"]};
    padding: 4px 6px;
    font-weight: 600;
}}
"""


def section_stylesheet(object_name: str, alt: bool = False) -> str:
    background = PALETTE["card_alt_bg"] if alt else PALETTE["card_bg"]
    return f"""
#{object_name} {{
    background: {background};
    border: 1px solid {PALETTE["border"]};
    border-radius: 8px;
}}
"""


def title_stylesheet() -> str:
    return f"font-size: 13px; font-weight: 700; color: {PALETTE['text']};"


def section_title_stylesheet() -> str:
    return f"font-size: 12px; font-weight: 700; color: {PALETTE['text']};"


def subtitle_stylesheet() -> str:
    return f"font-size: 11px; color: {PALETTE['muted']};"


def button_stylesheet(role: str = "secondary") -> str:
    if role == "primary":
        return f"""
QPushButton {{
    background: {PALETTE["accent"]};
    color: white;
    border: 1px solid {PALETTE["accent"]};
    border-radius: 10px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {PALETTE["accent_hover"]};
}}
"""
    if role == "flat":
        return f"""
QPushButton {{
    background: transparent;
    color: {PALETTE["text"]};
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 6px 10px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {PALETTE["button_bg"]};
}}
"""
    return f"""
QPushButton {{
    background: {PALETTE["button_bg"]};
    color: {PALETTE["text"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 10px;
    padding: 7px 12px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {PALETTE["button_hover"]};
    border-color: {PALETTE["border_strong"]};
}}
"""


def apply_button_role(button, role: str = "secondary") -> None:
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet(button_stylesheet(role))
