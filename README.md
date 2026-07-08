# NeuroSyncApp

NeuroSyncApp is a PySide6 desktop app for processing raw photometry recordings and aligning photometry with coded behaviour, telemetry, and optogenetic recordings.

The app opens to a dashboard. The default first tool is **Analyse Raw Data**.

## Active Tools

| Tool | App ID | Purpose |
| --- | --- | --- |
| Analyse Raw Data | `raw_analysis` | Inspect raw photometry CSVs, choose an analysis window, preview DFer options, run DFer, and run PFer peak finding. |
| Align Photometry and Behaviour | `single_animal` | Align a photometry trace with coded behaviour events, plot full/single-row/mean-SEM views, and export aligned metrics. |
| Align Telemetry Data | `telemetry_photom_opto` | Align telemetry, photometry, and optogenetic recordings; detect clusters; export workbook summaries. |

`combine_data` is still listed in the dashboard as a placeholder and has not been ported to Qt yet.

## Install

### End Users

Use the GitHub Releases page.

- Windows: download the `.exe`.
- macOS: download the `.zip`, unzip it, and run `NeuroSyncApp.app`.
- The macOS zip also includes `NeuroSyncApp Debug.command`, which prints useful diagnostic output if macOS blocks or kills the app.

No Python install is needed for release builds.

### Developers

`pyproject.toml` is the source of truth for dependencies. `requirements.txt` is no longer used.

Use Python 3.14 for the current tested dependency set. The package metadata allows Python 3.12 through 3.14, but release builds and package snapshots target Python 3.14.

Windows:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python main.py
```

macOS:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python main.py
```

Build dependencies are separate:

```bash
python -m pip install -e ".[build]"
```

## Tested Package Snapshots

The `requirements/` folder contains resolved pip-list snapshots for Python 3.14:

- `requirements/windows-py314.txt`
- `requirements/macos-py314.txt`

These are not the primary install path. Use them only when you need to recreate the tested package set exactly:

```bash
python -m pip install -r requirements/windows-py314.txt
```

The snapshots were validated with pip wheel resolution for:

- Windows: `win_amd64`
- macOS Apple Silicon: `macosx_14_0_arm64`
- macOS Intel: `macosx_14_0_x86_64`

## Run

Launch the dashboard:

```bash
python main.py
```

Launch one tool directly:

```bash
python main.py --tool raw_analysis
python main.py --tool single_animal
python main.py --tool telemetry_photom_opto
```

The dashboard remembers the last active supported tool and opens it next time.

## First App: Analyse Raw Data

This is the default first screen.

1. Optional: click **Select Folder** to remember a default data folder.
2. Click **Raw Photometry File** and choose a raw photometry CSV.
3. The raw trace appears in the **Raw Data** tab.
4. Set the analysis window:
   - `start`, `min`, or blank means the start of the recording.
   - `end`, `max`, or blank means the end of the recording.
   - Numeric values are seconds.
5. Click **Apply** to update the red/blue window markers and regenerate DFer option previews.
6. Open the **DFer Options** graph tab to inspect options 1-4.
7. In **DFer Settings**, select the final DFer option and click **Run final analysis**.
8. Use **DFer Results** to view dF/F or Z-score output and save plots.
9. For PFer, select a DFer output CSV in the PFer settings, choose baseline/prominence settings, then click **Run peak finder**.

DFer/PFer outputs are written beside the selected recording or into the app-created output folders. The app log panel shows progress and saved paths.

## Align Photometry and Behaviour

Use this tool when you already have a processed photometry trace and a behaviour coding CSV.

1. Open **Align Photometry and Behaviour** from the dashboard.
2. In **Data Selection**, choose the photometry file.
3. Select one or more signal columns.
4. Optionally set and save a baseline window for z-scoring.
5. In **Behaviour Input**, import the behaviour CSV.
6. On first use, map the behaviour, start-time, and end-time columns from your CSV.
7. Use **Static Inputs** to set pre-behaviour time, post-behaviour time, and bin size.
8. In the graph view, choose:
   - Full Trace Display
   - Single Row Display
   - Behaviour Mean and SEM
9. Use **Graph Settings** for colours, line width, axis limits, duration bars, time units, and zeroing the x-axis to a selected behaviour.
10. Use **Export Options** to export aligned data and save figures.

Exports include workbook outputs with metric sheets such as AUC, max amplitude, mean dF/F, binned data, and raw aligned traces depending on the selected options.

## Align Telemetry Data

Use this tool for telemetry, photometry, and optogenetic alignment workflows.

1. Open **Align Telemetry Data** from the dashboard.
2. Select the main recording file.
3. Add or confirm associated temperature and activity files.
4. Enter the light-off/start time values needed for alignment.
5. Configure pre/post cluster windows and bin sizes in **Static Inputs**.
6. Generate or refresh cluster displays from the graph controls.
7. Use cluster checkboxes, colours, peak alignment, and graph settings to refine the display.
8. Use **Export Options** to create the telemetry workbook export and save figures.

The telemetry exporter writes Excel workbooks with summary, cluster, signal, and raw sheets.

## Tests

Run the test suite from an activated environment:

Windows:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q
```

macOS:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

Useful focused checks:

```bash
python -m pytest -q tests/unit/test_qt_lifecycle.py
python -m pytest -q tests/unit/test_raw_qt_app.py tests/unit/test_behaviour_qt_app.py tests/unit/test_telemetry_qt_app.py
```

## Release Builds

Tagged pushes (`v*`) run `.github/workflows/python-app.yml`.

The workflow builds:

- Windows executable
- macOS Apple Silicon zip
- macOS Intel zip

The workflow installs from `pyproject.toml` with:

```bash
python -m pip install -e ".[build]"
```

## Configuration

User settings are stored outside the repo using platform-specific config directories via `platformdirs`. You can override the config location for tests or debugging:

```bash
NEUROSYNCAPP_CONFIG_DIR=/path/to/config python main.py
```

On Windows PowerShell:

```powershell
$env:NEUROSYNCAPP_CONFIG_DIR = "C:\path\to\config"
python main.py
```

## Example Data

Example input files live in `example_data/`:

- `example_data/photometry_behaviour`
- `example_data/menopause_photometry`
- `example_data/menopause_stim`

These are useful for smoke-testing the UI and export flows.

## Dependency Notes

Direct runtime dependencies are kept intentionally small:

- PySide6
- matplotlib
- numpy
- pandas
- scipy
- openpyxl
- XlsxWriter
- platformdirs

Test and packaging tools live in optional extras:

- `.[dev]`: pytest and coverage tools
- `.[build]`: PyInstaller and Pillow for release packaging

Do not add transitive packages to `pyproject.toml` unless the app imports them directly.

## Attribution

The DFer/PFer raw photometry analysis workflow in NeuroSyncApp was ported from
the Argotech/Tussock Innovation DFer_v1.4 + PFer_2.4 analysis scripts and README
(OCT-2024), distributed through the Argotech fibre photometry resources:
https://www.argotech.co.nz/fibre-photometry

The DFer/PFer workflow is based on analysis methods from GuPPy:

Sherathiya, V. N., Schaid, M. D., Seiler, J. L., Lopez, G. C., & Lerner, T. N.
GuPPy, a Python toolbox for the analysis of fiber photometry data.
Scientific Reports 11, 24212 (2021). https://doi.org/10.1038/s41598-021-03626-9

## License

NeuroSyncApp is licensed under the GNU General Public License v3.0.
