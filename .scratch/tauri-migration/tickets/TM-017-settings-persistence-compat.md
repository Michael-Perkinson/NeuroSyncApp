# TM-017 - Settings/persistence compatibility

**Priority:** P2
**Depends on:** TM-001
**Blocks:** none
**Status:** proposed

## Context / evidence

Settings are JSON files in a per-user config dir with legacy fallbacks:

- Config dir resolution: `NEUROSYNCAPP_CONFIG_DIR` override, else
  `platformdirs.user_config_dir("NeuroSyncApp")`, else workspace fallback
  (`src/persistence/app_paths.py:10, 32-59`); `config_file_path`/`legacy_repo_file_path`
  helpers (`:55-63`).
- App settings: `settings_store.py:14-55` writes
  `{config_dir}/settings/{app_type}_settings.json`, falls back to repo-local
  `{app_type}_settings.json` (`:28-44`). `app_settings_manager.py` handles
  per-app keys (`raw_photometry_processing`, `align_photometry_and_behaviour`,
  `telemetry_photom_opto`) with legacy alias migration (`:17-21, 178-184`) and
  value validation (e.g. DFer option coerced to "1" `:174-175`).
- Dashboard state: `dashboard_state.py:14-54` (`state/app_state.json`, legacy
  `src/gui/shared/.neurosync/app_state.json`).
- Column-selection memory: `column_selection_memory.py:20-65`
  (`signal_column_selections.json`, keyed by column-title set).
- Feature-specific: `src/data/behaviour_settings_io.py:13-56`,
  `io/column_mapping_store.py:14-31` (column_names.json),
  `io/static_settings_store.py` (cluster/stim static inputs with legacy repo
  fallbacks `:172-198`).
- Repo files exist as legacy fixtures: `config/*.json`, `src/*.json`,
  `src/app_state.pkl` (see also src/gui/framework/.neurosync/app_state.json).

## Required work

1. Keep the exact same JSON schemas and the same config directory so existing
   user settings carry over unchanged. Tauri owns the directory location (or
   passes the existing one through `NEUROSYNCAPP_CONFIG_DIR` semantics); the
   sidecar writes files.
2. Expose settings via the contract (TM-001): get/set typed settings per app,
   plus legacy-file migration on first run (read repo-local legacy JSON, copy to
   per-user config, leave originals untouched).
3. Decide `src/app_state.pkl` fate (likely dead; confirm before dropping).
4. Add a schema version field going forward (read-old, write-new).

## Acceptance criteria

- [ ] A user's existing settings files load identically in the Tauri app.
- [ ] Legacy repo-local JSON is migrated (not deleted) on first run.
- [ ] Column-selection memory and dashboard last-app restore work across
      sessions.
- [ ] Writes remain atomic-ish and never crash on corrupted JSON (current
      behavior: warn + empty, `settings_store.py:34-42`,
      `column_selection_memory.py:32-37`).

## Risk

- Low-moderate; risk is schema drift during migration. Do not rename keys while
  PySide6 is still shippable (both apps may write the same files).

## Validation strategy

- Golden test: existing `config/*.json` fixtures load into the new settings
  service unchanged.
- Re-run `tests/test_persistence_paths.py`, `tests/unit/test_app_settings_manager.py`,
  `tests/unit/test_column_selection_memory.py`.