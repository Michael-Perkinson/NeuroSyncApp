# Architecture, dependency order, and release gates

## Architecture verdict: viable direction, unproven depth

Keep Python as the owner of scientific analysis and export. Keep React responsible for presentation and interaction, and Rust responsible for process lifecycle and native filesystem grants. Correct the diagram at migration-map.md:13-38: the actual call path is **React -> Tauri invoke -> Rust -> private child stdio -> Python**, with replies flowing back through Rust. Python cannot directly use Tauri invoke/events as the diagram appears to suggest.

TM-001 names reasonable operations, but a list of methods is not a deep module. Callers would still need to know the old widget's operation order, cache contents, time transforms, precompute prerequisites, and export preparation. This reproduces the current shallow `app` interface across three languages. Examples include telemetry `workbook_exporter.py:63-80` invoking precompute through the widget and `services/plot_service.py:362-385` mutating scientific and display state together.

The public interface should expose a small set of domain operations with typed workflow variants:

| Operation family | Interface contract |
| --- | --- |
| Open/replace/close session | Accept granted file identities plus workflow type and parsing choices. Return metadata, selected signals, warnings, session ID and revision, or a typed request for additional user input. Python owns full-resolution frames and their lifetimes. Replacement validates before publishing a new revision. |
| Submit analysis | Accept session/revision, workflow-specific parameters and an idempotency key. Return job ID promptly. Python orchestrates loading, alignment, calculation, cache invalidation and summary preparation. Return immutable result IDs when complete. |
| Query result | Obtain bounded table pages, summary and plot views using result ID, view options and viewport. Changing scientific options requires analysis; style-only changes need not recompute science. Rows and series have stable identities. |
| Export result | Accept result ID, a validated view revision for images, export options and an authorized output destination. Return a job and eventually an artifact manifest, warnings and output paths. Python prepares data and commits outputs safely. |
| Control/inspect jobs | Status, subscribe/reconcile, cancel, close session, health and shutdown. Define cancellation acknowledgement, terminal status and result validity separately. |

These are design families, not a demand for a generic `execute(any)` dispatcher. Keep discriminated workflow parameters so illegal combinations can be rejected. Native dialogs, settings operations and platform lifecycle can be separate adapters without exposing filesystem or widget implementation details to the webview.

A frontend must not round-trip full pandas frames just to send them back for export. It must not compute SEM, peak acceptance, interpolation, event-window slicing or native-rate export frames itself. A per-channel PFer result descriptor should include channel ID and stats/waveform artifacts; preserve the old newline-string Python return value in a compatibility adapter if that public interface remains supported. No identity should be reconstructed from filenames or formatted dropdown labels.

## Session, result and choice semantics

- One active analysis job per session initially; bounded global concurrency and queue. Keep queued parameter snapshots immutable. Mutating a session while a job runs either creates a new revision or is explicitly refused. State this per action.
- Analysis results identify their source file fingerprint, parsing options, selected signals, parameters and numeric dependency versions. Plot, table and export queries use the same result revision.
- View changes such as pan/zoom/colour are distinct from baseline, cluster threshold, alignment time and trim changes. Telemetry's current trim toggle recomputes cluster state; it is not only an x-axis decoration. Define invalidation using `plot_service.py:362-385` and label baseline changes at `views/label_settings_dialog.py:197-256` as evidence.
- An alignment-date conflict returns candidate IDs with local wall-clock values and coverage, not a generic exception or opaque label to parse. Cancel preserves the previous completed result. A chosen candidate is applied consistently to both telemetry signals. Native data are naive local timestamps (`pyproject.toml:56-59`); do not let JavaScript Date/timezone conversion silently shift them.
- Restart increments a sidecar epoch. Old handles fail with `session_lost` or `result_unavailable`; outstanding jobs terminate as failed/interrupted. UI parameter drafts and confirmed output paths may survive. Completed analysis survives only if a tested replay or durable snapshot mechanism has been implemented. Never promise to preserve memory after process death.
- Closing/switching tools uses one policy. Recommended baseline: ask to cancel an active job or stay, then switch only once cancellation/shutdown has reached a safe terminal state. Background execution is separate scope. Do not automatically destroy work merely because navigation occurred.

