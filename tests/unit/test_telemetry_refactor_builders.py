"""Unit tests for telemetry refactor helpers and settings persistence."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pandas as pd

from src.features.telemetry_alignment.io.static_input_builders import (
    build_opto_cluster_entries,
    build_photometry_cluster_entries,
    normalize_static_settings,
)
from src.features.telemetry_alignment.io.static_settings_store import (
    TelemetryStaticSettingsStore,
)


class _DummyApp:
    pass


def _repo_local_tmp_dir(name: str) -> Path:
    root = Path("tmp_test_artifacts") / f"{name}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_static_settings_roundtrip_with_pathlib(monkeypatch):
    config_dir = _repo_local_tmp_dir("telemetry_refactor_builders")
    monkeypatch.setenv("NEUROSYNCAPP_CONFIG_DIR", str(config_dir))
    controller = TelemetryStaticSettingsStore(_DummyApp())

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

    controller.save_static_inputs(df)
    loaded = controller.load_static_inputs()

    assert loaded["clusters"]["3 Peaks_cluster"]["pre_cluster_time"] == "45"
    assert loaded["clusters"]["3 Peaks_cluster"]["post_cluster_time"] == "90"
    assert loaded["clusters"]["3 Peaks_cluster"]["bin_size"] == "5"

    assert loaded["stimulations"]["5_stim_cluster"]["pre_stim_time"] == "30"
    assert loaded["stimulations"]["5_stim_cluster"]["post_stim_time"] == "60"
    assert loaded["stimulations"]["5_stim_cluster"]["bin_size"] == "10"


def test_build_photometry_cluster_entries_uses_stored_values():
    cluster_dict = {
        (0, 2, 3): {
            "name": "3 Peaks_cluster_1",
            "peaks": [0.1, 0.3, 0.5],
            "alignment_index": 1,
        }
    }
    time_column = pd.Series([0.0, 1.0, 2.0, 3.0])
    settings = normalize_static_settings(
        {
            "clusters": {
                "3 Peaks_cluster": {
                    "pre_cluster_time": "20",
                    "post_cluster_time": "40",
                    "bin_size": "5",
                }
            }
        }
    )

    entries, used_defaults = build_photometry_cluster_entries(
        cluster_dict, time_column, settings
    )
    entry = entries["3 Peaks_cluster_1"]

    assert used_defaults is False
    assert entry["pre_cluster_time"] == "20"
    assert entry["post_cluster_time"] == "40"
    assert entry["bin_size"] == "5"
    assert entry["start_time"] == 0.0
    assert entry["end_time"] == 2.0


def test_build_opto_cluster_entries_uses_defaults_when_missing():
    stim_timings = [(4, [(1.0, 1.5), (2.0, 2.5)])]
    settings = normalize_static_settings({"stimulations": {}})

    entries, used_defaults = build_opto_cluster_entries(stim_timings, settings)
    entry = entries["4_stim_cluster_1"]

    assert used_defaults is True
    assert entry["pre_stim_time"] == "60"
    assert entry["post_stim_time"] == "60"
    assert entry["bin_size"] == "10"
    assert entry["stim_start"] == 1.0
    assert entry["stim_end"] == 2.5
