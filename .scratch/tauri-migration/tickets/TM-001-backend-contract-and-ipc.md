# TM-001 - Define backend service contract and IPC protocol

**Priority:** P0 (foundation)
**Depends on:** none
**Blocks:** TM-003, TM-004, TM-005, TM-006, TM-010, TM-013, TM-017, TM-019
**Status:** proposed

## Context / evidence

The proposed architecture requires "a small explicit interface" between the
frontend and the local backend (`.scratch/architecture/01-tauri-react-python-desktop-ui.md:36-39`),
with six deep seams to build before porting screens (`:53-67`): load a recording
session and associated files; run DFer/PFer, behaviour alignment, or telemetry
alignment; return serializable plot data, labels, annotations, and axis
metadata; return table data and analysis summaries; run exports and return
output paths; report progress, cancellation, validation errors, and recoverable
warnings.

Today the entry points are the Qt widgets: `main.py:20-36` routes to a tool
window or dashboard; `src/dashboard/catalog.py:8-24` lazily imports a widget
class per app. There is no headless API.

## Required work

1. Write an API/contract document (the "deep interface") listing operations per
   app:
   - session/file loading (`load_recording`, `discover_associated_files`)
   - processing (`run_dfer`, `run_pfer`, `run_behaviour_alignment`,
     `run_telemetry_alignment`, `run_cluster_detection`)
   - plot data (`get_plot_spec`, `get_table_data`, `get_summary`)
   - exports (`export_workbook`, `export_image`)
   - lifecycle (`ping`, `shutdown`, `cancel`)
2. Choose the transport (see assumptions Q1: stdio JSON-RPC recommended) and
   define the message envelope: request id, method, params, result, error
   `{code, user_text, recovery, details}`, and event channel for
   progress/log/cancel.
3. Version the protocol (request/response `protocol_version`) so the frontend
   and sidecar can be released independently.
4. Define a TypeScript client and a Python server skeleton that both implement
   the same spec, with schema tests shared between them.

## Acceptance criteria

- [ ] API spec document exists with every operation typed (params/result/error).
- [ ] A Python stub server and a TypeScript client both pass the same
      schema/contract tests.
- [ ] `ping` round-trips through the live transport with protocol version check.
- [ ] Error envelope is used by all operations (no raw exception strings on the
      wire).

## Risk

- Contract churn is the most expensive thing to change later; any ambiguity
  now propagates to every port. Mitigate with typed schemas and contract tests.
- Over-modeling (designing for future apps) delays the behaviour tracer bullet.

## Validation strategy

- Contract tests run in CI for both sides of the interface (Python + TS).
- Golden scenario: `ping` -> load example data -> run one processing op ->
  return plot spec and table data -> export -> shutdown, all without a GUI.