## IPC, transfer, and errors

Choose stdio for the first implementation. Tests can spawn and drive the same child without a browser; localhost is not needed to make the backend testable. A later HTTP transport is not a drop-in merely because both protocols use JSON. It needs origin/authentication, streaming, cancellation, reconnection and deployment decisions of its own.

Define UTF-8 framed messages, maximum frame size, buffering rules, partial/combined reads, malformed frame handling, timeout policy and backpressure. For Gate 0, bounded JSON metadata and decimated arrays are sufficient. Do not prematurely add MessagePack plus raw bytes. If later measurements justify binary transfer, specify framing, byte order, dtype, shape validation, checksums, ownership, cleanup, and the complete Python-to-Rust-to-webview path. A Tauri event carrying a copied array can erase Python-side efficiency gains.

Reserve stdout exclusively for protocol frames. Send diagnostics on stderr or through structured log events; keep bounded logs and redact launch tokens and unnecessary full data/path contents. A per-launch handshake identifies the expected child/protocol; it does not protect against arbitrary malicious code already running as the same user. Keep launch secrets out of the webview and command line.

Use one negotiated protocol/schema version with app/build identifiers and supported methods. Co-bundle compatible host/frontend/sidecar artifacts. Report a clear mismatch before accepting work. Reject unknown methods, duplicate/invalid IDs, oversized frames, invalid enum combinations, nonfinite numeric inputs, impossible array shapes and stale session revisions. Define null/NaN/infinity policies and safe integer limits; JSON cannot carry arbitrary numpy scalar values unchanged.

File grants must cover associated discovery and derived outputs deliberately: canonical path containment, symbolic-link/reparse-point policy, read versus write permission, grant lifetime and revocation, and revalidation if a file changes between selection and use. A dialog-returned main file does not grant the webview unrestricted access to its drive. Limit archive/spreadsheet expansion and parser allocations as well as IPC frames. Render user labels as text; export untrusted string values as literal spreadsheet data rather than executable formulas, while preserving intentional application-generated formulas/hyperlinks. Record any hardening deviation from legacy output in the compatibility ledger.

Errors distinguish validation, required user input, warnings, cancellation, retryable filesystem failures, protocol failures and backend death. Stable codes and field-specific details drive UI actions; friendly text is data, not the control protocol. Preserve the information in existing errors and allow reviewed wording improvements. Unknown exceptions have safe user text and local diagnostic IDs; TM-019 must not propagate `describe_exception`'s arbitrary fallback string as a public contract.

## Plot specification and testability

Use a domain plot model shared by a web adapter and a Matplotlib Agg adapter. Those are two real adapters at the seam. The model must be sufficient to render/export without an old Qt figure, but should not become a serialized Matplotlib object graph or expose arbitrary drawing commands.

Required primitives include panels/subplots, stable series identity, axes with units/origin/scale/limits, trace gaps, SEM bands, behaviour boxes, duration and onset markers, cluster spans and labels, stimulation spans, weighted activity bars with precomputed bin edges/values, legends and visibility. Coordinate space must be explicit: data units, axis fraction, or physical export dimensions. Behaviour box geometry (`graph_plotter.py:289-411`) and telemetry overlays (`plot_service.py:676-876`) make this distinction essential. Defaults and style values cannot be inferred independently by the two adapters.

Use canonical numeric time plus an explicit display transform. Preserve source timestamps for export, display trim offsets, baseline zeroing, and local clock tick labels separately. Define whether export reflects current zoom/visibility/colours; recommendation is the selected completed result plus a captured current view revision, matching current figure export intent.

For large traces, bounded viewport queries return points plus original sample indices and a “display reduced” marker. Preserve extrema, gaps and scientific annotations independently of decimation. Analysis and export use original data or the existing expressly defined export resampling. `workbook_exporter.py:217-245` averages preview bins; it is not a substitute for peak-preserving display decimation. Mode changes may fetch new data, contrary to TM-008:30.

