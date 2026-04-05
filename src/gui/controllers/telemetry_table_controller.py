"""Controller for telemetry table setup, sorting, and population."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout

from src.gui.shared.qt_view_styles import panel_stylesheet
from src.gui.shared.qt_table_adapter import QtTableAdapter

class TelemetryTableController:
    """Owns telemetry cluster table construction and row updates."""

    COLUMNS = [
        "file_name",
        "number_of_peaks",
        "pre_cluster_time",
        "post_cluster_time",
        "bin_size",
        "start_time",
        "end_time",
    ]

    COLUMN_HEADINGS = {
        "file_name": "File name",
        "number_of_peaks": "Number of peaks",
        "pre_cluster_time": "Pre-cluster time",
        "post_cluster_time": "Post-cluster time",
        "bin_size": "Bin size",
        "start_time": "Start time",
        "end_time": "End time",
    }

    def __init__(self, app):
        self.app = app

    def create_table_container(self, frame) -> None:
        table_container_frame = QFrame(frame)
        table_container_frame.setObjectName("telemetryTableContainer")
        table_container_frame.setStyleSheet(
            panel_stylesheet("telemetryTableContainer")
        )
        layout = QVBoxLayout(table_container_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        frame.layout().addWidget(table_container_frame)

        self.app.table_treeview = QtTableAdapter(self.COLUMNS, table_container_frame)
        self.app.table_treeview.configure(height=30)
        layout.addWidget(self.app.table_treeview)
        self.app.table_treeview.tag_configure("Even", background="white")
        self.app.table_treeview.tag_configure("Odd", background="lightgray")

        for column in self.COLUMNS:
            heading_text = self.COLUMN_HEADINGS.get(
                column, column.capitalize().replace("_", " ")
            )
            self.app.table_treeview.heading(
                column,
                text=heading_text,
                command=lambda _col=column: self.treeview_sort_column(
                    self.app.table_treeview, _col, False
                ),
            )
            self.app.table_treeview.column(column, width=max(len(column) * 10, 80))

    def treeview_sort_column(self, tv, col, reverse) -> None:
        values = [(tv.set(key, col), key) for key in tv.get_children("")]

        def convert(value):
            if value == "":
                return None
            try:
                return float(value)
            except ValueError:
                return value

        values = [(convert(value), key) for value, key in values]
        if reverse:
            values.sort(
                key=lambda row: float("-inf") if row[0] is None else row[0], reverse=True
            )
        else:
            values.sort(key=lambda row: float("inf") if row[0] is None else row[0])

        for index, (_, key) in enumerate(values):
            tv.move(key, "", index)

        tv.heading(
            col,
            command=lambda _col=col: self.treeview_sort_column(tv, _col, not reverse),
        )

    def clear_table(self) -> None:
        self.app.table_data.clear()
        self.app.duration_data_cache = {}
        if self.app.table_treeview is not None:
            self.app.table_treeview.delete(*self.app.table_treeview.get_children())

    def populate_table(self) -> None:
        from pathlib import Path

        self.clear_table()
        file_path_str = Path(self.app.file_path.get()).name
        for index, (cluster_name, cluster_data) in enumerate(
            self.app.data_dict[file_path_str].items()
        ):
            if "stim" in cluster_name:
                pre_time = cluster_data.get("pre_stim_time", "N/A")
                post_time = cluster_data.get("post_stim_time", "N/A")
                start_time = format(cluster_data.get("stim_start", 0), ".1f")
                end_time = format(cluster_data.get("stim_end", 0), ".1f")
            else:
                pre_time = cluster_data.get("pre_cluster_time", "N/A")
                post_time = cluster_data.get("post_cluster_time", "N/A")
                start_time = format(cluster_data.get("start_time", 0), ".1f")
                end_time = format(cluster_data.get("end_time", 0), ".1f")

            bin_size = cluster_data.get("bin_size", "N/A")
            tag = "Even" if index % 2 == 0 else "Odd"
            self.app.table_treeview.insert(
                "",
                "end",
                values=(
                    file_path_str,
                    cluster_name,
                    pre_time,
                    post_time,
                    bin_size,
                    start_time,
                    end_time,
                ),
                tags=(tag,),
            )

        self.app.table_treeview.update_idletasks()
