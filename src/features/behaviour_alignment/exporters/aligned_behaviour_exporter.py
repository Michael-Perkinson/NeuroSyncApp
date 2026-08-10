"""Export orchestration for the photometry-behaviour app."""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd
from PySide6.QtWidgets import QMessageBox

from src.excel_ops.behaviour_exporter import (
    build_output_file_name,
    create_df_for_behaviours,
    export_combined_excel,
    generate_summary_data,
)
from src.gui.framework.messages_and_errors import show_action_error
from src.processing.behaviour_metrics import (
    calculate_auc,
    calculate_max_amp,
    calculate_mean_dff,
    compute_full_trace_zscore,
    zscore_column_key,
)
from src.processing.behaviour_parser import (
    create_extraction_folder,
    extract_behaviour_results,
    truncate_sheet_title,
)

logger = logging.getLogger(__name__)

_INVALID_SHEET_CHARS = re.compile(r'[\\/*?:"<>|]')


def _unique_sheet_name(name: str, used_names: set[str], suffix: str = "") -> str:
    """Build a <=31-char Excel sheet name unique within *used_names*.

    Truncates *name* to leave room for *suffix* (e.g. "_dFoF_465") so two
    differently-named behaviours can't collapse to the same truncated
    prefix. If a collision still occurs — two behaviours can be identical
    up to the truncation point — disambiguates with a numeric tag rather
    than silently overwriting one sheet's data with another's.
    """
    max_base_length = max(31 - len(suffix), 1)
    candidate = _INVALID_SHEET_CHARS.sub(
        "_", truncate_sheet_title(name, max_base_length) + suffix
    )[:31]
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    for tag_index in range(2, 1000):
        tag = f"~{tag_index}"
        max_base_length = max(31 - len(suffix) - len(tag), 1)
        candidate = _INVALID_SHEET_CHARS.sub(
            "_", truncate_sheet_title(name, max_base_length) + tag + suffix
        )[:31]
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
    raise RuntimeError(f"Could not generate a unique sheet name for {name!r}")


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

    def _handle_zscore_checkbox_export(
        self, duration_df: pd.DataFrame, columns: list[str]
    ) -> pd.DataFrame:
        """Append baseline mean/std for every baselined column to the duration sheet.

        ``app.baseline_data_mean``/``baseline_data_std`` are dicts keyed by
        column name (one entry per selected column, all computed from the
        same baseline window — see ``BehaviourDataService.calculate_z_score``).
        """
        duration_df = duration_df.copy()
        duration_df[""] = [np.nan] * len(duration_df)
        baseline_means = self.app.baseline_data_mean or {}
        baseline_stds = self.app.baseline_data_std or {}
        multi_column = len(columns) > 1
        for column in columns:
            mean_label = "Mean df/f for baseline" + (
                f" ({column})" if multi_column else ""
            )
            std_label = "STD for baseline" + (f" ({column})" if multi_column else "")
            padding = [np.nan] * (len(duration_df) - 1)
            duration_df[mean_label] = [baseline_means.get(column)] + padding
            duration_df[std_label] = [baseline_stds.get(column)] + padding
        return duration_df

    def _handle_full_trace_zscore_export(
        self, duration_df: pd.DataFrame, columns: list[str]
    ) -> pd.DataFrame:
        """Append the whole-trace mean/SD used by DFer's Z-score calculation."""
        duration_df = duration_df.copy()
        multi_column = len(columns) > 1
        for column in columns:
            _, trace_mean, trace_std = compute_full_trace_zscore(
                self.app.dataframe[column]
            )
            suffix = f" ({column})" if multi_column else ""
            mean_label = f"Mean dF/F for whole-trace Z-score{suffix}"
            std_label = f"STD for whole-trace Z-score{suffix}"
            duration_df[mean_label] = np.nan
            duration_df[std_label] = np.nan
            if not duration_df.empty:
                first_index = duration_df.index[0]
                duration_df.loc[first_index, mean_label] = trace_mean
                duration_df.loc[first_index, std_label] = trace_std
        return duration_df

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
        signal_results: list[tuple[str, dict, dict]],
        params: dict,
        file_path: str,
        folder_path: str,
        detail_df_list: list[tuple[pd.DataFrame, str]],
        duration_df: pd.DataFrame,
    ) -> None:
        summary_parts: list[pd.DataFrame] = []
        multi_column = len(signal_results) > 1
        formatting_behaviours: dict = {}
        for column, behaviours_results, time_ranges in signal_results:
            formatting_behaviours.update(behaviours_results)
            signal_summary = generate_summary_data(
                sorted(behaviours_results.keys()),
                behaviours_results,
                params,
                self._get_metric_functions(),
                time_ranges,
            )
            if multi_column:
                signal_label = pd.DataFrame(
                    [[f"Signal: {column}"] + [np.nan] * (signal_summary.shape[1] - 1)]
                )
                summary_parts.extend([signal_label, signal_summary])
            else:
                summary_parts.append(signal_summary)

        max_columns = max((part.shape[1] for part in summary_parts), default=0)
        df_summary = pd.concat(
            [part.reindex(columns=range(max_columns)) for part in summary_parts],
            ignore_index=True,
        )
        # Keep one headline summary sheet, with a labelled section per signal.
        df_list = [(duration_df, "Event Duration")]
        df_list.extend(detail_df_list)

        output_file_name = self._get_output_file_name(file_path, folder_path)
        export_combined_excel(
            df_summary, df_list, output_file_name, formatting_behaviours
        )

    def extract_data_from_photometry(self, file_path: str, params: dict) -> None:
        """Extract and export photometry-aligned behaviour data."""
        folder_path = create_extraction_folder(file_path)
        behaviours_to_export = params.get("behaviours_to_export", [])

        selected_columns = self.app.selected_columns_var.get() or [
            self.app.selected_column_var.get()
        ]
        multi_column = len(selected_columns) > 1

        duration_df = self._extract_duration_data()
        duration_df = self._handle_full_trace_zscore_export(
            duration_df, selected_columns
        )
        if self.app.checkbox_state:
            duration_df = self._handle_zscore_checkbox_export(
                duration_df, selected_columns
            )

        detail_df_list: list[tuple[pd.DataFrame, str]] = []
        signal_results: list[tuple[str, dict, dict]] = []
        used_sheet_names: set[str] = {"Event Duration", "Summary Results"}

        for column in selected_columns:
            use_zscore = self.app.checkbox_state
            column_z_data = (
                self.app.dataframe[zscore_column_key(column)] if use_zscore else None
            )
            suffix = f"_{column}" if multi_column else ""

            behaviours_results, time_ranges = extract_behaviour_results(
                behaviours_to_export,
                params,
                self.app.dataframe,
                use_zscore,
                column,
                column_z_data,
            )
            sorted_behaviours = sorted(behaviours_results.keys())

            signal_results.append((column, behaviours_results, time_ranges))

            df_list = create_df_for_behaviours(
                behaviours_results,
                sorted_behaviours,
                time_ranges,
                True,
                column,
                use_zscore,
                folder_path,
            )
            df_list = [
                (df, _unique_sheet_name(behaviour_name, used_sheet_names, suffix))
                for (df, _sheet), behaviour_name in zip(df_list, sorted_behaviours)
            ]
            detail_df_list.extend(df_list)

        self._export_binned_data(
            signal_results,
            params,
            file_path,
            folder_path,
            detail_df_list,
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
            try:
                self.extract_data_from_photometry(file_path, params)
            except Exception as exc:
                show_action_error(
                    "Behaviour export failed",
                    "NeuroSyncApp could not export the aligned behaviour data",
                    exc,
                    self.app,
                    "Close any existing output workbook, check the selected data, and try again.",
                )
                return
            logger.info("Behaviour data extraction completed.")
        else:
            logger.info("Behaviour data extraction cancelled by user.")

        self.app.settings_manager.save_variables()
