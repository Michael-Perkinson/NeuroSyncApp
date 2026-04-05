"""Controller for app-level data preparation and z-score state management."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from src.processing.behavior_metrics import compute_z_score
from src.processing.behaviour_parser import build_params_from_df


class BehaviourDataController:
    """Owns parameter validation and cached z-score computation."""

    def __init__(self, app):
        self.app = app

    def calculate_z_score(self):
        selected_column = self.app.selected_column_var.get()
        if self.app.figure_display_dropdown.get() != "Z-scored data":
            self.app.figure_display_dropdown.set("Z-scored data")

        raw_start = self.app.data_selection_frame.baseline_start_entry.get().strip()
        raw_end = self.app.data_selection_frame.baseline_end_entry.get().strip()
        if not raw_start or not raw_end:
            QMessageBox.warning(
                self.app,
                "Baseline Incomplete",
                "Please enter both a start and end time for the baseline before applying z-score.",
            )
            return
        current_baseline_start = float(raw_start) / 60
        current_baseline_end = float(raw_end) / 60

        if (
            self.app.z_score_computed
            and self.app.previous_baseline_start == current_baseline_start
            and self.app.previous_baseline_end == current_baseline_end
        ):
            return (
                self.app.dataframe["baselined_z_score"],
                self.app.dataframe["z_scored_time"],
            )

        z_scored_data, z_scored_time, baseline_mean, baseline_std = compute_z_score(
            self.app.dataframe,
            selected_column,
            current_baseline_start,
            current_baseline_end,
        )

        self.app.baseline_data_mean = baseline_mean
        self.app.baseline_data_std = baseline_std
        self.app.dataframe["baselined_z_score"] = z_scored_data
        self.app.dataframe["z_scored_time"] = z_scored_time
        self.app.z_score_computed = True
        self.app.previous_baseline_start = current_baseline_start
        self.app.previous_baseline_end = current_baseline_end
        return z_scored_data, z_scored_time

    def check_and_prepare_parameters(self, table_key):
        if table_key not in self.app.tables:
            return None

        display_status = {
            name: (variable.get() if variable else 0)
            for name, variable in self.app.behaviour_display_status.items()
        }

        params, _, missing_pre, missing_post, not_divisible = build_params_from_df(
            self.app.tables[table_key], display_status
        )

        if missing_pre:
            QMessageBox.warning(
                self.app,
                "Pre-behaviour Time Missing",
                f"Pre-behaviour time is missing for: {', '.join(missing_pre)}",
            )
            return None

        if missing_post:
            QMessageBox.warning(
                self.app,
                "Post-behaviour Time Missing",
                f"Post-behaviour time is missing for: {', '.join(missing_post)}",
            )
            return None

        if not_divisible:
            QMessageBox.warning(
                self.app,
                "Total Time Not Divisible",
                f"Total time not divisible by bin size for: {', '.join(not_divisible)}",
            )
            return None

        if self.app.checkbox_state:
            baseline_start_time_min = (
                float(self.app.data_selection_frame.baseline_start_entry.get()) / 60
            )
            self.app.z_scored_data, self.app.z_scored_time = self.calculate_z_score()
            params["baseline_start_time_min"] = baseline_start_time_min

        return params
