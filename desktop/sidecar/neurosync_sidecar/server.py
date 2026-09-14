from __future__ import annotations

import importlib.util
import json
import logging
import math
import platform
import re
import sys
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np
import pandas as pd

# The debug Tauri host starts this module with desktop/sidecar as its working
# directory. Add the repository root so the headless sidecar can use the same
# Qt-free DFer/PFer implementation as the existing application.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if PROJECT_ROOT.is_dir() and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from . import (  # noqa: E402
    APP_VERSION,
    MAX_FRAME_BYTES,
    MAX_POINTS_ACROSS_PANELS,
    MAX_POINTS_PER_SERIES,
    PROTOCOL_VERSION,
    SIDECAR_VERSION,
)
from .protocol import FrameError, failure, read_frame, success, write_frame  # noqa: E402

logger = logging.getLogger(__name__)
SCIENTIFIC_MODULES = (
    "numpy",
    "pandas",
    "scipy",
    "matplotlib",
    "openpyxl",
    "xlsxwriter",
    "platformdirs",
)
OPTION_TITLES = [
    "Option 1: Good noise correction and bleach correction",
    "Option 2: Assumes shifts in 465 baseline are independent of activity",
    "Option 3: No noise correction",
    "Option 4: No noise correction, no activity-dependent baseline correction",
]


def _normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(column).strip().lstrip("#").strip() for column in frame.columns]
    return frame


def _sample_indices(length: int, maximum: int) -> list[int]:
    if length <= 0:
        return []
    if length <= maximum:
        return list(range(length))
    if maximum <= 1:
        return [0]
    return [round(index * (length - 1) / (maximum - 1)) for index in range(maximum)]


def _json_values(values: Any, indices: list[int] | None = None) -> list[float | None]:
    array = np.asarray(values, dtype=float)
    selected = array if indices is None else array[indices]
    return [float(value) if np.isfinite(value) else None for value in selected]


