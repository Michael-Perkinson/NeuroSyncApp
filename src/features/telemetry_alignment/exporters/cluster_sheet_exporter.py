"""Cluster summary sheet helpers for telemetry workbook exports."""

from __future__ import annotations

from pathlib import Path
import re


def populate_cluster_sheet(exporter, writer, sheet_name, cluster_number):
    worksheet = writer.book.add_worksheet(sheet_name)

    exporter.app.bold = writer.book.add_format({"bold": True})
    exporter.app.all_cell_format = writer.book.add_format(
        {"bold": True, "bg_color": "#e0eadf"}
    )
    exporter.app.day_cell_format = writer.book.add_format(
        {"bold": True, "bg_color": "yellow"}
    )
    exporter.app.night_cell_format = writer.book.add_format(
        {"bold": True, "bg_color": "#8f9ed9"}
    )

    temp_act_headers = ["Time (s)", "Mean Temp", "SEM Temp", "Mean Act", "SEM Act"]
    row_idx = 0

    if exporter.app.data_type == "photometry":
        day_clusters = sum(
            1
            for key, info in exporter.app.cluster_dict.items()
            if info["time_period"] == "Day" and key[2] == cluster_number
        )
        night_clusters = sum(
            1
            for key, info in exporter.app.cluster_dict.items()
            if info["time_period"] == "Night" and key[2] == cluster_number
        )
        file_data = exporter.app.data_dict[Path(exporter.app.file_path.get()).name]
    else:
        file_data = exporter.app.data_dict[Path(exporter.app.file_path.get()).name]
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
        period_data = exporter.app.mean_cluster_data.get(cluster_number, {}).get(period)
        if period_data and "binned_mean_temp_data" in period_data:
            if period == "full":
                row_idx = 0
                peak_or_peaks = "Peak" if cluster_number == 1 else "Peaks"
                hyperlink_label = f"Go to Clusters with {cluster_number} {peak_or_peaks}: raw data"
                hyperlink_target = f"internal: 'Raw, Clusters with {cluster_number} {peak_or_peaks}'!A1"
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
                worksheet.merge_range(row_idx, 1, row_idx, 4, hyperlink_label, hyperlink_format)
            else:
                row_idx += 1

            period_title = f"{period.capitalize()} Clusters({cluster_counts[period]})"
            worksheet.write(row_idx, 0, period_title, exporter.app.bold)

            row_idx += 1
            for col_num, header in enumerate(temp_act_headers):
                worksheet.write(row_idx, col_num, header, exporter.app.bold)
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

    write_cluster_details(exporter, worksheet, cluster_number, file_data, exporter.app.cluster_dict)


