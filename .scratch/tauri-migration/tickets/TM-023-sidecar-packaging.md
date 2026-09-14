# TM-023 - Sidecar packaging parity (Windows x64, macOS AS, macOS Intel)

**Priority:** P3
**Depends on:** TM-003, TM-006/010/013 (processing ready)
**Blocks:** TM-024, TM-025
**Status:** proposed

## Context / evidence

Current release builds one PyInstaller artifact per platform, Python 3.14:
Windows `--onefile` (`python-app.yml:39-55`), macOS `--windowed` app bundle
(`:122-138`), runners `windows-latest`, `macos-15` (Apple Silicon),
`macos-15-intel` (Intel) (`:12-13, 76-82`). Dependencies
(`pyproject.toml:15-24`): PySide6, matplotlib, numpy, pandas, openpyxl,
platformdirs, scipy, XlsxWriter; `.[build]` adds Pillow + PyInstaller (`:30-33`).
Requires-python >=3.12,<3.15 (`:10`).

For Tauri the Python compute ships as a **sidecar**: Tauri bundles an external
binary per target triple. PySide6/matplotlib-qt are no longer needed in the
sidecar, which should shrink it.

## Required work

1. Build the sidecar as a standalone binary per target: Windows x64, macOS
   arm64, macOS x86_64 (decision per assumption Q4 — PyInstaller onedir
   recommended for startup speed; alternative uv standalone).
2. Strip PySide6 from the sidecar build (compute only). Keep numpy, pandas,
   scipy, matplotlib (Agg), openpyxl, XlsxWriter, platformdirs.
3. Configure Tauri `externalBin` for the sidecar with matching target triples
   and version pinning.
4. Preserve debug-ability: current macOS build ships a Debug.command helper
   (`python-app.yml:150-191`); provide an equivalent sidecar log/health debug
   script.
5. Record startup time and binary size per target; set a budget.

## Acceptance criteria

- [ ] Sidecar runs without a Python install on Windows x64, macOS AS, macOS
      Intel.
- [ ] Tauri bundle includes the correct sidecar per target triple.
- [ ] Cold-start sidecar latency within the agreed budget (assumption Q4).
- [ ] Sidecar and app versions are pinned together.

## Risk

- PyInstaller + numpy/pandas/scipy cross-target issues; macOS Intel wheels for
  scipy/pandas must exist (check availability for Python 3.14).
- Startup latency of the heavy sidecar; mitigate with onedir and lazy imports.

## Validation strategy

- CI: build each target and run a smoke (`ping` + one analysis + shutdown)
  inside the built bundle.
- Manual: launch on each OS from Finder/Explorer, run the debug script.