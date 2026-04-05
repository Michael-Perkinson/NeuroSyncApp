"""Controller for behaviour CSV column-name settings and persistence."""

from __future__ import annotations

import json
from pathlib import Path

from src.gui.shared.qt_bindings import ObservableValue


class BehaviourColumnSettingsController:
    """Owns column-name settings persistence and app-state sync."""

    COLUMN_NAMES_PATH = Path("column_names.json")

    def __init__(self, app):
        self.app = app

    def save_from_frame(self) -> None:
        """Read column name fields from the embedded frame and persist to JSON."""
        frame = self.app.behaviour_event_input_frame
        data = {
            "Behaviours/events": frame.behaviours_col_var.get(),
            "Start Time": frame.start_col_var.get(),
            "End Time": frame.end_col_var.get(),
            "Time Unit": frame.time_unit_var.get(),
        }
        self.app.time_input_unit_var.set(data["Time Unit"])
        self.COLUMN_NAMES_PATH.write_text(json.dumps(data), encoding="utf-8")

    def prompt_column_names(self) -> dict:
        """Return a normalised lowercase column mapping for parsing.

        Reads live values from the embedded frame fields so the user
        does not need to re-open any dialog.
        """
        frame = self.app.behaviour_event_input_frame
        column_names = {
            "Behaviours/events": frame.behaviours_col_var.get(),
            "Start Time": frame.start_col_var.get(),
            "End Time": frame.end_col_var.get(),
            "Time Unit": frame.time_unit_var.get(),
        }
        column_names = {key: value.lower() for key, value in column_names.items()}
        self.app.time_input_unit_var.set(
            column_names.get("Time Unit", "seconds").lower()
        )
        return column_names

    def load_column_names(self) -> dict:
        """Load persisted CSV column-name mapping from JSON."""
        try:
            return json.loads(self.COLUMN_NAMES_PATH.read_text(encoding="utf-8"))
        except (IOError, json.JSONDecodeError):
            return getattr(self.app, "default_column_names", {})
