"""Summary sheet helpers for telemetry workbook exports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.features.telemetry_alignment.exporters.export_frames import (
    get_standardized_native_window_bounds,
)


def populate_summary_sheet(exporter, writer, sorted_cluster_numbers) -> None:
    worksheet = writer.book.add_worksheet("Summary")
    writer.sheets["Summary"] = worksheet
    worksheet.activate()

    title_format = writer.book.add_format({"bold": True, "font_size": 14})
    subtitle_format = writer.book.add_format({"italic": True, "font_color": "#62758B"})
    section_format = writer.book.add_format(
        {"bold": True, "font_size": 12, "bg_color": "#DCE6F1", "border": 1}
    )
    header_format = writer.book.add_format(
        {"bold": True, "bg_color": "#E0EADF", "border": 1, "text_wrap": True}
    )
    label_format = writer.book.add_format({"bold": True, "text_wrap": True})
    value_format = writer.book.add_format({"text_wrap": True, "valign": "top"})
    link_format = writer.book.add_format(
        {"underline": True, "font_color": "blue", "text_wrap": True}
    )

    worksheet.set_column(0, 0, 30)
    worksheet.set_column(1, 1, 44)
    worksheet.set_column(2, 2, 58)
    worksheet.set_column(3, 8, 18)

    row_idx = 0
    worksheet.write(row_idx, 0, "Telemetry Export Summary", title_format)
    row_idx += 1
    worksheet.write(
        row_idx,
        0,
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        subtitle_format,
    )
    row_idx += 2

    row_idx = _write_summary_key_value_section(
        worksheet,
        row_idx,
        "Export Overview",
        _build_summary_overview_rows(exporter, sorted_cluster_numbers),
        section_format,
        label_format,
        value_format,
    )
    row_idx += 1

    static_input_headers, static_input_rows = _build_static_input_summary(
        exporter,
        sorted_cluster_numbers,
    )
    row_idx = _write_summary_table_section(
        worksheet,
        row_idx,
        "Cluster Settings Used",
        static_input_headers,
        static_input_rows,
        section_format,
        header_format,
        value_format,
    )
    row_idx += 1

    sheet_guide_rows = _build_sheet_guide_rows(exporter, sorted_cluster_numbers)
    _write_summary_table_section(
        worksheet,
        row_idx,
        "Sheet Guide",
        ["Sheet Name", "What It Contains", "Notes"],
        sheet_guide_rows,
        section_format,
        header_format,
        value_format,
        link_first_column=True,
        link_format=link_format,
    )


def _write_summary_key_value_section(
    worksheet,
    row_idx,
    section_title,
    rows,
    section_format,
    label_format,
    value_format,
):
    worksheet.write(row_idx, 0, section_title, section_format)
    row_idx += 1

    for label, value in rows:
        worksheet.write(row_idx, 0, label, label_format)
        worksheet.write(row_idx, 1, value, value_format)
        row_idx += 1

    return row_idx


def _write_summary_table_section(
    worksheet,
    row_idx,
    section_title,
    headers,
    rows,
    section_format,
    header_format,
    value_format,
    link_first_column=False,
    link_format=None,
):
    worksheet.write(row_idx, 0, section_title, section_format)
    row_idx += 1

    for col_idx, header in enumerate(headers):
        worksheet.write(row_idx, col_idx, header, header_format)
    row_idx += 1

    if not rows:
        worksheet.write(row_idx, 0, "No data available.", value_format)
        return row_idx + 1

    for row in rows:
        for col_idx, value in enumerate(row):
            if link_first_column and col_idx == 0 and link_format is not None and value:
                worksheet.write_url(
                    row_idx,
                    col_idx,
                    f"internal:'{value}'!A1",
                    string=str(value),
                    cell_format=link_format,
                )
            else:
                worksheet.write(row_idx, col_idx, value, value_format)
        row_idx += 1

    return row_idx


def _build_summary_overview_rows(exporter, sorted_cluster_numbers):
    file_data = exporter._get_active_file_data()
    total_counts = _get_total_cluster_counts(exporter, sorted_cluster_numbers, file_data)
    fixed_window_start, fixed_window_end = get_standardized_native_window_bounds(
        cluster_dict=exporter.app.cluster_dict,
        file_data=file_data,
        data_type=exporter.app.data_type,
        window_mode="fixed_window",
    )

    main_file_path = exporter.app._get_current_file_path()
    selected_column_name = exporter.app.data_selection_frame.selected_column_var.get()
    associated_start_time = _get_associated_start_time_used(exporter)
    photometry_preview_interval = (
        f"~{exporter._get_photometry_export_interval_seconds():g} s bins"
        if exporter.app.data_type == "photometry"
        else "Not applicable"
    )

    rows = [
        ("Main data file", Path(main_file_path).name if main_file_path else "Not available"),
        (
            "Mouse name",
            exporter._format_summary_value(getattr(exporter.app, "mouse_name", "")),
        ),
        (
            "Recording date",
            exporter._format_summary_value(getattr(exporter.app, "date", "")),
        ),
        (
            "Data type",
            (
                "Photometry telemetry alignment"
                if exporter.app.data_type == "photometry"
                else "Optogenetic telemetry alignment"
            ),
        ),
        (
            "Associated temperature file",
            (
                Path(exporter.app.temp_file_path).name
                if exporter.app.temp_file_path
                else "Not available"
            ),
        ),
        (
            "Associated activity file",
            (
                Path(exporter.app.act_file_path).name
                if exporter.app.act_file_path
                else "Not available"
            ),
        ),
        (
            "Associated telemetry start time used",
            exporter._format_summary_value(associated_start_time),
        ),
        (
            "Clustering minimum time between clusters (s)",
            exporter._format_summary_value(exporter.app.adjust_clustering_var.get()),
        ),
        (
            "Remove first 60 minutes before cluster detection",
            exporter._format_summary_value(
                exporter.app.graph_settings_container_instance.remove_first_60_minutes_var.get()
            ),
        ),
        (
            "Lights off time used for Day/Night split",
            exporter._format_summary_value(exporter.app.light_off_time_var.get()),
        ),
        (
            "Recording duration analyzed (min)",
            exporter._format_summary_value(
                getattr(exporter.app, "duration_main_data", "")
            ),
        ),
        (
            "Temperature sampling interval (s)",
            exporter._format_summary_value(getattr(exporter.app, "temp_sample_rate", "")),
        ),
        (
            "Activity sampling interval (s)",
            exporter._format_summary_value(getattr(exporter.app, "act_sample_rate", "")),
        ),
        ("Photometry preview interval in raw sheets", photometry_preview_interval),
        (
            "Fixed native window used in native exports (min)",
            f"{fixed_window_start:.3f} to {fixed_window_end:.3f}",
        ),
        ("Total clusters exported", total_counts["full"]),
        ("Day clusters exported", total_counts["day"]),
        ("Night clusters exported", total_counts["night"]),
    ]

    if exporter.app.data_type == "photometry":
        rows.insert(
            4,
            (
                "Photometry column exported",
                exporter._format_summary_value(selected_column_name),
            ),
        )

    return rows


def _build_static_input_summary(exporter, sorted_cluster_numbers):
    file_data = exporter._get_active_file_data()
    label_root = "Peaks" if exporter.app.data_type == "photometry" else "Stims"
    static_label_root = "cluster" if exporter.app.data_type == "photometry" else "stim"

    headers = [
        f"{label_root} per Cluster",
        "Full",
        "Day",
        "Night",
    ]
    if exporter.app.data_type == "photometry":
        headers.append("Alignment Peak Used")
    headers.extend(
        [
            f"Pre-{static_label_root} Time (s)",
            f"Post-{static_label_root} Time (s)",
            "Bin Size (s)",
        ]
    )

    rows = []
    for cluster_number in sorted_cluster_numbers:
        count_breakdown = _get_cluster_count_breakdown(exporter, cluster_number, file_data)
        static_inputs = _get_cluster_static_inputs(exporter, cluster_number, file_data)
        row = [
            cluster_number,
            count_breakdown["full"],
            count_breakdown["day"],
            count_breakdown["night"],
        ]
        if exporter.app.data_type == "photometry":
            row.append(_get_alignment_peak_label(exporter, cluster_number))
        row.extend(
            [
                static_inputs["pre"],
                static_inputs["post"],
                static_inputs["bin"],
            ]
        )
        rows.append(row)

    return headers, rows


def _build_sheet_guide_rows(exporter, sorted_cluster_numbers):
    rows = []
    for cluster_number in sorted_cluster_numbers:
        cluster_sheet_name = (
            "Clusters with 1 Peak"
            if cluster_number == 1
            else f"Clusters with {cluster_number} peaks"
        )
        raw_sheet_name = (
            "Raw, Clusters with 1 Peak"
            if cluster_number == 1
            else f"Raw, Clusters with {cluster_number} Peaks"
        )
        peak_label = "peak" if cluster_number == 1 else "peaks"
        cluster_subject = (
            f"clusters containing {cluster_number} {peak_label}"
            if exporter.app.data_type == "photometry"
            else f"stim clusters containing {cluster_number} stims"
        )

        rows.append(
            [
                cluster_sheet_name,
                f"Binned mean temperature/activity summary for {cluster_subject}.",
                "Includes Full, Day, and Night sections plus per-cluster metadata.",
            ]
        )
        raw_notes = (
            "Wide aligned raw temperature/activity matrices. Photometry is included as a downsampled preview to keep Excel manageable."
            if exporter.app.data_type == "photometry"
            else "Wide aligned raw temperature/activity matrices for each period."
        )
        rows.append(
            [
                raw_sheet_name,
                f"Raw aligned export blocks for {cluster_subject}.",
                raw_notes,
            ]
        )

    fixed_window_start, fixed_window_end = get_standardized_native_window_bounds(
        cluster_dict=exporter.app.cluster_dict,
        file_data=exporter._get_active_file_data(),
        data_type=exporter.app.data_type,
        window_mode="fixed_window",
    )
    rows.extend(
        [
            [
                "Intercluster Intervals",
                "Chronological spacing between clusters across the recording.",
                "Useful for checking whether nearby clusters may influence one another.",
            ],
            [
                "Raw Temp Native FullCluster",
                "Native-rate temperature samples for each cluster using the actual available full-cluster window.",
                "Long-format export with one row per native telemetry sample.",
            ],
            [
                "Raw Act Native FullCluster",
                "Native-rate activity samples for each cluster using the actual available full-cluster window.",
                "Long-format export with one row per native telemetry sample.",
            ],
            [
                "Raw Temp Native FixedWindow",
                "Native-rate temperature samples using a standardized first-peak-centered fixed window.",
                f"Window bounds: {fixed_window_start:.3f} to {fixed_window_end:.3f} min. Blank rows can appear if a cluster starts near recording start.",
            ],
            [
                "Raw Act Native FixedWindow",
                "Native-rate activity samples using a standardized first-peak-centered fixed window.",
                f"Window bounds: {fixed_window_start:.3f} to {fixed_window_end:.3f} min. Blank rows can appear if a cluster starts near recording start.",
            ],
        ]
    )
    return rows


def _get_cluster_static_inputs(exporter, cluster_number, file_data):
    static_values_name = "cluster" if exporter.app.data_type == "photometry" else "stim"
    cluster_pattern_peaks = (
        f"{cluster_number} Peak{'s' if cluster_number > 1 else ''} in Cluster_"
    )
    cluster_pattern_stim = f"{cluster_number}_stim_cluster_"

    for key, value in file_data.items():
        if key.startswith(cluster_pattern_peaks) or key.startswith(cluster_pattern_stim):
            return {
                "pre": exporter._format_summary_value(
                    value.get(f"pre_{static_values_name}_time", "")
                ),
                "post": exporter._format_summary_value(
                    value.get(f"post_{static_values_name}_time", "")
                ),
                "bin": exporter._format_summary_value(value.get("bin_size", "")),
            }

    return {"pre": "", "post": "", "bin": ""}


def _get_cluster_count_breakdown(exporter, cluster_number, file_data):
    if exporter.app.data_type == "photometry":
        full_count = sum(1 for key in exporter.app.cluster_dict if key[2] == cluster_number)
        day_count = sum(
            1
            for key, details in exporter.app.cluster_dict.items()
            if key[2] == cluster_number and details.get("time_period") == "Day"
        )
        night_count = sum(
            1
            for key, details in exporter.app.cluster_dict.items()
            if key[2] == cluster_number and details.get("time_period") == "Night"
        )
    else:
        full_count = sum(
            1
            for details in file_data.values()
            if int(details.get("cluster_size", 0) or 0) == cluster_number
        )
        day_count = sum(
            1
            for details in file_data.values()
            if int(details.get("cluster_size", 0) or 0) == cluster_number
            and details.get("time_period") == "Day"
        )
        night_count = sum(
            1
            for details in file_data.values()
            if int(details.get("cluster_size", 0) or 0) == cluster_number
            and details.get("time_period") == "Night"
        )

    return {"full": full_count, "day": day_count, "night": night_count}


def _get_total_cluster_counts(exporter, sorted_cluster_numbers, file_data):
    totals = {"full": 0, "day": 0, "night": 0}
    for cluster_number in sorted_cluster_numbers:
        breakdown = _get_cluster_count_breakdown(exporter, cluster_number, file_data)
        for key in totals:
            totals[key] += breakdown[key]
    return totals


def _get_alignment_peak_label(exporter, cluster_number):
    alignment_indices = {
        details.get("alignment_index")
        for key, details in exporter.app.cluster_dict.items()
        if key[2] == cluster_number and details.get("alignment_index") is not None
    }
    alignment_indices.discard(None)

    if len(alignment_indices) == 1:
        alignment_index = next(iter(alignment_indices))
        if alignment_index == -1:
            return "Last peak"
        return f"Peak {alignment_index + 1}"

    if len(alignment_indices) > 1:
        return "Mixed"

    fallback_var = getattr(exporter.app, "peak_alignment_vars", {}).get(cluster_number)
    if fallback_var is not None and fallback_var.get():
        return f"Peak {fallback_var.get()}"
    return ""


def _get_associated_start_time_used(exporter):
    start_time_str = (exporter.app.temp_and_act_start_time_var.get() or "").strip()
    if start_time_str:
        return start_time_str
    return str(getattr(exporter.app, "start_time_timedelta", "") or "").strip()
