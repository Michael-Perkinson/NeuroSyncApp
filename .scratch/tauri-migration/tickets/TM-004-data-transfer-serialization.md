# TM-004 - Data-transfer and plot-spec serialization layer

**Priority:** P0 (foundation)
**Depends on:** TM-001
**Blocks:** TM-005, TM-006, TM-008, TM-010, TM-013, TM-014, TM-021, TM-022
**Status:** proposed

## Context / evidence

All scientific data crosses the process boundary as numpy/pandas arrays and
matplotlib figures today. Key observations:

- DFer computes plain dicts of numpy arrays (`df_single.py:64-74`,
  `df_dual.py:75-81`) and writes CSVs via `np.savetxt`
  (`df_single.py:144-152`, `df_dual.py:154-162`).
- Behaviour and telemetry plot functions mutate a matplotlib `Figure`/`Axes`
  in place and return `None` (`plot_service.py:288-543`, telemetry
  `plot_service.py:594-674`), then embed the figure in `FigureCanvasQTAgg`
  (`qt_graph_canvas.py:27-34`; embed at behaviour `plot_service.py:181`).
- Telemetry plot data is not serializable anywhere; the 1216-line service
  (telemetry `plot_service.py`) needs a Qt event loop and a live canvas.
- CSV output naming is a compatibility contract (see migration-map.md).

## Required work

1. Array encoding: define how numpy arrays transfer over IPC. For large traces
   (up to tens of millions of samples) use a binary-efficient encoding
   (MessagePack / raw bytes with dtype+shape headers) rather than base64 JSON;
   keep JSON for small metadata. Enforce a size limit with a decimation plan
   (TM-021) for display payloads.
2. Plot spec schema: a JSON-serializable description covering everything the
   three apps draw:
   - traces (x, y, labels, twin-axis membership), SEM bands, error bars
   - rectangles/boxes (behaviour boxes `graph_plotter.py:242-411`, cluster
     boxes `plot_service.py:643-649, 914-921`), duration bars
   - vertical spans (nighttime `axvspan`, telemetry `plot_service.py:109-115`)
   - annotations (peak counts `plot_service.py:654-662`), markers
   - axis configuration (time-unit scaling min/s/h, tick spacing, axis range,
     zeroing, time-of-day ticks `plot_service.py:387-459`)
   - figure title/labels/legend metadata
3. Rasterization bridge: keep matplotlib Agg available in the sidecar to render
   the same plot spec to PNG/SVG/EPS/TIFF/JPG for image export and golden
   comparison (TM-009, TM-016).
4. Table data: typed columnar schema (name, dtype, values, units) for the
   telemetry table and behaviour table panels.

## Acceptance criteria

- [ ] 1e5-1e6-sample arrays round-trip with acceptable latency and memory.
- [ ] Plot spec schema covers every element enumerated above, and a rendering
      of the spec by both the web charting layer and matplotlib Agg produces
      visually equivalent output.
- [ ] Table schema covers all current table views.
- [ ] Golden fixtures: existing example_data CSV/Excel flows produce identical
      plot specs before/after refactor.

## Risk

- Rewriting plot_service to emit specs is the highest-effort refactor of the
  whole migration (especially telemetry's 1216-line file). Spec schema changes
  are expensive; version it (see TM-001).
- Double-rendering (web + Agg) doubles plot code unless the spec is the single
  source of truth.

## Validation strategy

- Property tests: for random inputs, plot spec -> Agg render matches the
  current matplotlib output on golden images (pixel diff within tolerance).
- Latency benchmarks recorded in CI for representative example files.