"""Controller for telemetry static settings and data-dict population."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from src.processing.telemetry_data_builder import (
    build_opto_cluster_entries,
    build_photometry_cluster_entries,
    normalize_static_settings,
)

logger = logging.getLogger(__name__)


class TelemetrySettingsController:
    """Owns settings persistence, update orchestration, and data-dict builders."""

    CLUSTER_SETTINGS_PATH = Path("cluster_static_settings.json")
    STIM_SETTINGS_PATH = Path("stim_static_settings.json")

    def __init__(self, app):
        self.app = app

    def save_inputs(self) -> None:
        selected_cluster_label = self.app.static_inputs_frame.selected_behaviour.get().strip()

        pre_time = self.app.static_inputs_frame.pre_behaviour_time_entry.get()
        post_time = self.app.static_inputs_frame.post_behaviour_time_entry.get()
        bin_size = self.app.static_inputs_frame.bin_size_entry.get()

        updated_clusters = set()
        is_stim_update = "stim" in selected_cluster_label.lower()

        if selected_cluster_label in {"All Clusters", "All Stims"}:
            for _, clusters in self.app.data_dict.items():
                for cluster_name, data in clusters.items():
                    if is_stim_update:
                        if "stim" in cluster_name:
                            data["pre_stim_time"] = pre_time
                            data["post_stim_time"] = post_time
                            data["bin_size"] = bin_size
                            updated_clusters.add(cluster_name)
                    else:
                        data["pre_cluster_time"] = pre_time
                        data["post_cluster_time"] = post_time
                        data["bin_size"] = bin_size
                        updated_clusters.add(cluster_name)

        elif is_stim_update:
            match = re.search(r"(\d+) stim", selected_cluster_label)
            if match:
                stim_count = int(match.group(1))
                for _, clusters in self.app.data_dict.items():
                    for cluster_name, data in clusters.items():
                        if f"{stim_count}_stim" in cluster_name:
                            data["pre_stim_time"] = pre_time
                            data["post_stim_time"] = post_time
                            data["bin_size"] = bin_size
                            updated_clusters.add(cluster_name)
        else:
            match = re.search(r"(\d+) Peak", selected_cluster_label)
            if match:
                num_peaks_in_selected_cluster = int(match.group(1))
                for _, clusters in self.app.data_dict.items():
                    for cluster_name, data in clusters.items():
                        if f"{num_peaks_in_selected_cluster} Peaks" in cluster_name:
                            data["pre_cluster_time"] = pre_time
                            data["post_cluster_time"] = post_time
                            data["bin_size"] = bin_size
                            updated_clusters.add(cluster_name)

        df = self.app.data_dict_to_df(self.app.data_dict)
        self.update_cluster_inputs()
        if self.app.temp_data is not None and self.app.act_data is not None:
            self.app.precompute_all_clusters(updated_clusters)
        self.save_static_inputs(df)

    def update_cluster_inputs(self) -> None:
        if not hasattr(self.app.file_path, "get") and not self.app.file_path:
            return

        file_path_str = Path(self.app.file_path.get()).name
        pre_time = self.app.static_inputs_frame.pre_behaviour_time_entry.get()
        post_time = self.app.static_inputs_frame.post_behaviour_time_entry.get()
        bin_size = self.app.static_inputs_frame.bin_size_entry.get()

        selected_cluster_label = self.app.static_inputs_frame.selected_behaviour.get().strip()
        is_stim_update = "stim" in selected_cluster_label.lower()

        if is_stim_update:
            selected_stim_label = selected_cluster_label.split()[0]
        else:
            selected_peak_label = selected_cluster_label.split()[0]

        if file_path_str in self.app.data_dict:
            for cluster_name, cluster_data in self.app.data_dict[file_path_str].items():
                if is_stim_update:
                    if (
                        selected_cluster_label == "All Stims"
                        or (selected_stim_label == "All" and "stim" in cluster_name)
                        or (f"{selected_stim_label}_stim" in cluster_name)
                    ):
                        cluster_data["pre_stim_time"] = pre_time
                        cluster_data["post_stim_time"] = post_time
                        cluster_data["bin_size"] = bin_size

                        for item in self.app.table_treeview.get_children():
                            if self.app.table_treeview.set(item, "number_of_peaks") == cluster_name:
                                self.app.table_treeview.set(item, "pre_cluster_time", pre_time)
                                self.app.table_treeview.set(item, "post_cluster_time", post_time)
                                self.app.table_treeview.set(item, "bin_size", bin_size)
                else:
                    if (
                        selected_cluster_label == "All Clusters"
                        or (selected_peak_label == "All" and "Peak" in cluster_name)
                        or (f"{selected_peak_label} Peak" in cluster_name)
                    ):
                        cluster_data["pre_cluster_time"] = pre_time
                        cluster_data["post_cluster_time"] = post_time
                        cluster_data["bin_size"] = bin_size

                        for item in self.app.table_treeview.get_children():
                            if self.app.table_treeview.set(item, "number_of_peaks") == cluster_name:
                                self.app.table_treeview.set(item, "pre_cluster_time", pre_time)
                                self.app.table_treeview.set(item, "post_cluster_time", post_time)
                                self.app.table_treeview.set(item, "bin_size", bin_size)

        self.app.table_treeview.update_idletasks()
        if (
            getattr(self.app, "date", None)
            and (self.app.view_state.temp_and_act_start_time or "").strip()
            and getattr(self.app, "nighttime_periods", None)
        ):
            self.app.annotate_clusters_with_time_period()

    def save_static_inputs(self, df) -> None:
        data = {"clusters": {}, "stimulations": {}}

        for _, row in df.iterrows():
            cluster_name = row["Cluster Name"]
            base_cluster_name = cluster_name.rsplit("_", 1)[0]

            pre_time = (
                row["pre_stim_time"]
                if "stim" in cluster_name
                else row["pre_cluster_time"]
            )
            post_time = (
                row["post_stim_time"]
                if "stim" in cluster_name
                else row["post_cluster_time"]
            )
            bin_size = row["bin_size"]

            if "stim" in cluster_name:
                data["stimulations"][base_cluster_name] = [pre_time, post_time, bin_size]
            else:
                data["clusters"][base_cluster_name] = [pre_time, post_time, bin_size]

        self.CLUSTER_SETTINGS_PATH.write_text(
            json.dumps(data["clusters"]), encoding="utf-8"
        )
        self.STIM_SETTINGS_PATH.write_text(
            json.dumps(data["stimulations"]), encoding="utf-8"
        )

    def load_static_inputs(self) -> dict:
        settings = {"clusters": {}, "stimulations": {}}

        def load_data(path: Path, data_key: str) -> None:
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    settings[data_key] = data
                except Exception as exc:
                    logger.warning("Error reading JSON file %s: %s", path, exc)
            else:
                path.write_text("{}", encoding="utf-8")

        load_data(self.CLUSTER_SETTINGS_PATH, "clusters")
        load_data(self.STIM_SETTINGS_PATH, "stimulations")
        return normalize_static_settings(settings)

    def populate_data_dict(self, replace_existing: bool = False) -> None:
        file_path_str = Path(self.app.file_path.get()).name

        if replace_existing or file_path_str not in self.app.data_dict:
            self.app.data_dict[file_path_str] = {}

        used_defaults = False
        if self.app.data_type == "photometry":
            used_defaults = self.populate_photometry_data_dict(file_path_str)
        elif self.app.data_type == "optogenetics":
            used_defaults = self.populate_opto_data_dict(file_path_str)

        self.app.used_default_values = used_defaults
        if self.app.data_type in {"photometry", "optogenetics"} and used_defaults:
            logger.debug("Using default values for cluster/stim settings.")
            df = self.app.data_dict_to_df(self.app.data_dict)
            self.save_static_inputs(df)

    def populate_photometry_data_dict(self, file_path_str: str) -> bool:
        normalized_settings = self.load_static_inputs()
        entries, used_default_values = build_photometry_cluster_entries(
            self.app.cluster_dict,
            self.app.time_column,
            normalized_settings,
        )
        self.app.data_dict[file_path_str].update(entries)
        return used_default_values

    def populate_opto_data_dict(self, file_path_str: str) -> bool:
        normalized_settings = self.load_static_inputs()
        entries, used_default_values = build_opto_cluster_entries(
            self.app.stim_timings,
            normalized_settings,
        )
        self.app.data_dict[file_path_str].update(entries)
        return used_default_values
