# TM-011 - Raw photometry React frontend

**Priority:** P1
**Depends on:** TM-002, TM-010
**Blocks:** none
**Status:** proposed

## Context / evidence

PySide6 raw-photometry UI to port
(`src/features/raw_photometry/photometry_processing_widget.py`):

- Raw Data tab: raw trace with 405/465 (single) or 470/560 (dual) lines
  (`_draw_single_raw` `:937-968`, `_draw_dual_raw` `:970-986`).
- Analysis Window panel: start/end line edits, live duration label, Apply
  button updating red/blue `axvline` markers (`:416-472`, `_refresh_time_preview`
  `:990-1020`); aliases start/min/end/max (`:1031-1035`).
- DFer Options tab: "Preview option" dropdown (titles in
  `src/features/raw_photometry/plotting.py:39-44`), Signals selector
  Both/470nm/560nm enabled only for dual files (`:1118-1130`), option preview
  via `mpl_single_option_figure` (`plotting.py:102-131`).
- DFer tab: option radio buttons 1-4, Run final analysis (`:476-586`,
  `:1213-1235`), log panel (`:569-612`).
- DFer Results tab: dF/F vs Z-score combo, Show-405 checkbox (disabled for
  dual), Save image (`:284-318`, `:1134-1155`).
- PFer tab: Select DFer CSV, baseline window, prominence (default 0.003),
  artifact threshold (default 10), Run peak finder, Open PFer results
  (`:671-807`, `:1325-1342`); results via `mpl_pfer_figure` (`df_plots.py:132-174`).
- Settings persistence for default folder + last DFer option
  (`AppSettingsManager(app_type="raw_photometry_processing")`, widget `:181-182`).

## Required work

1. Recreate all tabs and controls as React components with the same labels,
   defaults, and enable/disable rules (e.g. Signals selector only for dual,
   PFer Run gated on a DFer CSV being selected).
2. Live window-marker updates: apply window updates markers and regenerates
   option previews without a full reload.
3. Log panel fed by the sidecar log stream (TM-005).
4. Save-image flow via sidecar Agg PNG at dpi=150 into the same
   `plots/{recording}/..._plot_{N}.png` naming (`:1163-1191`).
5. Restore/save the two persisted settings.

## Acceptance criteria

- [ ] Every tab/control/validation message from the PySide6 widget has a web
      equivalent.
- [ ] Window markers and duration label update identically (including alias
      inputs).
- [ ] Image export lands at the identical path with identical naming.

## Risk

- Medium: many small interactions; parity is interaction-level rather than
  algorithmic. The dual-file "both/470/560" preview selector logic
  (`:1107-1130`) must be ported exactly.

## Validation strategy

- Manual parity walkthrough on single and dual example recordings.
- Extend the existing `tests/unit/test_raw_qt_app.py` headless coverage to the
  web-equivalent flows (interaction specs).