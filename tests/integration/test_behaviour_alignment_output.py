"""
Integration test: runs DataProcessingSingleInstance end-to-end on the example
photometry + behaviour CSV files and compares the produced Excel against the
known-good golden file sheet by sheet.

Settings that were used when generating the golden file
(deduced from sheet shapes and bin-label ranges in the golden file):
  - Active investigation : pre=30 s, post=30 s, bin=5 s  → 600 rows, 12 bins
  - All other behaviours : pre=10 s, post=10 s, bin=5 s  → 200 rows,  4 bins
  - Exported column      : dFoF_465
  - use_binned_data      : True   (Summary Results sheet present)
  - combine_csv          : True   (single workbook)
  - use_auc, use_max_amp, use_mean_dff : True  (all three metric rows present)
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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EXAMPLE_DIR = (
    Path(__file__).parent.parent.parent
    / "example_data"
    / "photometry_behaviour"
)
PHOTOMETRY_CSV = EXAMPLE_DIR / "example_Data ST5435.csv"
BEHAVIOUR_CSV  = EXAMPLE_DIR / "example_coding_behaviour.csv"
EXPECTED_XLSX  = (
    EXAMPLE_DIR
    / "example_Data ST5435_NeuroBehaviorSync"
    / "example_Data ST5435_dFoF_465.xlsx"
)

# ---------------------------------------------------------------------------
# Settings used when producing the golden file
# ---------------------------------------------------------------------------
_DEFAULT_SETTINGS = {"pre": "60", "post": "60", "bin": "30"}
BEHAVIOUR_SETTINGS = {}

# Sheet names in the order they appear in the golden workbook
EXPECTED_SHEETS = [
    "Summary Results",
    "Event Duration",
    "Active investigation",
    "Approach",
    "Nest building",
    "On nest no pups",
    "On nest with pups",
    "On nest with pups not int... ac",
    "On nest with pups not int... pa",
    "On nest with pups passive",
    "Pups in",
    "Pups out",
    "Retrieve",
]
BEHAVIOUR_SHEETS = [
    s for s in EXPECTED_SHEETS if s not in ("Summary Results", "Event Duration")
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_behaviour_df() -> pd.DataFrame:
    """Load and normalise the example behaviour CSV (same transforms the app does)."""
    df = pd.read_csv(str(BEHAVIOUR_CSV))
    df.columns = [c.lower() for c in df.columns]
    df = df.dropna(subset=["behaviour"])
    df["behaviour"] = df["behaviour"].apply(lambda x: str(x).strip().capitalize())
    df["start"] = df["start"].astype(float)
    df["end"] = df["end"].astype(float)
    return df


def _read_numeric(path: str, sheet: str) -> np.ndarray:
    """Read *sheet* from *path*; return a float array (text cells → NaN)."""
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    return df.apply(pd.to_numeric, errors="coerce").values


# ---------------------------------------------------------------------------
# Fixture — runs the pipeline once, module-scoped
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def output_xlsx(tmp_path_factory):
    """
    Spin up a headless DataProcessingSingleInstance, inject all required state,
    call extract_data_from_photometry, and yield the path to the produced xlsx.
    """
    tmp_dir = tmp_path_factory.mktemp("behaviour_alignment")

    # Copy the photometry CSV so create_extraction_folder writes into tmp_dir
    csv_copy = tmp_dir / PHOTOMETRY_CSV.name
    shutil.copy(PHOTOMETRY_CSV, csv_copy)

    qt_app = QApplication.instance() or QApplication([])
    app = DataProcessingSingleInstance()

    # ── 1. photometry data ────────────────────────────────────────────────
    app.dataframe = pd.read_csv(str(PHOTOMETRY_CSV))
    app.selected_column_var.set("dFoF_465")
    app.checkbox_state = False

    # ── 2. duration cache ─────────────────────────────────────────────────
    # calculate_duration_metrics stores durations in minutes; time_unit_menu
    # defaults to "minutes" so convert_and_retrieve_time multiplies by 1 (no-op).
    # extract_duration_data then multiplies by 60 to produce seconds for the sheet.
    beh_df = _load_behaviour_df()
    app.duration_data_cache: dict = {}

    for beh_name, grp in beh_df.groupby("behaviour"):
        starts = grp["start"].tolist()
        ends   = grp["end"].tolist()
        durations_min = [(e - s) / 60 for s, e in zip(starts, ends)]
        n = len(durations_min)
        mean_dur = float(np.nanmean(durations_min))
        sem_dur  = (
            float(np.nanstd(durations_min) / np.sqrt(n)) if n > 1 else 0.0
        )
        app.duration_data_cache[beh_name] = {
            "mean_duration":      mean_dur,
            "sem_duration":       sem_dur,
            "mean_sem_df":        None,
            "number_of_instances": n,
        }

    # ── 3. tables DataFrame ───────────────────────────────────────────────
    rows = []
    for _, row in beh_df.iterrows():
        beh_name = row["behaviour"]
        s = BEHAVIOUR_SETTINGS.get(beh_name, _DEFAULT_SETTINGS)
        rows.append((
            str(PHOTOMETRY_CSV),
            "dFoF_465",
            beh_name,
            "Continuous",
            s["pre"],
            s["post"],
            s["bin"],
            row["start"],
            row["end"],
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

    # ── 4. export options (all True by default, but be explicit) ──────────
    app.export_options_container.use_binned_data_var.set(True)
    app.export_options_container.combine_csv_var.set(True)
    app.export_options_container.use_auc_var.set(True)
    app.export_options_container.use_max_amp_var.set(True)
    app.export_options_container.use_mean_dff_var.set(True)

    # ── 5. params dict (bypasses check_and_prepare_parameters to avoid
    #       messagebox calls in headless mode) ────────────────────────────
    params: dict = {}
    behaviours_to_export: set = set()

    for _, row in display_df.iterrows():
        beh_name = row["Behaviour Name"]
        instance = {
            "pre_behaviour_time":  row["Pre Behaviour Time"],
            "post_behaviour_time": row["Post Behaviour Time"],
            "bin_size":            row["Bin Size"],
            "behaviour_start_time": float(row["Start Time"]),
        }
        params.setdefault(beh_name, []).append(instance)
        behaviours_to_export.add(beh_name)

    params["behaviours_to_export"] = behaviours_to_export
    params["params_to_extract"]    = []

    # ── 6. run ────────────────────────────────────────────────────────────
    app.extract_data_from_photometry(str(csv_copy), params)

    out_dir  = tmp_dir / (PHOTOMETRY_CSV.stem + "_NeuroBehaviorSync")
    out_xlsx = out_dir / f"{PHOTOMETRY_CSV.stem}_dFoF_465.xlsx"

    yield out_xlsx

    app.deleteLater()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestBehaviourAlignmentOutput:

    # ── file existence ────────────────────────────────────────────────────
    def test_output_file_exists(self, output_xlsx):
        assert output_xlsx.exists(), f"Expected output not found: {output_xlsx}"

    # ── sheet inventory ───────────────────────────────────────────────────
    def test_sheet_names_match(self, output_xlsx):
        produced = pd.ExcelFile(str(output_xlsx)).sheet_names
        expected = pd.ExcelFile(str(EXPECTED_XLSX)).sheet_names
        assert produced == expected

    # ── behaviour sheets: shape ───────────────────────────────────────────
    @pytest.mark.parametrize("sheet", BEHAVIOUR_SHEETS)
    def test_behaviour_sheet_shape(self, output_xlsx, sheet):
        produced = pd.read_excel(str(output_xlsx), sheet_name=sheet, header=None)
        expected = pd.read_excel(str(EXPECTED_XLSX), sheet_name=sheet, header=None)
        assert produced.shape == expected.shape, (
            f"Sheet '{sheet}': produced {produced.shape} != expected {expected.shape}"
        )

    # ── behaviour sheets: values ──────────────────────────────────────────
    @pytest.mark.parametrize("sheet", BEHAVIOUR_SHEETS)
    def test_behaviour_sheet_numeric_values(self, output_xlsx, sheet):
        produced_arr = _read_numeric(str(output_xlsx), sheet)
        expected_arr = _read_numeric(str(EXPECTED_XLSX), sheet)
        np.testing.assert_allclose(
            produced_arr,
            expected_arr,
            rtol=1e-3,
            atol=1e-6,
            equal_nan=True,
            err_msg=f"Numeric mismatch in sheet '{sheet}'",
        )

    # ── Event Duration ────────────────────────────────────────────────────
    def test_event_duration_shape(self, output_xlsx):
        produced = pd.read_excel(str(output_xlsx), sheet_name="Event Duration", header=None)
        expected = pd.read_excel(str(EXPECTED_XLSX), sheet_name="Event Duration", header=None)
        assert produced.shape == expected.shape

    def test_event_duration_numeric_values(self, output_xlsx):
        produced_arr = _read_numeric(str(output_xlsx), "Event Duration")
        expected_arr = _read_numeric(str(EXPECTED_XLSX), "Event Duration")
        np.testing.assert_allclose(
            produced_arr,
            expected_arr,
            rtol=1e-3,
            atol=1e-3,
            equal_nan=True,
            err_msg="Numeric mismatch in Event Duration sheet",
        )

    # ── Summary Results ───────────────────────────────────────────────────
    def test_summary_results_shape(self, output_xlsx):
        produced = pd.read_excel(str(output_xlsx), sheet_name="Summary Results", header=None)
        expected = pd.read_excel(str(EXPECTED_XLSX), sheet_name="Summary Results", header=None)
        assert produced.shape == expected.shape

    def test_summary_results_numeric_values(self, output_xlsx):
        produced_arr = _read_numeric(str(output_xlsx), "Summary Results")
        expected_arr = _read_numeric(str(EXPECTED_XLSX), "Summary Results")
        np.testing.assert_allclose(
            produced_arr,
            expected_arr,
            rtol=1e-3,
            atol=1e-6,
            equal_nan=True,
            err_msg="Numeric mismatch in Summary Results sheet",
        )