Tests cross the public interface using a real headless module and actual subprocess transport. Fake native-dialog and filesystem adapters exercise grant/choice outcomes; controlled internal workers can inject failure/cancellation. Run a packaged or isolated Python import test with PySide6 absent. Monkeypatching QMessageBox in a Qt-installed test proves neither import independence nor a deep interface.

Critically, preserve an independent reference: observation of current numeric results, table content and Matplotlib artists/exported images. Comparing new web and Agg renderers from the same incorrect plot model will happily pass. Existing Qt tests continue to protect the retained app while the new interface gets its own scenario tests.

## Cancellation and output ownership

Define queued, running, awaiting-input, cancelling, succeeded, failed and cancelled states, with exactly one terminal state. Progress includes phase, completed/total when meaningful, indeterminate status otherwise, a monotonic sequence and session/job IDs. Coalesce repetitive events so logs cannot starve control messages. Support status reconciliation if the frontend misses an event.

The sidecar control loop must remain responsive while scientific calls run. A token checked by the same blocked thread cannot cancel anything. Prefer a control process plus isolated job worker, with cooperative checks and a bounded process-tree termination fallback; validate frozen multiprocessing behaviour on all targets. If an operation is only cancellable between stages, show “cancelling” honestly and define its bound. Cancelling one worker must not reset unrelated sessions or kill the control pipe.

Legacy writers target final paths directly (`df_single.py:144-152`, `pfer.py:36-59`, behaviour exporter:500-536, telemetry widget:1685-1697). A transaction adapter must stage a complete job's outputs, validate them, and reserve destinations before publishing. Preserve logical legacy names and offer the architecture proposal's user-selected output location without changing scientific calculations. Cancellation before publication removes only job-owned staging files; pre-existing user files remain intact.

A multi-file PFer run is not made atomic by renaming each CSV separately. Specify an artifact manifest and commit/recovery policy, including what happens after one rename fails, output is locked in Excel, the disk fills, or a process dies. Either refuse replacing existing destinations by default or explicitly confirm replacement and use a documented backup/recovery scheme. Do not promise filesystem-wide atomicity across directories/drives. After publication begins, cancellation may be refused as too late; report success/failure and actual committed artifacts unambiguously. New collision/replacement safeguards are explicit safety improvements, not byte-for-byte preservation of accidental overwrite behaviour.

## Corrected dependency/order recommendation

Split IDs below are review-local work packages, not newly published issues. The original ticket contents must be reconciled to this graph before implementation. “Feature complete” dependencies include backend, renderer, exports and interaction tests, even where screen scaffolding starts earlier.

| Work package | Source tickets | Must follow | Completion role |
| --- | --- | --- | --- |
| F0 baseline + capability/fixture registry | TM-022 early, TM-017 discovery, TM-027 scope | none | Establish intended current behaviour, file identities, known defects, comparators and target constraints. |
| F1 domain/session/output contract | TM-001 domain, TM-005 design, TM-019 semantics | F0 | Set ownership, revisions, choices, errors, cancellation/commit rules. |
| F2 minimal shell + private IPC/lifecycle | TM-002 early, TM-001 transport, TM-003, TM-020 early | F1; shell skeleton can start alongside F1 | Real transport, restrictive commands, startup/shutdown, native grants. |
| F3 bounded jobs/data + plot adapter experiment | TM-004 split, TM-005 implementation, TM-021 early | F1, F2 | Verify result queries, representative plots, cancellation and backpressure. |
| F4 three-target scientific packaging/CI proof | TM-023 early, TM-025 validation | F2; enrich with F3 | Prove bundled numerical dependencies and offline native launch on every architecture. |
| F5 settings + shell/catalog integration | TM-017, TM-018 plus TM-002 remainder | F0, F1, F2, job lifecycle | Four IDs, fallback semantics, native directories, durable compatible settings. |
| U0 interaction specification | TM-026 essential UX | F0, F1 | Define workflow states before building full screens; chart experiment can inform it. |
| B behaviour complete | TM-006/007/008/009 | Gate 0, F5, U0; backend then renderer/export then UI integration | First full workflow. Jobs, errors and parity are embedded dependencies, not future work. |
| R raw complete | TM-010/011 plus merged TM-012 | Gate 0, F5, U0; final product acceptance after B | Reuse the Gate 0 compute probe; finish all raw/PFer paths and exports. |
| T1 telemetry recording and cluster state | split TM-013 | Gate 0, F5, F1; early input characterization may run alongside B/R | All file/date/opto/state branches tested without GUI. |
| T2 telemetry complete | TM-014/015/016 | T1, proven TM-008 adapter approach, jobs/settings/output contracts | Mean/full/single and all exports complete. TM-014 must actually depend on TM-013 and TM-008. |
| Q cross-feature qualification | TM-019/020/021/022 remainder | B, R, T2, F5 | All feature/state/error/performance/offline cases pass. Combine placeholder checked explicitly. |
| P distributable release candidate | TM-023 remainder, TM-024, TM-025 release | F4; final acceptance after Q | Signed/notarized according to declared policy; install/upgrade/rollback qualified. |
| X retirement | TM-027 retirement only | Q, P, documentation and retained-symbol inventory | Separate post-qualification decision; no cyclic release/retirement gate. |
| Optional enhancements | TM-026 optional; updater; new Combine | explicit separate scope | Do not block parity by accident. |

