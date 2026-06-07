from __future__ import annotations

from matplotlib import cbook
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.gui.shared.qt_view_styles import PALETTE


class LightNavigationToolbar(NavigationToolbar2QT):
    """Navigation toolbar with stable dark icons for light Qt panels."""

    def _icon(self, name):
        path_regular = cbook._get_data_path("images", name)
        path_large = path_regular.with_name(
            path_regular.name.replace(".png", "_large.png")
        )
        filename = str(path_large if path_large.exists() else path_regular)
        pixmap = QPixmap(filename)
        pixmap.setDevicePixelRatio(self.devicePixelRatioF() or 1)
        return QIcon(pixmap)


def create_styled_figure() -> tuple[Figure, object]:
    fig = Figure(figsize=(10, 6), dpi=100, constrained_layout=True)
    ax = fig.add_subplot(111)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    return fig, ax


def destroy_embedded_figure(figure_canvas, toolbar) -> None:
    for widget in (toolbar, figure_canvas):
        if widget is None:
            continue
        try:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        except RuntimeError:
            continue


def embed_figure_in_qt(fig: Figure, graph_canvas: QWidget):
    layout = graph_canvas.layout()
    if layout is None:
        layout = QVBoxLayout(graph_canvas)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()

    figure_canvas = FigureCanvasQTAgg(fig)
    # Set parent immediately to prevent the parentless widget briefly appearing
    # as a standalone top-level window before it is added to the layout.
    figure_canvas.setParent(graph_canvas)
    toolbar = LightNavigationToolbar(figure_canvas, graph_canvas)
    toolbar.setIconSize(QSize(18, 18))
    toolbar.setMinimumHeight(34)
    toolbar.setStyleSheet(
        f"""
QToolBar {{
    background: {PALETTE["panel_bg"]};
    border: 0;
    spacing: 4px;
}}
QToolButton {{
    background: {PALETTE["card_bg"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 6px;
    padding: 3px;
}}
QToolButton:hover {{
    background: {PALETTE["button_hover"]};
    border-color: {PALETTE["border_strong"]};
}}
QToolButton:checked {{
    background: {PALETTE["accent_soft"]};
    border-color: {PALETTE["accent"]};
}}
QToolButton:disabled {{
    background: {PALETTE["panel_bg"]};
    border-color: {PALETTE["border"]};
}}
QToolBar QLabel {{
    color: {PALETTE["muted"]};
}}
"""
    )
    layout.addWidget(figure_canvas, 1)
    layout.addWidget(toolbar)
    figure_canvas.draw()
    return figure_canvas, toolbar
