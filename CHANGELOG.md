# Changelog

## [Unreleased] — PySide6 rewrite (branch: pyside6-rewrite)

### CI

- Updated `python-app.yml` to build with PySide6 (removes Tkinter, updates entry point to `main.py`, adds macOS `.dmg` job, splits into `build-windows` / `build-macos` / `release` jobs).

### Changed

- Migrated the entire UI from Tkinter to PySide6. All views, controllers, and shared widgets have been rewritten using `QWidget`-based components.
- `main.py` now launches a PySide6 `QApplication` with a central dashboard and tool launcher, replacing the old Tkinter root window.
- `requirements.txt` updated to reflect the new dependency set (PySide6, removed Tkinter-specific packages).

### Added

- `src/gui/shared/app_catalog.py` — central registry (`APP_DEFINITIONS`) that maps tool IDs to their PySide6 widget classes, used by the dashboard to launch tools on demand.
- `src/gui/shared/qt_view_styles.py` — shared colour palette (`PALETTE`), stylesheet helpers, and `apply_button_role()` for consistent button styling across all views.
- `src/gui/shared/qt_graph_canvas.py` — reusable Matplotlib-in-Qt canvas widget.
- `src/gui/shared/qt_log_handler.py` — Qt log handler that routes Python `logging` output to a `QTextEdit`.
- `src/gui/shared/qt_table_adapter.py` — adapter that bridges pandas DataFrames to `QTableWidget`.
- `src/gui/shared/qt_bindings.py` — thin compatibility shim for PySide6 imports.
- `src/gui/views/dashboard.py` — new home screen with tool cards for each app.
- `src/gui/views/data_selection_panel.py`, `export_options_panel.py`, `graph_settings_panel.py` — PySide6 replacements for the old Tkinter container frames.
- `src/main_apps/raw_photometry_processing_qt.py` — new PySide6 widget for the "Analyse Raw Data" tool, with file loading, column detection, raw data graph, and time-window selection.

### Removed

- All Tkinter-specific modules: `tk_graph_canvas.py`, `tk_log_handler.py`, `tk_state.py`, `tk_styles.py`, `tkinter_widgets.py`, `ui_elements.py`, `window_manager.py`, `create_main_frame.py`, `data_selection_state.py`.
- Legacy view files: `data_selection_frame_legacy.py`, `export_options_container.py`, `graph_settings_container.py`, `tk_dashboard.py`.
- `src/core/ttk_styles.py` — Tkinter/ttk styling, no longer needed.
- `src/processing/instance_controller.py` — replaced by the controller pattern in the new Qt views.
- `REFACTOR_PLAN_telemetry.md` — planning document, no longer needed.

## [0.1.0] — 2024 initial release

- Tkinter-based GUI for aligning fibre photometry data with coded behaviour events.
- Support for single-animal photometry + behaviour alignment.
- Telemetry + photometry + optogenetics alignment tool.
- CSV and XLSX data loading.
- AUC, max amplitude, and mean dF/F export to Excel.
- Configurable graph settings saved and loaded via `AppSettingsManager`.
