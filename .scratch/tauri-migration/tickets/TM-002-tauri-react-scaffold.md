# TM-002 - Tauri 2 + React/TypeScript scaffold and dashboard shell

**Priority:** P0 (foundation)
**Depends on:** none
**Blocks:** TM-007, TM-011, TM-015, TM-018, TM-026
**Status:** proposed

## Context / evidence

The current shell is a Qt `QMainWindow` dashboard with a floating sidebar and
four catalog entries (`src/dashboard/dashboard.py:26-225`; catalog in
`src/dashboard/catalog.py:27-62`). The dashboard remembers the last active tool
and opens it next time (`dashboard.py:205-219`, `save_state` at `:162`).
The app is registered as a console script `neurosyncapp` (`pyproject.toml:41`)
and launched via `main.py`.

There is no Node/`package.json`/`tauri.conf.json`/Vite/React in the repo today
(confirmed by tree scan).

## Required work

1. Scaffold a Tauri 2 app with Vite + React + TypeScript in a new
   `app/` (or `src-tauri/` + `web/`) workspace, pinned Tauri 2 crates.
2. Recreate the dashboard shell: tool sidebar with the four catalog apps,
   last-app restore (read `app_state.json` via TM-017), window sizing and
   title. Note the current floating-overlay sidebar behaviour
   (`dashboard.py:62-84, 90-96`) can be replaced with a normal layout.
3. Wire Tauri native open/save/folder dialogs, remembered-directory handling,
   and "open output folder in Explorer/Finder" adapters behind the contract
   from TM-001.
4. Configure webview: CSP that disallows remote content (see TM-020), app
   icon, window config, offline-bundled assets only.
5. Dev workflow: `npm run tauri dev` with the sidecar from TM-003 attached.

## Acceptance criteria

- [ ] `tauri dev` and `tauri build` succeed on Windows and macOS.
- [ ] Dashboard renders the four catalog tools; opening an app restores the
      last-used one.
- [ ] Native file/folder dialogs open at remembered directories.
- [ ] "Open output folder" opens Explorer/Finder for a generated path.
- [ ] No network requests are made by the webview (CSP enforced).

## Risk

- Tauri 2 + Rust toolchain is new to the repo (no existing Rust/Node code);
  bootstrap risk is the first Rust build and sidecar spawn.
- Webview behavior differences between Windows WebView2 and macOS WKWebView.

## Validation strategy

- Smoke test on each OS (Windows x64, macOS AS, macOS Intel): app launches,
  dialogs work, remembered directory persists across restart.
- Keep the PySide6 app running in parallel; compare dashboard behavior by eye
  against golden screenshots.