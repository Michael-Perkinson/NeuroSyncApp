# TM-025 - CI/CD migration to the Tauri release pipeline

**Priority:** P3
**Depends on:** TM-023, TM-024
**Blocks:** none
**Status:** proposed

## Context / evidence

Current workflow `python-app.yml` runs only on `v*` tag pushes, builds one
Windows `.exe` and two macOS zips, and publishes a GitHub Release
(`:207-235`). There is no CI on pull requests, no test job in the workflow, no
auto-update, and no artifact signature/checksum verification beyond the build
steps.

## Required work

1. Add PR/CI validation: run the pure pytest suite, sidecar IPC tests, and
   frontend unit/E2E (TM-022) on every push, not just tags.
2. Replace the release build with Tauri (`tauri-action`) building Windows x64
   and macOS arm64 + x86_64, with sidecar builds from TM-023 and signing from
   TM-024; keep the existing artifact names/format continuity or document the
   change (currently `NeuroSyncApp_<tag>.exe`,
   `NeuroSyncApp_<tag>_macos-arm64.zip`, `_macos-intel.zip`).
3. Version alignment: sidecar version == app version (3.0.0 today,
   `pyproject.toml:7`) — single source of truth.
4. Optional: `tauri-plugin-updater` (assumption Q5) with a signed updater
   channel; otherwise keep manual-download releases.
5. Publish checksums and provenance for each artifact.

## Acceptance criteria

- [ ] Tag push produces the three installers from the Tauri pipeline with
      signing/notarization applied.
- [ ] PR CI is green on the full matrix (unit, sidecar IPC, frontend, parity).
- [ ] Release notes/checksums are generated automatically.
- [ ] Update flow (if adopted) upgrades in place without losing settings.

## Risk

- Moderate: GitHub Actions matrix complexity for Rust + Node + Python toolchains
  per target; runner availability for `macos-15-intel`.

## Validation strategy

- Release-validation checklist on all three targets (TM-024 installs + full
  workflow walkthrough).
- Rollback test for the updater if adopted.