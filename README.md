# NeuroSyncApp

NeuroSyncApp is a desktop application for analysing fibre-photometry recordings and aligning photometry with coded behaviour, telemetry, and optogenetic recordings. It uses PySide6 and runs from a Python environment on Windows, macOS, and Linux.

## Available tools

| Tool | What it does |
| --- | --- |
| **Analyse Raw Data** | Load raw photometry CSV/OFRS recordings, run DFer, and run PFer peak finding. |
| **Align Photometry and Behaviour** | Align processed photometry with coded behaviour and export metrics. |
| **Align Telemetry Data** | Align telemetry, photometry, and optogenetic recordings and export workbooks. |
| **Combine Data** | Listed as a future placeholder; not currently available. |

Choose a tool from the dashboard after the app opens. On a new installation, the dashboard opens with **Analyse Raw Data** selected; afterwards it remembers the last tool you used.

## Before you start

You need two free programs. Install each with its default options unless noted.

- **Git**, used to download the app and get updates: [official Git downloads](https://git-scm.com/downloads).
- **Python 3.12, 3.13, or 3.14** (the project requires `>=3.12,<3.15`). If the installer offers **Add python.exe to PATH** (Windows), tick it.

> **Python 3.15 and newer are not supported yet.** The main download button on python.org may offer a newer Python than this app supports. Instead, pick the newest **Python 3.14.x** (or 3.13.x) installer from the official release list for your system: [Windows releases](https://www.python.org/downloads/windows/) or [macOS releases](https://www.python.org/downloads/macos/).

You type the commands in this guide into a terminal: **PowerShell** on Windows (search for "PowerShell" in the Start menu) or **Terminal** on macOS (search for "Terminal" in Spotlight). Paste one block at a time and press Enter. Linux users can use their usual terminal.

## Get the app

Cloning the repository with Git is recommended, because you can then get updates with a single command. Open a terminal and run:

```bash
git clone https://github.com/Michael-Perkinson/NeuroSyncApp.git
cd NeuroSyncApp
```

This creates a `NeuroSyncApp` folder inside the folder the terminal started in (normally your user/home folder) and moves the terminal into it. Keep this folder: you will use it to launch the app and get updates.

### Opening a terminal in the NeuroSyncApp folder later

Every command below must run from inside the `NeuroSyncApp` folder. When you open a new terminal later:

- **Windows 11:** open the `NeuroSyncApp` folder in File Explorer, right-click an empty area, and choose **Open in Terminal**.
- **macOS:** open Terminal, type `cd ` (with a trailing space), drag the `NeuroSyncApp` folder from Finder into the Terminal window, and press Enter.
- **Any system:** type `cd` followed by the folder path, for example `cd NeuroSyncApp` if the terminal starts in your home folder.

## First-time setup

Setup creates a private Python environment (a `.venv` folder inside `NeuroSyncApp`), installs the app into it, and opens the app. You only need to do this once.

### Windows

In PowerShell, from the `NeuroSyncApp` folder:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install .
neurosyncapp
```

`python --version` must report Python 3.12, 3.13, or 3.14. If it opens the Microsoft Store or is not recognised, install a supported Python (see [Before you start](#before-you-start)), close PowerShell, and open a new one.

If `python` reports an unsupported version (for example 3.15, or 3.11 or older) but a supported Python is also installed, use the Windows `py` launcher to create the environment with that version instead:

```powershell
py -3.14 -m venv .venv
```

(Use `py -3.13` if that is the version you installed.) Then continue from `.\.venv\Scripts\activate`; once the environment is active, `python` refers to the environment's Python. If you already created `.venv` with the unsupported Python, delete the `.venv` folder first and recreate it.

If `.\.venv\Scripts\activate` fails with an error saying that running scripts is disabled on this system, PowerShell's execution policy is blocking the activation script. Either:

- use **Command Prompt** instead of PowerShell (search for "Command Prompt" in the Start menu) and activate with `.venv\Scripts\activate.bat`; the other commands are the same, or
- allow scripts in the current PowerShell window only, then activate again:

  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\.venv\Scripts\activate
  ```

  This setting ends when you close the window. If your organisation blocks it, use Command Prompt.

### macOS

In Terminal, from the `NeuroSyncApp` folder:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
neurosyncapp
```

If macOS asks to install the **command line developer tools** when you run `git` or `python3`, accept the prompt, wait for it to finish, and run the command again.

`python3 --version` must report Python 3.12, 3.13, or 3.14. macOS can include an older `python3`, and a newer unsupported one (3.15+) may also be installed. If the version is not supported, install Python 3.14.x or 3.13.x from the [macOS releases](https://www.python.org/downloads/macos/) list (or Homebrew), open a new Terminal window, and create the environment with the versioned command instead, for example:

```bash
python3.14 --version
python3.14 -m venv .venv
```

Then continue from `source .venv/bin/activate`. If you already created `.venv` with an unsupported Python, delete the `.venv` folder first.

### Linux

Use a Python 3.12–3.14 interpreter from your distribution or Python installation. From the `NeuroSyncApp` folder:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
neurosyncapp
```

If `python3` is missing or reports an unsupported version (older than 3.12, or 3.15+), use the versioned command provided by your Python installation (for example `python3.13`). Some distributions also need their `venv` package installed before `python3 -m venv` works.

### What the install does

`python -m pip install .` installs NeuroSyncApp and its required packages, including PySide6, into `.venv`. It also adds the `neurosyncapp` command, which opens the app. The command and packages are only available while the environment is **activated**; the terminal prompt then usually starts with `(.venv)`.

## Launch the app again

After the first-time setup, open a terminal in the `NeuroSyncApp` folder ([how](#opening-a-terminal-in-the-neurosyncapp-folder-later)), activate the environment, and launch:

| System | Commands |
| --- | --- |
| Windows (PowerShell) | `.\.venv\Scripts\activate` then `neurosyncapp` |
| Windows (Command Prompt) | `.venv\Scripts\activate.bat` then `neurosyncapp` |
| macOS / Linux | `source .venv/bin/activate` then `neurosyncapp` |

Do not create the environment or reinstall each time.

## Get updates

Close the app, open a terminal in the `NeuroSyncApp` folder, activate the environment as above, and run:

```bash
git pull
python -m pip install .
neurosyncapp
```

`git pull` downloads the latest version. `python -m pip install .` installs it into your environment; run it after every update so the `neurosyncapp` command uses the new code and any new required packages.

## Advanced launch options

You can open a single tool directly with `neurosyncapp --tool <option>`:

| Tool | `--tool` option |
| --- | --- |
| Analyse Raw Data | `raw_analysis` |
| Align Photometry and Behaviour | `single_animal` |
| Align Telemetry Data | `telemetry_photom_opto` |

For example, `neurosyncapp --tool raw_analysis`. Omit `--tool` to open the dashboard.

With the environment activated, `python main.py` (which accepts the same `--tool` option) starts the app directly from the repository code without using the `neurosyncapp` command.

## Analyse Raw Data: DFer and PFer

Use this workflow for a raw photometry CSV or an OFRS recording.

1. Open **Analyse Raw Data**.
2. Optionally use **Select Folder** to choose the folder shown by the file picker.
3. Select the original raw photometry file. Supported inputs are `.csv` and `.ofrs`; OFRS recordings are decoded directly and do not need manual channel export.
4. Review the **Raw Data** tab. Single-channel recordings use a 465 nm target with a 405 nm control. Dual-channel recordings use 470 nm and 560 nm targets with a 410 nm control.
5. Enter the analysis window in seconds. Blank, `start`, or `min` uses the beginning of the recording; blank, `end`, or `max` uses the end. Click **Apply**.
6. Review the five DFer options in **DFer Options**. For dual-channel recordings, use the signal selector to show both channels or only 470 nm or 560 nm.
7. Select the final DFer option in **DFer Settings** and click **Run final analysis**. DFer expects a sufficiently long numeric window; the UI currently requires at least about 120 seconds for the preview workflow.
8. Review the result in **DFer Results**. Single-channel control-based results can show or hide the 405 nm reference. Option 5 is the independent per-channel `msbackadj` correction and does not use the control channel.
9. Save a plot if needed. The analysis CSV and log show the output path.
10. In **PFer Settings**, select the DFer result CSV, set the optional baseline window and peak parameters, and click **Run peak finder**. PFer writes statistics and waveform CSVs beside the selected DFer result.

DFer output CSVs preserve the legacy format, including the single metadata field that records the selected option. Use a DFer output—not the original raw recording—as PFer input.

## Align Photometry and Behaviour

Use this tool when you have a processed photometry CSV and a behaviour-coding file.

1. Open **Align Photometry and Behaviour**.
2. Select the photometry file in **Data Selection**.
3. Select one or more signal columns. Multiple signals can be displayed together with independent trace and SEM colours.
4. Optionally enable and configure a baseline window for z-scoring.
5. Import the behaviour-coding file and map its behaviour, start-time, and end-time columns when prompted.
6. In **Static Inputs**, set pre-behaviour time, post-behaviour time, and bin size.
7. Use the graph views for the full trace, a single behaviour row, or behaviour mean and SEM. **Graph Settings** controls colours, line widths, axis limits, time units, duration bars, and zeroing relative to a selected behaviour.
8. Use **Export Options** to export aligned data and figures.

The workbook export includes a summary sheet with AUC, maximum-amplitude, mean-dF/F, and binned-data sections, plus per-behaviour sheets containing aligned traces. If event times fall outside the photometry recording, check the time unit and any video-coding offset before continuing.

## Align Telemetry Data

Use this tool for telemetry, photometry, and optogenetic alignment.

1. Open **Align Telemetry Data**.
2. Select the primary recording file.
3. Add or confirm the associated temperature and activity files.
4. Provide the recording/alignment start time and light-off values requested by the form. If more than one telemetry date can match, choose the intended alignment when prompted.
5. Configure pre/post cluster windows, baseline settings, and bin sizes in **Static Inputs**.
6. Review the **Graph** and **Table** views. Overlay temperature and activity when needed.
7. Generate or refresh photometry peak clusters or optogenetic stimulation clusters.
8. Use cluster checkboxes, colours, peak alignment, and graph settings to refine the display.
9. Use **Export Options** to create the telemetry Excel workbook and save figures.

Telemetry exports contain summary, cluster, signal, and raw sheets. Photometry and telemetry clusters are grouped by detected peak count; optogenetic recordings are grouped by stimulation category.

## Files and settings

- Raw DFer results are written to the `dfof_results` output folder associated with the selected recording.
- PFer statistics and waveform CSVs are written beside the selected DFer result.
- User settings are stored outside the repository using platform-specific configuration directories.
- Set `NEUROSYNCAPP_CONFIG_DIR` to use a different settings directory, for example:

  ```bash
  NEUROSYNCAPP_CONFIG_DIR=/path/to/config neurosyncapp
  ```

  In Windows PowerShell:

  ```powershell
  $env:NEUROSYNCAPP_CONFIG_DIR = "C:\path\to\config"
  neurosyncapp
  ```

## Troubleshooting

- **`git` or `python` is not recognised:** install it from the links in [Before you start](#before-you-start), then close and reopen the terminal.
- **Windows says running scripts is disabled:** see the execution-policy note under [Windows](#windows), or use Command Prompt with `.venv\Scripts\activate.bat`.
- **`neurosyncapp` command is unavailable:** make sure the terminal is in the `NeuroSyncApp` folder and the environment is activated (see [Launch the app again](#launch-the-app-again)). If it still fails, run `python -m pip install .` with the environment activated.
- **`pip install .` reports an unsupported Python version:** the environment was created with an unsupported Python. Python 3.15 and newer are not supported yet. Delete the `.venv` folder and recreate it with Python 3.12, 3.13, or 3.14 (`py -3.14 -m venv .venv` on [Windows](#windows); a versioned command such as `python3.14 -m venv .venv` on [macOS](#macos) or Linux).
- **The app still looks old after `git pull`:** activate the environment and run `python -m pip install .` again.
- **PySide6 is not installed:** activate the environment and run `python -m pip install .` again.
- **A raw file is rejected:** select the original raw CSV/OFRS recording, not a processed DFer or PFer output. Confirm that the required time and channel columns are numeric.
- **DFer preview fails:** use a recording/window with at least about 120 seconds of numeric data and valid start/end values in seconds.
- **PFer rejects a CSV:** select a DFer output containing `t_min` and the expected dF/F columns, then check the baseline and peak settings.
- **Telemetry alignment is ambiguous:** choose the intended date/alignment candidate and verify that the associated files cover the same recording period.

## Development and tests

Contributors can install the editable development environment instead of the normal application install:

```bash
python -m pip install -e ".[dev]"
```

Run the test suite with Qt in headless mode:

Windows PowerShell:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q
```

macOS/Linux:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

Useful focused checks:

```bash
python -m pytest -q tests/unit/test_qt_lifecycle.py
python -m pytest -q tests/unit/test_raw_qt_app.py tests/unit/test_behaviour_qt_app.py tests/unit/test_telemetry_qt_app.py
```

## Distribution note

The recommended way to run NeuroSyncApp is the source-based Python installation described above. Changes between versions are recorded in [`CHANGELOG.md`](CHANGELOG.md).

## Example data

Example inputs are stored under `example_data/`:

- `example_data/photometry_behaviour` — processed photometry and behaviour-coding examples for the alignment workflow.
- `example_data/menopause_photometry` — photometry and telemetry spreadsheet examples.
- `example_data/menopause_stim` — optogenetic stimulation examples.

## Optional features

The runtime dependencies are declared in `pyproject.toml`. The optional extras are:

- `.[dev]` for pytest and coverage tools
- `.[html-plots]` for the legacy DFer/PFer Bokeh HTML plot exports

These extras are optional; the normal `python -m pip install .` installation already installs all required runtime packages. `pyproject.toml` is the source of truth for dependency versions.

## Attribution and license

The DFer/PFer workflow was ported from the Argotech/Tussock Innovation DFer_v1.4 and PFer_2.4 analysis scripts and README:
<https://www.argotech.co.nz/fibre-photometry>

The workflow is based on methods from GuPPy:

Sherathiya, V. N., Schaid, M. D., Seiler, J. L., Lopez, G. C., & Lerner, T. N. “GuPPy, a Python toolbox for the analysis of fiber photometry data.” *Scientific Reports* 11, 24212 (2021). <https://doi.org/10.1038/s41598-021-03626-9>

NeuroSyncApp is licensed under the GNU General Public License v3.0.
