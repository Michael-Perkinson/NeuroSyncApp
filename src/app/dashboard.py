from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.app.catalog import (
    DEFAULT_APP_ID,
    get_app_definition,
    iter_app_definitions,
)
from src.gui.shared.qt_view_styles import PALETTE
from src.shared.persistence.dashboard_state import load_state, save_state


class QtDashboard(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.sidebar_expanded = False
        self.sidebar: QWidget | None = None
        self.content_layout: QVBoxLayout | None = None
        self.toggle_button: QToolButton | None = None

        self._setup_window()
        self._setup_sidebar()
        self._load_initial_app()

    def _setup_window(self) -> None:
        self.setWindowTitle("NeuroSyncApp")
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry()
        w = min(1390, available.width())
        h = min(740, available.height() - 50)
        self.resize(w, h)

        root = QWidget(self)
        self.setCentralWidget(root)

        # Content fills the entire root
        content = QFrame(root)
        content.setObjectName("content")
        content.setStyleSheet(f"#content {{ background: {PALETTE['app_bg']}; }}")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(0)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(content, 1)

        # Sidebar floats as an overlay — not in the layout
        self.sidebar = QFrame(root)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet(
            f"#sidebar {{ background: #183247; border-right: 1px solid {PALETTE['border_strong']}; }}"
        )
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(18, 48, 18, 18)
        self.sidebar_layout.setSpacing(8)
        self.sidebar.hide()

        # Toggle button floats over the top-left corner
        self.toggle_button = QToolButton(root)
        self.toggle_button.setText("\u2630")
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.setFixedSize(34, 30)
        self.toggle_button.setStyleSheet(
            "QToolButton { background: #24506d; color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; }"
        )
        self.toggle_button.clicked.connect(self._toggle_sidebar)
        self.toggle_button.move(8, 8)
        self.toggle_button.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_sidebar()

    def _reposition_sidebar(self) -> None:
        if self.sidebar is None:
            return
        central = self.centralWidget()
        h = central.height() if central else self.height()
        self.sidebar.setFixedHeight(h)
        self.sidebar.move(0, 0)

    def _setup_sidebar(self) -> None:
        title = QLabel("Tools", self.sidebar)
        title.setStyleSheet("color: white; font-size: 18px; font-weight: 700;")
        self.sidebar_layout.addWidget(title)

        for definition in iter_app_definitions():
            button = QPushButton(definition.label, self.sidebar)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.08); color: white; border: 1px solid rgba(255,255,255,0.10); "
                "padding: 10px 12px; text-align: left; border-radius: 12px; font-weight: 600; }"
                "QPushButton:hover { background: rgba(255,255,255,0.16); }"
                "QPushButton:disabled { color: rgba(255,255,255,0.45); background: rgba(255,255,255,0.04); }"
            )
            button.clicked.connect(
                lambda _checked=False, app_id=definition.app_id: self.load_app(app_id)
            )
            self.sidebar_layout.addWidget(button)

        self.sidebar_layout.addStretch(1)

    def _clear_content(self) -> None:
        while self.content_layout and self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def load_app(self, app_id: str) -> None:
        definition = get_app_definition(app_id)
        self._clear_content()
        save_state(app_id)
        self._hide_sidebar()

        if not definition.qt_supported:
            card = QFrame(self)
            layout = QVBoxLayout(card)
            layout.setContentsMargins(32, 32, 32, 32)

            heading = QLabel(definition.label, card)
            heading.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {PALETTE['text']};")
            layout.addWidget(heading)

            body = QLabel(
                definition.description or "This tool has not been ported to PySide6 yet.",
                card,
            )
            body.setWordWrap(True)
            body.setStyleSheet(f"font-size: 14px; color: {PALETTE['muted']};")
            layout.addWidget(body)
            layout.addStretch(1)

            self.content_layout.addWidget(card)
            return

        widget_class = definition.load_widget_class()
        widget = widget_class(self)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content_layout.addWidget(widget)

    def _toggle_sidebar(self) -> None:
        self.sidebar_expanded = not self.sidebar_expanded
        if self.sidebar_expanded:
            self._reposition_sidebar()
            self.sidebar.show()
            self.sidebar.raise_()
            self.toggle_button.raise_()
        else:
            self.sidebar.hide()

    def _hide_sidebar(self) -> None:
        self.sidebar_expanded = False
        self.sidebar.hide()

    def _load_initial_app(self) -> None:
        last_app = load_state()
        try:
            definition = (
                get_app_definition(last_app)
                if last_app
                else get_app_definition(DEFAULT_APP_ID)
            )
        except ValueError:
            definition = get_app_definition(DEFAULT_APP_ID)

        if not definition.qt_supported:
            definition = get_app_definition(DEFAULT_APP_ID)

        self.load_app(definition.app_id)
