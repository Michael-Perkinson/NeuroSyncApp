# TM-022 - Test strategy and parity harness

**Priority:** P2 (grows with each port; gates Gate 4)
**Depends on:** TM-004, TM-005
**Blocks:** TM-027
**Status:** proposed

## Context / evidence

Current test setup: pytest (`pytest.ini`), Qt tests run with
`QT_QPA_PLATFORM=offscreen` (README.md:142-155), integration tests use example
data and golden workbooks (e.g. `tests/integration/test_behaviour_alignment_output.py:96-208`,
`test_behaviour_alignment_multi_column_export.py`). Telemetry plot tests stub
matplotlib with Agg and monkeypatch dialogs (`tests/unit/test_telemetry_plot_service.py:5-17, 273-276`).
`tests/unit/test_telemetry_app_startup.py` is fully skipped (5 lines).

`.scratch/repo-correctness-audit/issues/01-05` record five resolved defects
(activity-only cluster display, nighttime shading units, z-score baseline
overlap, sample-count preservation, single-row binning) that must not regress.

## Required work

1. Keep the pure-core pytest suite (no PySide6) running in the sidecar repo;
   move Qt-coupled tests into a separate profile.
2. **Parity harness**: a golden-file diff harness that runs the same input
   through the PySide6 implementation and the Tauri sidecar, comparing:
   - DFer/PFer CSVs (byte-level), behaviour + telemetry workbooks (content),
   - figure exports (pixel diff), plot specs (JSON),
   - cluster records, extracted windows, table data.
   This harness gates every app port (Gate 4).
3. Sidecar integration tests: drive the real sidecar binary over the real IPC
   transport (spawn, auth, methods, cancel, shutdown).
4. Frontend E2E (Playwright) for the three apps' primary flows against a
   sidecar test fixture.
5. Regression tests mirroring audit issues 01-05 and the current uncommitted
   PFer fixes (`tests/unit/test_pfer_detection.py`).
6. Test matrix in CI: unit (pure), sidecar IPC, frontend unit, E2E, parity.

## Acceptance criteria

- [ ] Parity harness reports zero diffs for the golden corpus at Gate 4.
- [ ] Regression tests for audit issues 01-05 and PFer changes run in CI.
- [ ] Sidecar can be exercised without any GUI (headless IPC tests).
- [ ] E2E covers load -> process -> graph -> export for all three apps.

## Risk

- Moderate: golden corpus must be curated (representative single/dual,
  multi-signal, overnight telemetry); pixel-diff tolerance must be tuned to
  avoid flakiness.

## Validation strategy

- CI job fails on any parity diff.
- Coverage report tracked for the pure-core suite (target: keep current
  coverage; `.[dev]` has coverage/pytest-cov, `pyproject.toml:34-38`).