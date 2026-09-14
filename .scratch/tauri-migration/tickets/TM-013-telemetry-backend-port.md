# TM-013 - Port telemetry backend (associated files, clusters)

**Priority:** P1/P2
**Depends on:** TM-001, TM-004
**Blocks:** TM-015, TM-016
**Status:** proposed

## Context / evidence

Telemetry is the largest and most complex app
(`src/features/telemetry_alignment/telemetry_processing_widget.py`, 1780
lines). Backend-relevant pieces:

- Associated-file auto-discovery:
  `io/associated_file_locator.py:192-243` (`retrieve_associated_files` scans
  the main file's dir, then a saved telemetry folder, then a manual picker).
  Date extraction `:182-190`, zero-padding variants `:18-27`, previous-day
  fallback `:53-71`, macOS `._` resource-fork exclusion `:93-97, 197-201`.
  The module imports `QFileDialog` at `:11` only for the manual folder picker —
  that picker moves to the frontend native dialog; the scan logic is pure.
- Cluster detection: `services/cluster_analysis.py` wraps
  `src/processing/cluster_detection.py` — peak detection
  (`cluster_detection.py:318-334`), `identify_clusters` (`:25-143`), cluster
  grouping by peak count (`:171-177`), longest-cluster windows (`:180-207`),
  window processing (`:210-250`).
- Stimulation clusters from opto metadata (`calculate_stim_timings`,
  `telemetry_processing.py:389-417`; `static_input_builders.py:93-149`).
- Telemetry recording IO: duplicate-timestamp drop
  (`telemetry_recording_io.py:286-289`), >10% missing-data warning (`:296-304`),
  ambiguous alignment date error (`:17-25, 208-217`), extraction edge cases
  (`:332-342`).
- Settings: `io/static_settings_store.py` (cluster/stim inputs),
  `AppSettingsManager(app_type="telemetry_photom_opto")` (widget `:154`).
- Correctness fixes already resolved (`.scratch/repo-correctness-audit/`
  issues 01, 02, 04, 05) are regression risks to lock in.

## Required work

1. Headless service operations: discover associated files (pure scan), load
   recordings (temp/act/photometry), detect photometry peaks + clusters,
   compute stim timings, build per-cluster windows with pre/post times.
2. Move the manual-folder-picker and the ambiguous-date choice out of the
   service into the UI layer (the `QInputDialog` choice at
   `plot_service.py:136-198` becomes a frontend dialog).
3. Return cluster/table data via the typed table schema (TM-004).
4. Preserve all edge-case behavior covered by the audit issues and existing
   tests (`tests/unit/test_telemetry_processing.py`,
   `test_telemetry_associated_file_locator.py`,
   `test_telemetry_processing_extended.py`).

## Acceptance criteria

- [ ] Associated-file discovery returns identical matches to the current
      implementation (including previous-day fallback and zero-padding cases).
- [ ] Cluster/stim detection outputs match (peak counts, cluster bounds, stim
      windows) for the same inputs.
- [ ] No Qt imports remain in telemetry `services/`, `io/`, `processing/`.

## Risk

- High: cross-file state (temp/act/photometry), ambiguous dates, overnight
  recordings. The resolved audit issues (01-05) show the surface area; parity
  tests are essential.

## Validation strategy

- Re-run existing telemetry unit tests headless.
- Golden comparison of cluster records and extracted windows on the
  `example_data/menopause_*` samples.
- Regression tests for each resolved audit issue are part of TM-022.