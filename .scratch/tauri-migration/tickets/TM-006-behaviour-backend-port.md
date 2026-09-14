# TM-006 - Port behaviour alignment backend to a headless service

**Priority:** P1 (behaviour tracer bullet)
**Depends on:** TM-001, TM-004
**Blocks:** TM-007, TM-008, TM-009
**Status:** proposed

## Context / evidence

The behaviour feature (`src/features/behaviour_alignment`) is the recommended
first port (`.scratch/architecture/01-...md:71-79`) because it has explicit view
state, services, tables, plots, and an exporter. Today the services are coupled
to Qt:

- `services/data_service.py:5` imports `QMessageBox`; baseline/z-score logic at
  `:47-84` and parameter validation at `:126-171`.
- `services/plot_service.py:8,23-27` imports `QMessageBox` and matplotlib Qt
  canvas helpers; plot functions at `:288-543` mutate figures in place.
- `services/manual_session_service.py:10` imports `QMessageBox`; warning logic
  at `:83-127`.
- `io/behaviour_file_pipeline.py:11-12` uses `file_dialogs.select_csv_file`
  (`QFileDialog`) and `messages_and_errors`.
- Services read widget fields directly, e.g.
  `data_service.py:47-48` reads `app.data_selection_frame.baseline_start_entry`,
  `manual_session_service.py:98` reads the synchronize entry.
- Pure logic already isolated: `src/processing/behaviour_input_parser.py:76-130`
  (CSV parse + out-of-range detection), `behaviour_metrics.py:281-307`
  (z-score), `behaviour_window_extractor.py:28-69`, `behaviour_plotting.py`.

## Required work

1. Extract a headless pipeline in the sidecar that takes a typed request
   (paths, signals, baseline, static inputs, behaviour mapping) and returns
   results (frames, summary metrics, warnings), with **no Qt imports**.
2. Move the QMessageBox-modal behaviours into the error/validation envelope
   (TM-001) returned by the pipeline (warnings as data, not dialogs).
3. Replace widget-field reads with explicit parameters (inject view state via
   the request).
4. Keep `src/processing/*` and `src/excel_ops/*` unchanged; wrap them.
5. Produce the table/summary payloads the frontend needs (per-behaviour aligned
   frames, Event Duration, baseline stats).

## Acceptance criteria

- [ ] The behaviour pipeline runs headless (no PySide6, no QApplication) and
      returns the same data as the current widget for identical inputs.
- [ ] All behaviour services no longer import Qt.
- [ ] Warnings (out-of-range times, negative adjusted times) are returned in
      the result envelope, not raised as dialogs.

## Risk

- The synchronous freezes on large files move into the sidecar; must be paired
  with the job manager (TM-005) so the UI stays responsive.
- Behaviour "app state" is scattered across widget attributes; enumerating all
  inputs is the main discovery risk.

## Validation strategy

- Re-run existing unit/integration tests against the headless pipeline
  (e.g. `tests/unit/test_behaviour_data_service.py`,
  `tests/integration/test_behaviour_alignment_output.py:96-208`) with Qt
  monkeypatched away.
- Golden comparison of returned frames vs current in-memory frames.