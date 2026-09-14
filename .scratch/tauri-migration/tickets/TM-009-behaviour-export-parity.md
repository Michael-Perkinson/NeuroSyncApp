# TM-009 - Behaviour export parity (Excel + figures)

**Priority:** P1 (behaviour tracer bullet)
**Depends on:** TM-006
**Blocks:** none
**Status:** proposed

## Context / evidence

Export is the compatibility contract that must not drift:

- Excel workbook built by `src/features/behaviour_alignment/exporters/aligned_behaviour_exporter.py`
  (`:266-328` entry; sheet naming rules `:34-63`; multi-signal per-column
  sheets `:228-254`) plus `src/excel_ops/behaviour_exporter.py` formatting pass
  (`:528-628`). Golden integration tests exist:
  `tests/integration/test_behaviour_alignment_output.py:96-208` and
  `test_behaviour_alignment_multi_column_export.py`.
- File naming: `<stem>_NeuroBehaviorSync/<stem>[...].xlsx`, compact tags
  `dual_dfof` / `dual_Z` (`behaviour_exporter.py:286-352`); per-behaviour raw
  CSVs (`:140-147`).
- Figures: EPS/SVG/TIFF/PNG/JPG, default PNG, DPI default 600
  (`src/gui/views/export_options_panel.py:56-57, 110`); save via
  `figure_export.py:60-112` into `exported_images_<mouse>/...` with collision
  counter; image-request validation in `src/processing/image_export.py:30-75`.
- Export currently requires a live matplotlib figure
  (`plot_service.py:833` deepcopy) — must become spec-driven.

## Required work

1. Export runs in the sidecar as a job (progress via TM-005): build workbook
   from the headless pipeline outputs; render figures from the plot spec via
   matplotlib Agg.
2. Preserve exact sheet structure, ordering, naming, and formatting
   (bold rows, headerless Summary, signal banners).
3. Preserve file/folder naming and location rules exactly.
4. Replace the blocking confirmation question before export
   (`aligned_behaviour_exporter.py:280-309`) with an async confirm in the UI.
5. Figure export must not depend on a live figure: derive axes metadata
   (labels, units) from the spec.

## Acceptance criteria

- [ ] Golden workbook equality: identical bytes/content for the canonical
      integration tests, single-signal and multi-signal + baseline variants.
- [ ] Figure exports (all five formats, DPI, custom size/fonts) match PySide6
      output for the same plot spec.
- [ ] Exports land in the same folders with the same filenames.

## Risk

- openpyxl formatting rewrite is order-sensitive; the golden tests are the
  guard. Any pandas 3.x upgrade side-effects need monitoring
  (pandas>=3.0 in `pyproject.toml:20`).
- XlsxWriter (telemetry) and openpyxl (behaviour) both stay in the sidecar.

## Validation strategy

- Reuse `tests/integration/test_behaviour_alignment_output.py` and the
  multi-column variant as the parity harness baseline (TM-022).
- Add golden PNG/SVG diffs for figure export.