def _safe_path_part(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", value).strip(" .")
    return cleaned or "recording"


def _strip_data_suffix(stem: str) -> str:
    for suffix in ("_Dual_Data", "_Data"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


class ProtocolServer:
    def __init__(self, diagnostic_stream: Any = sys.stderr) -> None:
        self.negotiated = False
        self.sequence = 0
        self.stopping = False
        self.diagnostic_stream = diagnostic_stream

        self.loaded_path: Path | None = None
        self.loaded_file_type: str | None = None
        self.raw_context: dict[str, Any] | None = None
        self.options_data: dict[str, Any] | None = None
        self.window: tuple[str, str] = ("", "")
        self.dfer_csv: Path | None = None
        self.pfer_csv: Path | None = None
        self.pfer_stats: list[Path] = []

    def dispatch(self, request: Any) -> dict[str, Any]:
        if not isinstance(request, dict):
            return failure(None, "invalid_request", "A request must be a JSON object.", "change_input")
        request_id = request.get("id")
        if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
            return failure(None, "invalid_request_id", "The request ID is missing or invalid.", "change_input")
        method = request.get("method")
        params = request.get("params", {})
        if not isinstance(method, str) or not isinstance(params, dict):
            return failure(request_id, "invalid_request", "The method or parameters are invalid.", "change_input")
        if method == "protocol.negotiate":
            return self._negotiate(request_id, params)
        if not self.negotiated:
            return failure(request_id, "negotiation_required", "Protocol negotiation must complete first.", "restart_sidecar")
        if request.get("protocol_version") != PROTOCOL_VERSION:
            return failure(
                request_id,
                "protocol_mismatch",
                "The host and sidecar protocol versions do not match.",
                "none",
                {"supported_versions": [PROTOCOL_VERSION]},
            )
        handlers = {
            "sidecar.ping": self._ping,
            "sidecar.version": self._version,
            "plot.sample": self._sample_plot,
            "raw.load_file": self._load_file,
            "raw.generate_options": self._generate_options,
            "raw.preview_option": self._preview_option,
            "raw.run_dfer": self._run_dfer,
            "raw.run_pfer": self._run_pfer,
            "raw.save_plot": self._save_plot,
            "sidecar.shutdown": self._shutdown,
        }
        handler = handlers.get(method)
        if handler is None:
            return failure(
                request_id,
                "unknown_method",
                "The requested operation is not supported.",
                "change_input",
                {"method": method},
            )
        try:
            return handler(request_id, params)
        except FileNotFoundError as error:
            return failure(request_id, "file_not_found", str(error), "change_input")
        except (OSError, ValueError, TypeError) as error:
            return failure(request_id, "invalid_input", str(error), "change_input")
        except Exception as error:
            logger.exception("Unhandled sidecar operation: %s", method)
            self._log(f"Unhandled {method}: {type(error).__name__}: {error}")
            return failure(
                request_id,
                "internal_error",
                "The sidecar could not complete the request.",
                "restart_sidecar",
            )

    def _negotiate(self, request_id: str, params: dict[str, Any]) -> dict[str, Any]:
        versions = params.get("supported_versions")
        if not isinstance(versions, list) or PROTOCOL_VERSION not in versions:
            return failure(
                request_id,
                "protocol_mismatch",
                "No compatible protocol version is available.",
                "none",
                {"supported_versions": [PROTOCOL_VERSION]},
            )
        self.negotiated = True
        return success(
            request_id,
            {
                "protocol_version": PROTOCOL_VERSION,
                "sidecar": {"name": "neurosyncapp-sidecar", "version": SIDECAR_VERSION, "app_version": APP_VERSION},
                "capabilities": [
                    "ping",
                    "version",
                    "sample_plot",
                    "raw_photometry",
                    "plot.save_image",
                    "shutdown",
                ],
                "limits": {
                    "max_frame_bytes": MAX_FRAME_BYTES,
                    "max_points_per_series": MAX_POINTS_PER_SERIES,
                    "max_points_across_panels": MAX_POINTS_ACROSS_PANELS,
                },
            },
        )

    def _ping(self, request_id: str, _params: dict[str, Any]) -> dict[str, Any]:
        self.sequence += 1
        return success(request_id, {"status": "ready", "protocol_version": PROTOCOL_VERSION, "sequence": self.sequence})

    def _version(self, request_id: str, _params: dict[str, Any]) -> dict[str, Any]:
        available = {name: importlib.util.find_spec(name) is not None for name in SCIENTIFIC_MODULES}
        return success(
            request_id,
            {
                "sidecar_version": SIDECAR_VERSION,
                "app_version": APP_VERSION,
                "python_version": platform.python_version(),
                "protocol_version": PROTOCOL_VERSION,
                "scientific_runtime": available,
            },
        )

    def _sample_plot(self, request_id: str, params: dict[str, Any]) -> dict[str, Any]:
        sample_count = params.get("sample_count", 48_000)
        max_points = params.get("max_points", 900)
        viewport = params.get(
            "viewport",
            {"start_index": 0, "end_index": sample_count - 1 if isinstance(sample_count, int) else 0},
        )
        if not isinstance(sample_count, int) or isinstance(sample_count, bool) or not 2 <= sample_count <= 1_000_000:
            return failure(request_id, "invalid_sample_count", "Sample count must be between 2 and 1,000,000.", "change_input")
        if not isinstance(max_points, int) or isinstance(max_points, bool) or not 2 <= max_points <= MAX_POINTS_PER_SERIES:
            return failure(request_id, "invalid_max_points", "Display points must be between 2 and 10,000 per series.", "change_input")
        if not isinstance(viewport, dict):
            return failure(request_id, "invalid_viewport", "The viewport is invalid.", "change_input")
        start, end = viewport.get("start_index"), viewport.get("end_index")
        if not isinstance(start, int) or not isinstance(end, int) or isinstance(start, bool) or isinstance(end, bool) or not 0 <= start < end < sample_count:
            return failure(request_id, "invalid_viewport", "Viewport indices must describe a valid increasing range.", "change_input")
        displayed = min(max_points, end - start + 1)
        indices = [start + round(i * (end - start) / (displayed - 1)) for i in range(displayed)]
        x = [round(index / 100, 6) for index in indices]
        values = [round(0.32 * math.sin(index / 1300) + 0.09 * math.sin(index / 109), 6) for index in indices]
        reference = [round(0.12 * math.cos(index / 1600) + 0.04 * math.sin(index / 83), 6) for index in indices]
        common = {"sample_indices": indices, "x": x, "unit": "a.u."}
        return success(
            request_id,
            {
                "plot_id": "gate0.sample.trace",
                "title": "Bounded diagnostic trace",
                "x_axis": {"label": "Elapsed time", "unit": "s"},
                "sample_count": sample_count,
                "viewport": {"start_index": start, "end_index": end},
                "display_reduced": displayed < end - start + 1,
                "decimation": "uniform-index-v1",
                "series": [
                    {"id": "sample.signal.465", "signal_id": "signal-465", "label": "465 nm signal", **common, "y": values},
                    {"id": "sample.reference.405", "signal_id": "reference-405", "label": "405 nm reference", **common, "y": reference},
                ],
            },
        )

    @staticmethod
    def _path_param(params: dict[str, Any], key: str) -> Path:
        value = params.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty file path.")
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        return path

    @staticmethod
    def _endpoint(value: Any, name: str) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            raise ValueError(f"{name} must be a number or null.")
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite.")
            return str(value)
        if isinstance(value, str):
            text = value.strip()
            if not text or text.lower() in ({"start", "min"} if name == "start_s" else {"end", "max"}):
                return ""
            try:
                if not math.isfinite(float(text)):
                    raise ValueError
            except ValueError as error:
                raise ValueError(f"{name} must be a number or blank.") from error
            return text
        raise ValueError(f"{name} must be a number or null.")

    @classmethod
    def _window_params(cls, params: dict[str, Any]) -> tuple[str, str]:
        window = params.get("window", {})
        if not isinstance(window, dict):
            raise ValueError("window must be an object.")
        return cls._endpoint(window.get("start_s"), "start_s"), cls._endpoint(window.get("end_s"), "end_s")

    @staticmethod
    def _source_frame(path: Path) -> tuple[str, int, pd.DataFrame]:
        from src.dfer.df_common import detect_photometry_file_type, validate_dual_df, validate_single_df

        file_type, skiprows = detect_photometry_file_type(path)
        frame = pd.read_csv(path, skiprows=skiprows, index_col=False, low_memory=False)
        if file_type == "single":
            validate_single_df(frame)
        else:
            validate_dual_df(frame)
        return file_type, skiprows, frame

    @staticmethod
    def _plot_payload(
        plot_id: str,
        title: str,
        x_values: Any,
        definitions: list[tuple[str, str, str, str, Any]],
        sample_count: int | None = None,
        x_unit: str = "s",
    ) -> dict[str, Any]:
        x_array = np.asarray(x_values, dtype=float)
        total = len(x_array)
        per_series_limit = max(2, min(MAX_POINTS_PER_SERIES, MAX_POINTS_ACROSS_PANELS // max(1, len(definitions))))
        indices = _sample_indices(total, per_series_limit)
        series: list[dict[str, Any]] = []
        for series_id, signal_id, label, unit, values in definitions:
            series.append(
                {
                    "id": series_id,
                    "signal_id": signal_id,
                    "label": label,
                    "unit": unit,
                    "sample_indices": indices,
                    "x": _json_values(x_array, indices),
                    "y": _json_values(values, indices),
                }
            )
        source_count = total if sample_count is None else sample_count
        return {
            "plot_id": plot_id,
            "title": title,
            "x_axis": {"label": "Time", "unit": x_unit},
            "sample_count": source_count,
            "viewport": {"start_index": 0, "end_index": max(0, source_count - 1)},
            "display_reduced": len(indices) < total,
            "decimation": "uniform-index-v1",
            "series": series,
        }

    def _load_file(self, request_id: str, params: dict[str, Any]) -> dict[str, Any]:
        path = self._path_param(params, "path")
        file_type, _skiprows, frame = self._source_frame(path)
        if file_type == "single":
            t_values = frame["#time(seconds)"][1:].to_numpy(dtype=float)
            signal_column = "465nm" if "465nm" in frame.columns else "490nm"
            signal_values = frame[signal_column][1:].to_numpy(dtype=float)
            reference_values = frame["405nm"][1:].to_numpy(dtype=float)
            plot = self._plot_payload(
                f"raw.{path.stem}.single",
                "Raw Data — single channel",
                t_values,
                [
                    ("raw.signal.465", signal_column, f"{signal_column} Signal", "a.u.", signal_values),
                    ("raw.reference.405", "405nm", "405nm Signal", "a.u.", reference_values),
                ],
            )
            output_folder = path.parent / "dfof_results"
            signal_columns = ["405nm", signal_column]
            signal_label = signal_column
            duration = float(t_values[-1] - t_values[0]) if len(t_values) > 1 else 0.0
        else:
            t_values = frame["TimeStamp"].astype(float).to_numpy() / 1000.0
            signal_values = frame["CH1-470"].astype(float).to_numpy()
            reference_values = frame["CH1-560"].astype(float).to_numpy()
            plot = self._plot_payload(
                f"raw.{path.stem}.dual",
                "Raw Data — dual channel",
                t_values,
                [
                    ("raw.signal.470", "470nm", "470nm Signal", "a.u.", signal_values),
                    ("raw.signal.560", "560nm", "560nm Signal", "a.u.", reference_values),
                ],
            )
            output_folder = path.parent.parent / "dfof_results"
            signal_columns = ["CH1-410", "CH1-470", "CH1-560"]
            signal_label = "470nm / 560nm"
            duration = float(t_values[-1] - t_values[0]) if len(t_values) > 1 else 0.0

        self.loaded_path = path
        self.loaded_file_type = file_type
        self.raw_context = {
            "file_path": str(path),
            "file_type": file_type,
            "signal_label": signal_label,
            "signal_columns": signal_columns,
            "output_folder": str(output_folder),
            "sample_count": int(plot["sample_count"]),
            "duration_s": duration,
            "plot": plot,
        }
        self.options_data = None
        self.window = ("", "")
        self.dfer_csv = None
        self.pfer_csv = None
        self.pfer_stats = []
        self._log(f"Loaded raw photometry file: {path}")
        return success(request_id, self.raw_context)

    def _require_loaded(self) -> Path:
        if self.loaded_path is None or self.raw_context is None:
            raise ValueError("Select a raw photometry CSV first.")
        return self.loaded_path

    def _compute_options_data(self) -> dict[str, Any]:
        path = self._require_loaded()
        from src.dfer.analysis import compute_options

        return compute_options(path, self.window[0], self.window[1])

    def _generate_options(self, request_id: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_loaded()
        self.window = self._window_params(params)
        self.options_data = self._compute_options_data()
        data = self.options_data
        return success(
            request_id,
            {
                "file_type": str(data["file_type"]),
                "signal_label": str(data.get("signal_label", "465nm")),
                "option_titles": OPTION_TITLES,
            },
        )

    def _preview_option(self, request_id: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_loaded()
        if self.options_data is None:
            self.options_data = self._compute_options_data()
        data = self.options_data
        index = params.get("index")
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(OPTION_TITLES):
            raise ValueError("Option index must be between 0 and 3.")
        dual_display = params.get("dual_display", "both")
        if dual_display not in {"both", "470", "560"}:
            raise ValueError("dual_display must be 'both', '470', or '560'.")

        if data["file_type"] == "single":
            adjustment_key = ["smooth_adj_1", "smooth_adj_2", "smooth_adj_3", "smooth_adj_4"][index]
            definitions = [
                (f"option.{index}.signal", str(data["signal_label"]), str(data["signal_label"]), "RFU", data["smooth_465"]),
                (f"option.{index}.fit", "fit", "fitted control", "RFU", data[adjustment_key]),
            ]
            plot = self._plot_payload(
                f"raw.option.{index + 1}",
                OPTION_TITLES[index],
                data["t_min"],
                definitions,
                x_unit="min",
            )
        else:
            adjustment_key = ["adj1", "adj2", "adj3", "adj4"][index]
            definitions = []
            if dual_display in {"both", "470"}:
                definitions.extend(
                    [
                        (f"option.{index}.470", "470nm", "470nm", "RFU", data["p470"]["target_smooth"]),
                        (f"option.{index}.470.fit", "470nm_fit", "470nm fitted", "RFU", data["p470"][adjustment_key]),
                    ]
                )
            if dual_display in {"both", "560"}:
                definitions.extend(
                    [
                        (f"option.{index}.560", "560nm", "560nm", "RFU", data["p560"]["target_smooth"]),
                        (f"option.{index}.560.fit", "560nm_fit", "560nm fitted", "RFU", data["p560"][adjustment_key]),
                    ]
                )
            plot = self._plot_payload(
                f"raw.option.{index + 1}",
                OPTION_TITLES[index],
                data["t_min"],
                definitions,
                x_unit="min",
            )
        return success(request_id, plot)

    @staticmethod
    def _dfer_result_plots(csv_path: Path) -> dict[str, dict[str, Any]]:
        frame = _normalise_columns(pd.read_csv(csv_path, index_col=False))
        t_min = frame["t_min"].to_numpy(dtype=float)
        if "dFoF_470" in frame.columns:
            dfof_definitions = [
                ("dfer.dfof.470", "470nm", "470nm dF/F", "a.u.", frame["dFoF_470"].to_numpy(dtype=float)),
                ("dfer.dfof.560", "560nm", "560nm dF/F", "a.u.", frame["dFoF_560"].to_numpy(dtype=float)),
            ]
            zscore_definitions = [
                ("dfer.zscore.470", "470nm", "470nm Z-score", "a.u.", frame["Z_470"].to_numpy(dtype=float)),
                ("dfer.zscore.560", "560nm", "560nm Z-score", "a.u.", frame["Z_560"].to_numpy(dtype=float)),
            ]
        else:
            dfof_definitions = [
                ("dfer.dfof.465", "465nm", "465nm dF/F", "a.u.", frame["dFoF_465"].to_numpy(dtype=float)),
                ("dfer.dfof.405", "405nm", "405nm dF/F", "a.u.", frame["dFoF_405"].to_numpy(dtype=float)),
            ]
            zscore_definitions = [
                ("dfer.zscore.465", "465nm", "465nm Z-score", "a.u.", frame["Z_465"].to_numpy(dtype=float)),
                ("dfer.zscore.405", "405nm", "405nm Z-score", "a.u.", frame["Z_405"].to_numpy(dtype=float)),
            ]
        return {
            "dfof": ProtocolServer._plot_payload(
                f"{csv_path.stem}.dfof",
                "DFer Results — dF/F",
                t_min,
                dfof_definitions,
                x_unit="min",
            ),
            "zscore": ProtocolServer._plot_payload(
                f"{csv_path.stem}.zscore",
                "DFer Results — Z-score",
                t_min,
                zscore_definitions,
                x_unit="min",
            ),
        }

    def _run_dfer(self, request_id: str, params: dict[str, Any]) -> dict[str, Any]:
        path = self._require_loaded()
        option = params.get("option")
        if not isinstance(option, str) or option not in {"1", "2", "3", "4"}:
            raise ValueError("option must be one of '1', '2', '3', or '4'.")
        self.window = self._window_params(params)
        from src.dfer.analysis import run_analysis

        self._log(f"Running DFer option {option}: {path}")
        output = run_analysis(
            path,
            w_start=self.window[0],
            w_end=self.window[1],
            analysis_path=option,
            make_plots=False,
            mode="full",
            plot_stage="final",
        )
        if not output:
            raise ValueError("DFer did not return an output CSV path.")
        self.dfer_csv = Path(output).expanduser().resolve()
        plots = self._dfer_result_plots(self.dfer_csv)
        self.pfer_csv = self.dfer_csv
        self.pfer_stats = []
        self._log(f"DFer complete: {self.dfer_csv}")
        return success(
            request_id,
            {
                "result_csv": str(self.dfer_csv),
                "output_folder": str(self.dfer_csv.parent),
                "plots": plots,
            },
        )

    @staticmethod
    def _pfer_plot(csv_path: Path, stats_paths: list[Path]) -> dict[str, Any]:
        from src.dfer.pfer_detection import signal_specs

        frame = _normalise_columns(pd.read_csv(csv_path, index_col=False))
        t_min = frame["t_min"].to_numpy(dtype=float)
        _dataset_kind, specs = signal_specs(frame)
        if len(stats_paths) != len(specs):
            raise ValueError("PFer statistics files do not match the DFer result channels.")

        definitions: list[tuple[str, str, str, str, Any]] = []
        for spec, stats_path in zip(specs, stats_paths):
            signal_name = str(spec["name"])
            signal_column = str(spec["signal_col"])
            definitions.append(
                (
                    f"pfer.trace.{signal_name}",
                    f"{signal_name}nm",
                    f"{signal_name}nm dF/F",
                    "a.u.",
                    frame[signal_column].to_numpy(dtype=float),
                )
            )
            stats = _normalise_columns(pd.read_csv(stats_path, index_col=False))
            definitions.append(
                (
                    f"pfer.peaks.{signal_name}",
                    "peak",
                    f"{signal_name}nm peaks",
                    "a.u.",
                    (stats["peak_time_min"].to_numpy(dtype=float), stats["peak_amplitude"].to_numpy(dtype=float)),
                )
            )
            definitions.append(
                (
                    f"pfer.troughs.{signal_name}",
                    "trough",
                    f"{signal_name}nm troughs",
                    "a.u.",
                    (stats["trough_time_min"].to_numpy(dtype=float), stats["trough_amplitude"].to_numpy(dtype=float)),
                )
            )

        per_series_limit = max(2, min(MAX_POINTS_PER_SERIES, MAX_POINTS_ACROSS_PANELS // max(1, len(definitions))))
        base_indices = _sample_indices(len(t_min), per_series_limit)
        payload_series: list[dict[str, Any]] = []
        for series_id, signal_id, label, unit, values in definitions:
            if isinstance(values, tuple):
                marker_x, marker_y = values
                marker_x_array = np.asarray(marker_x, dtype=float)
                marker_y_array = np.asarray(marker_y, dtype=float)
                marker_indices = _sample_indices(len(marker_x_array), per_series_limit)
                payload_series.append(
                    {
                        "id": series_id,
                        "signal_id": signal_id,
                        "label": label,
                        "unit": unit,
                        "sample_indices": marker_indices,
                        "x": _json_values(marker_x_array, marker_indices),
                        "y": _json_values(marker_y_array, marker_indices),
                    }
                )
            else:
                payload_series.append(
                    {
                        "id": series_id,
                        "signal_id": signal_id,
                        "label": label,
                        "unit": unit,
                        "sample_indices": base_indices,
                        "x": _json_values(t_min, base_indices),
                        "y": _json_values(values, base_indices),
                    }
                )
        return {
            "plot_id": f"{csv_path.stem}.pfer",
            "title": "PFer Results — detected peaks",
            "x_axis": {"label": "Time", "unit": "min"},
            "sample_count": len(t_min),
            "viewport": {"start_index": 0, "end_index": max(0, len(t_min) - 1)},
            "display_reduced": len(base_indices) < len(t_min),
            "decimation": "uniform-index-v1",
            "series": payload_series,
        }

    def _run_pfer(self, request_id: str, params: dict[str, Any]) -> dict[str, Any]:
        csv_path = self._path_param(params, "csv_path")
        baseline_start = params.get("baseline_start", "")
        baseline_end = params.get("baseline_end", "")
        if not isinstance(baseline_start, str) or not isinstance(baseline_end, str):
            raise ValueError("PFer baseline endpoints must be strings.")
        prominence = params.get("prominence", 0.003)
        artifact_threshold = params.get("artifact_threshold", 10)
        if isinstance(prominence, bool) or not isinstance(prominence, (int, float)) or not math.isfinite(float(prominence)) or float(prominence) <= 0:
            raise ValueError("prominence must be a positive number.")
        if isinstance(artifact_threshold, bool) or not isinstance(artifact_threshold, (int, float)) or int(artifact_threshold) < 1:
            raise ValueError("artifact_threshold must be a positive integer.")

        from src.dfer.pfer import run_pfer

        self._log(f"Running PFer: {csv_path}")
        output = run_pfer(
            csv_path,
            w_start=baseline_start.strip(),
            w_end=baseline_end.strip(),
            prominence=float(prominence),
            artifact_threshold=int(artifact_threshold),
            make_plots=False,
        )
        stats_paths = [Path(line).expanduser().resolve() for line in str(output).splitlines() if line.strip()]
        if not stats_paths or not all(path.is_file() for path in stats_paths):
            raise ValueError("PFer did not return statistics CSV files.")
        self.pfer_csv = csv_path
        self.pfer_stats = stats_paths
        plot = self._pfer_plot(csv_path, stats_paths)
        self._log(f"PFer complete: {', '.join(str(path) for path in stats_paths)}")
        return success(request_id, {"stats_csv": "\n".join(str(path) for path in stats_paths), "plot": plot})

    def _plot_output_path(self, kind: str) -> Path:
        source = self.dfer_csv if kind == "dfer" else self.pfer_csv
        if source is None:
            raise ValueError("Run the requested analysis before saving its plot.")
        source = source.resolve()
        if self.raw_context is not None:
            output_root = Path(str(self.raw_context["output_folder"])).resolve().parent
        else:
            output_root = source.parent
        recording = _strip_data_suffix(source.stem)
        if recording.endswith("_Dual"):
            recording = recording.removesuffix("_Dual")
        plot_dir = output_root / "plots" / _safe_path_part(recording)
        plot_dir.mkdir(parents=True, exist_ok=True)
        stem = _safe_path_part(recording)
        pattern = re.compile(rf"^{re.escape(stem)}_plot_(\d+)\.png$")
        used = [int(match.group(1)) for path in plot_dir.glob(f"{stem}_plot_*.png") if (match := pattern.match(path.name))]
        next_number = max(used, default=0) + 1
        return plot_dir / f"{stem}_plot_{next_number}.png"

    def _save_plot(self, request_id: str, params: dict[str, Any]) -> dict[str, Any]:
        kind = params.get("kind")
        if kind not in {"dfer", "pfer"}:
            raise ValueError("kind must be 'dfer' or 'pfer'.")
        output_path = self._plot_output_path(str(kind))
        import matplotlib

        matplotlib.use("Agg", force=True)
        from src.dfer.df_plots import mpl_pfer_figure
        from src.features.raw_photometry.plotting import mpl_dfer_results_figure

        if kind == "dfer":
            graph = params.get("graph", "dfof")
            if graph not in {"dfof", "zscore"}:
                raise ValueError("graph must be 'dfof' or 'zscore'.")
            figure = mpl_dfer_results_figure(str(self.dfer_csv), str(graph), bool(params.get("show_405", True)))
        else:
            if self.pfer_csv is None or not self.pfer_stats:
                raise ValueError("Run PFer before saving its plot.")
            figure = mpl_pfer_figure(str(self.pfer_csv), "\n".join(str(path) for path in self.pfer_stats))
        figure.savefig(output_path, dpi=150, bbox_inches="tight")
        self._log(f"Saved plot image: {output_path}")
        return success(request_id, {"path": str(output_path)})

    def _shutdown(self, request_id: str, _params: dict[str, Any]) -> dict[str, Any]:
        self.stopping = True
        return success(request_id, {"status": "shutting_down"})

    def _log(self, message: str) -> None:
        print(message, file=self.diagnostic_stream, flush=True)


def serve(input_stream: BinaryIO, output_stream: BinaryIO, diagnostic_stream: Any = sys.stderr) -> int:
    server = ProtocolServer(diagnostic_stream)
    print("NeuroSyncApp sidecar control loop started", file=diagnostic_stream, flush=True)
    while not server.stopping:
        try:
            payload = read_frame(input_stream)
            if payload is None:
                return 0
            try:
                request = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                write_frame(output_stream, failure(None, "invalid_json", "The protocol frame does not contain valid UTF-8 JSON.", "change_input"))
                continue
            write_frame(output_stream, server.dispatch(request))
        except FrameError as error:
            write_frame(output_stream, failure(None, error.code, error.user_text, error.recovery))
            return 2
        except Exception:
            print("Unhandled sidecar diagnostic; details withheld from protocol response", file=diagnostic_stream, flush=True)
            write_frame(output_stream, failure(None, "internal_error", "The sidecar could not complete the request.", "restart_sidecar"))
    return 0
