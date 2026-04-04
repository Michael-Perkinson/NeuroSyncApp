"""Controller for telemetry table setup, sorting, and population."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkf
from tkinter import ttk


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
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        style.map("Treeview", background=[("selected", "blue")])
        style.configure("Treeview", selectbackground="blue", selectforeground="white")
        style.configure("Treeview", relief="flat", borderwidth=0)
        style.configure("Treeview.Heading", relief="flat", borderwidth=0)
        style.map("Treeview.Heading", background=[("", "grey")])

        table_container_frame = ttk.Frame(frame, style="NoBorder.TFrame")
        table_container_frame.grid(
            row=0, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW
        )

        table_hscrollbar = ttk.Scrollbar(table_container_frame, orient=tk.HORIZONTAL)
        table_hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.app.table_vscrollbar = ttk.Scrollbar(
            table_container_frame, orient="vertical"
        )
        self.app.table_vscrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.app.table_canvas = tk.Canvas(
            table_container_frame,
            xscrollcommand=table_hscrollbar.set,
            yscrollcommand=self.app.table_vscrollbar.set,
            height=430,
        )
        self.app.table_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        table_scroll_frame = ttk.Frame(self.app.table_canvas)
        self.app.table_canvas.create_window((0, 0), window=table_scroll_frame, anchor="nw")

        def configure_scroll_region(_event):
            self.app.table_canvas.configure(
                scrollregion=self.app.table_canvas.bbox("all"), height=420
            )

        table_scroll_frame.bind("<Configure>", configure_scroll_region)

        self.app.table_treeview = ttk.Treeview(
            table_scroll_frame,
            columns=self.COLUMNS,
            show="headings",
            name="treeview",
        )
        self.app.table_treeview.configure(height=30)
        self.app.table_treeview.pack(fill=tk.BOTH, expand=True)
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
            self.app.table_treeview.column(column, width=tkf.Font().measure(column) + 11)

        table_hscrollbar.configure(command=self.app.table_canvas.xview)
        self.app.table_vscrollbar.configure(command=self.app.table_treeview.yview)
        table_container_frame.grid_rowconfigure(0, weight=1)
        table_container_frame.grid_columnconfigure(0, weight=1)

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
