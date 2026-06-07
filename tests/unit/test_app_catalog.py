import pytest

from src.app.catalog import (
    DEFAULT_APP_ID,
    get_app_definition,
    iter_app_definitions,
)


def test_app_catalog_contains_expected_default_app():
    app_ids = [definition.app_id for definition in iter_app_definitions()]
    assert DEFAULT_APP_ID in app_ids
    assert "telemetry_photom_opto" in app_ids
    assert "combine_data" in app_ids


def test_get_app_definition_rejects_unknown_app_id():
    with pytest.raises(ValueError, match="Unknown app id"):
        get_app_definition("not-a-real-tool")


def test_raw_analysis_is_the_first_qt_supported_tool():
    raw_analysis = get_app_definition("raw_analysis")
    assert raw_analysis.qt_supported is True
    assert raw_analysis.class_name == "RawPhotometryProcessingQt"


def test_behaviour_alignment_is_qt_supported():
    behaviour_app = get_app_definition("single_animal")
    assert behaviour_app.qt_supported is True
    assert behaviour_app.class_name == "DataProcessingSingleInstance"


def test_telemetry_alignment_is_qt_supported():
    telemetry_app = get_app_definition("telemetry_photom_opto")
    assert telemetry_app.qt_supported is True
    assert telemetry_app.class_name == "TelemetryPhotomOptoProcessingApp"
