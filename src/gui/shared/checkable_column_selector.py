from __future__ import annotations

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import (
    QFrame,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.shared.qt_view_styles import PALETTE, apply_button_role

_POPUP_STYLESHEET = f"""
QFrame#checkableColumnPopup {{
    background: #FFFFFF;
    border: 1px solid {PALETTE["border_strong"]};
    border-radius: 6px;
}}
QListWidget {{
    background: #FFFFFF;
    border: none;
    outline: none;
}}
QListWidget::item {{
    padding: 4px 6px;
    color: {PALETTE["text"]};
}}
QListWidget::item:hover {{
    background: {PALETTE["card_alt_bg"]};
}}
QListWidget::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {PALETTE["border_strong"]};
    border-radius: 3px;
    background: #FFFFFF;
}}
QListWidget::indicator:checked {{
    background: {PALETTE["accent"]};
    border: 1px solid {PALETTE["accent"]};
}}
"""


class CheckableColumnSelector(QFrame):
    """Button that opens an overlaying popup with a checkable list of columns.

    Replaces the single ComboBoxControl for column selection so multiple
    signal columns can be selected at once for plotting and export. Behaves
    like a combo-box dropdown — the list overlays the UI and disappears on
    an outside click, rather than expanding the surrounding layout.
    """

    selectionChanged = Signal(list)  # list[str] of checked column names

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._building = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._button = QPushButton("No columns loaded", self)
        apply_button_role(self._button)
        self._button.clicked.connect(self._toggle_popup)
        layout.addWidget(self._button)

        self._popup = QFrame(self, Qt.WindowType.Popup)
        self._popup.setObjectName("checkableColumnPopup")
        self._popup.setStyleSheet(_POPUP_STYLESHEET)
        popup_layout = QVBoxLayout(self._popup)
        popup_layout.setContentsMargins(4, 4, 4, 4)

        self._list = QListWidget(self._popup)
        self._list.setMaximumHeight(160)
        self._list.itemChanged.connect(self._on_item_changed)
        popup_layout.addWidget(self._list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_columns(
        self, columns: list[str], default_checked: str | list[str] = ""
    ) -> None:
        """Populate the list, ticking *default_checked* initially.

        *default_checked* may be a single column name or a list of names
        (used to restore a remembered multi-column selection).
        """
        if isinstance(default_checked, str):
            checked = {default_checked} if default_checked else set()
        else:
            checked = set(default_checked)
        self._building = True
        self._list.clear()
        for col in columns:
            item = QListWidgetItem(col)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
            )
            state = (
                Qt.CheckState.Checked
                if col in checked
                else Qt.CheckState.Unchecked
            )
            item.setCheckState(state)
            self._list.addItem(item)
        self._building = False
        self._update_button_text()
        self.setEnabled(True)

    @property
    def selected_columns(self) -> list[str]:
        return [
            self._list.item(i).text()
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.CheckState.Checked
        ]

    @property
    def primary_column(self) -> str:
        cols = self.selected_columns
        return cols[0] if cols else ""

    # ------------------------------------------------------------------
    # Tkinter-compat shim — callers use widget["state"] = "normal"
    # ------------------------------------------------------------------

    def __setitem__(self, key: str, value) -> None:
        if key == "state":
            self.setEnabled(value not in {"disabled", False})

    def __getitem__(self, key: str):
        if key == "state":
            return "normal" if self.isEnabled() else "disabled"
        raise KeyError(key)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _toggle_popup(self) -> None:
        if self._popup.isVisible():
            self._popup.hide()
            return
        width = max(self._button.width(), 220)
        self._popup.setFixedWidth(width)
        position = self._button.mapToGlobal(QPoint(0, self._button.height()))
        self._popup.move(position)
        self._popup.show()

    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        if self._building:
            return
        self._update_button_text()
        self.selectionChanged.emit(self.selected_columns)

    def _update_button_text(self) -> None:
        cols = self.selected_columns
        if not cols:
            self._button.setText("0 columns selected")
        elif len(cols) == 1:
            self._button.setText(f"1 column: {cols[0]}")
        else:
            names = ", ".join(cols)
            self._button.setText(f"{len(cols)} columns: {names}")
