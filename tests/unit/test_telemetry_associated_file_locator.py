from __future__ import annotations

from src.features.telemetry_alignment.io.associated_file_locator import (
    _filename_matches_date,
    _matching_files_for_date,
)


def test_filename_date_match_accepts_zero_padded_month_and_day():
    assert _filename_matches_date("Mouse_TEMP_24-03-05.xlsx", "24-3-5")
    assert _filename_matches_date("Mouse_Act_24-3-5.xlsx", "24-03-05")


def test_matching_files_falls_back_to_previous_date_when_requested_date_absent():
    files = ["Mouse_TEMP_24-03-04.xlsx", "Mouse_Act_24-03-04.xlsx"]

    assert _matching_files_for_date(files, "temp", "24-03-05") == [
        "Mouse_TEMP_24-03-04.xlsx"
    ]
