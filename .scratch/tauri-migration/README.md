# NeuroSyncApp Tauri 2 Migration Audit

Read-only audit of the current checkout (`feat/tauri-migration`, dirty working
tree) for a PySide6-to-Tauri 2 migration. Produced without modifying source
code, tests, Git metadata, or existing user changes.

## Scope

- Feature parity for all four catalog apps (`raw_analysis`, `single_animal`,
  `telemetry_photom_opto`, `combine_data`).
- Python processing/UI seams.
- Tauri 2 + React/TypeScript frontend.
- Python sidecar packaging for Windows x64, macOS Apple Silicon, macOS Intel.
- IPC/data-transfer design for scientific data and plots.
- Persistence/settings/export compatibility.
- Error handling, cancellation, progress, security, offline behavior.
- Test strategy, UX redesign, release/CI implications.

## Artifacts

| File | Purpose |
| --- | --- |
| [migration-map.md](migration-map.md) | Phase plan, dependency ordering, feature-parity matrix, gate criteria. |
| [assumptions-and-questions.md](assumptions-and-questions.md) | Product decisions still required before implementation. |
| [tickets/](tickets/) | One file per actionable ticket (TM-001 .. TM-027). |

## Ticket index

### Phase 0 - Foundation (P0, blocking)
| ID | Title |
| --- | --- |
| [TM-001](tickets/TM-001-backend-contract-and-ipc.md) | Define backend service contract and IPC protocol |
| [TM-002](tickets/TM-002-tauri-react-scaffold.md) | Tauri 2 + React/TS scaffold and dashboard shell |
| [TM-003](tickets/TM-003-python-sidecar-lifecycle.md) | Python sidecar process lifecycle |
| [TM-004](tickets/TM-004-data-transfer-serialization.md) | Data-transfer and plot-spec serialization layer |
| [TM-005](tickets/TM-005-job-manager-progress-cancel.md) | Job manager: progress, cancellation, error envelopes |

### Phase 1 - Behaviour alignment (P1, tracer bullet)
| ID | Title |
| --- | --- |
| [TM-006](tickets/TM-006-behaviour-backend-port.md) | Port behaviour alignment backend to headless service |
| [TM-007](tickets/TM-007-behaviour-react-frontend.md) | Behaviour alignment React frontend |
| [TM-008](tickets/TM-008-behaviour-web-plots.md) | Web plot rendering for behaviour |
| [TM-009](tickets/TM-009-behaviour-export-parity.md) | Behaviour export parity (Excel + figures) |

### Phase 2 - Raw photometry (P1)
| ID | Title |
| --- | --- |
| [TM-010](tickets/TM-010-raw-photometry-backend-port.md) | Port DFer/PFer backend to headless service |
| [TM-011](tickets/TM-011-raw-photometry-react-frontend.md) | Raw photometry React frontend |
| [TM-012](tickets/TM-012-raw-photometry-job-flows.md) | Wire DFer/PFer flows through the job manager |

### Phase 3 - Telemetry (P1/P2)
| ID | Title |
| --- | --- |
| [TM-013](tickets/TM-013-telemetry-backend-port.md) | Port telemetry backend (associated files, clusters) |
| [TM-014](tickets/TM-014-telemetry-plot-service-headless.md) | Telemetry plot_service headless refactor |
| [TM-015](tickets/TM-015-telemetry-react-frontend.md) | Telemetry React frontend |
| [TM-016](tickets/TM-016-telemetry-export-parity.md) | Telemetry workbook export parity |

### Phase 4 - Persistence, parity, hardening (P2)
| ID | Title |
| --- | --- |
| [TM-017](tickets/TM-017-settings-persistence-compat.md) | Settings/persistence compatibility |
| [TM-018](tickets/TM-018-dashboard-catalog-parity.md) | Dashboard and catalog parity |
| [TM-019](tickets/TM-019-error-handling-parity.md) | Error handling and validation parity |
| [TM-020](tickets/TM-020-security-hardening.md) | Security hardening |
| [TM-021](tickets/TM-021-offline-large-data.md) | Offline behavior and large-data responsiveness |

### Phase 5 - Release, UX, retirement (P3)
| ID | Title |
| --- | --- |
| [TM-022](tickets/TM-022-test-strategy-parity-harness.md) | Test strategy and parity harness |
| [TM-023](tickets/TM-023-sidecar-packaging.md) | Sidecar packaging (Win x64, macOS AS, macOS Intel) |
| [TM-024](tickets/TM-024-signing-notarization.md) | Signing and notarization |
| [TM-025](tickets/TM-025-ci-cd-tauri-action.md) | CI/CD migration to Tauri release pipeline |
| [TM-026](tickets/TM-026-ux-redesign.md) | UX redesign for a modern scientific workstation |
| [TM-027](tickets/TM-027-retire-pyside6.md) | PySide6 retirement and combine_data decision |

## Constraint notes

- The parent approved local ticket artifacts only. No production source, test,
  or Git changes were made.
- Current uncommitted work is treated as part of the migration baseline:
  PFer detection fixes and the standalone "Select DFer CSV" flow
  (`src/dfer/df_plots.py`, `src/dfer/pfer.py`, `src/dfer/pfer_detection.py`,
  `src/features/raw_photometry/photometry_processing_widget.py`), plus the new
  tests `tests/unit/test_pfer_detection.py` and the extended
  `tests/unit/test_raw_qt_app.py`. These must not be lost or reverted during
  the migration.
- `.scratch/repo-correctness-audit/issues/01-05` document five telemetry/
  behaviour defects already resolved in local commits; each is a regression
  risk that the parity harness (TM-022) must keep covered.