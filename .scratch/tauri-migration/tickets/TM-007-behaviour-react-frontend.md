# TM-007 - Behaviour alignment React frontend

**Priority:** P1 (behaviour tracer bullet)
**Depends on:** TM-002, TM-006
**Blocks:** none
**Status:** proposed

## Context / evidence

PySide6 behaviour UI pieces to port (all cited from the audit):

- Data selection: photometry file + multi-signal column selection
  (`CheckableColumnSelector`, `src/gui/framework/checkable_column_selector.py:47-169`),
  baseline window with Save Baseline (`src/gui/views/data_selection_panel.py:159-183, 301-332`),
  mouse-name prompt (`QInputDialog`, `:266-272`).
- Behaviour input: CSV import and column-mapping modal (behaviour/start/end
  columns + time unit), `src/gui/views/behaviour_event_input_frame.py:196-218`,
  persisted via `column_mapping_store.py:21-50`.
- Static inputs: pre/post time, bin size (`src/gui/views/static_inputs_frame.py:81-97`,
  `static_inputs_service.py:19-58`).
- View modes: Full Trace, Single Row, Behaviour Mean and SEM, plus a
  dynamically added Z-scored mode when baseline is on
  (`ui_builder.py:157-161`; `data_selection_panel.py:312-322`).
- Options panel: behaviour visibility checkboxes + colours
  (`views/options_panel.py:16-115`).
- Table panel with negative-time warnings (`views/table_panel.py:126-143`).
- Graph settings: line width, box height/alpha, duration bars, time units,
  tick spacing, axis ranges, zeroing (`src/panels/graph_settings_sections.py`,
  `plot_service.py:693-826`).

## Required work

1. Implement each screen as a React component bound to a typed view-state model
   (mirroring `BehaviourViewState` in
   `src/features/behaviour_alignment/models.py:8-26` and the shared panel state
   in `src/gui/framework/view_state_models.py`).
2. Replace modal dialogs (QInputDialog mouse name, QColorDialog, column-mapping
   dialog) with async web dialogs/color pickers.
3. Reproduce the multi-signal workflow: overlay selection, per-signal trace/SEM
   colours, single `Summary Results` sheet semantics preserved in export.
4. Preserve the out-of-range-behaviour and negative-time warnings as inline
   notices.
5. Wire all operations through the job manager (TM-005) so file load/export
   never blocks.

## Acceptance criteria

- [ ] Every PySide6 behaviour screen/interaction has a working web equivalent.
- [ ] Column mapping persists across sessions via the same JSON schema.
- [ ] Baseline save/restore behaves identically (including the validation
      messages from TM-019).

## Risk

- The Tk-style `ObservableValue` binding layer
  (`src/gui/framework/tk_compat_controls.py:9-52`) is Qt/Tk-specific; the web
  port needs a real reactive state layer (React state / zustand), and
  reproducing every two-way binding is fiddly.

## Validation strategy

- Manual parity walkthrough against the PySide6 app using the same example
  files, with a check-off list per screen.
- E2E (Playwright) for the primary flows once TM-022 lands.