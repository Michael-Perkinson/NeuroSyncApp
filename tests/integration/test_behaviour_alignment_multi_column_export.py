"""
Integration test: multi-column export.

Runs DataProcessingSingleInstance end-to-end with two signal columns ticked
(dFoF_465 + dFoF_405 — a real dual-wavelength scenario) and checks the
produced workbook has distinct, correctly suffixed sheets per column.
"""

import matplotlib
matplotlib.use("Agg")  # must be set before any GUI import

import shutil
import uuid

import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication

from src.features.behaviour_alignment.app import DataProcessingSingleInstance

EXAMPLE_DIR = (
    Path(__file__).parent.parent.parent
    / "example_data"
    / "photometry_behaviour"
)
PHOTOMETRY_CSV = EXAMPLE_DIR / "example_Data ST5435.csv"
BEHAVIOUR_CSV  = EXAMPLE_DIR / "example_coding_behaviour.csv"

_DEFAULT_SETTINGS = {"pre": "60", "post": "60", "bin": "30"}
PRIMARY_COLUMN = "dFoF_465"
SECONDARY_COLUMN = "dFoF_405"


def _load_behaviour_df() -> pd.DataFrame:
    df = pd.read_csv(str(BEHAVIOUR_CSV))
    df.columns = [c.lower() for c in df.columns]
    df = df.dropna(subset=["behaviour"])
    df["behaviour"] = df["behaviour"].apply(lambda x: str(x).strip().capitalize())
    df["start"] = df["start"].astype(float)
    df["end"] = df["end"].astype(float)
    return df


def _build_app_and_run_export(
    tmp_path_factory,
    tmp_name: str,
    columns: list[str],
    checkbox_state: bool = False,
    baseline_start: str = "0",
    baseline_end: str = "60",
):
    """Shared harness: build a headless app, wire state, run the export."""
    tmp_dir = tmp_path_factory.mktemp(tmp_name)
    csv_copy = tmp_dir / PHOTOMETRY_CSV.name
    shutil.copy(PHOTOMETRY_CSV, csv_copy)

    qt_app = QApplication.instance() or QApplication([])
    app = DataProcessingSingleInstance()

    app.dataframe = pd.read_csv(str(PHOTOMETRY_CSV))
    app.selected_column_var.set(columns[0])
    app.selected_columns_var.set(columns)
    app.checkbox_state = checkbox_state

    if checkbox_state:
        app.data_selection_frame.baseline_start_entry.set(baseline_start)
        app.data_selection_frame.baseline_end_entry.set(baseline_end)
        app.data_selection_frame.baseline_button_pressed = True
        app.data_service.calculate_z_score()

    beh_df = _load_behaviour_df()
    app.duration_data_cache: dict = {}
    for beh_name, grp in beh_df.groupby("behaviour"):
        starts = grp["start"].tolist()
        ends = grp["end"].tolist()
        durations_min = [(e - s) / 60 for s, e in zip(starts, ends)]
        n = len(durations_min)
        mean_dur = float(np.nanmean(durations_min))
        sem_dur = float(np.nanstd(durations_min) / np.sqrt(n)) if n > 1 else 0.0
        app.duration_data_cache[beh_name] = {
            "mean_duration": mean_dur,
            "sem_duration": sem_dur,
            "mean_sem_df": None,
            "number_of_instances": n,
        }

    rows = []
    for _, row in beh_df.iterrows():
        beh_name = row["behaviour"]
        s = _DEFAULT_SETTINGS
        rows.append((
            str(PHOTOMETRY_CSV), columns[0], beh_name, "Continuous",
            s["pre"], s["post"], s["bin"], row["start"], row["end"],
        ))
    display_df = pd.DataFrame(
        rows,
        columns=[
            "File Path", "Selected Column", "Behaviour Name", "Behaviour Type",
            "Pre Behaviour Time", "Post Behaviour Time", "Bin Size",
            "Start Time", "End Time",
        ],
    )
    key = str(uuid.uuid4())
    app.current_table_key = key
    app.tables[key] = display_df

    app.export_options_container.use_binned_data_var.set(True)
    app.export_options_container.combine_csv_var.set(True)
    app.export_options_container.use_auc_var.set(True)
    app.export_options_container.use_max_amp_var.set(True)
    app.export_options_container.use_mean_dff_var.set(True)

    params: dict = {}
    behaviours_to_export: set = set()
    for _, row in display_df.iterrows():
        beh_name = row["Behaviour Name"]
        instance = {
            "pre_behaviour_time": row["Pre Behaviour Time"],
            "post_behaviour_time": row["Post Behaviour Time"],
            "bin_size": row["Bin Size"],
            "behaviour_start_time": float(row["Start Time"]),
        }
        params.setdefault(beh_name, []).append(instance)
        behaviours_to_export.add(beh_name)
    params["behaviours_to_export"] = behaviours_to_export
    params["params_to_extract"] = []
    if checkbox_state:
        params["baseline_start_time_min"] = float(baseline_start) / 60

    app.extract_data_from_photometry(str(csv_copy), params)

    out_dir = tmp_dir / (PHOTOMETRY_CSV.stem + "_NeuroBehaviorSync")
    out_name = f"{PHOTOMETRY_CSV.stem}_{columns[0]}"
    if checkbox_state:
        out_name += f"_baseline_{baseline_start}"
    out_xlsx = out_dir / f"{out_name}.xlsx"

    return app, out_xlsx


