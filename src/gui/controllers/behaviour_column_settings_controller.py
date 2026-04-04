"""Controller for behaviour CSV column-name settings UI and persistence."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from src.gui.shared.window_manager import center_window_on_screen


class BehaviourColumnSettingsController:
    """Owns column-name settings popup creation and JSON persistence."""

    COLUMN_NAMES_PATH = Path("column_names.json")

    def __init__(self, app):
        self.app = app

    def select_column_names(self) -> None:
        """Open a settings dialog where the user maps CSV column names."""
        current_column_names = self.load_column_names()

        settings_window = tk.Toplevel(self.app.winfo_toplevel())
        settings_window.title("Column Names in CSV")

        column_labels = ["Behaviours/events", "Start Time", "End Time"]
        entry_boxes = self.create_column_entries(
            settings_window, column_labels, current_column_names
        )
        self.create_time_unit_dropdown(
            settings_window, len(column_labels), current_column_names
        )

        save_button = tk.Button(
            settings_window,
            text="Save",
            command=lambda: self.save_column_names(settings_window, entry_boxes),
        )
        save_button.grid(
            row=len(column_labels) + 1,
            column=0,
            columnspan=2,
            padx=10,
            pady=5,
            sticky=tk.NSEW,
        )

        settings_window.update_idletasks()
        center_window_on_screen(settings_window)

    def load_column_names(self) -> dict:
        """Load persisted CSV column-name mapping from JSON."""
        try:
            return json.loads(self.COLUMN_NAMES_PATH.read_text(encoding="utf-8"))
        except (IOError, json.JSONDecodeError):
            return self.app.default_column_names

    def create_column_entries(self, window, labels, current_names) -> dict:
        """Create row labels and text entries for column-name mapping."""
        entry_boxes = {}
        for i, label in enumerate(labels):
            tk.Label(window, text=label, font=("Helvetica", 10)).grid(
                row=i, column=0, padx=10, pady=5
            )
            entry_box = tk.Entry(window)
            entry_box.insert(0, current_names[label])
            entry_box.grid(row=i, column=1, padx=10, pady=5)
            entry_boxes[label] = entry_box
        return entry_boxes

    def create_time_unit_dropdown(self, window, row, current_names) -> None:
        """Create time-unit dropdown and bind it to app state."""
        tk.Label(window, text="Time Unit", font=("Helvetica", 10)).grid(
            row=row, column=0, padx=10, pady=5
        )
        time_unit_options = ["seconds", "minutes"]
        self.app.time_input_unit_var = tk.StringVar(window)
        self.app.time_input_unit_var.set(current_names.get("Time Unit", "seconds"))
        time_unit_dropdown = ttk.Combobox(
            window,
            state="readonly",
            values=time_unit_options,
            width=15,
            textvariable=self.app.time_input_unit_var,
        )
        time_unit_dropdown.grid(row=row, column=1, padx=10, pady=5)

    def save_column_names(self, settings_window, entry_boxes) -> None:
        """Persist mapping and close the settings dialog."""
        column_names = {}
        for label, entry_box in entry_boxes.items():
            column_names[label] = entry_box.get().strip()

        column_names["Time Unit"] = self.app.time_input_unit_var.get()
        self.app.column_names = column_names
        self.COLUMN_NAMES_PATH.write_text(
            json.dumps(column_names), encoding="utf-8"
        )
        settings_window.destroy()

    def prompt_column_names(self) -> dict:
        """Return a normalized lowercase column mapping for parsing."""
        try:
            column_names = json.loads(self.COLUMN_NAMES_PATH.read_text(encoding="utf-8"))
        except (IOError, json.JSONDecodeError):
            column_names = self.app.default_column_names

        column_names = {key: value.lower() for key, value in column_names.items()}
        self.app.time_input_unit_var.set(
            column_names.get("Time Unit", "seconds").lower()
        )
        return column_names
