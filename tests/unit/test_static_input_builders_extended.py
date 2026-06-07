"""Extended tests for static_input_builders — covers default and stored-value branches."""
from __future__ import annotations

import pandas as pd
import pytest

from src.features.telemetry_alignment.io.static_input_builders import (
    build_opto_cluster_entries,
    build_photometry_cluster_entries,
)


def _minimal_cluster_dict(cluster_name="1 Peak in Cluster_1"):
    """Return a minimal cluster_dict for one single-peak cluster."""
    return {
        (0, 4, 1): {
            "peaks": [1.0, 2.0],
            "alignment_index": 0,
            "name": cluster_name,
        }
    }


def _time_column(n=5):
    return pd.Series([float(i) for i in range(n)])


class TestBuildPhotometryClusterEntriesDefaults:
    """Covers the else-branch (lines 73-76): empty/missing settings → defaults."""

    def test_empty_settings_uses_defaults(self):
        cluster_dict = _minimal_cluster_dict()
        normalized = {"clusters": {}, "stimulations": {}}
        entries, used_defaults = build_photometry_cluster_entries(
            cluster_dict, _time_column(), normalized
        )
        assert used_defaults is True
        entry = next(iter(entries.values()))
        assert entry["pre_cluster_time"] == "60"
        assert entry["post_cluster_time"] == "60"
        assert entry["bin_size"] == "10"

    def test_custom_defaults_are_applied(self):
        cluster_dict = _minimal_cluster_dict()
        normalized = {"clusters": {}, "stimulations": {}}
        entries, used_defaults = build_photometry_cluster_entries(
            cluster_dict,
            _time_column(),
            normalized,
            default_pre="30",
            default_post="45",
            default_bin="5",
        )
        assert used_defaults is True
        entry = next(iter(entries.values()))
        assert entry["pre_cluster_time"] == "30"
        assert entry["post_cluster_time"] == "45"
        assert entry["bin_size"] == "5"

    def test_stored_empty_strings_still_uses_defaults(self):
        # stored_inputs with all empty-string values should fall through to defaults
        cluster_dict = _minimal_cluster_dict()
        normalized = {
            "clusters": {
                "1 Peak in Cluster": {
                    "pre_cluster_time": "",
                    "post_cluster_time": "",
                    "bin_size": "",
                }
            },
            "stimulations": {},
        }
        entries, used_defaults = build_photometry_cluster_entries(
            cluster_dict, _time_column(), normalized
        )
        assert used_defaults is True


class TestBuildPhotometryClusterEntriesStoredValues:
    """Already partially covered — verify stored values are NOT overridden."""

    def test_stored_values_win_over_defaults(self):
        cluster_dict = _minimal_cluster_dict()
        normalized = {
            "clusters": {
                "1 Peak in Cluster": {
                    "pre_cluster_time": "90",
                    "post_cluster_time": "120",
                    "bin_size": "15",
                }
            },
            "stimulations": {},
        }
        entries, used_defaults = build_photometry_cluster_entries(
            cluster_dict, _time_column(), normalized
        )
        assert used_defaults is False
        entry = next(iter(entries.values()))
        assert entry["pre_cluster_time"] == "90"
        assert entry["post_cluster_time"] == "120"
        assert entry["bin_size"] == "15"


class TestBuildOptoClusterEntriesStoredValues:
    """Covers the stored-values branch (lines 125-127) in build_opto_cluster_entries."""

    def _stim_timings(self, cluster_size=2):
        return [(cluster_size, [(1.0, 1.5), (2.0, 2.5)])]

    def test_stored_values_used_when_present(self):
        stim_timings = self._stim_timings(2)
        # cluster_name would be "2_stim_cluster_1", base is "2_stim_cluster"
        normalized = {
            "clusters": {},
            "stimulations": {
                "2_stim_cluster": {
                    "pre_stim_time": "45",
                    "post_stim_time": "75",
                    "bin_size": "20",
                }
            },
        }
        entries, used_defaults = build_opto_cluster_entries(stim_timings, normalized)
        assert used_defaults is False
        entry = next(iter(entries.values()))
        assert entry["pre_stim_time"] == "45"
        assert entry["post_stim_time"] == "75"
        assert entry["bin_size"] == "20"

    def test_exact_cluster_name_match_in_stored_values(self):
        stim_timings = self._stim_timings(3)
        # Use the full cluster_name "3_stim_cluster_1"
        normalized = {
            "clusters": {},
            "stimulations": {
                "3_stim_cluster_1": {
                    "pre_stim_time": "10",
                    "post_stim_time": "20",
                    "bin_size": "5",
                }
            },
        }
        entries, used_defaults = build_opto_cluster_entries(stim_timings, normalized)
        assert used_defaults is False
        entry = next(iter(entries.values()))
        assert entry["pre_stim_time"] == "10"

    def test_stored_values_not_used_when_all_empty(self):
        stim_timings = self._stim_timings(2)
        normalized = {
            "clusters": {},
            "stimulations": {
                "2_stim_cluster": {
                    "pre_stim_time": "",
                    "post_stim_time": "",
                    "bin_size": "",
                }
            },
        }
        entries, used_defaults = build_opto_cluster_entries(stim_timings, normalized)
        assert used_defaults is True


class TestBuildOptoClusterEntriesDefaults:
    """Already partially covered — confirm defaults path still works."""

    def test_empty_settings_gives_defaults(self):
        stim_timings = [(1, [(0.5, 1.0)])]
        normalized = {"clusters": {}, "stimulations": {}}
        entries, used_defaults = build_opto_cluster_entries(stim_timings, normalized)
        assert used_defaults is True
        entry = next(iter(entries.values()))
        assert entry["pre_stim_time"] == "60"
        assert entry["post_stim_time"] == "60"
        assert entry["bin_size"] == "10"
