"""Export orchestration for the photometry-behaviour app."""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from tkinter import messagebox

from src.processing.behavior_metrics import calculate_auc, calculate_max_amp, calculate_mean_dff
from src.processing.behaviour_parser import create_extraction_folder, extract_behaviour_results
from src.excel_ops.behaviour_exporter import (
    build_non_binned_metrics_df,
    build_output_file_name,
    build_separate_summary_file_name,
    create_df_for_behaviours,
    export_combined_csv,
    export_separate_csv,
    format_non_binned_excel,
    generate_summary_data,
    save_to_excel,
)

logger = logging.getLogger(__name__)


class BehaviourExportController:
    """Controller for export flow; callers provide widget-resolved app state."""

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
        metrics = {}
        if self.app.export_options_container.use_auc_var.get():
            metrics["auc"] = calculate_auc
        if self.app.export_options_container.use_max_amp_var.get():
            metrics["max_amp"] = calculate_max_amp
        if self.app.export_options_container.use_mean_dff_var.get():
            metrics["mean_dff"] = calculate_mean_dff
        return metrics

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
        params: dict,
        file_path: str,
        folder_path: str,
        df_list: list[tuple[pd.DataFrame, str]],
        duration_df: pd.DataFrame,
    ) -> None:
        df_summary = generate_summary_data(
            sorted_behaviours, behaviours_results, params, self._get_metric_functions()
        )
        df_list.insert(0, (duration_df, "Event Duration"))

        if self.app.export_options_container.combine_csv_var.get() == 1:
            output_file_name = self._get_output_file_name(file_path, folder_path)
            export_combined_csv(df_summary, df_list, output_file_name, behaviours_results)
        else:
            baseline_start = (
                self.app.data_selection_frame.baseline_start_entry.get()
                if self.app.checkbox_state
                else ""
            )
            output_file_name = build_separate_summary_file_name(
                file_path,
                folder_path,
                self.app.selected_column_var.get(),
                self.app.checkbox_state,
                baseline_start,
                True,
            )
            export_separate_csv(df_summary, output_file_name)

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
            self.app.export_options_container.combine_csv_var.get() == 1,
            self.app.selected_column_var.get(),
            self.app.checkbox_state,
            folder_path,
        )

        if self.app.export_options_container.use_binned_data_var.get() == 1:
            self._export_binned_data(
                sorted_behaviours,
                behaviours_results,
                params,
                file_path,
                folder_path,
                df_list,
                duration_df,
            )
            return

        metric_flags = {
            "use_auc": bool(self.app.export_options_container.use_auc_var.get()),
            "use_max_amp": bool(self.app.export_options_container.use_max_amp_var.get()),
            "use_mean_dff": bool(self.app.export_options_container.use_mean_dff_var.get()),
        }
        baseline_start = (
            float(self.app.data_selection_frame.baseline_start_entry.get())
            if self.app.checkbox_state
            else 0.0
        )
        baseline_end = (
            float(self.app.data_selection_frame.baseline_end_entry.get())
            if self.app.checkbox_state
            else 0.0
        )
        df_results = build_non_binned_metrics_df(
            behaviours_results,
            params,
            metric_flags,
            self._get_metric_functions(),
            self.app.checkbox_state,
            baseline_start,
            baseline_end,
        )
        df_list.insert(0, (df_results, "Summary Results"))

        if self.app.export_options_container.combine_csv_var.get() == 1:
            output_file_name = self._get_output_file_name(file_path, folder_path)
            save_to_excel(df_list, output_file_name)
            format_non_binned_excel(output_file_name)
            return

        baseline_start_str = (
            self.app.data_selection_frame.baseline_start_entry.get()
            if self.app.checkbox_state
            else ""
        )
        output_file_name = build_separate_summary_file_name(
            file_path,
            folder_path,
            self.app.selected_column_var.get(),
            self.app.checkbox_state,
            baseline_start_str,
        )
        df_results.to_csv(output_file_name, index=False)

    def extract_button_click_handler(self) -> None:
        """Handle Extract button click including confirmation prompts."""
        params = self.app.behaviour_data_controller.check_and_prepare_parameters(
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
            proceed = messagebox.askokcancel("Behaviours to Export", proceed_message)
        else:
            proceed_message = (
                "No behaviours have been selected for export.\nDo you want to proceed?"
            )
            proceed = messagebox.askokcancel("No Behaviours Selected", proceed_message)

        if proceed:
            file_path = self.app.data_selection_frame.file_path_var.get()
            self.extract_data_from_photometry(file_path, params)
            logger.info("Behaviour data extraction completed.")
        else:
            logger.info("Behaviour data extraction cancelled by user.")

        self.app.settings_manager.save_variables()
