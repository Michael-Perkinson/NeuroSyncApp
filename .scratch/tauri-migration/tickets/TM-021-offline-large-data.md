# TM-021 - Offline behavior and large-data responsiveness

**Priority:** P2
**Depends on:** TM-004, TM-005
**Blocks:** none
**Status:** proposed

## Context / evidence

- The app must run fully offline (architecture note acceptance: "The app runs
  offline on supported Windows and macOS versions"; "Large example recordings
  remain responsive through backend jobs and plot downsampling or decimation",
  `.scratch/architecture/01-...md:84-94`).
- Today behaviour and telemetry load whole CSVs synchronously on the GUI thread
  (`behaviour_input_parser.py:76`; telemetry `update_idletasks` via
  `QApplication.processEvents()`, widget:959). No downsampling exists.
- Telemetry raw sheets already down-sample photometry for export
  (`workbook_exporter._prepare_photometry_export_frame`,
  `raw_sheet_exporter.py:29-53`), a pattern to reuse.

## Required work

1. Display-path decimation: when sending plot payloads over IPC, decimate to a
  bounded number of points per series (with min/max-preserving or
  LTTB-style downsampling for peaks); keep full-resolution data in the sidecar
  for export and exact analyses.
2. Progressive load: read CSV in chunks with progress (TM-005) rather than
  one blocking `pd.read_csv`.
3. Ensure plots remain responsive to zoom/pan after downsampling (re-request a
  window from the sidecar when zoomed in, or precompute pyramid levels).
4. Verify no hidden online dependency anywhere (offline smoke with network
  disabled).

## Acceptance criteria

- [ ] A multi-million-row recording loads and plots with visible progress and
      a responsive UI.
- [ ] Zooming into a decimated view shows full-resolution detail.
- [ ] All features work with the network disabled (offline smoke test).

## Risk

- Moderate: decimation must never change DFer/PFer/export results (only display
  payloads). Keep a strict separation: display-downsampled vs
  analysis-full-resolution.

## Validation strategy

- Performance benchmarks on generated large recordings (load time, IPC payload
  size, first-paint).
- Golden: analyses and exports on downsampled-display datasets equal
  full-resolution results.