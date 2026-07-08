# Changelog

## [Unreleased] - PySide6 rewrite

### CI

- Updated `python-app.yml` to build with PySide6, install from `pyproject.toml`, target Python 3.14, and publish Windows plus macOS zip artifacts.

### Changed

- Migrated the UI from Tkinter to PySide6 with `QWidget`-based app widgets.
- `main.py` now launches a PySide6 dashboard and can also launch a specific tool with `--tool`.
- Replaced `requirements.txt` with `pyproject.toml` and platform-specific tested package snapshots under `requirements/`.

### Added

- `src/app/catalog.py` - central registry (`APP_DEFINITIONS`) that maps tool IDs to their PySide6 widget classes.
- `src/app/dashboard.py` - dashboard shell and tool launcher.
- `src/gui/shared/qt_view_styles.py` - shared palette, stylesheet helpers, and button roles.
- `src/gui/shared/qt_graph_canvas.py` - reusable Matplotlib-in-Qt canvas helpers.
- `src/gui/shared/qt_log_handler.py` - Qt log handler for in-app logging.
- `src/gui/shared/qt_table_adapter.py` - adapter from pandas data frames to `QTableWidget`.
- `src/gui/shared/qt_bindings.py` - small compatibility controls for PySide6 views.
- `src/gui/views/data_selection_panel.py`, `src/gui/views/export_options_panel.py`, and `src/shared/ui/graph_settings_panel.py` - PySide6 replacements for old Tkinter panels.
- `src/features/raw_photometry/app.py` - "Analyse Raw Data" Qt tool with file loading, raw graphing, window selection, DFer, and PFer.

### Removed

- All Tkinter-specific modules: `tk_graph_canvas.py`, `tk_log_handler.py`, `tk_state.py`, `tk_styles.py`, `tkinter_widgets.py`, `ui_elements.py`, `window_manager.py`, `create_main_frame.py`, and `data_selection_state.py`.
- Legacy view files: `data_selection_frame_legacy.py`, `export_options_container.py`, `graph_settings_container.py`, and `tk_dashboard.py`.
- `src/core/ttk_styles.py` - Tkinter/ttk styling.
- `src/processing/instance_controller.py` - replaced by controller classes in the Qt views.
- `REFACTOR_PLAN_telemetry.md` and `REFACTOR.md` - planning documents.

## [0.1.0] - 2024 initial release

- Tkinter GUI for aligning fibre photometry data with coded behaviour events.
- Single-animal photometry and behaviour alignment.
- Telemetry, photometry, and optogenetics alignment.
- CSV and XLSX data loading.
- AUC, max amplitude, and mean dF/F export to Excel.
- Configurable graph settings saved and loaded via `AppSettingsManager`.
