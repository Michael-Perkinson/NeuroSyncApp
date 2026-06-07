from __future__ import annotations

from src.core.app_settings_manager import AppSettingsManager


def test_app_settings_manager_instantiates_without_gui_state():
    manager = AppSettingsManager(app_type="telemetry_photom_opto")

    assert manager.display_duration_box_var is True
    assert manager.num_instances_box_var is True


def test_app_settings_manager_applies_boolean_settings_without_tk_vars():
    manager = AppSettingsManager(app_type="align_photometry_and_behaviour_app")

    manager.apply_settings(
        {
            "display_duration_box_var": False,
            "num_instances_box_var": "true",
        }
    )

    assert manager.display_duration_box_var is False
    assert manager.num_instances_box_var is True


def test_align_config_construction_no_longer_requires_widget_instances():
    manager = AppSettingsManager(app_type="align_photometry_and_behaviour_app")

    config = manager.construct_config({})

    assert config["display_duration_box_var"] is True
    assert config["num_instances_box_var"] is True
    assert "selected_photometry_line_width" in config


def test_raw_settings_reject_invalid_last_run_dfer_option():
    manager = AppSettingsManager(app_type="raw_photometry_processing")

    manager.apply_settings({"last_run_dfer_option": "9"})

    assert manager.last_run_dfer_option == "1"


def test_raw_settings_ignore_legacy_dfer_option_keys():
    manager = AppSettingsManager(app_type="raw_photometry_processing")

    manager.apply_settings(
        {
            "selected_dfer_option": "4",
            "last_dfer_option": "4",
        }
    )

    assert manager.last_run_dfer_option == "1"