@pytest.fixture(scope="module")
def multi_column_output_xlsx(tmp_path_factory):
    app, out_xlsx = _build_app_and_run_export(
        tmp_path_factory, "behaviour_alignment_multi", [PRIMARY_COLUMN, SECONDARY_COLUMN]
    )
    yield out_xlsx
    app.deleteLater()


@pytest.fixture(scope="module")
def baseline_single_column_xlsx(tmp_path_factory):
    app, out_xlsx = _build_app_and_run_export(
        tmp_path_factory,
        "behaviour_alignment_baseline_single",
        [PRIMARY_COLUMN],
        checkbox_state=True,
    )
    yield out_xlsx
    app.deleteLater()


@pytest.fixture(scope="module")
def baseline_multi_column_xlsx(tmp_path_factory):
    app, out_xlsx = _build_app_and_run_export(
        tmp_path_factory,
        "behaviour_alignment_baseline_multi",
        [PRIMARY_COLUMN, SECONDARY_COLUMN],
        checkbox_state=True,
    )
    yield out_xlsx
    app.deleteLater()


@pytest.mark.integration
class TestMultiColumnExport:
    def test_output_file_exists(self, multi_column_output_xlsx):
        assert multi_column_output_xlsx.exists()

    def test_sheets_suffixed_per_column_and_distinct(self, multi_column_output_xlsx):
        sheets = pd.ExcelFile(str(multi_column_output_xlsx)).sheet_names
        assert len(sheets) == len(set(sheets)), f"Duplicate sheet names: {sheets}"

        primary_sheets = [
            s for s in sheets if s.endswith(f"_{PRIMARY_COLUMN}") and not s.startswith("Summary")
        ]
        secondary_sheets = [
            s for s in sheets if s.endswith(f"_{SECONDARY_COLUMN}") and not s.startswith("Summary")
        ]
        assert primary_sheets, f"No sheets suffixed with primary column found in {sheets}"
        assert secondary_sheets, f"No sheets suffixed with secondary column found in {sheets}"
        assert len(primary_sheets) == len(secondary_sheets), (
            f"Mismatched behaviour-sheet counts per column: "
            f"primary={primary_sheets} secondary={secondary_sheets}"
        )

    def test_single_summary_sheet_only(self, multi_column_output_xlsx):
        # Extra signal columns add behaviour detail sheets, not extra summary
        # sheets. There must be exactly one summary, and it must come first.
        sheets = pd.ExcelFile(str(multi_column_output_xlsx)).sheet_names
        summary_sheets = [s for s in sheets if s.startswith("Summary")]
        assert summary_sheets == ["Summary Results"], (
            f"Expected a single 'Summary Results' sheet, got {summary_sheets}"
        )
        assert sheets[0] == "Summary Results", f"Summary not first: {sheets}"
        assert not any(SECONDARY_COLUMN in s for s in summary_sheets)

    def test_summary_and_event_duration_lead(self, multi_column_output_xlsx):
        # The two headline sheets sit at the front, before any detail sheet.
        sheets = pd.ExcelFile(str(multi_column_output_xlsx)).sheet_names
        assert sheets[:2] == ["Summary Results", "Event Duration"], sheets

    def test_primary_and_secondary_sheet_data_differ(self, multi_column_output_xlsx):
        sheets = pd.ExcelFile(str(multi_column_output_xlsx)).sheet_names
        primary_sheet = next(
            s for s in sheets if s.endswith(f"_{PRIMARY_COLUMN}") and not s.startswith("Summary")
        )
        secondary_sheet = next(
            s for s in sheets if s.endswith(f"_{SECONDARY_COLUMN}") and not s.startswith("Summary")
        )

        primary_df = pd.read_excel(str(multi_column_output_xlsx), sheet_name=primary_sheet)
        secondary_df = pd.read_excel(str(multi_column_output_xlsx), sheet_name=secondary_sheet)

        primary_numeric = primary_df.select_dtypes(include=[np.number]).to_numpy()
        secondary_numeric = secondary_df.select_dtypes(include=[np.number]).to_numpy()
        assert primary_numeric.shape == secondary_numeric.shape
        assert not np.allclose(
            primary_numeric, secondary_numeric, equal_nan=True
        ), "Primary and secondary column sheets contain identical data"


