# 02 - Scale nighttime shading coordinates with the selected time unit

**Priority:** High

**Status:** resolved

**Resolution:** Fixed in local commits `f181dbb` and `bdadded`.

**What to fix:** Nighttime spans must align with the plotted x-axis in minutes, seconds, or hours.

Evidence: `src/features/telemetry_alignment/services/plot_service.py:89-107` computes span coordinates in minutes, while `prepare_figure()` passes an unscaled time column at `:580` and `create_photometry_figure()` passes a scaled column at `:615`. The x-axis is set from `scaled_time_column` at `:583`.

Reproduction: for a 00:00 to 02:00 recording displayed in seconds, a 01:00 to 02:00 nighttime period is plotted at x=60 to 120 instead of x=3600 to 7200. In hours, the span can disappear after clipping.

- [ ] Nighttime shading aligns in minutes, seconds, and hours.
- [ ] Shading remains clipped correctly to the visible recording range.
- [ ] Tests cover at least minutes and one scaled unit.
