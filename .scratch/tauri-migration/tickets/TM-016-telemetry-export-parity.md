# TM-016 - Telemetry workbook export parity

**Priority:** P1/P2
**Depends on:** TM-013
**Blocks:** none
**Status:** proposed

## Context / evidence

Telemetry exporter is already pure pandas + `xlsxwriter`
(`pd.ExcelWriter(engine='xlsxwriter')`) with no PySide6/matplotlib imports —
ideal for the sidecar. Structure
(`exporters/workbook_exporter.py:62-101`):
1. Summary sheet with overview rows, cluster settings, sheet guide with
   hyperlinks (`summary_sheet_exporter.py:13-88, 150-377`).
2. Per-peak-count cluster sheets with Full/Day/Night binned means and cluster
   details (`cluster_sheet_exporter.py:9-105, 108-374`).
3. Raw sheets with downsampled photometry preview and navigation hyperlinks
   (`raw_sheet_exporter.py:12-131, 193-210`).
4. Intercluster intervals (`signal_sheet_exporter.py:14-25`).
5. Native-rate temp/act sheets, full-cluster and fixed-window variants
   (`signal_sheet_exporter.py:28-53`; `export_frames.py:57-365`).

Grouping: photometry clusters by peak count, stim clusters by cluster size;
Full/Day/Night split via `annotate_clusters_with_time_period`
(widget `:469-485`). Column widths set at workbook level (widget `:1710-1715`).

## Required work

1. Export runs as a sidecar job (TM-005) using the headless cluster outputs
   from TM-013.
2. Preserve sheet order, names, grouping, hyperlinks, and column widths
   exactly.
3. Preserve the unwritable-cell-skip warning behavior
   (`raw_sheet_exporter.py:168-174`).
4. Figure saving for telemetry through sidecar Agg (formats/DPI/custom size
   via `export_options_panel.py:108-137, 200-262`).

## Acceptance criteria

- [ ] Golden workbook equality for the menopause example inputs.
- [ ] Grouping rules (peak count, stim size, Full/Day/Night) match.
- [ ] Export errors surface as structured envelopes with the current recovery
      text.

## Risk

- Low-moderate: exporter is already pure. Main risk is input data shapes from
  the refactored backend (TM-013) — keep the exporter's frame contracts as the
  interface boundary.

## Validation strategy

- Re-run `tests/unit/test_telemetry_exporter.py` headless.
- Add golden workbook fixture comparison to the parity harness (TM-022).