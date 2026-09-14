# TM-018 - Dashboard and catalog parity

**Priority:** P2
**Depends on:** TM-002
**Blocks:** none
**Status:** proposed

## Context / evidence

- Catalog: `src/dashboard/catalog.py:27-62` defines four apps
  (`raw_analysis`, `single_animal`, `telemetry_photom_opto`, `combine_data`),
  `DEFAULT_APP_ID = "raw_analysis"` (`:62`). `combine_data` is a placeholder
  (`:52-59`).
- Dashboard: `src/dashboard/dashboard.py` sidebar + content swap
  (`:26-225`); remembers last app (`_load_initial_app` `:205-219`, `save_state`
  `:162`); unload guard `:119-156`; placeholder card for non-Qt apps `:165-184`.
- Tests: `tests/dashboard/test_feature_catalog.py`,
  `tests/unit/test_app_catalog.py`.

## Required work

1. Frontend catalog mirroring `AppDefinition` (id, label, description,
   availability) in TypeScript, with the same labels.
2. Last-app restore on startup (via TM-017) and default to `raw_analysis`.
3. Placeholder screen for `combine_data` pending the product decision
   (assumption Q3).
4. App-switch cleanup: today the PySide6 dashboard carefully destroys Qt
   widgets and cancels worker callbacks on switch (`dashboard.py:139-156`); in
   Tauri this becomes cancel-active-jobs-on-switch + state reset.

## Acceptance criteria

- [ ] The four tools render with the same labels/descriptions.
- [ ] Reopening the app lands on the last-used tool.
- [ ] Switching tools cancels/cleans up any running job (TM-005).

## Risk

- Low.

## Validation strategy

- Reuse `tests/dashboard/test_feature_catalog.py` logic as a frontend unit test
  (label/id/description parity).