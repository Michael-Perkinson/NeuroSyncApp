from __future__ import annotations

import pytest

from src.features.behaviour_alignment.io.behaviour_file_selector import (
    BehaviourFileSelector,
)
from src.gui.shared.messages_and_errors import (
    describe_exception,
    format_action_error,
)
from src.processing.image_export import build_image_export_request


def test_key_error_is_described_as_a_missing_required_column():
    message = describe_exception(KeyError("CH1-470"))

    assert message == "The selected file is missing the required column 'CH1-470'."


def test_action_error_contains_summary_cause_and_recovery():
    message = format_action_error(
        "The file could not be loaded",
        KeyError("CH1-470"),
        "Select the original raw CSV.",
    )

    assert "The file could not be loaded." in message
    assert "missing the required column 'CH1-470'" in message
    assert "Select the original raw CSV." in message


def test_behaviour_file_is_not_marked_parsed_after_failed_import():
    class ManualSessionService:
        @staticmethod
        def parse_manual_data(_file_path):
            return False

    class App:
        is_file_parsed = True
        manual_session_service = ManualSessionService()

    app = App()
    BehaviourFileSelector(app).process_file("wrong.csv")

    assert app.is_file_parsed is False


@pytest.mark.parametrize(
    ("height", "width", "dpi", "expected"),
    [
        ("10", "", "300", "both image width and height"),
        ("ten", "12", "300", "must be valid numbers"),
        ("10", "12", "abc", "positive whole number"),
        ("-10", "12", "300", "greater than zero"),
    ],
)
def test_invalid_image_export_settings_are_explained(height, width, dpi, expected):
    with pytest.raises(ValueError, match=expected):
        build_image_export_request(height, width, "png", dpi, "Full Trace", "")


def test_blank_image_dimensions_use_automatic_size():
    request = build_image_export_request("", "", "png", "", "Full Trace", "")

    assert request.axis_height_cm is None
    assert request.axis_width_cm is None
    assert request.dpi == 300
