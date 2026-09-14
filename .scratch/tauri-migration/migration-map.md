# Migration Map

Target: replace the PySide6 desktop app with a Tauri 2 desktop app, React +
TypeScript frontend, and a bundled local Python sidecar that owns file loading,
scientific processing, plotting-data preparation, and Excel/image exports.

The existing PySide6 app stays operational during migration and is retired only
after feature parity and release validation (see TM-027). This matches the
proposed architecture in `.scratch/architecture/01-tauri-react-python-desktop-ui.md`.

## High-level architecture

```
+-----------------------------------------------------------+
| Tauri 2 host (Rust)                                       |
|  - window, native open/save/folder dialogs                |
|  - sidecar process lifecycle + auth token                 |
|  - remembered directories, open-output-folder             |
|  - packaging, signing, updater                            |
+----------------------------+------------------------------+
                             | IPC (JSON-RPC over stdio or
                             |  localhost + per-launch token)
+----------------------------v------------------------------+
| Python sidecar (PyInstaller standalone per target)        |
|  - session/file loading (CSV, Excel, temp/act discovery)  |
|  - scientific processing: DFer/PFer, behaviour alignment, |
|    telemetry cluster detection                            |
|  - plot-data/spec preparation (numpy/pandas)              |
|  - exports: openpyxl/xlsxwriter workbooks, matplotlib     |
|    Agg PNG/SVG/EPS/TIFF/JPG, bokeh HTML                   |
+----------------------------+------------------------------+
                             | Tauri invoke / events
+----------------------------v------------------------------+
| React + TypeScript webview                                |
|  - screens for all four catalog apps                      |
|  - view state, tables, charts (web charting), progress,   |
|    cancellation, async dialogs, log panel                 |
+-----------------------------------------------------------+
```

## Feature-parity matrix (current state -> target)

| App | App ID | PySide6 status | Porting surface | Difficulty |
| --- | --- | --- | --- | --- |
| Analyse Raw Data | `raw_analysis` | Done (`src/features/raw_photometry`, catalog.py:29-35) | Compute core already Qt-free (`src/dfer/`, `src/processing/`); only widget + plotting + workers are Qt-bound | Medium |
| Align Photometry and Behaviour | `single_animal` | Done (`src/features/behaviour_alignment`, catalog.py:36-43) | Fully synchronous; services reach into Qt widgets; plot_service mutates matplotlib in place | High |
| Align Telemetry Data | `telemetry_photom_opto` | Done (`src/features/telemetry_alignment`, catalog.py:44-51) | Largest: 1780-line widget, 1216-line plot_service, associated-file discovery, cluster state | Very high |
| Combine Data | `combine_data` | Placeholder only (catalog.py:52-59; README.md:16) | No implementation exists; product decision required | n/a |

Key parity contract to preserve (all export/output file naming):
- DFer single output `{src}/dfof_results/{stem}_Data.csv`; dual
  `{src}/../dfof_results/{session}_Dual_Data.csv` (df_common.py:145-156).
- PFer `*_Peak_STATS.csv` / `*_Peak_WAVEFORM.csv` beside the DFer CSV
  (pfer.py:24-59).
- Plot PNGs in `plots/{recording}/` (widget photometry_processing_widget.py:1183-1191).
- Behaviour workbook `<stem>_NeuroBehaviorSync/<stem>[...].xlsx` with Summary,
  Event Duration, and per-behaviour sheets (behaviour_exporter.py:286-352).
- Telemetry workbook: Summary, per-peak-count cluster sheets, raw sheets,
  intercluster intervals, native signal sheets (workbook_exporter.py:62-101).

## Dependency graph (tickets)

```
Phase 0 (foundation, P0)
  TM-001 backend contract/IPC   <- everything depends on this
  TM-002 Tauri+React scaffold   (independent of TM-001; can start in parallel)
  TM-003 sidecar lifecycle      depends TM-001
  TM-004 data transfer/plot spec depends TM-001
  TM-005 job manager            depends TM-001, TM-004

Phase 1 (behaviour, tracer bullet)
  TM-006 behaviour backend      depends TM-001, TM-004
  TM-007 behaviour frontend     depends TM-002, TM-006
  TM-008 behaviour web plots    depends TM-004, TM-006
  TM-009 behaviour export       depends TM-006

Phase 2 (raw photometry)
  TM-010 raw backend            depends TM-001, TM-004
  TM-011 raw frontend           depends TM-002, TM-010
  TM-012 raw job flows          depends TM-005, TM-010

Phase 3 (telemetry)
  TM-013 telemetry backend      depends TM-001, TM-004
  TM-014 telemetry plot headless depends TM-004
  TM-015 telemetry frontend     depends TM-002, TM-013, TM-014
  TM-016 telemetry export       depends TM-013

Phase 4 (parity/hardening)
  TM-017 settings/persistence   depends TM-001
  TM-018 dashboard/catalog      depends TM-002
  TM-019 error handling parity  depends TM-001, TM-005
  TM-020 security hardening     depends TM-003
  TM-021 offline/large data     depends TM-004, TM-005

Phase 5 (release/UX/retirement)
  TM-022 test parity harness    depends TM-004, TM-005 (grows with each port)
  TM-023 sidecar packaging      depends TM-003, TM-006/10/13
  TM-024 signing/notarization   depends TM-023
  TM-025 CI/CD tauri-action     depends TM-023, TM-024
  TM-026 UX redesign            depends TM-002, TM-007 (starts with behaviour)
  TM-027 retire PySide6         depends TM-022, TM-023, TM-025 (parity achieved)
```

## Phase gates

1. **Gate 0 (foundation)**: a debug frontend can call a hello/ping through the
   live sidecar over the chosen IPC transport, with token auth, progress
   events, and a cancelled job that leaves no orphan process.
2. **Gate 1 (behaviour tracer bullet)**: a user can run the full behaviour
   workflow end-to-end in Tauri (select files, map columns, graph, export) with
   outputs matching the PySide6 golden workbooks, and the app stays responsive.
3. **Gate 2 (raw photometry)**: DFer/PFer run via job manager with progress and
   cancellation; outputs byte-identical to PySide6.
4. **Gate 3 (telemetry)**: full telemetry workflow including associated-file
   auto-discovery and workbook export.
5. **Gate 4 (parity)**: parity harness green across all three apps; settings
   migrate; security and offline checks pass.
6. **Gate 5 (release)**: signed/notarized installers on all three targets;
   PySide6 app retired.

## Suggested implementation order (from architecture note)

Behaviour first (explicit view state, services, tables, plots, exporter), then
Raw Photometry, then Telemetry last (associated-file discovery, cluster state,
overlays, multi-file plotting), then packaging/signing and real file-manager
end-to-end tests.