Behaviour-first is evidenced by architecture proposal:71-79 and migration-map:123-126. A raw compute probe is useful for early scientific packaging but is not a full raw-first migration. If parallel implementation is later authorized, backend work can overlap once contracts exist; ordering here expresses integration and acceptance dependencies, not a requirement to leave engineers idle.

## Parity policy to adopt before generating goldens

| Artifact/behaviour | Exact invariants | Comparison and exceptions |
| --- | --- | --- |
| Scientific results | Selected signals; sample/event/peak/cluster identities and counts; array shapes; time origin/unit; window inclusion; missing-value masks | Float64 numerical comparison with per-field absolute/relative tolerances justified from the baseline. Never tolerate an altered peak/cluster assignment just because aggregate means are close. |
| DFer/PFer CSV | Path rules, headers including `# `, column/row order, decimal formatting, waveform existence and channel mapping | Keep byte equality in a pinned same-platform replay if deterministic. Cross-target qualification compares the explicit text-format contract and numeric cells with documented line-ending/tolerance policy. Six-decimal `%f` output does not justify arbitrary wider numeric tolerance. |
| XLSX | File naming; sheet order/names; row/column structure; cell types and formulas; labels; blank cells; relevant styles, formats, column widths and links | Compare workbook semantics, not ZIP bytes, serialization order, timestamps or generated style IDs. Allowlist nonsemantic metadata only. Existing 1e-3 tests are starting evidence, not an approved universal tolerance. |
| Static images | Formats, axes, labels, legends, geometry, colours, visibility, dimensions/DPI, source view/result and filename collision policy | Same-renderer pinned-font/image comparisons with defined tolerances. Cross-renderer reviews compare scene/geometry and readability; do not demand identical pixels between WebView and Agg. EPS/SVG need structural/rendered comparison, not raw bytes. |
| UI | Task outcomes, controls' defaults/enabling, choice/cancel/reset/switch semantics, settings recall, accessible input, export discoverability | Deterministic interaction scenarios plus native installed-app evidence. A workbook or screenshot diff cannot prove these. |
| Settings | Actual app identity, config paths, key/value types, aliases, selection order and fallback precedence | Load old data, save, reopen in new and legacy app; preserve unknown keys where existing writer does. New version metadata must not corrupt keyed maps. |

Byte identity is useful where it is defined and demonstrated. Semantic parity is not permission to change science, naming, worksheet structure, or defaults. Record each intended difference with owner, evidence and an acceptance case. No baseline regeneration may silently turn a regression green.

## Packaging and release gates

