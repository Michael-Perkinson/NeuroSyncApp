from pathlib import Path
import shutil
import uuid

from src.shared.persistence.dashboard_state import (
    get_state_file_path,
    load_state,
    save_state,
)
from src.shared.persistence.settings_store import (
    load_settings,
    save_settings,
    settings_file_path,
)


def _make_local_tmp_dir(name: str) -> Path:
    path = Path("tmp_test_artifacts") / f"{name}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_settings_store_uses_user_config_dir_override(monkeypatch):
    tmp_dir = _make_local_tmp_dir("settings_store")
    monkeypatch.setenv("NEUROSYNCAPP_CONFIG_DIR", str(tmp_dir))

    save_settings("telemetry_photom_opto", {"selected_column_name": "signal"})
    path = settings_file_path("telemetry_photom_opto")

    assert path.exists()
    assert path.is_relative_to(tmp_dir)
    assert load_settings("telemetry_photom_opto") == {
        "selected_column_name": "signal"
    }
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_dashboard_state_uses_user_config_dir_override(monkeypatch):
    tmp_dir = _make_local_tmp_dir("dashboard_state")
    monkeypatch.setenv("NEUROSYNCAPP_CONFIG_DIR", str(tmp_dir))

    save_state("telemetry_photom_opto")
    path = Path(get_state_file_path())

    assert path.exists()
    assert path.is_relative_to(tmp_dir)
    assert load_state() == "telemetry_photom_opto"
    shutil.rmtree(tmp_dir, ignore_errors=True)
