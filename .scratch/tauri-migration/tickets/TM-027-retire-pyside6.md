# TM-027 - PySide6 retirement and combine_data decision

**Priority:** P3
**Depends on:** TM-022, TM-023, TM-025 (parity + release achieved)
**Blocks:** none
**Status:** proposed

## Context / evidence

The architecture note's final gate: "The existing PySide6 application remains
usable until the replacement passes feature and release validation"
(`.scratch/architecture/01-...md:95-96`). Today PySide6 is a hard dependency
(`pyproject.toml:16`), the entry point is `main.py` / `neurosyncapp` script
(`pyproject.toml:41`), and `combine_data` is a placeholder with no
implementation (`catalog.py:52-59`, README.md:14-16).

## Required work

1. Implement or drop `combine_data` (product decision, assumption Q3) before
   retirement so the catalog is complete or intentionally reduced.
2. After the Tauri build passes parity (Gate 4) and release validation
   (Gate 5): remove PySide6 from dependencies, delete `main.py`,
   `src/dashboard/*`, `src/gui/*`, `src/panels/*`, and the Qt-coupled tests;
   the Tauri host + sidecar are the only supported path.
3. Update README (installation, running, config, release instructions) and the
   CHANGELOG to describe the Tauri app.
4. Update `src/dashboard/catalog.py`-equivalent (frontend catalog) as the
   single source of truth for app definitions.
5. Leave legacy config-migration code in place (TM-017) so existing users'
   settings survive the cutover.

## Acceptance criteria

- [ ] combine_data outcome decided and implemented/dropped.
- [ ] Release validation checklist passes on all three targets with the Tauri
      build only.
- [ ] PySide6 removed from dependencies; no dead Qt modules remain.
- [ ] Docs describe the new app accurately (no stale PySide6 references).

## Risk

- Premature retirement would strand users; gate strictly on TM-022 + TM-025.
- The legacy config-migration path must remain even after Qt is gone.

## Validation strategy

- Full release checklist (install on clean Windows/macOS, run each app,
  process + export + settings restore).
- Dependency scan confirms no PySide6/matplotlib-qt imports remain.