# 01 - Prevent Single Cluster Display crash without temperature telemetry

**Priority:** High

**Status:** resolved

**Resolution:** Fixed in local commit `87675ed`.

**What to fix:** Selecting Single Cluster Display must work when an alignment contains Activity telemetry but no Temperature telemetry.

Evidence: `src/features/telemetry_alignment/services/plot_service.py:1039-1045` explicitly permits either telemetry file, but `src/features/telemetry_alignment/views/display_mode_presenter.py:369-372` unconditionally reads `self.app.temp_data["Time (min)"]`.

Reproduction: load a photometry recording with only an Activity file, select a cluster, and open Single Cluster Display. The presenter raises `TypeError: 'NoneType' object is not subscriptable` before the existing optional-overlay checks run.

- [ ] Activity-only cluster display renders without an exception.
- [ ] Temperature-only and Activity-plus-Temperature displays still render.
- [ ] A regression test covers `temp_data=None`.
