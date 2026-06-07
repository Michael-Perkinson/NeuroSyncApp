"""Signal sheet helpers for telemetry workbook exports."""

from __future__ import annotations

import pandas as pd

from src.features.telemetry_alignment.exporters.export_frames import (
    build_intercluster_interval_frame,
    build_native_signal_frame,
    get_standardized_native_window_bounds,
)


def populate_intercluster_intervals_sheet(exporter, writer, sheet_name):
    interval_frame = build_intercluster_interval_frame(
        cluster_dict=exporter.app.cluster_dict,
        file_data=exporter._get_active_file_data(),
        data_type=exporter.app.data_type,
    )
    _write_titled_dataframe_sheet(
        writer,
        sheet_name,
        "Intercluster intervals in chronological cluster order",
        interval_frame,
    )


def populate_native_signal_sheet(exporter, writer, sheet_name, signal_type, window_mode):
    signal_label = "temperature" if signal_type == "temp" else "activity"
    if window_mode == "full_cluster":
        window_label = "full cluster context"
    else:
        window_start, window_end = get_standardized_native_window_bounds(
            cluster_dict=exporter.app.cluster_dict,
            file_data=exporter._get_active_file_data(),
            data_type=exporter.app.data_type,
            window_mode=window_mode,
        )
        window_label = f"fixed first-peak window {window_start:.3f} to {window_end:.3f} min"
    native_frame = build_native_signal_frame(
        mean_cluster_data=exporter.app.mean_cluster_data,
        cluster_dict=exporter.app.cluster_dict,
        file_data=exporter._get_active_file_data(),
        data_type=exporter.app.data_type,
        signal_type=signal_type,
        window_mode=window_mode,
    )
    _write_titled_dataframe_sheet(
        writer,
        sheet_name,
        f"Native-rate {signal_label} samples aligned by cluster ({window_label})",
        native_frame,
    )


def _write_titled_dataframe_sheet(writer, sheet_name, title, dataframe: pd.DataFrame) -> None:
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
