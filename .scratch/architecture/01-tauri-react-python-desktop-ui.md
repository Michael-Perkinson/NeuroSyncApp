# 01 - Build a modern local-first desktop UI with Tauri

**Priority:** High

**Status:** proposed

**Tracking:** Untracked planning ticket. No external issue or ticket ID.

## Decision

Evaluate and prototype a Tauri desktop application with a React/TypeScript
frontend and a bundled local Python processing backend. Keep the existing
PySide6 application operational during migration and retire it only after
feature parity and release validation.

## Why

The application needs a modern, responsive UI while retaining reliable local
file workflows on Windows and macOS. A pure browser application cannot provide
the same native file-manager experience. Tauri provides native dialogs and
desktop integration while the web frontend provides greater freedom for layout,
tables, charts, accessibility, and interaction design.

The Python processing and export implementation should remain local and be
reused rather than rewritten in JavaScript or Rust. Recordings must not need to
leave the user's computer.

## Proposed architecture

- Tauri owns the desktop window, native open/save/folder dialogs, remembered
  directories, opening output folders, backend lifecycle, and packaging.
- React and TypeScript own the application screens, view state, tables, charts,
  progress states, and user interaction.
- A local Python backend owns workflow orchestration, file loading, scientific
  processing, plotting data preparation, and Excel/image exports.
- The frontend communicates with the local backend through a small explicit
  interface over localhost or a controlled sidecar protocol.
- The backend binds to localhost only and uses a per-launch capability or token
  so it is not an unauthenticated network service.

## File workflow requirements

- Remember the last selected data and telemetry directories in the existing
  platform-specific settings.
- Open native file and directory pickers at the remembered locations.
- Return real Windows and macOS paths to the Python backend.
- Preserve automatic discovery of associated temperature and activity files.
- Allow exports to be written beside source files or to a user-selected path.
- Open generated output folders in Windows Explorer or macOS Finder.
- Report protected-folder, missing-drive, read-only, and cloud-sync failures
  clearly without losing the completed analysis.

## Migration seams

Create deep, UI-independent interfaces around these workflows before porting
screens:

- load a recording session and associated files
- run DFer/PFer, behaviour alignment, or telemetry alignment
- return serializable plot data, labels, annotations, and axis metadata
- return table data and analysis summaries
- run exports and return output paths
- report progress, cancellation, validation errors, and recoverable warnings

Remove direct dependencies on Qt widgets, `QMessageBox`, `QFileDialog`, and
Matplotlib Qt canvases from processing and orchestration modules. Keep native
dialogs and desktop notifications in adapters at the Tauri seam.

## Suggested order

1. Prototype the Behaviour alignment workflow because it has an explicit view
   state, services, tables, plots, and exporter.
2. Add the local Python backend interface without changing scientific results.
3. Build the React screen against that interface.
4. Convert plot implementations to return serializable plot specifications;
   retain Matplotlib for static image export where appropriate.
5. Migrate Raw Photometry.
6. Migrate Telemetry last because of its associated-file discovery, cluster
   state, overlays, and multi-file plotting.
7. Add Windows and macOS packaging, signing, notarization, install, upgrade,
   and real file-manager end-to-end tests.

## Acceptance criteria

- The app runs offline on supported Windows and macOS versions.
- A user can select a directory, close the app, reopen it, and start in the
  previously selected directory.
- A user can select a main recording and associated files using native dialogs.
- Analysis results remain local and exports can be saved to a user-selected
  location without requiring administrator privileges.
- Windows Explorer and macOS Finder can open generated output folders.
- Large example recordings remain responsive through backend jobs and plot
  downsampling or decimation.
- Scientific outputs match the existing PySide6 implementation.
- The existing PySide6 application remains usable until the replacement passes
  feature and release validation.

## Non-goals

- Rewriting the scientific algorithms in JavaScript or Rust.
- Uploading recordings to a hosted service.
- Porting the existing Qt widgets one-for-one into web components.
- Introducing a second UI without first defining the backend interfaces.
