"""Raw sheet helpers for telemetry workbook exports."""

from __future__ import annotations

import pandas as pd


def populate_raw_data_sheet(exporter, writer, sheet_name, cluster_number):
    cluster_data = exporter.app.mean_cluster_data.get(cluster_number)
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

    full_temp_data = cluster_data["full"]["raw_temp_data"]
    full_act_data = cluster_data["full"]["raw_act_data"]
    if exporter.app.data_type == "photometry":
        full_photometry_data, photometry_export_label = exporter._prepare_photometry_export_frame(
            cluster_data["full"]["photometry_cluster_data"]
        )

    row_idx, col_idx = 0, 0
    next_col_idx, full_row_idx_after_temp = write_raw_data_to_sheet(
        exporter, worksheet, writer, row_idx, col_idx, "Full", "Temp", full_temp_data
    )
    next_col_idx, full_row_idx_after_act = write_raw_data_to_sheet(
        exporter, worksheet, writer, row_idx, next_col_idx, "Full", "Act", full_act_data
    )
    full_section_end_rows = [full_row_idx_after_temp, full_row_idx_after_act]
    if exporter.app.data_type == "photometry":
        next_col_idx, full_row_idx_after_photometry = write_raw_data_to_sheet(
            exporter,
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
        if exporter.app.data_type == "photometry":
            day_photometry_data, photometry_export_label = exporter._prepare_photometry_export_frame(
                cluster_data["day"]["photometry_cluster_data"]
            )

        next_col_idx, day_row_idx_after_temp = write_raw_data_to_sheet(
            exporter, worksheet, writer, row_idx, col_idx, "Day", "Temp", day_temp_data
        )
        next_col_idx, day_row_idx_after_act = write_raw_data_to_sheet(
            exporter, worksheet, writer, row_idx, next_col_idx, "Day", "Act", day_act_data
        )
        day_section_end_rows = [day_row_idx_after_temp, day_row_idx_after_act]
        if exporter.app.data_type == "photometry":
            next_col_idx, day_row_idx_after_photometry = write_raw_data_to_sheet(
                exporter,
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
        if exporter.app.data_type == "photometry":
            night_photometry_data, photometry_export_label = exporter._prepare_photometry_export_frame(
                cluster_data["night"]["photometry_cluster_data"]
            )

        next_col_idx, night_row_idx_after_temp = write_raw_data_to_sheet(
            exporter, worksheet, writer, row_idx, col_idx, "Night", "Temp", night_temp_data
        )
        next_col_idx, night_row_idx_after_act = write_raw_data_to_sheet(
            exporter, worksheet, writer, row_idx, next_col_idx, "Night", "Act", night_act_data
        )
        night_section_end_rows = [night_row_idx_after_temp, night_row_idx_after_act]
        if exporter.app.data_type == "photometry":
            next_col_idx, night_row_idx_after_photometry = write_raw_data_to_sheet(
                exporter,
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
        add_navigation_hyperlink(worksheet, writer, "Day", day_start_row + 1, 1)

    if night_start_row is not None:
        night_col_idx = 2 if day_start_row is not None else 1
        add_navigation_hyperlink(worksheet, writer, "Night", night_start_row + 1, night_col_idx)

    worksheet.set_column(0, 30, 20.5)


def add_home_hyperlink(worksheet, writer, col_idx, row_idx):
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


def write_raw_data_to_sheet(exporter, worksheet, writer, row_idx, col_idx, period, data_type, data):
    worksheet.write(row_idx, col_idx, f"Raw data: {period} - {data_type}", exporter.app.bold)

    if (period == "Day" or period == "Night") and data_type == "Temp":
        add_home_hyperlink(worksheet, writer, col_idx + 1, row_idx)

    row_idx += 1
    next_col_idx = col_idx

    if isinstance(data, pd.DataFrame):
        if not data.empty:
            for col_num, header in enumerate(data.columns):
                worksheet.write(row_idx, col_idx + col_num, header, exporter.app.bold)
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


def add_navigation_hyperlink(worksheet, writer, period, row_idx, col_idx):
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
