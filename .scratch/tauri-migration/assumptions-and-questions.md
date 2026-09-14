# Assumptions and Open Questions

Product/architecture decisions that must be resolved before or during
implementation. Each is listed with the evidence that frames it and the tickets
it affects.

## Blocking decisions

1. **IPC transport (blocks TM-001, TM-003, TM-004).**
   Two options for frontend <-> sidecar communication:
   - (A) JSON-RPC 2.0 over **stdio** to a sidecar process spawned by Tauri
     (Rust owns the pipe). No network socket, simplest auth story (inherited
     process identity), recommended default for Tauri 2 sidecars.
   - (B) HTTP/JSON on **localhost with a per-launch token**, as the current
     architecture note suggests (`01-...md:37-39`, "binds to localhost only and
     uses a per-launch capability or token"). Easier to debug in a browser but
     adds a network service to harden.
   Trade-off: (A) is more secure by construction; (B) makes sidecar usable
   independently (e.g., for tests or a browser dev mode). **Recommendation:
   (A) stdio with a token handshake, keep the protocol JSON-RPC-shaped so (B)
   remains a drop-in later.**

2. **Web charting library for scientific plots (blocks TM-008, TM-014, TM-015).**
   The PySide6 app renders everything through matplotlib `Figure` objects
   embedded in `FigureCanvasQTAgg` (e.g. `plot_service.py:136-181`,
   `qt_graph_canvas.py:27-34`). A web port needs one of:
   - A JS charting library (uPlot / ECharts / Plotly.js / lightweight-charts)
     fed by a serializable plot spec from the sidecar.
   - Server-side rasterization to PNG/SVG via matplotlib Agg and image blobs.
   Requirements that must be met: multi-trace overlays, SEM bands
   (`plot_service.py:732-738`), twin y-axes for temp/act
   (`plot_service.py:700-707, 828`), behaviour boxes and duration bars
   (`graph_plotter.py:242-411`), cluster rectangles and peak annotations
   (`plot_service.py:643-662`), nighttime `axvspan` shading (49-65, 109-115),
   time-of-day tick generation (387-459), time-unit scaling (minutes/seconds/
   hours) for all three apps, and pixel parity with the existing matplotlib
   renders for golden tests. **Recommendation: a JS library with a strict plot
   spec schema; keep matplotlib Agg only for static image export and golden
   comparison (TM-009, TM-016).**

3. **combine_data future (blocks catalog parity, TM-018, TM-027).**
   `combine_data` is a dashboard placeholder with no Qt implementation
   (`catalog.py:52-59`, README.md:16). Decide: implement it in Tauri (new
   scope), port a future legacy version, or drop it from the catalog.

4. **Python runtime for the sidecar (blocks TM-023).**
   Current release uses PyInstaller one-file/one-dir with Python 3.14
   (`python-app.yml:12-138`). Options for the Tauri sidecar:
   - PyInstaller `--onedir` per target triple (faster startup than onefile),
   - `uv`-built standalone binaries / `uv build --standalone`,
   - pyoxidation / Nuitka.
   Decide startup-time budget and binary-size budget; current dependencies are
   numpy, pandas, scipy, matplotlib, openpyxl, XlsxWriter, platformdirs
   (`pyproject.toml:15-24`), so the sidecar is heavy either way.

## Decisions that shape UX and release

5. **Auto-update mechanism.** Today users download release artifacts manually
   (`python-app.yml:229-235`). If Tauri auto-update
   (`tauri-plugin-updater`) is wanted, it is the only network feature the app
   will ever have; confirm it is acceptable given the fully offline design
   (no network imports anywhere in `src/`, confirmed by grep). Affects TM-025.

6. **macOS signing/notarization credentials.** Current workflow only does
   ad-hoc codesign (`python-app.yml:142-144`, no notarization, no stapling).
   A Developer ID certificate and App Store Connect API key are required for a
   notarized, Gatekeeper-clean release (TM-024). Windows Authenticode is
   optional but recommended.

7. **Legacy settings/config migration.** Settings live as JSON in
   `NEUROSYNCAPP_CONFIG_DIR` (default platformdirs per-user dir) with legacy
   repo-local fallbacks (`app_paths.py:32-59`, `settings_store.py:28-44`,
   `dashboard_state.py:39-54`). Decide whether existing users' settings carry
   over unchanged (recommended: keep the same config directory and JSON
   schemas; Tauri owns the directory, sidecar writes files) or a fresh-start
   reset. Affects TM-017.

8. **Typical data scale.** No perf budget exists today; behaviour and telemetry
   run fully synchronously on the GUI thread (telemetry even calls
   `QApplication.processEvents()` to keep painting alive, widget:959).
   Assume recordings up to tens of millions of samples for the downsampling/
   decimation design in TM-021, and confirm real-world file sizes from example
   data during implementation.

9. **Bokeh HTML plot export.** `bokeh` is optional and only reachable when
   `make_plots=True`, which the current widget never sets
   (`photometry_processing_widget.py:1229,1338`; `df_plots.py:181-313`). In a
   Tauri webview the browser already renders plots natively, so these legacy
   HTML exports may be dropped or re-implemented as downloads. Decide whether
   to keep them for feature parity.

10. **Rust toolchain ownership.** Tauri adds a Rust host layer. Confirm the
    team/toolchain can build and maintain Rust code (dev and CI), or scope the
    Rust surface to the absolute minimum (window, dialogs, sidecar spawn,
    packaging).

## Working assumptions (no decision needed, stated for transparency)

- The PySide6 app must remain usable and shippable until the Tauri build passes
  feature and release validation (architecture note non-goals: no second UI
  without first defining backend interfaces; keep PySide6 operational).
- The app stays fully local/offline; recordings never leave the user's machine.
- The scientific algorithms are ported to Python sidecar unchanged, never
  rewritten in JavaScript or Rust.
- Output file naming/locations are part of the compatibility contract and must
  not change (see migration-map.md parity contract).
- Current uncommitted PFer/DFer work and the resolved correctness-audit issues
  (01-05) are part of the baseline that the parity harness must lock in.
- App version is currently 3.0.0 (`pyproject.toml:7`); the Tauri release should
  carry the same version number for continuity.