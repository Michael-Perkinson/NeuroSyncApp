"""Controller for behaviour table setup, sorting, and row lifecycle."""

from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QMessageBox, QFrame, QVBoxLayout

from src.gui.shared.qt_view_styles import panel_stylesheet
from src.gui.shared.qt_table_adapter import QtTableAdapter

from src.processing.behaviour_plotting import build_treeview_rows


class BehaviourTablePanel:
    """Owns the treeview UI setup plus table update/sort behaviors."""

    TABLE_COLUMNS = [
        "file_name",
        "column_title",
        "behaviour_name",
        "behaviour_type",
        "pre_behaviour_time",
        "post_behaviour_time",
        "bin_size",
        "start_time",
        "end_time",
    ]

    def __init__(self, app):
        self.app = app

    def create_table_container(self, frame) -> None:
        table_container_frame = QFrame(frame)
        table_container_frame.setObjectName("behaviourTableContainer")
        table_container_frame.setStyleSheet(
            panel_stylesheet("behaviourTableContainer")
        )
        layout = QVBoxLayout(table_container_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        frame.layout().addWidget(table_container_frame)

        self.app.table_treeview = QtTableAdapter(self.TABLE_COLUMNS, table_container_frame)
        self.app.table_treeview.configure(height=30)
        layout.addWidget(self.app.table_treeview)

        for column in self.TABLE_COLUMNS:
            self.app.table_treeview.heading(
                column,
                text=column.capitalize().replace("_", " "),
                command=lambda _col=column: self.treeview_sort_column(
                    self.app.table_treeview, _col, False
                ),
            )

        for column in self.TABLE_COLUMNS:
            measured_width = max(len(column) * 10, 80)
            width = measured_width - 20 if measured_width > 110 else measured_width
            self.app.table_treeview.column(column, width=width)

        self.app.table_treeview.bind(
            "<<TreeviewSelect>>", self.app.manual_session_service.on_row_click
        )

    def treeview_sort_column(self, treeview, column, reverse) -> None:
        values = [(treeview.set(item, column), item) for item in treeview.get_children("")]

        def convert(value):
            if value == "":
                return None
            try:
                return float(value)
            except ValueError:
                return value

        values = [(convert(value), item) for value, item in values]
        if reverse:
            values.sort(
                key=lambda row: float("-inf") if row[0] is None else row[0], reverse=True
            )
        else:
            values.sort(key=lambda row: float("inf") if row[0] is None else row[0])

        for index, (_, item) in enumerate(values):
            treeview.move(item, "", index)

        treeview.heading(
            column,
            command=lambda _col=column: self.treeview_sort_column(
                treeview, _col, not reverse
            ),
        )

    def clear_table(self) -> None:
        self.app.original_table = None
        self.app.current_table_key = None
        self.app.tables.clear()
        self.app.duration_data_cache = {}

    def adjust_start_end_times(self, dataframe):
        raw = self.app.data_selection_frame.baseline_start_entry.get().strip()
        if not raw:
            return dataframe
        baseline_offset = float(raw)
        dataframe["Start Time"] -= baseline_offset
        dataframe["End Time"] = pd.to_numeric(dataframe["End Time"], errors="coerce")
        dataframe["End Time"] = dataframe["End Time"].apply(
            lambda value: value - baseline_offset if pd.notnull(value) else value
        )
        return dataframe

    def update_table_from_frame(self) -> None:
        if self.app.current_table_key is None or self.app.current_table_key not in self.app.tables:
            return

        current_df = self.app.tables[self.app.current_table_key].copy()
        self.update_table(current_df)
        self.app.plot_service.handle_figure_display_selection(None)
        self.app.adjusted_behaviour_dataframes = {}

    def update_table(self, dataframe, new=False) -> None:
        if self.app.checkbox_state and new is not True:
            dataframe = self.adjust_start_end_times(dataframe)
            self.app.tables[self.app.current_table_key] = dataframe

        if not self.app.warning_shown:
            negative_behaviours = []
            for _, row in dataframe.iterrows():
                try:
                    start_time = float(row["Start Time"])
                    pre_behaviour_time = float(row["Pre Behaviour Time"])
                    if (start_time - pre_behaviour_time) < 0:
                        negative_behaviours.append(row["Behaviour Name"])
                except ValueError:
                    continue

            if negative_behaviours:
                negative_behaviours_str = ", ".join(negative_behaviours)
                QMessageBox.warning(
                    self.app,
                    "Negative Time Warning",
                    "The following behaviours have a start time that, when adjusted "
                    f"by the pre-behaviour time, becomes negative: {negative_behaviours_str}",
                )
                self.app.warning_shown = True

        try:
            dataframe["Start Time"] = dataframe["Start Time"].astype(float)
        except ValueError:
            pass

        dataframe = dataframe[dataframe["Start Time"] >= 0]
        self.app.table_treeview.delete(*self.app.table_treeview.get_children())
        self.populate_table(dataframe)
        self.adjust_column_widths()
        self.update_table_scrollbar()

    def populate_table(self, dataframe) -> None:
        for values in build_treeview_rows(dataframe):
            self.app.table_treeview.insert("", "end", values=values)

    def adjust_column_widths(self) -> None:
        for column in self.TABLE_COLUMNS:
            self.app.table_treeview.column(column, width=max(len(column) * 10, 80))

    def update_table_scrollbar(self) -> None:
        self.app.table_treeview.update_idletasks()
