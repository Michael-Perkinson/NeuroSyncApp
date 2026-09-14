# TM-010 - Port DFer/PFer backend to a headless service

**Priority:** P1
**Depends on:** TM-001, TM-004
**Blocks:** TM-011, TM-012
**Status:** proposed

## Context / evidence

The DFer/PFer compute core is already Qt-free — a big advantage:
- `src/dfer/` and `src/processing/` have **zero** PySide6 imports; only
  matplotlib `Figure` objects and lazy bokeh imports (`df_plots.py:182-313`,
  `pfer_plots.py:20-21`, `bokeh_html_plots.py:25`).
- File-type detection: `detect_photometry_file_type` (`df_common.py:119-135`).
- DFer outputs: single `np.savetxt` (`df_single.py:144-152`), dual
  (`df_dual.py:154-162`); PFer stats/waveform CSVs (`pfer.py:24-59, 81-82`),
  `run_pfer` returns a newline-joined path list for dual files
  (`pfer.py:155-157`).
- The Qt widget orchestrates workers (`photometry_processing_widget.py:811-826`),
  log plumbing to the panel (`:588-612`), and PNG-only image saving
  (`:1193-1209`).
- Current uncommitted work changes PFer detection semantics
  (`src/dfer/pfer_detection.py`, `src/dfer/df_plots.py`) and adds a standalone
  "Select DFer CSV" flow (`photometry_processing_widget.py:1285-1323`); this is
  baseline behavior to preserve.

## Required work

1. Wrap `compute_options`, `run_analysis`, and `run_pfer` as typed service
   operations (TM-001) returning the existing data dicts plus serialized plot
   specs (TM-004).
2. Move option titles/validation text into the contract (validation via
   `ValueError` today, e.g. `df_common.py:177-180` window <120s,
   `pfer_detection.py:45-49` baseline <5 min) so the frontend can render them.
3. Keep output-file naming and CSV schemas byte-identical
   (df_common.py:145-156).
4. Decide fate of the legacy bokeh HTML export path (`make_plots=True` never
   set by the widget today — see assumption Q9).

## Acceptance criteria

- [ ] `compute_options` / `run_analysis` / `run_pfer` run headless via IPC and
      produce identical CSVs to the current implementation (byte comparison).
- [ ] Validation errors surface as structured error envelopes with the same
      user text.
- [ ] Single and dual channel paths both covered, including the new
      standalone-PFer flow.

## Risk

- Low: the core is already pure. Main risk is wrapping it without changing
  behavior; the dirty working tree's PFer changes are in-flight and must be
  the locked baseline.

## Validation strategy

- Re-run `tests/unit/test_pfer_detection.py`, `tests/unit/test_raw_qt_app.py`
  (`:464-533` end-to-end DFer->PFer worker test), and df_common tests against
  the headless service.
- Golden CSV comparison for single/dual example inputs.