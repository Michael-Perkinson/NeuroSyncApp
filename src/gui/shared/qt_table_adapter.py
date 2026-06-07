from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem


class QtTableAdapter(QTableWidget):
    def __init__(self, columns: list[str], parent=None) -> None:
        super().__init__(0, len(columns), parent)
        self._columns = list(columns)
        self._column_index = {name: index for index, name in enumerate(self._columns)}
        self._row_ids: list[str] = []
        self._row_tags: dict[str, tuple[str, ...]] = {}
        self._tag_styles: dict[str, dict[str, str]] = {}
        self._heading_callbacks: dict[int, Callable[[], None]] = {}
        self._id_counter = 0

        self.setHorizontalHeaderLabels(
            [column.capitalize().replace("_", " ") for column in self._columns]
        )
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().sectionClicked.connect(self._on_header_clicked)

    def heading(self, column: str, text: str | None = None, command: Callable[[], None] | None = None) -> None:
        column_index = self._column_index[column]
        if text is not None:
            header_item = self.horizontalHeaderItem(column_index)
            if header_item is None:
                header_item = QTableWidgetItem(text)
                self.setHorizontalHeaderItem(column_index, header_item)
            else:
                header_item.setText(text)
        if command is not None:
            self._heading_callbacks[column_index] = command

    def column(self, column: str, width: int | None = None) -> None:
        if width is not None:
            self.setColumnWidth(self._column_index[column], max(int(width), 40))

    def bind(self, event_name: str, callback: Callable[..., None]) -> None:
        if event_name == "<<TreeviewSelect>>":
            self.itemSelectionChanged.connect(lambda: callback(None))

    def configure(self, **kwargs) -> None:
        height = kwargs.get("height")
        if height is not None:
            self.setMinimumHeight(150)
        yscrollcommand = kwargs.get("yscrollcommand")
        if yscrollcommand is not None:
            self.verticalScrollBar().valueChanged.connect(lambda *_args: yscrollcommand())

    config = configure

    def insert(self, _parent: str, _index: str, values=(), tags=()) -> str:
        row_id = f"row_{self._id_counter}"
        self._id_counter += 1
        row_index = self.rowCount()
        self.insertRow(row_index)
        self._row_ids.append(row_id)
        self._row_tags[row_id] = tuple(tags or ())

        for column_index, value in enumerate(values):
            item = QTableWidgetItem("" if value is None else str(value))
            self.setItem(row_index, column_index, item)

        self._apply_row_tags(row_index, row_id)
        return row_id

    def delete(self, *item_ids) -> None:
        if not item_ids:
            self.setRowCount(0)
            self._row_ids.clear()
            self._row_tags.clear()
            return

        for item_id in list(item_ids):
            if item_id not in self._row_ids:
                continue
            row_index = self._row_ids.index(item_id)
            self.removeRow(row_index)
            self._row_ids.pop(row_index)
            self._row_tags.pop(item_id, None)

    def get_children(self, _item: str = "") -> list[str]:
        return list(self._row_ids)

    def set(self, item_id: str, column: str, value=None):
        row_index = self._row_ids.index(item_id)
        column_index = self._column_index[column]
        cell = super().item(row_index, column_index)
        if cell is None:
            cell = QTableWidgetItem("")
            self.setItem(row_index, column_index, cell)

        if value is None:
            return cell.text()

        cell.setText("" if value is None else str(value))
        return cell.text()

    def move(self, item_id: str, _parent: str, index: int) -> None:
        if item_id not in self._row_ids:
            return

        current_index = self._row_ids.index(item_id)
        if current_index == index:
            return

        row_values = self.item(item_id)["values"]
        row_tags = self._row_tags.get(item_id, ())
        self.removeRow(current_index)
        self._row_ids.pop(current_index)

        self.insertRow(index)
        self._row_ids.insert(index, item_id)
        self._row_tags[item_id] = row_tags
        for column_index, value in enumerate(row_values):
            self.setItem(index, column_index, QTableWidgetItem("" if value is None else str(value)))
        self._apply_row_tags(index, item_id)

    def item(self, item_id: str | int):
        if isinstance(item_id, int):
            return super().item(item_id, 0)
        row_index = self._row_ids.index(item_id)
        values = []
        for column_index in range(self.columnCount()):
            cell = super().item(row_index, column_index)
            values.append(cell.text() if cell is not None else "")
        return {"values": values}

    def focus(self) -> str:
        current_row = self.currentRow()
        if current_row < 0 or current_row >= len(self._row_ids):
            return ""
        return self._row_ids[current_row]

    def selection(self) -> list[str]:
        current_row = self.currentRow()
        if current_row < 0 or current_row >= len(self._row_ids):
            return []
        return [self._row_ids[current_row]]

    def tag_configure(self, tag: str, background: str | None = None, **_kwargs) -> None:
        style = self._tag_styles.setdefault(tag, {})
        if background is not None:
            style["background"] = background

    def update_idletasks(self) -> None:
        self.viewport().update()

    def yview(self, *_args, **_kwargs) -> None:
        return

    def _on_header_clicked(self, section: int) -> None:
        callback = self._heading_callbacks.get(section)
        if callback is not None:
            callback()

    def _apply_row_tags(self, row_index: int, row_id: str) -> None:
        tags = self._row_tags.get(row_id, ())
        background = None
        for tag in tags:
            style = self._tag_styles.get(tag, {})
            if "background" in style:
                background = style["background"]

        if background is None:
            return

        color = QColor(background)
        for column_index in range(self.columnCount()):
            item = super().item(row_index, column_index)
            if item is not None:
                item.setBackground(color)

    def setSectionResizeMode(self, mode: QHeaderView.ResizeMode) -> None:
        self.horizontalHeader().setSectionResizeMode(mode)
