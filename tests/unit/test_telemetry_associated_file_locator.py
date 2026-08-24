from __future__ import annotations

import types

import pytest

from src.features.telemetry_alignment.io.associated_file_locator import (
    _filename_matches_date,
    _matching_files_for_date,
    TelemetryAssociatedFileLocator,
)


def test_filename_date_match_accepts_zero_padded_month_and_day():
    assert _filename_matches_date("Mouse_TEMP_24-03-05.xlsx", "24-3-5")
    assert _filename_matches_date("Mouse_Act_24-3-5.xlsx", "24-03-05")


def test_matching_files_falls_back_to_previous_date_when_requested_date_absent():
    files = ["Mouse_TEMP_24-03-04.xlsx", "Mouse_Act_24-03-04.xlsx"]

    assert _matching_files_for_date(files, "temp", "24-03-05") == [
        "Mouse_TEMP_24-03-04.xlsx"
    ]


def test_empty_opto_metadata_file_reports_missing_stimulation_records(tmp_path):
    metadata_path = tmp_path / "opto.csv"
    metadata_path.write_text(
        "Stim onset (hh:mm:ss),Start time (hh:mm:ss),Duration of test (min)\n",
        encoding="utf-8",
    )

    class _Value:
        def get(self):
            return str(metadata_path)

        def set(self, _value):
            pass

    app = types.SimpleNamespace(
        file_path=_Value(),
        label_settings_button=object(),
        data_selection_frame=types.SimpleNamespace(
            selected_column_var=_Value(),
            column_dropdown={},
        ),
        temp_and_act_start_time_var=_Value(),
    )

    with pytest.raises(ValueError, match="no stimulation records"):
        TelemetryAssociatedFileLocator(app).handle_opto_data_file()
