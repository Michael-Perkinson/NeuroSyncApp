# Refactor Plan: align_telemetry_photom_opto.py (5170 lines)

Goal: God-class → thin controller. Pure logic moved to pure modules.
No tkinter in pure modules. PySide6-ready.

---

## Target destination modules

| Module | Purpose |
|--------|---------|
| `src/processing/telemetry_processing.py` | Data pipeline, alignment, binning, stim |
| `src/processing/cluster_detection.py` | Cluster detection & metrics |
| `src/excel_ops/telemetry_exporter.py` | Excel/CSV write helpers |
| `src/gui/telemetry_plotter.py` | Matplotlib drawing functions |

---

## Phase 1 — Category A (fully pure, no self refs) ✅ easiest

Extract these first — no widget resolution needed.

| # | Method | Lines | Destination |
|---|--------|-------|-------------|
| 1 | `bin_data_dynamic` | 5067–5100 (33) | telemetry_processing.py |
| 2 | `compute_photometry_mean` | 5024–5065 (41) | telemetry_processing.py |
| 3 | `align_and_concatenate_data` | 1275–1332 (57) | telemetry_processing.py |
| 4 | `process_data_for_clusters` | 1080–1104 (24) | cluster_detection.py |
| 5 | `calculate_stim_timings` | 3177–3210 (33) | telemetry_processing.py |
| 6 | `generate_cluster_headings` | 4518–4546 (28) | telemetry_exporter.py |

---

## Phase 2 — Category B (widget reads at top only)

Resolve `self.x.get()` in controller, pass as plain args to pure fn.

| # | Method | Lines | Destination | Widget vars to resolve |
|---|--------|-------|-------------|------------------------|
| 7 | `identify_clusters` | 1941–2049 (108) | cluster_detection.py | `baseline_multiplier`, `adjust_clustering_var` |
| 8 | `process_cluster_data` | 1025–1078 (53) | cluster_detection.py | survey needed |
| 9 | `extract_and_prepare_temp_and_act_data` | 1154–1243 (89) | telemetry_processing.py | survey needed |
| 10 | `extract_and_prepare_temp_and_act_data_for_stim` | 780–860 (80) | telemetry_processing.py | survey needed |
| 11 | `extract_and_prepare_photometry_data` | 1334–1409 (75) | telemetry_processing.py | survey needed |
| 12 | `align_and_concatenate_data` | 1275–1332 (57) | telemetry_processing.py | (already Phase 1 — pure) |
| 13 | `overlay_temp_and_act` | 2206–2288 (82) | telemetry_processing.py | survey needed |
| 14 | `calculate_nighttime_period` | 2129–2173 (44) | telemetry_processing.py | survey needed |
| 15 | `add_nighttime_shading_to_plot` | 2174–2205 (31) | telemetry_plotter.py | survey needed |
| 16 | `visualize_single_cluster` | 2600–2668 (68) | telemetry_plotter.py | survey needed |
| 17 | `extract_and_trim_data` | 2670–2701 (31) | telemetry_processing.py | survey needed |
| 18 | `extract_data_for_date_and_offset` | 2703–2779 (76) | telemetry_processing.py | survey needed |
| 19 | `extract_data_with_buffer` | 2781–2819 (38) | telemetry_processing.py | survey needed |
| 20 | `find_offset_for_previous_time` | 3618–3650 (32) | telemetry_processing.py | survey needed |
| 21 | `precalculate_data_versions` | 3652–3688 (36) | telemetry_processing.py | survey needed |
| 22 | `populate_table` | 3403–3429 (26) | telemetry_plotter.py | survey needed |
| 23 | `save_static_inputs` | 3335–3367 (32) | telemetry_exporter.py | survey needed |
| 24 | `load_static_inputs` | 3369–3401 (32) | telemetry_exporter.py | survey needed |
| 25 | `bin_all_cluster_data` | 4992–5022 (30) | telemetry_processing.py | survey needed |
| 26 | `extract_button_click_handler` | 4953–4978 (25) | telemetry_exporter.py | survey needed |

---

## Phase 3 — Category C (widget reads scattered)

More surgical: extract pure inner logic, leave widget-resolution loop in controller.

| # | Method | Lines | Destination |
|---|--------|-------|-------------|
| 27 | `write_cluster_details` | 4561–4744 (183) | telemetry_exporter.py |
| 28 | `populate_raw_data_sheet` | 4221–4310 (89) | telemetry_exporter.py |
| 29 | `overlay_temp_on_figure` | 2366–2451 (85) | telemetry_plotter.py |
| 30 | `write_raw_data_to_sheet` | 4332–4410 (78) | telemetry_exporter.py |
| 31 | `extract_and_prepare_photometry_data` | 1334–1409 (75) | telemetry_processing.py |
| 32 | `overlay_act_on_figure` | 2477–2546 (69) | telemetry_plotter.py |
| 33 | `plot_mean_cluster` | 1469–1530 (61) | telemetry_plotter.py |
| 34 | `write_cluster_static_inputs` | 4879–4937 (58) | telemetry_exporter.py |
| 35 | `populate_opto_data_dict` | 3491–3537 (46) | telemetry_exporter.py |
| 36 | `populate_photometry_data_dict` | 3449–3490 (41) | telemetry_exporter.py |
| 37 | `prepare_figure` | 3212–3277 (65) | telemetry_plotter.py |
| 38 | `create_photometry_figure` | 3724–3830 (106) | telemetry_plotter.py |

---

## Execution strategy (per method)

1. Read the method body (already known for Phase 1)
2. Write pure function to destination module
3. Replace method body with widget-resolution + single delegation call
4. `python -c "import ast; ast.parse(open(f).read())"` on both files

## Progress tracker

- [ ] Phase 1 complete (6 methods)
- [ ] Phase 2 complete (20 methods)  
- [ ] Phase 3 complete (12 methods)
- [ ] `align_telemetry_photom_opto.py` < 1500 lines (thin controller)
