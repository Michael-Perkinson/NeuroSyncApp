"""Pure builders for telemetry cluster/stimulation data dictionaries."""

from __future__ import annotations


def normalize_static_settings(settings: dict | None) -> dict:
    """Normalize persisted static settings into canonical dict shape."""
    settings = settings or {}
    normalized = {"clusters": {}, "stimulations": {}}

    def _normalize_bucket(raw_bucket, key_pre, key_post):
        bucket = {}
        for name, value in (raw_bucket or {}).items():
            pre_val = ""
            post_val = ""
            bin_val = ""

            if isinstance(value, dict):
                pre_val = value.get(key_pre, value.get("pre_time", ""))
                post_val = value.get(key_post, value.get("post_time", ""))
                bin_val = value.get("bin_size", "")
            elif isinstance(value, (list, tuple)) and len(value) >= 3:
                pre_val, post_val, bin_val = value[0], value[1], value[2]

            bucket[name] = {
                key_pre: str(pre_val),
                key_post: str(post_val),
                "bin_size": str(bin_val),
            }
        return bucket

    normalized["clusters"] = _normalize_bucket(
        settings.get("clusters"), "pre_cluster_time", "post_cluster_time"
    )
    normalized["stimulations"] = _normalize_bucket(
        settings.get("stimulations"), "pre_stim_time", "post_stim_time"
    )
    return normalized


def build_photometry_cluster_entries(
    cluster_dict,
    time_column,
    normalized_settings,
    default_pre: str = "60",
    default_post: str = "60",
    default_bin: str = "10",
):
    """Build per-cluster entries for photometry clusters."""
    cluster_settings = normalized_settings.get("clusters", {})
    entries = {}
    used_default_values = False

    for (start_index, end_index, _peak_count), cluster_data in cluster_dict.items():
        peak_times = cluster_data["peaks"]
        alignment_index = cluster_data.get("alignment_index", -1)
        cluster_name = cluster_data["name"]

        start_time = time_column.iloc[start_index]
        end_time = time_column.iloc[end_index]

        cluster_base_name = cluster_name.rsplit("_", 1)[0]
        stored_inputs = cluster_settings.get(cluster_base_name)

        if stored_inputs and any(
            str(stored_inputs.get(key, "")) != ""
            for key in ("pre_cluster_time", "post_cluster_time", "bin_size")
        ):
            pre_cluster_time = stored_inputs["pre_cluster_time"]
            post_cluster_time = stored_inputs["post_cluster_time"]
            bin_size = stored_inputs["bin_size"]
        else:
            pre_cluster_time = default_pre
            post_cluster_time = default_post
            bin_size = default_bin
            used_default_values = True

        entries[cluster_name] = {
            "name": cluster_name,
            "cluster_size": len(peak_times),
            "pre_cluster_time": pre_cluster_time,
            "post_cluster_time": post_cluster_time,
            "bin_size": bin_size,
            "start_time": start_time,
            "end_time": end_time,
            "alignment_index": alignment_index,
            "peaks": peak_times,
        }

    return entries, used_default_values


def build_opto_cluster_entries(
    stim_timings,
    normalized_settings,
    default_pre: str = "60",
    default_post: str = "60",
    default_bin: str = "10",
):
    """Build per-cluster entries for optogenetic stim clusters."""
    stim_settings = normalized_settings.get("stimulations", {})
    entries = {}
    used_default_values = False
    cluster_count = {}

    for cluster_size, timings in stim_timings:
        if cluster_size not in cluster_count:
            cluster_count[cluster_size] = 0
        cluster_count[cluster_size] += 1

        cluster_suffix = f"_cluster_{cluster_count[cluster_size]}"
        cluster_name = f"{cluster_size}_stim{cluster_suffix}"
        base_cluster_name = cluster_name.rsplit("_", 1)[0]

        stim_start = timings[0][0]
        stim_end = timings[-1][1]

        stored_inputs = stim_settings.get(cluster_name) or stim_settings.get(
            base_cluster_name
        )
        if stored_inputs and any(
            str(stored_inputs.get(key, "")) != ""
            for key in ("pre_stim_time", "post_stim_time", "bin_size")
        ):
            pre_stim_time = stored_inputs["pre_stim_time"]
            post_stim_time = stored_inputs["post_stim_time"]
            bin_size = stored_inputs["bin_size"]
        else:
            pre_stim_time = default_pre
            post_stim_time = default_post
            bin_size = default_bin
            used_default_values = True

        entries[cluster_name] = {
            "name": cluster_name,
            "pre_stim_time": pre_stim_time,
            "post_stim_time": post_stim_time,
            "bin_size": bin_size,
            "stim_start": stim_start,
            "stim_end": stim_end,
            "cluster_size": cluster_size,
        }

    return entries, used_default_values
