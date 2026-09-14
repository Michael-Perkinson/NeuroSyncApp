# TM-026 - UX redesign for a modern scientific workstation

**Priority:** P3
**Depends on:** TM-002, TM-007
**Blocks:** none
**Status:** proposed

## Context / evidence

The PySide6 UI is functional but dated: a floating overlay sidebar
(`dashboard.py:62-84, 90-96`), Tk-style compatibility widgets
(`src/gui/framework/tk_compat_controls.py:9-52`, `tk_style_table.py`), modal
QMessageBox/QInputDialog/QColorDialog flows, and matplotlib's Qt toolbar for
interaction. The architecture note's stated motivation is "a modern, responsive
UI" with "greater freedom for layout, tables, charts, accessibility, and
interaction design" (`.scratch/architecture/01-...md:17-22`). Non-goal: "Porting
the existing Qt widgets one-for-one into web components" (`:102`).

## Required work (opportunities, not requirements — sized against parity work)

1. Persistent, resizable layout for data-selection / settings / graph panels
   (today everything is stacked in tabs/scroll areas).
2. Plot interactions: linked cursor/readout across trace + behaviour boxes,
   zoom-history, hover tooltips with values, copyable coordinates.
3. Tables: virtualized sorting/filtering (telemetry cluster table today is a
   Tk-style sortable table; a modern data grid is a clear win).
4. Themes (light/dark) and consistent typography/spacing; the webview makes
   this nearly free.
5. Workflow affordances: recent files, batch-processing hints, per-app
   onboarding for first-time DFer/PFer users (the README documents a long
   click-through flow).
6. Keyboard shortcuts and accessibility (the Qt app has none of note).

## Acceptance criteria

- [ ] Behaviour (tracer bullet) ships with the redesigned layout and plot
      interactions.
- [ ] Light/dark theme applies to all screens.
- [ ] No interaction regression vs the PySide6 feature set (parity harness
      still green).

## Risk

- UX polish competes with parity for time; keep redesign strictly additive to
  the parity-critical paths and behind the Gate 1 tracer bullet.

## Validation strategy

- Usability review walkthroughs; screenshot comparison against the current app
  and the `docs/readme_images/*.png` for visual progress.