# TM-012 - Wire DFer/PFer flows through the job manager

**Priority:** P1
**Depends on:** TM-005, TM-010
**Blocks:** none
**Status:** proposed

## Context / evidence

Raw photometry is the only app with worker threads today
(`photometry_processing_widget.py:12,191,812`). Three jobs run on the
AnalysisWorker (`workers.py:10-26`): option preview (`:1064-1069`), DFer final
(`:1222-1235`), PFer (`:1330-1342`). Busy state disables buttons + wait cursor
(`:828-836`); close during run shows a "Still working" modal after a 3s wait
(`:627-652`). The worker emits only `finished`/`failed` — no progress, no
cancel.

## Required work

1. Migrate the three jobs to the job manager (TM-005): sidecar executes, emits
   progress and log events, accepts cancel.
2. Port the close-during-run behavior: cancel-and-close or background-continue
   with a notification; remove the blocking modal.
3. Preserve button-disable semantics during jobs (Run final, Run PFer, Select
   PFer, Apply window).

## Acceptance criteria

- [ ] Options preview, DFer final, and PFer report progress and can be
      cancelled.
- [ ] Closing the app during a run is clean (no orphan thread/process, no hang).
- [ ] Busy-state UI matches PySide6 (buttons disabled, cursor changed).

## Risk

- Low-moderate; cancellation of scipy.signal operations is only possible
  between stages (see TM-005 risk).

## Validation strategy

- Automated: start each job, assert progress events, cancel, assert no partial
  outputs and clean shutdown.
- Manual soak on large single/dual recordings.