"""Reusable Qt panel for displaying a Matplotlib figure."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget


@dataclass
class GraphReference:
    figure: Figure
    primary_axis: object
    secondary_axis: object
    start_line: object
    end_line: object


class GraphPanel(QWidget):
    """Own the canvas and toolbar for one replaceable Matplotlib figure."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas: FigureCanvasQTAgg | None = None
        self.toolbar: NavigationToolbar2QT | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

    def set_figure(self, figure: Figure) -> None:
        self.clear()
        self.canvas = FigureCanvasQTAgg(figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self._layout.addWidget(self.canvas, 1)
        self._layout.addWidget(self.toolbar)
        self.canvas.draw()

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
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
