from __future__ import annotations

from pathlib import Path
import shutil
import uuid

import pandas as pd

from src.features.telemetry_alignment.io.static_settings_store import (
    TelemetryStaticSettingsStore,
)


class _DummyApp:
    pass


def test_static_settings_store_writes_to_user_config_dir(monkeypatch):
    tmp_dir = Path("tmp_test_artifacts") / f"static_store_{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NEUROSYNCAPP_CONFIG_DIR", str(tmp_dir))
    store = TelemetryStaticSettingsStore(_DummyApp())

    df = pd.DataFrame(
        [
            {
                "Cluster Name": "3 Peaks_cluster_1",
                "pre_cluster_time": "45",
                "post_cluster_time": "90",
                "pre_stim_time": "",
                "post_stim_time": "",
                "bin_size": "5",
            },
            {
                "Cluster Name": "5_stim_cluster_1",
                "pre_cluster_time": "",
                "post_cluster_time": "",
                "pre_stim_time": "30",
                "post_stim_time": "60",
                "bin_size": "10",
            },
        ]
    )

    store.save_static_inputs(df)
    loaded = store.load_static_inputs()

    cluster_path = tmp_dir / "telemetry_alignment" / "cluster_static_settings.json"
    stim_path = tmp_dir / "telemetry_alignment" / "stim_static_settings.json"

    assert cluster_path.exists()
    assert stim_path.exists()
    assert loaded["clusters"]["3 Peaks_cluster"]["pre_cluster_time"] == "45"
    assert loaded["stimulations"]["5_stim_cluster"]["post_stim_time"] == "60"
    shutil.rmtree(tmp_dir, ignore_errors=True)
