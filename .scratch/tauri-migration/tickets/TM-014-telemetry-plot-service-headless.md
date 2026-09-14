# TM-014 - Telemetry plot_service headless refactor

**Priority:** P1/P2
**Depends on:** TM-004
**Blocks:** TM-015
**Status:** proposed

## Context / evidence

`src/features/telemetry_alignment/services/plot_service.py` is 1216 lines of
in-place matplotlib against a live Qt canvas, with **no serialization
anywhere** (grep for json/serialize/dumps returns nothing). Highlights:

- Figure preparation with time-unit scaling (`:562-592`), time-of-day ticks
  (`:387-459`), 60-minute-trim offset (`:257-262, 290-331`).
- Photometry figure with cluster rectangles and peak-count annotations
  (`:594-674`), overlay Y-axis scaling for temp (`:676-803`) and activity
  (`:805-876`, `ax.hist` at `:859-867`), SEM bands (`:732-738`), nighttime
  `axvspan` shading (`:109-115`), stim overlays (`:901-923`), per-cluster
  window slicing (`:925-943`).
- `views/display_mode_presenter.py:311-341` adds stims to the single-cluster
  display; `:369-382` clamps to trace end.
- Tests already stub matplotlib with Agg and exercise methods in isolation
  (`tests/unit/test_telemetry_plot_service.py:5-17, 69-110, 225-424`).

## Required work

1. Split the service into (a) pure computation that returns a plot spec +
   computed data (windows, overlays, scaling), and (b) a thin renderer. This is
   the hard part of the whole migration (see TM-004 risk).
2. Represent temp/act overlay Y-axis scaling math (`:676-876`) and nighttime
   period computation (`:49-65`) as data in the spec.
3. Keep matplotlib Agg as the golden renderer (TM-004) so existing tests keep
   passing against the spec.
4. Preserve single-cluster window clamping and degenerate-axis handling
   (`:778-781`; non-finite filtering `:690-697, 773-776, 819-826`).

## Acceptance criteria

- [ ] The service runs headless (no QApplication, no canvas) and emits a
      serializable spec for the full and single-cluster displays.
- [ ] Agg rendering of the spec reproduces current figures (pixel diff within
      tolerance) for minutes/seconds/hours and time-of-day units.
- [ ] Existing `test_telemetry_plot_service.py` assertions keep passing,
      adapted to spec-based output.

## Risk

- Very high effort; highest-risk file in the codebase. Do not start until
  TM-004's plot-spec schema is stable and behaviour (TM-008) proves the
  approach.

## Validation strategy

- Golden image diffs across units (min/s/h/time-of-day), overlay combos (temp
  only, act only, both — see audit issue 01), and single-cluster edge cases.
- Property tests on random traces.