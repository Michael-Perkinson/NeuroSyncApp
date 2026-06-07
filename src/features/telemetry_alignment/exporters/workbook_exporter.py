"""Facade for telemetry workbook export orchestration."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.features.telemetry_alignment.exporters.cluster_sheet_exporter import (
    populate_cluster_sheet as export_cluster_sheet,
    write_cluster_data_in_columns as export_write_cluster_data_in_columns,
    write_cluster_data_to_worksheet as export_write_cluster_data_to_worksheet,
    write_cluster_details as export_write_cluster_details,
    write_cluster_static_inputs as export_write_cluster_static_inputs,
    write_headings as export_write_headings,
    write_peak_data_in_columns as export_write_peak_data_in_columns,
    write_vertical_headings as export_write_vertical_headings,
)
from src.features.telemetry_alignment.exporters.raw_sheet_exporter import (
    add_home_hyperlink as export_add_home_hyperlink,
    add_navigation_hyperlink as export_add_navigation_hyperlink,
    populate_raw_data_sheet as export_raw_data_sheet,
    write_raw_data_to_sheet as export_write_raw_data_to_sheet,
)
from src.features.telemetry_alignment.exporters.signal_sheet_exporter import (
    populate_intercluster_intervals_sheet as export_intercluster_intervals_sheet,
    populate_native_signal_sheet as export_native_signal_sheet,
)
from src.features.telemetry_alignment.exporters.summary_sheet_exporter import (
    populate_summary_sheet as export_summary_sheet,
)


class TelemetryWorkbookExporter:
    """Owns workbook-level orchestration while delegating sheet jobs to helpers."""

    def __init__(self, app):
        self.app = app

    def create_sheets_for_clusters(self, writer):
        unique_cluster_numbers = self.app.mean_cluster_data.keys()
        sorted_cluster_numbers = sorted(unique_cluster_numbers)

        self.populate_summary_sheet(writer, sorted_cluster_numbers)

        for cluster_number in sorted_cluster_numbers:
            if cluster_number == 1:
                sheet_name = "Clusters with 1 Peak"
            else:
                sheet_name = f"Clusters with {cluster_number} peaks"
            self.populate_cluster_sheet(writer, sheet_name, cluster_number)
            self.app.set_variable_column_widths(writer.sheets[sheet_name])

        for cluster_number in sorted_cluster_numbers:
            if cluster_number == 1:
                sheet_name = "Raw, Clusters with 1 Peak"
            else:
                sheet_name = f"Raw, Clusters with {cluster_number} Peaks"
            self.populate_raw_data_sheet(writer, sheet_name, cluster_number)

        self.populate_intercluster_intervals_sheet(writer, "Intercluster Intervals")
        self.populate_native_signal_sheet(
            writer, "Raw Temp Native FullCluster", "temp", "full_cluster"
        )
        self.populate_native_signal_sheet(
            writer, "Raw Act Native FullCluster", "act", "full_cluster"
        )
        self.populate_native_signal_sheet(
            writer, "Raw Temp Native FixedWindow", "temp", "fixed_window"
        )
        self.populate_native_signal_sheet(
            writer, "Raw Act Native FixedWindow", "act", "fixed_window"
        )

    def populate_summary_sheet(self, writer, sorted_cluster_numbers):
        export_summary_sheet(self, writer, sorted_cluster_numbers)

    def populate_intercluster_intervals_sheet(self, writer, sheet_name):
        export_intercluster_intervals_sheet(self, writer, sheet_name)

    def populate_native_signal_sheet(self, writer, sheet_name, signal_type, window_mode):
        export_native_signal_sheet(self, writer, sheet_name, signal_type, window_mode)

    def populate_raw_data_sheet(self, writer, sheet_name, cluster_number):
        export_raw_data_sheet(self, writer, sheet_name, cluster_number)

    def add_home_hyperlink(self, worksheet, writer, col_idx, row_idx):
        export_add_home_hyperlink(worksheet, writer, col_idx, row_idx)

    def write_raw_data_to_sheet(self, worksheet, writer, row_idx, col_idx, period, data_type, data):
        return export_write_raw_data_to_sheet(
            self, worksheet, writer, row_idx, col_idx, period, data_type, data
        )

    def add_navigation_hyperlink(self, worksheet, writer, period, row_idx, col_idx):
        export_add_navigation_hyperlink(worksheet, writer, period, row_idx, col_idx)

    def populate_cluster_sheet(self, writer, sheet_name, cluster_number):
        export_cluster_sheet(self, writer, sheet_name, cluster_number)

    def write_cluster_details(self, worksheet, cluster_number, file_data, cluster_dict):
        export_write_cluster_details(self, worksheet, cluster_number, file_data, cluster_dict)

    def write_cluster_data_to_worksheet(
        self,
        worksheet,
        clusters,
        row_idx_for_basic_data,
        col_idx,
        rows_to_skip,
        initial_row_idx_for_peak_data,
        cluster_number,
    ):
        return export_write_cluster_data_to_worksheet(
            self,
            worksheet,
            clusters,
            row_idx_for_basic_data,
            col_idx,
            rows_to_skip,
            initial_row_idx_for_peak_data,
            cluster_number,
        )

    def write_vertical_headings(self, worksheet, row_idx, headings):
        return export_write_vertical_headings(self, worksheet, row_idx, headings)

    def write_headings(self, worksheet, row_idx, cluster_headings, headings, rows_to_skip):
        return export_write_headings(
            self, worksheet, row_idx, cluster_headings, headings, rows_to_skip
        )

    def write_cluster_data_in_columns(self, worksheet, row_idx, col_idx, data_list):
        return export_write_cluster_data_in_columns(worksheet, row_idx, col_idx, data_list)

    def write_peak_data_in_columns(
        self,
        worksheet,
        row_idx,
        col_idx,
        data_list,
        row_idx_for_basic_data,
        rows_to_skip,
    ):
        return export_write_peak_data_in_columns(
            worksheet,
            row_idx,
            col_idx,
            data_list,
            row_idx_for_basic_data,
            rows_to_skip,
        )

    def write_cluster_static_inputs(self, worksheet, row_idx, col_idx, cluster_number, file_data):
        return export_write_cluster_static_inputs(
            self, worksheet, row_idx, col_idx, cluster_number, file_data
        )

    @staticmethod
    def _format_summary_value(value):
        if value in (None, ""):
            return ""
        if isinstance(value, bool):
            return "Yes" if value else "No"
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return str(value)
        if numeric_value.is_integer():
            return int(numeric_value)
        return round(numeric_value, 3)

    def _get_active_file_data(self):
        file_path = Path(self.app._get_current_file_path()).name
        return self.app.data_dict[file_path]

    def _get_photometry_export_interval_seconds(self) -> float:
        telemetry_intervals = []
        for attribute_name in ("temp_sample_rate", "act_sample_rate"):
            raw_value = getattr(self.app, attribute_name, None)
            try:
                interval_seconds = float(raw_value)
            except (TypeError, ValueError):
                continue
            if interval_seconds > 0:
                telemetry_intervals.append(interval_seconds)
        return max(telemetry_intervals) if telemetry_intervals else 1.0

    def _prepare_photometry_export_frame(self, data: pd.DataFrame | None):
        preview_label = "Photometry Preview"
        if not isinstance(data, pd.DataFrame) or data.empty:
            return data, preview_label

        interval_seconds = self._get_photometry_export_interval_seconds()
        interval_minutes = interval_seconds / 60.0
        time_column = data.columns[0]

        working = data.copy()
        working[time_column] = pd.to_numeric(working[time_column], errors="coerce")
        working = working.dropna(subset=[time_column]).sort_values(time_column).reset_index(
            drop=True
        )
        if working.empty or interval_minutes <= 0:
            return working, preview_label

        for column in working.columns[1:]:
            working[column] = pd.to_numeric(working[column], errors="coerce")

        start_time = float(working[time_column].iloc[0])
        working["_export_bin"] = (
            ((working[time_column] - start_time) / interval_minutes) // 1
        ).astype(int)
        downsampled = (
            working.groupby("_export_bin", sort=True, as_index=False)[list(data.columns)]
            .mean(numeric_only=True)
            .reset_index(drop=True)
        )
        downsampled = downsampled.drop(columns=["_export_bin"], errors="ignore")
        return downsampled, f"{preview_label} (~{interval_seconds:g}s bins)"
