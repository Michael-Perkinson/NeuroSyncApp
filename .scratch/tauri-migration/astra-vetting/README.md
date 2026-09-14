# Tauri migration: adversarial vetting

**Verdict: revise before implementation. Retain the architectural direction; do not treat TM-001 through TM-027 as an executable, parity-complete backlog.**

The plan correctly identifies local Python reuse, native file workflows, the three implemented tools, and most difficult Qt dependencies. It does not yet define a sufficiently deep interface, a measurable parity contract, or a release dependency graph. A ping demonstration could pass its Gate 0 while the proposed data transport, packaged scientific dependencies, export safety, and chart architecture remain unproven.

This is an architecture and product review, not implementation approval. All 27 tickets and the three parent documents were read. Source references, relevant callers, tests, the architecture proposal, correctness-audit notes, and the dirty diff were inspected. Source findings refer to the working tree, not just HEAD. No application tests, application launches, installers, or scientific pipelines were run. Thus this review establishes source evidence and planning defects, not runtime parity or platform qualification.

## Reports

| Report | Contents |
| --- | --- |
| [Evidence and baseline](evidence-and-baseline.md) | Verified and incorrect citations, dirty changes, existing-test limitations, external documentation checks. |
| [Ticket dispositions](ticket-dispositions.md) | Disposition, severity, evidence, and concrete edits for every original ticket. |
| [Architecture, order, and release gates](architecture-and-order.md) | Deep module interface, protocol and job rules, corrected dependencies, parity policy, packaging and release gates. |
| [Missing coverage and Gate 0](missing-coverage-and-gate-0.md) | Feature acceptance matrix, missing work packages, bounded implementation cut and exit criteria. |
| [Baseline manifest](baseline-manifest.json) | HEAD, branch, dirty status, SHA-256 hashes of reviewed source/test/planning files. This is an integrity record, not a saved runnable baseline. |
| [Review verification](verification.md) | Final integrity check and limitations. |

## Findings that prevent accepting the backlog

Severity: **Critical** invalidates the implementation/release gate; **High** risks lost functionality, scientific drift, data loss, or an unusable target build; **Medium** creates ambiguity, avoidable scope, or misleading evidence. These are review priorities, not assertions that the existing app has a production incident.

| ID | Severity | Finding and required edit |
| --- | --- | --- |
| V01 | Critical | Move baseline capture/comparators, security policy, settings discovery, and a three-target packaging proof into foundation work. TM-022 is nominally Phase 5 while Gates 1 and 2 already require goldens; TM-023 waits for every backend. See migration-map.md:95-113. |
| V02 | Critical | Replace generic workflow wrappers and widget-shaped requests with session/revision/result ownership. TM-001:25-40 and TM-006:37 do not settle cache invalidation, required user choices, exports of a specific result, or stale replies. Telemetry trim explicitly invalidates cluster state at services/plot_service.py:362-385. |
| V03 | High | Replace conflicting byte/content/pixel equality promises with artifact-specific comparators. TM-009:43, TM-010:35-43, TM-022:25-30, and assumptions:36-39 disagree. Existing workbook tests use tolerances and bypass UI validation, not byte equality. |
| V04 | High | Specify cancellation and output commit as one design. Existing DFer/PFer and workbook writers write final paths directly. Killing a worker or deleting a partial file can destroy a pre-existing result. TM-005:31-33 is insufficient. |
| V05 | High | Correct crash recovery: killing the process loses its memory. TM-003:37-38 needs either an explicit replay/checkpoint design or an honest lost-session/reload result. A lifecycle restart alone cannot meet it. |
| V06 | High | Add telemetry mean-cluster, optogenetics, and invalidation coverage. TM-014:40-43 only accepts full and single displays; Mean Cluster Display is implemented in views/display_mode_presenter.py:181-341. No-Qt imports do not make the exporter independent of widget state. |
| V07 | High | Prove the complete onedir resource layout and offline Windows WebView2 installation. Listing an external executable does not establish that Python extensions/data/DLLs are installed correctly. TM-023 currently defers this until all ports. |
| V08 | High | Keep `combine_data` as a visible unavailable entry for current parity. TM-027:19-20,34 invents a forced implement-or-drop decision that contradicts TM-018:25 and the four-tool promise. New Combine functionality requires a separate product specification. |
| V09 | High | Pull UX interaction rules forward; defer optional enhancements. TM-026 calls its work optional but makes redesigned behaviour interactions and all-screen themes acceptance criteria. TM-011's tab-for-tab prescription also conflicts with the architecture proposal's non-goal at line 102. |
| V10 | High | Do not delete whole `src/gui`/`src/dashboard` trees by category. TM-027:22-24 would include reusable plotting/export helpers and the installed console entry point. Extract/rehome what remains needed, then prove reachability and compatibility before retirement. |

## Order verdict

The supplied architecture proposal and migration map both explicitly say **behaviour first**, then raw, then telemetry. There is no raw-first full-product sequence in the reviewed ticket set. Raw is the dashboard default and has easier compute entry points, which does not make it the mandated first screen.

Recommendation: use `compute_options` as a small Gate 0 scientific packaging/transport probe; keep **behaviour as the first complete user workflow**. Include a bounded behaviour alignment/export seam check before freezing the interface. This resolves the distinction without silently replacing the architecture proposal. A decision to make the entire raw app first would require changing the map, gates, TM-006/007/008/009/010/011/012/014/026, and the architecture proposal together.

## Blockers and decisions

The review itself is complete. Implementation remains blocked on a baseline and parity contract, session/job/output semantics, renderer feasibility, and a verified packaging cut. Release additionally requires supported minimum OS versions, real Windows x64/macOS arm64/macOS x86_64 validation, credentials or an explicit distribution policy, installer identity/versioning, and upgrade/rollback evidence.

These do not all need to block the small Gate 0 experiment: use the explicit defaults in the Gate 0 report. Preserve settings and the Combine placeholder; use stdio; keep manual downloads; do not promise memory survival or immediate interruption of arbitrary scientific calls. Performance thresholds in this review are proposed experiment thresholds, not measured facts or approved product SLOs.

Only files under this report directory were created. No production source, tests, original tickets, Git history, or release state were intentionally changed. No GitHub issues, comments, PRs, commits, or releases were created.
