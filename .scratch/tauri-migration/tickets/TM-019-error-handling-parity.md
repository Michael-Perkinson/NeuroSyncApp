# TM-019 - Error handling and validation parity

**Priority:** P2
**Depends on:** TM-001, TM-005
**Blocks:** none
**Status:** proposed

## Context / evidence

Current error UX is modal QMessageBox plus a shared translator:

- `src/gui/framework/messages_and_errors.py:10-72`: `describe_exception` maps
  KeyError/PermissionError/FileNotFoundError/parse errors to friendly text;
  `format_action_error` builds summary/cause/recovery; `show_action_error`
  logs then `QMessageBox.critical`.
- Validation sites to replicate: behaviour baseline (`data_service.py:47-84`),
  behaviour parameters (`:126-171`), axis ranges (`plot_service.py:704-761`),
  image settings (`src/processing/image_export.py:30-75`), out-of-range
  behaviour times (`manual_session_service.py:83-127`, `table_panel.py:126-143`),
  telemetry no-file / bad alignment time (`plot_service.py:1047-1076`),
  raw DFer/PFer errors (widget `:1095-1103, 1273-1281, 1373-1381`).
- Tests: `tests/unit/test_user_facing_errors.py`.

## Required work

1. Error envelope (TM-001) carries `code`, user text, recovery text, and
   optional structured details (e.g. missing columns) so the frontend renders
   consistent messages without parsing exception strings.
2. Replace modal dialogs with an async toast/notification + inline validation
   system in the webview; confirm dialogs (export confirm) become async
   (behaviour export confirm `aligned_behaviour_exporter.py:280-309`).
3. Port `describe_exception` text exactly so message wording is unchanged.
4. Keep a single registry mapping exception types -> user text in the sidecar
   (mirroring `describe_exception`) and test it.

## Acceptance criteria

- [ ] Every current warning/error path has a web equivalent with identical or
      clearer wording.
- [ ] Warnings are non-blocking (toast/inline); hard errors are recoverable.
- [ ] `tests/unit/test_user_facing_errors.py` scenarios pass against the new
      envelope/registry.

## Risk

- Low; the main cost is auditing every `QMessageBox` call site. Grep count is
  manageable across the three apps (each app service layer cited above).

## Validation strategy

- A parity checklist of every dialog call site -> new UI element.
- Automated: feed the error registry the known exception classes and assert
  user text.