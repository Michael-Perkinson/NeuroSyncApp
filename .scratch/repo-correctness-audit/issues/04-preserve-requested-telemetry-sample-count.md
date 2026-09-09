# 04 - Preserve the requested telemetry extraction duration with fractional offsets

**Priority:** Medium

**Status:** resolved

**Resolution:** Fixed in local commit `22171c6`.

**What to fix:** Fractional alignment offsets must not shorten the extracted telemetry window by one sample.

Evidence: `src/processing/telemetry_recording_io.py:345-350` floors the buffered sample count but ceils the number of samples removed for the offset.

Reproduction: at a 100 ms sample interval, request one minute with a 0.001 minute offset. The current implementation extracts 600 samples, removes one for the offset, and returns 599 samples instead of the requested 600.

- [ ] Extraction returns the expected sample count for fractional offsets.
- [ ] The generated `Time (min)` axis starts at zero and covers the requested duration.
- [ ] Tests cover offsets below, equal to, and above one sample interval.
