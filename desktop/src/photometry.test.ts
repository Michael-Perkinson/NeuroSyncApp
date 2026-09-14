import { describe, expect, it } from "vitest";
import {
  classifySignals,
  computeDfof,
  findPeaks,
  formatDuration,
  normaliseWindowInput,
  resolveWindow,
  START_ALIASES,
  END_ALIASES,
} from "./photometry";
import type { SamplePlotResult } from "./protocol";

const singlePlot: SamplePlotResult = {
  plot_id: "raw.demo.trace",
  title: "Raw photometry trace",
  x_axis: { label: "Time", unit: "s" },
  sample_count: 480,
  viewport: { start_index: 0, end_index: 479 },
  display_reduced: false,
  decimation: "uniform-index-v1",
  series: [
    { id: "sig-465", signal_id: "signal-465", label: "465 nm signal", unit: "a.u.", sample_indices: [0, 1], x: [0, 1], y: [1, 2] },
    { id: "ref-405", signal_id: "reference-405", label: "405 nm reference", unit: "a.u.", sample_indices: [0, 1], x: [0, 1], y: [1, 1] },
  ],
};

const dualPlot: SamplePlotResult = {
  ...singlePlot,
  plot_id: "raw.dual.trace",
  series: [
    { id: "sig-470", signal_id: "signal-470", label: "470nm", unit: "a.u.", sample_indices: [0, 1], x: [0, 1], y: [1, 2] },
    { id: "sig-560", signal_id: "signal-560", label: "560nm", unit: "a.u.", sample_indices: [0, 1], x: [0, 1], y: [1, 3] },
  ],
};

describe("window helpers", () => {
  it("formats durations like the PySide6 widget", () => {
    expect(formatDuration(480)).toBe("8m 0s");
    expect(formatDuration(60)).toBe("1m 0s");
    expect(formatDuration(3661)).toBe("1h 1m 1s");
    expect(formatDuration(9)).toBe("9s");
  });

  it("normalises start/min/end/max aliases to full range", () => {
    expect(normaliseWindowInput("", START_ALIASES)).toBe("");
    expect(normaliseWindowInput("start", START_ALIASES)).toBe("");
    expect(normaliseWindowInput("min", START_ALIASES)).toBe("");
    expect(normaliseWindowInput("end", END_ALIASES)).toBe("");
    expect(normaliseWindowInput("max", END_ALIASES)).toBe("");
    expect(normaliseWindowInput("12.5", START_ALIASES)).toBe("12.5");
  });

  it("resolves and clamps a window to the recording bounds", () => {
    const resolved = resolveWindow("10", "70", 0, 480);
    expect(resolved.valid).toBe(true);
    expect(resolved.duration).toBe(60);
    expect(resolveWindow("", "max", 0, 480).start).toBe(0);
    expect(resolveWindow("min", "", 0, 480).end).toBe(480);
  });

  it("marks an inverted window as invalid", () => {
    expect(resolveWindow("70", "10", 0, 480).valid).toBe(false);
    expect(resolveWindow("nope", "10", 0, 480).valid).toBe(false);
  });
});

describe("signal classification", () => {
  it("classifies 465/405 series as single channel", () => {
    const context = classifySignals(singlePlot);
    expect(context.fileType).toBe("single");
    expect(context.primaryLabel).toBe("465nm");
    expect(context.referenceLabel).toBe("405nm");
    expect(context.signalOptions).toEqual(["465nm"]);
  });

  it("classifies 470/560 series as dual channel", () => {
    const context = classifySignals(dualPlot);
    expect(context.fileType).toBe("dual");
    expect(context.signalOptions).toEqual(["Both", "470nm", "560nm"]);
  });
});

describe("DFer and PFer demo processing", () => {
  it("computes a dF/F result in minutes from raw seconds", () => {
    const context = classifySignals(singlePlot);
    const result = computeDfof(context, [1, 2], [1, 1]);
    expect(result.time).toEqual([0, 1 / 60]);
    expect(result.primary).toHaveLength(2);
    expect(result.reference).toHaveLength(2);
  });

  it("finds peaks separated by the artifact threshold", () => {
    const values = [0, 1, 0, 2, 0, 3, 0];
    const times = values.map((_, index) => index);
    const { peaks, troughs } = findPeaks(values, times, 0.5, 2);
    expect(peaks.map((peak) => peak.value)).toEqual([1, 2, 3]);
    expect(troughs.length).toBe(peaks.length);
  });
});