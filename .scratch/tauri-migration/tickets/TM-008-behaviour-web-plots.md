# TM-008 - Web plot rendering for behaviour

**Priority:** P1 (behaviour tracer bullet)
**Depends on:** TM-004, TM-006
**Blocks:** none
**Status:** proposed

## Context / evidence

Behaviour plotting today is matplotlib in place (`plot_service.py:288-543`):
`plot_full_trace`, `plot_single_row`, `plot_mean_and_sem_trace`,
`plot_z_scored_data`. Supporting draw helpers in
`src/processing/behaviour_plotting.py` and `graph_plotter.py:242-411`
(draw_trace, draw_sem_band, draw_behaviour_boxes, draw_duration_bar). Zeroing
logic (`plot_service.py:764-826`), axis-range apply (`:693-761`), and SEM
band computation (`behaviour_metrics.py:141-171`) must all survive as data.

Current figure is created once at `plot_service.py:136-137`
(`create_styled_figure`, `qt_graph_canvas.py:27-34`) and figure export does
`copy.deepcopy(app.fig)` (`plot_service.py:833`) — this only works because a
live figure exists in memory, which a web frontend does not have.

## Required work

1. Drive the web chart from the plot spec (TM-004): traces, SEM bands, behaviour
   boxes, duration bars, axis configuration, time-unit scaling, zeroing.
2. Interactive requirements that matplotlib's Qt toolbar gave users: zoom/pan,
   axis-range editing (reuse the axis popup
   `src/panels/graph_settings_dialogs.py:129-168`), and view-mode switching
   without re-requesting data from the sidecar.
3. Per-signal independent trace/SEM colours (multi-signal overlay).
4. Golden parity: render the same spec with matplotlib Agg and the web chart;
   visually equivalent output for the same inputs.

## Acceptance criteria

- [ ] All four behaviour view modes render from the plot spec.
- [ ] Zoom/pan and axis-range editing behave like the matplotlib toolbar.
- [ ] Zeroing the x-axis to a selected behaviour matches PySide6 output.
- [ ] Image export (PNG/SVG/EPS/TIFF/JPG) still works via sidecar Agg.

## Risk

- Behaviour boxes/duration bars are visually dense; pixel-parity tolerance must
  be defined (label placement, box geometry — recently fixed in
  `bebae74`/`6a681cc`).
- No charting library choice yet (assumption Q2).

## Validation strategy

- Golden-image diff between Agg render and web render at a small set of
  canonical inputs.
- Manual comparison against the PySide6 graph for the example
  `example_data/photometry_behaviour` files.