def write_cluster_details(exporter, worksheet, cluster_number, file_data, cluster_dict):
    if exporter.app.data_type == "photometry":
        data_column_name = exporter.app.data_selection_frame.selected_column_var.get()
        delta_symbol = "\u0394"
        data_column_name = {
            "dFoF_465": f" ({delta_symbol}F/F)",
            "490DF/F": f" ({delta_symbol}F/F)",
            "Z_465": " (Z-score)",
        }.get(data_column_name, "")

        worksheet.write(0, 6, "Photometry Cluster Parameters", exporter.app.bold)
        worksheet.write(0, 7, "Data Column exported:", exporter.app.bold)
        worksheet.write(0, 8, f"{data_column_name}", exporter.app.bold)
    else:
        worksheet.write(0, 6, "Stim Parameters", exporter.app.bold)

    row_idx, col_idx = 3, 6
    write_cluster_static_inputs(exporter, worksheet, 1, 7, cluster_number, file_data)

    all_cluster_headings = exporter.app.generate_cluster_headings(file_data, cluster_number)
    rows_to_skip_all = len(all_cluster_headings)

    cluster_basic_headings = [
        "Cluster Start Time (min)",
        "Cluster End Time (min)",
        "Cluster Duration (min)",
        "Cluster alignment peak time",
    ]
    worksheet.write(row_idx, col_idx, "Full", exporter.app.all_cell_format)
    row_idx += 1

    row_idx, col_idx = write_headings(
        exporter,
        worksheet,
        row_idx,
        all_cluster_headings,
        cluster_basic_headings,
        rows_to_skip_all,
    )

    if exporter.app.data_type == "photometry":
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

        row_idx, col_idx = write_headings(
            exporter,
            worksheet,
            row_idx,
            all_cluster_headings,
            peak_time_headings,
            rows_to_skip_all,
        )
        row_idx, col_idx = write_headings(
            exporter,
            worksheet,
            row_idx,
            all_cluster_headings,
            peak_amp_headings,
            rows_to_skip_all,
        )
        if cluster_number != 1:
            row_idx, col_idx = write_headings(
                exporter,
                worksheet,
                row_idx,
                all_cluster_headings,
                peak_isi_headings,
                rows_to_skip_all,
            )

    if exporter.app.data_type == "photometry":
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

        def format_key(key):
            return f"{cluster_number} cluster in {key.split('_', 1)[1]}"

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

    day_cluster_headings = exporter.app.generate_cluster_headings_from_list(day_clusters)
    night_cluster_headings = exporter.app.generate_cluster_headings_from_list(night_clusters)

    rows_to_skip_day = len(day_cluster_headings)
    rows_to_skip_night = len(night_cluster_headings)

    row_idx_for_basic_data = 5
    initial_row_idx_for_peak_data = None
    row_idx_for_basic_data, row_idx_for_peak_data = write_cluster_data_to_worksheet(
        exporter,
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
        worksheet.write(initial_row_idx_for_peak_data, 6, "Day Clusters", exporter.app.day_cell_format)
        row_idx = initial_row_idx_for_peak_data + 1

        row_idx, col_idx = write_headings(
            exporter,
            worksheet,
            row_idx,
            day_cluster_headings,
            cluster_basic_headings,
            rows_to_skip_day,
        )

        if exporter.app.data_type == "photometry":
            row_idx, col_idx = write_headings(
                exporter,
                worksheet,
                row_idx,
                day_cluster_headings,
                peak_time_headings,
                rows_to_skip_day,
            )
            row_idx, col_idx = write_headings(
                exporter,
                worksheet,
                row_idx,
                day_cluster_headings,
                peak_amp_headings,
                rows_to_skip_day,
            )
            if cluster_number != 1:
                row_idx, col_idx = write_headings(
                    exporter,
                    worksheet,
                    row_idx,
                    day_cluster_headings,
                    peak_isi_headings,
                    rows_to_skip_day,
                )

            initial_row_idx_for_peak_data += rows_to_skip_day + 1

        row_idx_for_day, initial_row_idx_for_peak_data = write_cluster_data_to_worksheet(
            exporter,
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
        worksheet.write(initial_row_idx_for_peak_data, 6, "Night Clusters", exporter.app.night_cell_format)
        row_idx = initial_row_idx_for_peak_data + 1

        row_idx, col_idx = write_headings(
            exporter,
            worksheet,
            row_idx,
            night_cluster_headings,
            cluster_basic_headings,
            rows_to_skip_night,
        )

        if exporter.app.data_type == "photometry":
            row_idx, col_idx = write_headings(
                exporter,
                worksheet,
                row_idx,
                night_cluster_headings,
                peak_time_headings,
                rows_to_skip_night,
            )
            row_idx, col_idx = write_headings(
                exporter,
                worksheet,
                row_idx,
                night_cluster_headings,
                peak_amp_headings,
                rows_to_skip_night,
            )
            if cluster_number != 1:
                row_idx, col_idx = write_headings(
                    exporter,
                    worksheet,
                    row_idx,
                    night_cluster_headings,
                    peak_isi_headings,
                    rows_to_skip_night,
                )
        row_idx_for_night, initial_row_idx_for_peak_data = write_cluster_data_to_worksheet(
            exporter,
            worksheet,
            night_clusters,
            row_idx_for_night,
            col_idx,
            rows_to_skip_night,
            initial_row_idx_for_peak_data,
            cluster_number,
        )

    exporter.app.settings_manager.selected_column_name = (
        exporter.app.data_selection_frame.selected_column_var.get()
    )
    exporter.app.settings_manager.save_variables()


def write_cluster_data_to_worksheet(
    exporter,
    worksheet,
    clusters,
    row_idx_for_basic_data,
    col_idx,
    rows_to_skip,
    initial_row_idx_for_peak_data,
    cluster_number,
):
    for cluster_details in clusters:
        if exporter.app.data_type == "photometry":
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

        row_idx_for_basic_data = write_cluster_data_in_columns(
            worksheet, row_idx_for_basic_data, col_idx, basic_data
        )

        row_idx_for_peak_data = row_idx_for_basic_data + rows_to_skip

        if exporter.app.data_type == "photometry":
            row_idx_for_peak_data, next_row_idx_for_basic_data = write_peak_data_in_columns(
                worksheet,
                row_idx_for_peak_data,
                col_idx,
                cluster_details["peaks"],
                row_idx_for_basic_data,
                rows_to_skip,
            )

            row_idx_for_peak_data, next_row_idx_for_basic_data = write_peak_data_in_columns(
                worksheet,
                row_idx_for_peak_data,
                col_idx,
                cluster_details.get("peak_amplitudes", []),
                next_row_idx_for_basic_data,
                rows_to_skip,
            )

            if cluster_number > 1:
                row_idx_for_peak_data, next_row_idx_for_basic_data = write_peak_data_in_columns(
                    worksheet,
                    row_idx_for_peak_data,
                    col_idx,
                    cluster_details.get("interpeak_intervals", []),
                    next_row_idx_for_basic_data,
                    rows_to_skip,
                )
        else:
            next_row_idx_for_basic_data = row_idx_for_basic_data

    return next_row_idx_for_basic_data, row_idx_for_peak_data


def write_vertical_headings(exporter, worksheet, row_idx, headings):
    col_idx = 6
    for heading in headings:
        worksheet.write(row_idx, col_idx, heading, exporter.app.bold)
        row_idx += 1
    return col_idx + 1


def write_headings(exporter, worksheet, row_idx, cluster_headings, headings, rows_to_skip):
    col_idx = write_vertical_headings(exporter, worksheet, row_idx, cluster_headings)
    for heading in headings:
        worksheet.write(row_idx, col_idx, heading, exporter.app.bold)
        col_idx += 1
    row_idx = row_idx + rows_to_skip + 1
    return row_idx, 7


def write_cluster_data_in_columns(worksheet, row_idx, col_idx, data_list):
    for data in data_list:
        worksheet.write(row_idx, col_idx, data)
        col_idx += 1
    return row_idx + 1


def write_peak_data_in_columns(
    worksheet,
    row_idx,
    col_idx,
    data_list,
    row_idx_for_basic_data,
    rows_to_skip,
):
    for data in data_list:
        worksheet.write(row_idx, col_idx, data)
        col_idx += 1
    row_idx = row_idx + rows_to_skip
    next_row_idx_for_basic_data = row_idx_for_basic_data + rows_to_skip + 1
    return row_idx + 1, next_row_idx_for_basic_data


def write_cluster_static_inputs(exporter, worksheet, row_idx, col_idx, cluster_number, file_data):
    static_values_name = "cluster" if exporter.app.data_type == "photometry" else "stim"

    worksheet.write(row_idx, col_idx - 1, "Static Inputs", exporter.app.bold)
    cluster_static_headings = [
        f"Pre {static_values_name} time (s)",
        f"Post {static_values_name} time (s)",
        "Bin size",
    ]
    for heading in cluster_static_headings:
        worksheet.write(row_idx, col_idx, heading, exporter.app.bold)
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
