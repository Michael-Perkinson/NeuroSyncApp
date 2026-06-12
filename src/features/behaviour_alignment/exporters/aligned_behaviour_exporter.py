"""Export orchestration for the photometry-behaviour app."""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QMessageBox

from src.processing.behavior_metrics import calculate_auc, calculate_max_amp, calculate_mean_dff
from src.processing.behaviour_parser import create_extraction_folder, extract_behaviour_results
from src.excel_ops.behaviour_exporter import (
    build_output_file_name,
    create_df_for_behaviours,
    export_combined_csv,
    generate_summary_data,
)

logger = logging.getLogger(__name__)


class AlignedBehaviourExporter:
    """Export flow for the photometry-behaviour feature."""

    def __init__(self, app):
        self.app = app

    def _extract_duration_data(self) -> pd.DataFrame:
        duration_data = []
        for key, value in self.app.duration_data_cache.items():
            duration_data.append(
                [
                    key,
                    value["mean_duration"] * 60,
                    value["sem_duration"] * 60,
                    value["number_of_instances"],
                ]
            )
        return pd.DataFrame(
            duration_data,
            columns=["Behavior", "Mean Duration (s)", "SEM (s)", "Number of Instances"],
        ).sort_values(by="Behavior")

    def _handle_zscore_checkbox_export(self, duration_df: pd.DataFrame):
        z_scored_data = self.app.dataframe["baselined_z_score"]
        z_scored_time = self.app.dataframe["z_scored_time"]
        duration_df[""] = [np.nan] * len(duration_df)
        duration_df["Mean df/f for baseline"] = [self.app.baseline_data_mean] + [
            np.nan
        ] * (len(duration_df) - 1)
        duration_df["STD for baseline"] = [self.app.baseline_data_std] + [np.nan] * (
            len(duration_df) - 1
        )
        return z_scored_data, z_scored_time, duration_df

    def _get_metric_functions(self) -> dict:
        return {
            "auc": calculate_auc,
            "max_amp": calculate_max_amp,
            "mean_dff": calculate_mean_dff,
        }

    def _get_output_file_name(self, file_path: str, folder_path: str) -> str:
        baseline_start = (
            self.app.data_selection_frame.baseline_start_entry.get()
            if self.app.checkbox_state
            else ""
        )
        return build_output_file_name(
            file_path,
            folder_path,
            self.app.selected_column_var.get(),
            self.app.checkbox_state,
            baseline_start,
        )

    def _export_binned_data(
        self,
        sorted_behaviours: list[str],
        behaviours_results: dict,
        time_ranges: dict,
        params: dict,
        file_path: str,
        folder_path: str,
        df_list: list[tuple[pd.DataFrame, str]],
        duration_df: pd.DataFrame,
    ) -> None:
        df_summary = generate_summary_data(
            sorted_behaviours,
            behaviours_results,
            params,
            self._get_metric_functions(),
            time_ranges,
        )
        df_list.insert(0, (duration_df, "Event Duration"))

        output_file_name = self._get_output_file_name(file_path, folder_path)
        export_combined_csv(df_summary, df_list, output_file_name, behaviours_results)

    def extract_data_from_photometry(self, file_path: str, params: dict) -> None:
        """Extract and export photometry-aligned behaviour data."""
        folder_path = create_extraction_folder(file_path)
        behaviours_to_export = params.get("behaviours_to_export", [])

        duration_df = self._extract_duration_data()
        z_scored_data = None
        if self.app.checkbox_state:
            z_scored_data, _, duration_df = self._handle_zscore_checkbox_export(duration_df)

        behaviours_results, time_ranges = extract_behaviour_results(
            behaviours_to_export,
            params,
            self.app.dataframe,
            self.app.checkbox_state,
            self.app.selected_column_var.get(),
            z_scored_data,
        )
        sorted_behaviours = sorted(behaviours_results.keys())

        df_list = create_df_for_behaviours(
            behaviours_results,
            sorted_behaviours,
            time_ranges,
            True,
            self.app.selected_column_var.get(),
            self.app.checkbox_state,
            folder_path,
        )

        self._export_binned_data(
            sorted_behaviours,
            behaviours_results,
            time_ranges,
            params,
            file_path,
            folder_path,
            df_list,
            duration_df,
        )

    def extract_button_click_handler(self) -> None:
        """Handle Extract button click including confirmation prompts."""
        params = self.app.data_service.check_and_prepare_parameters(
            self.app.current_table_key
        )
        if params is None:
            return

        behaviours_to_export = {
            behaviour
            for behaviour in params["behaviours_to_export"]
            if self.app.behaviour_display_status[behaviour].get() == 1
        }

        if behaviours_to_export:
            behaviours_str = ", ".join(behaviours_to_export)
            proceed_message = (
                f"The following behaviours will be exported: {behaviours_str}\n"
                "Do you want to proceed?"
            )
            proceed = (
                QMessageBox.question(
                    self.app,
                    "Behaviours to Export",
                    proceed_message,
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Ok,
                )
                == QMessageBox.StandardButton.Ok
            )
        else:
            proceed_message = (
                "No behaviours have been selected for export.\nDo you want to proceed?"
            )
            proceed = (
                QMessageBox.question(
                    self.app,
                    "No Behaviours Selected",
                    proceed_message,
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Ok,
                )
                == QMessageBox.StandardButton.Ok
            )

        if proceed:
            file_path = self.app.data_selection_frame.file_path_var.get()
            self.extract_data_from_photometry(file_path, params)
            logger.info("Behaviour data extraction completed.")
        else:
            logger.info("Behaviour data extraction cancelled by user.")

        self.app.settings_manager.save_variables()
