from __future__ import annotations

import pandas as pd
from openpyxl import load_workbook

from src.excel_ops.behaviour_exporter import (
    build_output_file_name,
    export_combined_excel,
)


def test_output_file_name_includes_all_selected_columns(tmp_path):
    output_path = build_output_file_name(
        str(tmp_path / "recording.csv"),
        str(tmp_path),
        ["dFoF_465", "dFoF_405"],
        False,
    )

    assert output_path.endswith("recording_dual_dfof.xlsx")


def test_output_file_name_uses_z_tag_for_multi_signal_baseline_export(tmp_path):
    output_path = build_output_file_name(
        str(tmp_path / "recording.csv"),
        str(tmp_path),
        ["dFoF_465", "dFoF_405"],
        True,
        "0",
    )

    assert output_path.endswith("recording_dual_Z_baseline_0.xlsx")


def test_output_file_name_uses_multi_tag_for_three_signals(tmp_path):
    output_path = build_output_file_name(
        str(tmp_path / "recording.csv"),
        str(tmp_path),
        ["dFoF_465", "dFoF_405", "isosbestic"],
        False,
    )

    assert output_path.endswith("recording_multi_signal.xlsx")


def test_summary_signal_rows_are_full_width_banners(tmp_path):
    output_path = tmp_path / "summary.xlsx"
    summary = pd.DataFrame(
        [
            ["Signal: dFoF_465", "", ""],
            ["grooming", "-10 - 0", "0 - 10"],
            ["", "", ""],
            ["Signal: dFoF_405", "", ""],
            ["grooming", "-10 - 0", "0 - 10"],
        ]
    )

    export_combined_excel(summary, [], str(output_path), {})

    workbook = load_workbook(output_path)
    try:
        worksheet = workbook["Summary Results"]
        for row_number in (1, 4):
            row = worksheet[row_number]
            assert row[0].value.startswith("Signal:")
            assert all(cell.fill.fgColor.rgb == "0017324D" for cell in row)
            assert all(cell.font.bold for cell in row)
            assert all(cell.font.color.rgb == "00FFFFFF" for cell in row)
    finally:
        workbook.close()
