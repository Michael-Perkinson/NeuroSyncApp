# TM-015 - Telemetry React frontend

**Priority:** P1/P2
**Depends on:** TM-002, TM-013, TM-014
**Blocks:** none
**Status:** proposed

## Context / evidence

PySide6 telemetry UI to port (`telemetry_processing_widget.py`):

- Main recording selection with signal-column chooser and mouse-name prompt
  (`:791-799`; `src/gui/views/data_selection_panel.py:185-272`).
- Associated temp/act entries + manual override buttons (`:827-873`,
  `:1319-1349`).
- Lights-off and start-time inputs (defaults 19:00:00, models.py:14,
  settings_defaults.py:46).
- Graph/Table tabs (`:435-446`); sortable table via `TkStyleTable`
  (`views/cluster_table_panel.py:16-67, 101-137`).
- Temperature/activity overlay button and per-trace toggles
  (`:932-943`; `views/graph_settings_panel.py:12-57`).
- Cluster options: per-cluster-size colours, select/deselect all, peak
  alignment input, save peak alignment (`:975-1138`; `choose_cluster_color`
  `:1114-1122`).
- Graph settings incl. time unit, remove-first-60-min toggle, axis ranges.
- Label settings dialog (`views/label_settings_dialog.py`).
- Export Options and Save Image (`:1664-1780`).

## Required work

1. Port all tabs/controls as React components with identical defaults and
   enable/disable rules.
2. Sortable cluster table fed by the table schema (TM-004).
3. Cluster colour selection and peak-alignment index inputs with the same
   invalid-input fallback (defaults to last peak, widget `:1071-1112`).
4. Overlay toggles, time-unit switching, and remove-first-60-min behavior
   driven by the plot spec (TM-014).
5. Workbook export and figure save wired through the job manager (TM-005).

## Acceptance criteria

- [ ] Full telemetry workflow (select files -> auto-discover -> detect clusters
      -> refine display -> export) works end-to-end in the webview.
- [ ] Table/graph parity with PySide6 for the menopause example data.
- [ ] Ambiguous-date and no-telemetry-file paths show equivalent prompts/
      messages.

## Risk

- High complexity + high interaction density; the sortable Tk-style table
  (`src/gui/framework/tk_style_table.py`) and per-cluster options are the
  fiddliest parts. Keep the PySide6 app available as reference during porting.

## Validation strategy

- Manual parity walkthrough per tab on `example_data/menopause_photometry`
  and `menopause_stim`.
- E2E flows once TM-022 lands.