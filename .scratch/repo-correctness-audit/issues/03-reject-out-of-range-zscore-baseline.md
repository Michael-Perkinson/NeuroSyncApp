# 03 - Reject z-score baselines that do not overlap the recording

**Priority:** High

**Status:** resolved

**Resolution:** Fixed in local commit `97d9866`.

**What to fix:** Applying a baseline outside the signal range must show a validation error instead of silently replacing z-score output with NaNs.

Evidence: `src/processing/behaviour_metrics.py:281-304` computes the mean and standard deviation of an empty baseline selection as NaN. `src/features/behaviour_alignment/services/data_service.py:90-105` then assigns the empty result to dataframe columns, producing all-NaN z-score columns. The UI validates ordering but not overlap at `:66-72`.

Reproduction: with `Time (min) = [0, 1, 2]`, applying a baseline from 10 to 11 minutes returns empty z-score series and NaN statistics, then blanks the displayed/exported z-score data.

- [ ] Baselines with no samples are rejected with a user-visible message.
- [ ] Partially overlapping baselines have an explicit, tested policy.
- [ ] Existing ordering and numeric validation remains intact.
