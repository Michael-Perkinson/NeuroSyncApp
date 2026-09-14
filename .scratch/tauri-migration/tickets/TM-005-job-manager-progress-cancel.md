# TM-005 - Job manager: progress, cancellation, error envelopes

**Priority:** P0 (foundation)
**Depends on:** TM-001, TM-004
**Blocks:** TM-012, TM-019, TM-021, TM-022
**Status:** proposed

## Context / evidence

Current concurrency is inconsistent across the three apps:

- Raw photometry: one `QThread` + `AnalysisWorker` per task emitting only
  `finished`/`failed` (`workers.py:10-26`); a busy state disables buttons and
  shows a wait cursor (`photometry_processing_widget.py:828-836`); **no
  progress and no cancellation**; closing while running shows a blocking
  "Still working" modal (`:636-640`).
- Behaviour: **fully synchronous** on the GUI thread; no threads, no progress,
  no cancellation (grep confirms `QThread` only appears in raw photometry).
- Telemetry: fully synchronous; keeps painting alive only via
  `QApplication.processEvents()` in `update_idletasks`
  (`telemetry_processing_widget.py:959`). Large exports block the UI.

## Required work

1. Job registry in the sidecar: each long-running operation gets a job id;
   clients start, poll/subscribe, and cancel jobs.
2. Progress protocol: staged progress events (percent, stage label, current
   file/operation) matching TM-001's event channel. Map existing long steps:
   DFer option preview, DFer final, PFer, behaviour load/export, telemetry
   cluster precompute, telemetry workbook export.
3. Cancellation: a cancel request propagates into the compute (check a token in
   loops where practical; otherwise cancel between stages) and cleans up partial
   outputs.
4. Frontend: a progress/cancel control replacing wait cursors and the
   "Still working" modal; close-during-run behavior becomes "cancel then close"
   or "keep running in background with a notification".
5. Log streaming: route the existing `logger.info` lines (raw DFer/PFer modules
   log progress, e.g. `df_single.py:90,109`; `pfer.py:129-146`) over the same
   event channel to the frontend log panel.

## Acceptance criteria

- [ ] Every long-running operation reports progress and is cancellable.
- [ ] A cancelled DFer/export leaves no partial/corrupt output files.
- [ ] Closing the app during a run does not hang or lose unrelated state.
- [ ] UI thread never blocks for more than a frame during processing.

## Risk

- Cancellation correctness in pandas/scipy loops (some stages are not cheaply
  interruptible); mitigations: cancel between stages, discard results after
  cancel.
- Behavioral change risk: PySide6 had no cancellation, so users are not
  expecting it; keep defaults safe.

## Validation strategy

- Automated tests: start job, assert progress events, cancel mid-run, assert
  cleanup and state.
- Manual soak with the largest example recordings on each OS.