| Target | Required proof |
| --- | --- |
| Windows x64 | `x86_64-pc-windows-msvc`; complete Python payload, no development Python on PATH; hidden console while keeping stdio usable; restricted-user launch; offline WebView2 install when absent; Explorer dialogs/output opening; non-ASCII, spaced and long paths, missing drive, locked Excel file; child-tree cleanup. Declare installer format/per-user scope and portable compatibility policy. |
| macOS arm64 | `aarch64-apple-darwin`; native arm64 Python and all native extensions; complete resources; Finder launch with arbitrary cwd/PATH; signing of nested code and final bundle; quarantine/notarization/stapling/offline launch; file dialogs and output opening; minimum OS and native hardware evidence. |
| macOS x86_64 | `x86_64-apple-darwin`; same proof with Intel wheels/libraries and declared minimum OS; explicit Intel hardware/runtime evidence. An arm64 run under Rosetta or a successful cross-compile is not sufficient evidence for the complete target. |

Tauri external binaries are target-suffixed, while PyInstaller onedir ships dependencies beside its launcher. Define exactly how that layout is packaged and resolved, including native libraries, Matplotlib fonts/data, config/cache locations and multiprocessing entry points. Do not assume it from externalBin configuration. [Tauri sidecars](https://v2.tauri.app/develop/sidecar/), [PyInstaller packaging](https://pyinstaller.org/en/stable/operating-mode.html).

Offline includes installation, first launch, fonts/assets, all three scientific workflows, and retained HTML exports if in scope. A clean Windows machine may need WebView2; prove the offline distribution mode. Build-time dependency downloads are a separate concern from runtime offline behaviour. [Tauri Windows offline installer](https://v2.tauri.app/distribute/windows-installer/#offline-installer).

Declare minimum OS versions and choose a Python/toolchain/dependency matrix that actually satisfies all of them. Keep exact locks/hashes, architecture manifests, license notices and provenance. `pyproject.toml` ranges and runner names are not proof of wheel availability or minimum-OS compatibility. The three-target build must import and execute the scientific stack, Excel read/write, and Agg rendering inside the installed payload.

Signing acceptance is successful verified distribution under the declared trust policy, not an absolute no-prompt or SmartScreen-reputation promise. Sign nested Python code/libraries before the final macOS app; verify final signatures and notarization/stapling on the applicable distributable container. Hardened runtime is distinct from App Sandbox. Track signing credential readiness before release; keep unsigned local feasibility builds possible. Resolve the current mismatch between optional Windows signing in TM-024 and mandatory all-target signing in map:118.

Define stable application identity, monotonic release version, sidecar compatibility, upgrade from the existing portable app, coexistence, settings retention, uninstall behaviour and rollback. Keep manual download/update as default; an updater adds a separate network, trust and recovery design. Do not automatically publish from the experimental validation pipeline.

Revised gates:

1. **Gate 0: architecture feasibility.** Concrete cut in the next report: packaged science on three targets, real transport/job failure handling, bounded plot/array retrieval, a small behaviour seam proof, and independent parity checks. Ping is only one check.
2. **Gate 1: behaviour complete.** All behaviour cases, static exports, settings/native actions, cancellation and validation pass. Generic UX state rules are already exercised.
3. **Gate 2: raw complete.** All options, single/dual/490nm, standalone PFer, dirty semantic changes, plots, export paths and failure cases pass.
4. **Gate 3: telemetry complete.** Photometry/opto, associated files, date choices, all display modes/periods, trim/threshold invalidation, native/preview exports and error branches pass.
5. **Gate 4: replacement qualification.** Every implemented-app case and four-entry catalog/placeholder behaviour passes; settings coexistence, security, bounded large-data handling and offline checks pass. No unresolved High/Critical migration regression.
6. **Gate 5: distributable qualification.** Installed final artifacts pass all three architectures, signing policy, quarantine/offline, upgrade/rollback and real file-manager workflows; docs/support path complete. The legacy app is still available.
7. **Gate 6: retirement.** After qualification and an explicit retirement decision, remove only obsolete reachable code/dependencies after extracting retained helpers and resolving console/Python interface support. Keep the prior release obtainable. Gate 5 does not depend on Gate 6.