@pytest.mark.integration
class TestBaselineSingleColumnExport:
    """Baseline/z-score export with a single column ticked still works."""

    def test_output_file_exists(self, baseline_single_column_xlsx):
        assert baseline_single_column_xlsx.exists()

    def test_event_duration_has_baseline_columns(self, baseline_single_column_xlsx):
        df = pd.read_excel(str(baseline_single_column_xlsx), sheet_name="Event Duration")
        columns = list(df.columns)
        assert any("Mean df/f for baseline" in str(c) for c in columns), columns
        assert any("STD for baseline" in str(c) for c in columns), columns
        # Single column: no per-column suffix on the baseline labels.
        assert not any(PRIMARY_COLUMN in str(c) for c in columns), columns


@pytest.mark.integration
class TestBaselineMultiColumnExport:
    """Both columns get baselined over the same window, independently."""

    def test_output_file_exists(self, baseline_multi_column_xlsx):
        assert baseline_multi_column_xlsx.exists()

    def test_sheets_suffixed_and_distinct(self, baseline_multi_column_xlsx):
        sheets = pd.ExcelFile(str(baseline_multi_column_xlsx)).sheet_names
        assert len(sheets) == len(set(sheets)), f"Duplicate sheet names: {sheets}"
        primary_sheets = [
            s for s in sheets if s.endswith(f"_{PRIMARY_COLUMN}") and not s.startswith("Summary")
        ]
        secondary_sheets = [
            s for s in sheets if s.endswith(f"_{SECONDARY_COLUMN}") and not s.startswith("Summary")
        ]
        assert primary_sheets and secondary_sheets
        assert len(primary_sheets) == len(secondary_sheets)

    def test_event_duration_has_per_column_baseline_stats(self, baseline_multi_column_xlsx):
        df = pd.read_excel(str(baseline_multi_column_xlsx), sheet_name="Event Duration")
        columns = list(df.columns)
        assert any(PRIMARY_COLUMN in str(c) and "Mean df/f" in str(c) for c in columns), columns
        assert any(SECONDARY_COLUMN in str(c) and "Mean df/f" in str(c) for c in columns), columns
        assert any(PRIMARY_COLUMN in str(c) and "STD" in str(c) for c in columns), columns
        assert any(SECONDARY_COLUMN in str(c) and "STD" in str(c) for c in columns), columns

    def test_baseline_means_differ_between_columns(self, baseline_multi_column_xlsx):
        df = pd.read_excel(str(baseline_multi_column_xlsx), sheet_name="Event Duration")
        primary_mean_col = next(c for c in df.columns if PRIMARY_COLUMN in c and "Mean df/f" in c)
        secondary_mean_col = next(
            c for c in df.columns if SECONDARY_COLUMN in c and "Mean df/f" in c
        )
        primary_mean = df[primary_mean_col].dropna().iloc[0]
        secondary_mean = df[secondary_mean_col].dropna().iloc[0]
        assert primary_mean != pytest.approx(secondary_mean), (
            "Primary and secondary baseline means are identical — "
            "each column should be baselined independently"
        )

    def test_primary_and_secondary_behaviour_sheets_differ(self, baseline_multi_column_xlsx):
        sheets = pd.ExcelFile(str(baseline_multi_column_xlsx)).sheet_names
        primary_sheet = next(
            s for s in sheets if s.endswith(f"_{PRIMARY_COLUMN}") and not s.startswith("Summary")
        )
        secondary_sheet = next(
            s for s in sheets if s.endswith(f"_{SECONDARY_COLUMN}") and not s.startswith("Summary")
        )
        primary_df = pd.read_excel(str(baseline_multi_column_xlsx), sheet_name=primary_sheet)
        secondary_df = pd.read_excel(str(baseline_multi_column_xlsx), sheet_name=secondary_sheet)
        primary_numeric = primary_df.select_dtypes(include=[np.number]).to_numpy()
        secondary_numeric = secondary_df.select_dtypes(include=[np.number]).to_numpy()
        assert primary_numeric.shape == secondary_numeric.shape
        assert not np.allclose(primary_numeric, secondary_numeric, equal_nan=True)
