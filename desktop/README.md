# NeuroSyncApp desktop (React + Tauri) — Analyse Raw Data

Modern React/TypeScript screen for the **Analyse Raw Data** tool, driven by a
Tauri 2 process host and a headless Python sidecar. This migration slice does
not replace the PySide6 application; the PySide6 app stays the shippable build
until feature parity is validated.

The screen covers the raw photometry workflow: **Data Selection** (file/input
selection), **Signals** (signal/column context), the right-side **DFer/PFer
Settings** tabs (processing controls), and the **Raw Data / DFer Options / DFer
Results / PFer Results** graph tabs (plot/results). Connection status remains available from the top-right status indicator, and a compact activity log records sidecar operations.

Terminology mirrors the PySide6 app and the domain docs: single-channel
(405/465 nm) and dual-channel (470/560 nm) recordings, analysis window,
DFer option previews, DFer dF/F and Z-score results, and PFer peak finding.

## Browser preview

Node.js is the only runtime needed for the visible preview:

```bash
cd desktop
npm install
npm run dev
```

`npm run dev` explicitly selects `.env.demo`. It never starts Rust or Python;
the demo adapter simulates file loading, DFer option generation, final DFer
analysis, and PFer peak finding. Open `http://127.0.0.1:1420` if needed.

## Sidecar and protocol tests

The protocol is a four-byte big-endian length followed by UTF-8 JSON, with a 4 MiB frame limit. stdout is protocol-only and diagnostics use stderr.

```bash
cd desktop
python3 -m unittest discover -s sidecar/tests -v
# Includes framed-IPC raw single/dual DFer/PFer and PNG-export E2E coverage.
```

The isolated sidecar dependency definition includes NumPy, pandas, SciPy, Matplotlib/Agg, openpyxl, XlsxWriter, and platformdirs, and deliberately excludes PySide6:

```bash
python3 -m venv .venv-sidecar
source .venv-sidecar/bin/activate
python -m pip install -e sidecar
```

## Frontend checks

```bash
cd desktop
npm test
npm run lint
npm run build
```

## Native development and build

These commands require Cargo, Rust, Tauri system prerequisites, and the isolated sidecar environment:

```bash
cd desktop
npm run tauri dev
npm run tauri build
```

In development the host runs `python3 -m neurosync_sidecar` from `desktop/sidecar`. It automatically uses the repository `.venv` when present; `NEUROSYNC_SIDECAR_PYTHON` can select another interpreter. A release host looks for a co-bundled `neurosync-sidecar` executable beside the app executable; `NEUROSYNC_SIDECAR_EXECUTABLE` is an override.

The sidecar implements negotiation, diagnostics, raw single/dual photometry
loading, four DFer option previews, final DFer analysis, PFer peak finding, and
PNG plot export. Use `npm run tauri dev` for the real native flow. The browser
preview (`npm run dev`) intentionally uses the demo adapter and does not write
analysis files; this keeps it usable without Rust/Python.