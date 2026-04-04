"""Controller for behaviour table setup, sorting, and row lifecycle."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkf
from tkinter import messagebox, ttk

import pandas as pd

from src.processing.behaviour_plotting import build_treeview_rows


class BehaviourTableController:
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
            columns=self.TABLE_COLUMNS,
            show="headings",
            name="treeview",
        )
        self.app.table_treeview.configure(height=30)
        self.app.table_treeview.pack(fill=tk.BOTH, expand=True)

        for column in self.TABLE_COLUMNS:
            self.app.table_treeview.heading(
                column,
                text=column.capitalize().replace("_", " "),
                command=lambda _col=column: self.treeview_sort_column(
                    self.app.table_treeview, _col, False
                ),
            )

        for column in self.TABLE_COLUMNS:
            measured_width = tkf.Font().measure(column)
            width = measured_width - 20 if measured_width > 110 else measured_width
            self.app.table_treeview.column(column, width=width)

        table_hscrollbar.configure(command=self.app.table_canvas.xview)
        self.app.table_vscrollbar.configure(command=self.app.table_treeview.yview)

        table_container_frame.grid_rowconfigure(0, weight=1)
        table_container_frame.grid_columnconfigure(0, weight=1)
        self.app.table_treeview.bind(
            "<<TreeviewSelect>>", self.app.manual_controller.on_row_click
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
        baseline_offset = float(self.app.data_selection_frame.baseline_start_entry.get())
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
        self.app.plot_controller.handle_figure_display_selection(None)
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
                messagebox.showwarning(
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
            self.app.table_treeview.column(column, width=tkf.Font().measure(column))

    def update_table_scrollbar(self) -> None:
        self.app.table_treeview.configure(yscrollcommand=self.app.table_vscrollbar.set)
        self.app.table_treeview.update_idletasks()
