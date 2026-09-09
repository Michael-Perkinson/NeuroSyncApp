# 05 - Handle one-row telemetry frames in dynamic binning

**Priority:** Medium

**Status:** resolved

**Resolution:** Fixed in local commit `511462d`.

**What to fix:** Dynamic telemetry binning must return a valid result or a clear empty-data outcome for a one-row input.

Evidence: `src/processing/telemetry_processing.py:257-263` assumes `bin_edges` has at least two entries. `_float_range()` returns one edge when the frame contains one timestamp.

Reproduction: `bin_data_dynamic(pd.DataFrame({'Time (s)': [0.0], 'Mean': [1.0], 'SEM': [0.0]}), 10)` raises `IndexError: list index out of range` at line 261.

- [ ] One-row input no longer raises `IndexError`.
- [ ] The returned bin range and aggregate values follow the documented contract.
- [ ] Empty, one-row, short, and normal frames are covered by tests.
