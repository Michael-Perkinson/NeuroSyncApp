from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget


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
    toolbar = NavigationToolbar2QT(figure_canvas, graph_canvas)
    layout.addWidget(figure_canvas, 1)
    layout.addWidget(toolbar)
    figure_canvas.draw()
    return figure_canvas, toolbar
