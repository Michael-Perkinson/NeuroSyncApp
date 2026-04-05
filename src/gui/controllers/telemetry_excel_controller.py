"""Controller for telemetry Excel sheet orchestration."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from src.excel_ops.telemetry_exporter import (
    build_intercluster_interval_frame,
    build_native_signal_frame,
    get_standardized_native_window_bounds,
)


class TelemetryExcelController:
    """Owns high-level cluster sheet creation and raw-sheet composition."""

    def __init__(self, app):
        self.app = app

    def create_sheets_for_clusters(self, writer):
        unique_cluster_numbers = self.app.mean_cluster_data.keys()
        sorted_cluster_numbers = sorted(unique_cluster_numbers)

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

    def calculate_column_widths(self, headers):
        return [max(len(str(header)), 10) for header in headers]

    def _get_active_file_data(self):
        file_path = Path(self.app._get_current_file_path()).name
        return self.app.data_dict[file_path]

    def _write_titled_dataframe_sheet(self, writer, sheet_name, title, dataframe):
        worksheet = writer.book.add_worksheet(sheet_name)
        writer.sheets[sheet_name] = worksheet

        title_format = writer.book.add_format({"bold": True, "font_size": 12})
        header_format = writer.book.add_format(
            {"bold": True, "bg_color": "#e0eadf", "border": 1}
        )

        worksheet.write(0, 0, title, title_format)

        if dataframe.empty:
            worksheet.write(2, 0, "No data available for export.")
            worksheet.set_column(0, 0, 28)
            return

        dataframe.to_excel(writer, sheet_name=sheet_name, startrow=1, index=False)

        for col_num, column in enumerate(dataframe.columns):
            worksheet.write(1, col_num, column, header_format)
            series = dataframe[column].astype(str).replace("nan", "")
            max_value_width = series.map(len).max() if not series.empty else 0
            width = min(max(len(str(column)), max_value_width) + 2, 28)
            worksheet.set_column(col_num, col_num, max(width, 12))

        worksheet.freeze_panes(2, 0)
        worksheet.autofilter(1, 0, len(dataframe) + 1, max(len(dataframe.columns) - 1, 0))

    def populate_intercluster_intervals_sheet(self, writer, sheet_name):
        interval_frame = build_intercluster_interval_frame(
            cluster_dict=self.app.cluster_dict,
            file_data=self._get_active_file_data(),
            data_type=self.app.data_type,
        )
        self._write_titled_dataframe_sheet(
            writer,
            sheet_name,
            "Intercluster intervals in chronological cluster order",
            interval_frame,
        )

    def populate_native_signal_sheet(self, writer, sheet_name, signal_type, window_mode):
        signal_label = "temperature" if signal_type == "temp" else "activity"
        if window_mode == "full_cluster":
            window_label = "full cluster context"
        else:
            window_start, window_end = get_standardized_native_window_bounds(
                cluster_dict=self.app.cluster_dict,
                file_data=self._get_active_file_data(),
                data_type=self.app.data_type,
                window_mode=window_mode,
            )
            window_label = (
                f"fixed first-peak window {window_start:.3f} to {window_end:.3f} min"
            )
        native_frame = build_native_signal_frame(
            mean_cluster_data=self.app.mean_cluster_data,
            cluster_dict=self.app.cluster_dict,
            file_data=self._get_active_file_data(),
            data_type=self.app.data_type,
            signal_type=signal_type,
            window_mode=window_mode,
        )
        self._write_titled_dataframe_sheet(
            writer,
            sheet_name,
            f"Native-rate {signal_label} samples aligned by cluster ({window_label})",
            native_frame,
        )

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
        working["_export_bin"] = (((working[time_column] - start_time) / interval_minutes) // 1).astype(
            int
        )
        downsampled = (
            working.groupby("_export_bin", sort=True, as_index=False)[list(data.columns)]
            .mean(numeric_only=True)
            .reset_index(drop=True)
        )
        downsampled = downsampled.drop(columns=["_export_bin"], errors="ignore")
        return downsampled, f"{preview_label} (~{interval_seconds:g}s bins)"

    def populate_raw_data_sheet(self, writer, sheet_name, cluster_number):
        cluster_data = self.app.mean_cluster_data.get(cluster_number)
        worksheet = writer.book.add_worksheet(sheet_name)

        self.app.bold = writer.book.add_format({"bold": True})
        self.app.all_cell_format = writer.book.add_format(
            {"bold": True, "bg_color": "#e0eadf"}
        )
        self.app.day_cell_format = writer.book.add_format(
            {"bold": True, "bg_color": "yellow"}
        )
        self.app.night_cell_format = writer.book.add_format(
            {"bold": True, "bg_color": "#8f9ed9"}
        )

        full_temp_data = cluster_data["full"]["raw_temp_data"]
        full_act_data = cluster_data["full"]["raw_act_data"]
        if self.app.data_type == "photometry":
            full_photometry_data, photometry_export_label = self._prepare_photometry_export_frame(
                cluster_data["full"]["photometry_cluster_data"]
            )

        row_idx, col_idx = 0, 0
        next_col_idx, full_row_idx_after_temp = self.write_raw_data_to_sheet(
            worksheet, writer, row_idx, col_idx, "Full", "Temp", full_temp_data
        )
        next_col_idx, full_row_idx_after_act = self.write_raw_data_to_sheet(
            worksheet, writer, row_idx, next_col_idx, "Full", "Act", full_act_data
        )
        full_section_end_rows = [full_row_idx_after_temp, full_row_idx_after_act]
        if self.app.data_type == "photometry":
            next_col_idx, full_row_idx_after_photometry = self.write_raw_data_to_sheet(
                worksheet,
                writer,
                row_idx,
                next_col_idx,
                "Full",
                photometry_export_label,
                full_photometry_data,
            )
            full_section_end_rows.append(full_row_idx_after_photometry)

        col_idx = 0
        row_idx = max(full_section_end_rows)
        day_start_row = None
        night_start_row = None

        if cluster_data["day"].get("mean_temp_data") is not None:
            day_start_row = row_idx
            day_temp_data = cluster_data["day"]["raw_temp_data"]
            day_act_data = cluster_data["day"]["raw_act_data"]
            if self.app.data_type == "photometry":
                day_photometry_data, photometry_export_label = self._prepare_photometry_export_frame(
                    cluster_data["day"]["photometry_cluster_data"]
                )

            next_col_idx, day_row_idx_after_temp = self.write_raw_data_to_sheet(
                worksheet, writer, row_idx, col_idx, "Day", "Temp", day_temp_data
            )
            next_col_idx, day_row_idx_after_act = self.write_raw_data_to_sheet(
                worksheet, writer, row_idx, next_col_idx, "Day", "Act", day_act_data
            )
            day_section_end_rows = [day_row_idx_after_temp, day_row_idx_after_act]
            if self.app.data_type == "photometry":
                next_col_idx, day_row_idx_after_photometry = self.write_raw_data_to_sheet(
                    worksheet,
                    writer,
                    row_idx,
                    next_col_idx,
                    "Day",
                    photometry_export_label,
                    day_photometry_data,
                )
                day_section_end_rows.append(day_row_idx_after_photometry)

            row_idx = max(day_section_end_rows)
            col_idx = 0

        if cluster_data["night"].get("mean_temp_data") is not None:
            night_start_row = row_idx
            night_temp_data = cluster_data["night"]["raw_temp_data"]
            night_act_data = cluster_data["night"]["raw_act_data"]
            if self.app.data_type == "photometry":
                night_photometry_data, photometry_export_label = self._prepare_photometry_export_frame(
                    cluster_data["night"]["photometry_cluster_data"]
                )

            next_col_idx, night_row_idx_after_temp = self.write_raw_data_to_sheet(
                worksheet, writer, row_idx, col_idx, "Night", "Temp", night_temp_data
            )
            next_col_idx, night_row_idx_after_act = self.write_raw_data_to_sheet(
                worksheet, writer, row_idx, next_col_idx, "Night", "Act", night_act_data
            )
            night_section_end_rows = [night_row_idx_after_temp, night_row_idx_after_act]
            if self.app.data_type == "photometry":
                next_col_idx, night_row_idx_after_photometry = self.write_raw_data_to_sheet(
                    worksheet,
                    writer,
                    row_idx,
                    next_col_idx,
                    "Night",
                    photometry_export_label,
                    night_photometry_data,
                )
                night_section_end_rows.append(night_row_idx_after_photometry)

            row_idx = max(night_section_end_rows)
            col_idx = 1

        if day_start_row is not None:
            self.add_navigation_hyperlink(
                worksheet, writer, "Day", day_start_row + 1, 1
            )

        if night_start_row is not None:
            night_col_idx = 2 if day_start_row is not None else 1
            self.add_navigation_hyperlink(
                worksheet, writer, "Night", night_start_row + 1, night_col_idx
            )

        worksheet.set_column(0, 30, 20.5)

    def add_home_hyperlink(self, worksheet, writer, col_idx, row_idx):
        hyperlink_format = writer.book.add_format(
            {
                "align": "center",
                "valign": "vcenter",
                "underline": True,
                "font_color": "blue",
            }
        )

        worksheet.write_url(
            row_idx,
            col_idx,
            f"internal:'{worksheet.name}'!A1",
            string="Go to Full Data",
            cell_format=hyperlink_format,
        )

    def write_raw_data_to_sheet(
        self, worksheet, writer, row_idx, col_idx, period, data_type, data
    ):
        worksheet.write(row_idx, col_idx, f"Raw data: {period} - {data_type}", self.app.bold)

        if (period == "Day" or period == "Night") and data_type == "Temp":
            self.add_home_hyperlink(worksheet, writer, col_idx + 1, row_idx)

        row_idx += 1
        next_col_idx = col_idx

        if isinstance(data, pd.DataFrame):
            if not data.empty:
                for col_num, header in enumerate(data.columns):
                    worksheet.write(row_idx, col_idx + col_num, header, self.app.bold)
                for row_num, row_data in enumerate(data.itertuples(index=False, name=None)):
                    for col_num, value in enumerate(row_data):
                        try:
                            worksheet.write(row_idx + row_num + 1, col_idx + col_num, value)
                        except Exception:
                            pass
                next_col_idx += len(data.columns)
                next_row_idx = row_idx + len(data) + 1
            else:
                next_row_idx = row_idx
        elif isinstance(data, list):
            for row_num, row_data in enumerate(data):
                for col_num, value in enumerate(row_data):
                    worksheet.write(row_idx + row_num, col_idx + col_num, value)
            next_col_idx += len(data[0]) if data else 1
            next_row_idx = row_idx + len(data) + 1 if data else row_idx
        else:
            next_row_idx = row_idx

        next_row_idx += 1
        next_col_idx += 1
        return next_col_idx, next_row_idx

    def add_navigation_hyperlink(self, worksheet, writer, period, row_idx, col_idx):
        hyperlink_format = writer.book.add_format(
            {
                "align": "center",
                "valign": "vcenter",
                "underline": True,
                "font_color": "blue",
            }
        )

        target_cell = f"A{row_idx + 1}"
        worksheet.write_url(
            0,
            col_idx,
            f"internal:'{worksheet.name}'!{target_cell}",
            string=f"Go to {period} Data",
            cell_format=hyperlink_format,
        )

    def populate_cluster_sheet(self, writer, sheet_name, cluster_number):
        worksheet = writer.book.add_worksheet(sheet_name)

        self.app.bold = writer.book.add_format({"bold": True})
        self.app.all_cell_format = writer.book.add_format(
            {"bold": True, "bg_color": "#e0eadf"}
        )
        self.app.day_cell_format = writer.book.add_format(
            {"bold": True, "bg_color": "yellow"}
        )
        self.app.night_cell_format = writer.book.add_format(
            {"bold": True, "bg_color": "#8f9ed9"}
        )

        temp_act_headers = ["Time (s)", "Mean Temp", "SEM Temp", "Mean Act", "SEM Act"]
        row_idx = 0

        if self.app.data_type == "photometry":
            day_clusters = sum(
                1
                for key, info in self.app.cluster_dict.items()
                if info["time_period"] == "Day" and key[2] == cluster_number
            )
            night_clusters = sum(
                1
                for key, info in self.app.cluster_dict.items()
                if info["time_period"] == "Night" and key[2] == cluster_number
            )
            file_data = self.app.data_dict[Path(self.app.file_path.get()).name]
        else:
            file_data = self.app.data_dict[Path(self.app.file_path.get()).name]
            day_clusters = sum(
                1
                for _, info in file_data.items()
                if info["time_period"] == "Day" and info["cluster_size"] == cluster_number
            )
            night_clusters = sum(
                1
                for _, info in file_data.items()
                if info["time_period"] == "Night" and info["cluster_size"] == cluster_number
            )

        full_clusters = day_clusters + night_clusters
        cluster_counts = {"full": full_clusters, "day": day_clusters, "night": night_clusters}

        for period in ["full", "day", "night"]:
            period_data = self.app.mean_cluster_data.get(cluster_number, {}).get(period)
            if period_data and "binned_mean_temp_data" in period_data:
                if period == "full":
                    row_idx = 0
                    peak_or_peaks = "Peak" if cluster_number == 1 else "Peaks"
                    hyperlink_label = (
                        f"Go to Clusters with {cluster_number} {peak_or_peaks}: raw data"
                    )
                    hyperlink_target = (
                        f"internal: 'Raw, Clusters with {cluster_number} {peak_or_peaks}'!A1"
                    )
                    hyperlink_format = writer.book.add_format(
                        {
                            "align": "center",
                            "valign": "vcenter",
                            "underline": True,
                            "font_color": "blue",
                        }
                    )

                    worksheet.write_url(
                        row_idx,
                        1,
                        hyperlink_target,
                        hyperlink_format,
                        string=hyperlink_label,
                    )
                    worksheet.merge_range(
                        row_idx, 1, row_idx, 4, hyperlink_label, hyperlink_format
                    )
                else:
                    row_idx += 1

                period_title = f"{period.capitalize()} Clusters({cluster_counts[period]})"
                worksheet.write(row_idx, 0, period_title, self.app.bold)

                row_idx += 1
                for col_num, header in enumerate(temp_act_headers):
                    worksheet.write(row_idx, col_num, header, self.app.bold)
                row_idx += 1
                for bin_idx, row_temp in period_data["binned_mean_temp_data"].iterrows():
                    if bin_idx not in period_data["binned_mean_act_data"].index:
                        continue
                    bin_label = row_temp["Bin Range"]
                    worksheet.write(row_idx, 0, bin_label)
                    worksheet.write(row_idx, 1, row_temp["Mean"])
                    worksheet.write(row_idx, 2, row_temp["SEM"])
                    row_act = period_data["binned_mean_act_data"].loc[bin_idx]
                    worksheet.write(row_idx, 3, row_act["Mean"])
                    worksheet.write(row_idx, 4, row_act["SEM"])
                    row_idx += 1
            else:
                row_idx += 1

        self.write_cluster_details(worksheet, cluster_number, file_data, self.app.cluster_dict)

    def write_cluster_details(self, worksheet, cluster_number, file_data, cluster_dict):
        if self.app.data_type == "photometry":
            data_column_name = self.app.data_selection_frame.selected_column_var.get()
            delta_symbol = "\u0394"
            data_column_name = {
                "dFoF_465": f" ({delta_symbol}F/F)",
                "490DF/F": f" ({delta_symbol}F/F)",
                "Z_465": " (Z-score)",
            }.get(data_column_name, "")

            worksheet.write(0, 6, "Photometry Cluster Parameters", self.app.bold)
            worksheet.write(0, 7, "Data Column exported:", self.app.bold)
            worksheet.write(0, 8, f"{data_column_name}", self.app.bold)
        else:
            worksheet.write(0, 6, "Stim Parameters", self.app.bold)

        row_idx, col_idx = 3, 6
        self.write_cluster_static_inputs(worksheet, 1, 7, cluster_number, file_data)

        all_cluster_headings = self.app.generate_cluster_headings(file_data, cluster_number)
        rows_to_skip_all = len(all_cluster_headings)

        cluster_basic_headings = [
            "Cluster Start Time (min)",
            "Cluster End Time (min)",
            "Cluster Duration (min)",
            "Cluster alignment peak time",
        ]
        worksheet.write(row_idx, col_idx, "Full", self.app.all_cell_format)
        row_idx += 1

        row_idx, col_idx = self.write_headings(
            worksheet, row_idx, all_cluster_headings, cluster_basic_headings, rows_to_skip_all
        )

        if self.app.data_type == "photometry":
            peak_time_headings = [f"Peak {i + 1} Time (min)" for i in range(cluster_number)]
            peak_isi_headings = [
                f"Interpeak Interval(min)[{i + 1}] - [{i + 2}]"
                for i in range(cluster_number - 1)
            ]

            peak_amp_unit = {
                "dFoF_465": f" ({delta_symbol}F/F)",
                "490DF/F": f" ({delta_symbol}F/F)",
                "Z_465": " (Z-score)",
            }.get(data_column_name, "")
            peak_amp_headings = [
                f"Peak {i + 1} Amplitude{peak_amp_unit}" for i in range(cluster_number)
            ]

            row_idx, col_idx = self.write_headings(
                worksheet, row_idx, all_cluster_headings, peak_time_headings, rows_to_skip_all
            )
            row_idx, col_idx = self.write_headings(
                worksheet, row_idx, all_cluster_headings, peak_amp_headings, rows_to_skip_all
            )
            if cluster_number != 1:
                row_idx, col_idx = self.write_headings(
                    worksheet, row_idx, all_cluster_headings, peak_isi_headings, rows_to_skip_all
                )

        if self.app.data_type == "photometry":
            full_clusters = [
                details for key, details in cluster_dict.items() if key[2] == cluster_number
            ]
            day_clusters = [
                details
                for key, details in cluster_dict.items()
                if key[2] == cluster_number and details["time_period"] == "Day"
            ]
            night_clusters = [
                details
                for key, details in cluster_dict.items()
                if key[2] == cluster_number and details["time_period"] == "Night"
            ]
        else:
            pattern = re.compile(rf"^{cluster_number}_stim_cluster_\d+$")
            format_key = lambda key: f"{cluster_number} cluster in {key.split('_', 1)[1]}"

            full_clusters = [
                {
                    **details,
                    "name": format_key(key),
                    "alignment_peak_time": 0,
                    "cluster_duration": details["stim_end"] - details["stim_start"],
                }
                for key, details in file_data.items()
                if pattern.match(key)
            ]
            day_clusters = [
                {
                    **details,
                    "name": format_key(key),
                    "alignment_peak_time": 0,
                    "cluster_duration": details["stim_end"] - details["stim_start"],
                }
                for key, details in file_data.items()
                if pattern.match(key) and details["time_period"] == "Day"
            ]
            night_clusters = [
                {
                    **details,
                    "name": format_key(key),
                    "alignment_peak_time": 0,
                    "cluster_duration": details["stim_end"] - details["stim_start"],
                }
                for key, details in file_data.items()
                if pattern.match(key) and details["time_period"] == "Night"
            ]

        day_cluster_headings = self.app.generate_cluster_headings_from_list(day_clusters)
        night_cluster_headings = self.app.generate_cluster_headings_from_list(night_clusters)

        rows_to_skip_day = len(day_cluster_headings)
        rows_to_skip_night = len(night_cluster_headings)

        row_idx_for_basic_data = 5
        initial_row_idx_for_peak_data = None
        row_idx_for_basic_data, row_idx_for_peak_data = self.write_cluster_data_to_worksheet(
            worksheet,
            full_clusters,
            row_idx_for_basic_data,
            col_idx,
            rows_to_skip_all,
            initial_row_idx_for_peak_data,
            cluster_number,
        )

        initial_row_idx_for_peak_data = row_idx_for_peak_data - (rows_to_skip_all - 1)

        row_idx_for_day = row_idx_for_night = row_idx_for_basic_data + 3

        if day_clusters:
            worksheet.write(initial_row_idx_for_peak_data, 6, "Day Clusters", self.app.day_cell_format)
            row_idx = initial_row_idx_for_peak_data + 1

            row_idx, col_idx = self.write_headings(
                worksheet, row_idx, day_cluster_headings, cluster_basic_headings, rows_to_skip_day
            )

            if self.app.data_type == "photometry":
                row_idx, col_idx = self.write_headings(
                    worksheet, row_idx, day_cluster_headings, peak_time_headings, rows_to_skip_day
                )
                row_idx, col_idx = self.write_headings(
                    worksheet, row_idx, day_cluster_headings, peak_amp_headings, rows_to_skip_day
                )
                if cluster_number != 1:
                    row_idx, col_idx = self.write_headings(
                        worksheet, row_idx, day_cluster_headings, peak_isi_headings, rows_to_skip_day
                    )

                initial_row_idx_for_peak_data += rows_to_skip_day + 1

            row_idx_for_day, initial_row_idx_for_peak_data = self.write_cluster_data_to_worksheet(
                worksheet,
                day_clusters,
                row_idx_for_day,
                col_idx,
                rows_to_skip_day,
                initial_row_idx_for_peak_data,
                cluster_number,
            )

            row_idx_for_night = row_idx_for_day + 3
            initial_row_idx_for_peak_data -= rows_to_skip_day - 1

        if night_clusters:
            worksheet.write(initial_row_idx_for_peak_data, 6, "Night Clusters", self.app.night_cell_format)
            row_idx = initial_row_idx_for_peak_data + 1

            row_idx, col_idx = self.write_headings(
                worksheet, row_idx, night_cluster_headings, cluster_basic_headings, rows_to_skip_night
            )

            if self.app.data_type == "photometry":
                row_idx, col_idx = self.write_headings(
                    worksheet, row_idx, night_cluster_headings, peak_time_headings, rows_to_skip_night
                )
                row_idx, col_idx = self.write_headings(
                    worksheet, row_idx, night_cluster_headings, peak_amp_headings, rows_to_skip_night
                )
                if cluster_number != 1:
                    row_idx, col_idx = self.write_headings(
                        worksheet, row_idx, night_cluster_headings, peak_isi_headings, rows_to_skip_night
                    )
            row_idx_for_night, initial_row_idx_for_peak_data = self.write_cluster_data_to_worksheet(
                worksheet,
                night_clusters,
                row_idx_for_night,
                col_idx,
                rows_to_skip_night,
                initial_row_idx_for_peak_data,
                cluster_number,
            )

        self.app.settings_manager.selected_column_name = (
            self.app.data_selection_frame.selected_column_var.get()
        )
        self.app.settings_manager.save_variables()

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
        for cluster_details in clusters:
            if self.app.data_type == "photometry":
                basic_data = [
                    cluster_details["start_time"],
                    cluster_details["end_time"],
                    cluster_details["cluster_duration"],
                    cluster_details["peaks"][cluster_details["alignment_index"]],
                ]
            else:
                basic_data = [
                    cluster_details["stim_start"],
                    cluster_details["stim_end"],
                    cluster_details["cluster_duration"],
                    cluster_details["cluster_size"],
                ]

            row_idx_for_basic_data = self.write_cluster_data_in_columns(
                worksheet, row_idx_for_basic_data, col_idx, basic_data
            )

            row_idx_for_peak_data = row_idx_for_basic_data + rows_to_skip

            if self.app.data_type == "photometry":
                row_idx_for_peak_data, next_row_idx_for_basic_data = (
                    self.write_peak_data_in_columns(
                        worksheet,
                        row_idx_for_peak_data,
                        col_idx,
                        cluster_details["peaks"],
                        row_idx_for_basic_data,
                        rows_to_skip,
                    )
                )

                row_idx_for_peak_data, next_row_idx_for_basic_data = (
                    self.write_peak_data_in_columns(
                        worksheet,
                        row_idx_for_peak_data,
                        col_idx,
                        cluster_details.get("peak_amplitudes", []),
                        next_row_idx_for_basic_data,
                        rows_to_skip,
                    )
                )

                if cluster_number > 1:
                    row_idx_for_peak_data, next_row_idx_for_basic_data = (
                        self.write_peak_data_in_columns(
                            worksheet,
                            row_idx_for_peak_data,
                            col_idx,
                            cluster_details.get("interpeak_intervals", []),
                            next_row_idx_for_basic_data,
                            rows_to_skip,
                        )
                    )
            else:
                next_row_idx_for_basic_data = row_idx_for_basic_data

        return next_row_idx_for_basic_data, row_idx_for_peak_data

    def write_vertical_headings(self, worksheet, row_idx, headings):
        col_idx = 6
        for heading in headings:
            worksheet.write(row_idx, col_idx, heading, self.app.bold)
            row_idx += 1
        return col_idx + 1

    def write_headings(self, worksheet, row_idx, cluster_headings, headings, rows_to_skip):
        col_idx = self.write_vertical_headings(worksheet, row_idx, cluster_headings)
        for heading in headings:
            worksheet.write(row_idx, col_idx, heading, self.app.bold)
            col_idx += 1
        row_idx = row_idx + rows_to_skip + 1
        return row_idx, 7

    def write_cluster_data_in_columns(self, worksheet, row_idx, col_idx, data_list):
        for data in data_list:
            worksheet.write(row_idx, col_idx, data)
            col_idx += 1
        return row_idx + 1

    def write_peak_data_in_columns(
        self, worksheet, row_idx, col_idx, data_list, row_idx_for_basic_data, rows_to_skip
    ):
        for data in data_list:
            worksheet.write(row_idx, col_idx, data)
            col_idx += 1
        row_idx = row_idx + rows_to_skip
        next_row_idx_for_basic_data = row_idx_for_basic_data + rows_to_skip + 1
        return row_idx + 1, next_row_idx_for_basic_data

    def write_cluster_static_inputs(self, worksheet, row_idx, col_idx, cluster_number, file_data):
        static_values_name = "cluster" if self.app.data_type == "photometry" else "stim"

        worksheet.write(row_idx, col_idx - 1, "Static Inputs", self.app.bold)
        cluster_static_headings = [
            f"Pre {static_values_name} time (s)",
            f"Post {static_values_name} time (s)",
            "Bin size",
        ]
        for heading in cluster_static_headings:
            worksheet.write(row_idx, col_idx, heading, self.app.bold)
            col_idx += 1

        row_idx += 1
        col_idx -= len(cluster_static_headings)
        cluster_pattern_peaks = (
            f"{cluster_number} Peak{'s' if cluster_number > 1 else ''} in Cluster_"
        )
        cluster_pattern_stim = f"{cluster_number}_stim_cluster_"

        for key, value in file_data.items():
            if key.startswith(cluster_pattern_peaks) or key.startswith(cluster_pattern_stim):
                data_keys = [f"pre_{static_values_name}_time", f"post_{static_values_name}_time", "bin_size"]
                for data_key in data_keys:
                    try:
                        static_value = float(value.get(data_key, 0))
                        if static_value.is_integer():
                            static_value = int(static_value)
                    except ValueError:
                        static_value = value.get(data_key, "")

                    worksheet.write(row_idx, col_idx, static_value)
                    col_idx += 1
                break

        row_idx += 1
        return row_idx

    def format_bin_label(self, start_time, bin_size_sec):
        end_time = start_time + bin_size_sec
        return f"{start_time} - {end_time}"
