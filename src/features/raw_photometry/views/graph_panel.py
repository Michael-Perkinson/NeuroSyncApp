"""Reusable Qt panel for displaying a Matplotlib figure."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from matplotlib.axes import Axes
from matplotlib.backends.backend_qt import NavigationToolbar2QT
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPalette, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

_RAW_GRAPH_TOOLBAR_STYLESHEET = """
QToolBar {
    background: #DCE8F2;
    border: 1px solid #A9BBCD;
    border-radius: 6px;
    spacing: 3px;
    padding: 2px 4px;
}
QToolBar QLabel {
    color: #17324D;
    background: transparent;
    padding: 0 4px;
}
QToolBar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 2px;
    min-width: 22px;
    min-height: 22px;
}
QToolBar QToolButton:hover {
    background: #EEF4F9;
    border-color: #A9BBCD;
}
QToolBar QToolButton:pressed,
QToolBar QToolButton:checked {
    background: #D7EEEB;
    border-color: #0F766E;
}
QToolBar QToolButton:disabled {
    background: transparent;
    border-color: transparent;
}
QToolBar::separator {
    width: 1px;
    background: #A9BBCD;
    margin: 3px 2px;
}
"""


def _tint_toolbar_pixmap(pixmap: QPixmap, color: QColor) -> QPixmap:
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    tinted_color = QColor(color)
    for y in range(image.height()):
        for x in range(image.width()):
            alpha = image.pixelColor(x, y).alpha()
            if alpha:
                tinted_color.setAlpha(alpha)
                image.setPixelColor(x, y, tinted_color)
    return QPixmap.fromImage(image)


def _recolor_toolbar_icons(toolbar: NavigationToolbar2QT) -> None:
    for button in toolbar.findChildren(QToolButton):
        source_icon = button.icon()
        if button.defaultAction() is None or source_icon.isNull():
            continue
        tinted_icon = QIcon()
        for mode, color in (
            (QIcon.Mode.Normal, QColor("#17324D")),
            (QIcon.Mode.Disabled, QColor("#62758B")),
            (QIcon.Mode.Active, QColor("#17324D")),
            (QIcon.Mode.Selected, QColor("#0F766E")),
        ):
            for state in (QIcon.State.Off, QIcon.State.On):
                for dimension in (16, 20, 24, 32):
                    pixmap = source_icon.pixmap(
                        QSize(dimension, dimension), mode, state
                    )
                    if not pixmap.isNull():
                        tinted_icon.addPixmap(
                            _tint_toolbar_pixmap(pixmap, color), mode, state
                        )
        button.setIcon(tinted_icon)


@dataclass
class GraphReference:
    figure: Figure
    primary_axis: Axes
    secondary_axis: Axes | None
    start_line: Line2D
    end_line: Line2D
    time_start: float
    time_end: float


class GraphPanel(QWidget):
    """Own the canvas and toolbar for one replaceable Matplotlib figure."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas: FigureCanvasQTAgg | None = None
        self.toolbar: NavigationToolbar2QT | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def set_figure(self, figure: Figure, *, compact_axis_labels: bool = False) -> None:
        self.clear()
        self.canvas = FigureCanvasQTAgg(figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        toolbar_palette = self.toolbar.palette()
        toolbar_color = QColor("#DCE8F2")
        toolbar_palette.setColor(QPalette.ColorRole.Window, toolbar_color)
        toolbar_palette.setColor(QPalette.ColorRole.Button, toolbar_color)
        toolbar_palette.setColor(QPalette.ColorRole.Base, toolbar_color)
        toolbar_palette.setColor(QPalette.ColorRole.WindowText, QColor("#17324D"))
        toolbar_palette.setColor(QPalette.ColorRole.Text, QColor("#17324D"))
        self.toolbar.setPalette(toolbar_palette)
        self.toolbar.setAutoFillBackground(True)
        self.toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.toolbar.setStyleSheet(_RAW_GRAPH_TOOLBAR_STYLESHEET)
        _recolor_toolbar_icons(self.toolbar)
        self.toolbar.setProperty("rawToolbarIconsTinted", True)
        self._layout.addWidget(self.canvas, 1)
        if compact_axis_labels:
            footer = QWidget(self)
            footer_layout = QHBoxLayout(footer)
            footer_layout.setContentsMargins(0, 0, 0, 0)
            footer_layout.setSpacing(8)
            self.toolbar.setSizePolicy(
                QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
            )
            footer_layout.addWidget(self.toolbar)
            footer_layout.addStretch(1)
            axis_label_strip = self._axis_label_strip(figure, footer)
            if axis_label_strip is not None:
                footer_layout.addWidget(axis_label_strip)
            self._layout.addWidget(footer)
        else:
            self._layout.addWidget(self.toolbar)
        self.canvas.draw()

    @staticmethod
    def _axis_label_strip(figure: Figure, parent: QWidget) -> QWidget | None:
        labels: list[QLabel] = []
        for axis in figure.axes:
            if not axis.get_visible():
                continue
            text = axis.get_ylabel().strip()
            if not text:
                continue
            color = axis.yaxis.label.get_color()
            if not isinstance(color, str):
                color = "#17324D"
            label = QLabel(text, parent)
            label.setObjectName("rawGraphAxisLabel")
            label.setStyleSheet(f"color: {color}; font-weight: 600; padding: 0 4px;")
            labels.append(label)
        if not labels:
            return None

        strip = QWidget(parent)
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(0, 0, 0, 0)
        strip_layout.setSpacing(4)
        for label in labels:
            strip_layout.addWidget(label)
        strip_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        return strip

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                if isinstance(widget, FigureCanvasQTAgg):
                    widget._draw_pending = False
                    widget._is_drawing = False
                    try:
                        widget.figure.clear()
                    except RuntimeError:
                        logging.getLogger(__name__).debug(
                            "Figure cleanup: Qt object already deleted"
                        )
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.canvas = None
        self.toolbar = None
