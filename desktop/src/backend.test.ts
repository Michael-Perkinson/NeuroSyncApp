import { DemoBackend, createBackend } from "./backend";
import { MAX_POINTS_PER_SERIES } from "./protocol";
import { describe, expect, it } from "vitest";

describe("explicit backend selection", () => {
  it("creates the browser-only demo adapter explicitly", () => {
    expect(createBackend("demo")).toBeInstanceOf(DemoBackend);
  });

  it("rejects an unknown transport", () => {
    expect(() => createBackend("unknown")).toThrow(/Unsupported/);
  });
});

describe("DemoBackend raw photometry surface", () => {
  it("negotiates, retains sample identity, and bounds arrays", async () => {
    const backend = new DemoBackend();
    const negotiation = await backend.start();
    const plot = await backend.samplePlot(MAX_POINTS_PER_SERIES);
    expect(negotiation.protocol_version).toBe(1);
    expect(plot.display_reduced).toBe(true);
    expect(plot.series).toHaveLength(2);
    for (const series of plot.series) {
      expect(series.y).toHaveLength(MAX_POINTS_PER_SERIES);
      expect(series.sample_indices).toHaveLength(series.y.length);
      expect(series.sample_indices[0]).toBe(0);
      expect(series.sample_indices.at(-1)).toBe(plot.sample_count - 1);
    }
  });

  it("loads a raw photometry file with single-channel column context", async () => {
    const backend = new DemoBackend();
    await backend.start();
    const context = await backend.loadPhotometryFile("example_data/recording_465.csv");
    expect(context.file_type).toBe("single");
    expect(context.signal_label).toBe("465nm");
    expect(context.signal_columns).toEqual(["405nm", "465nm"]);
    expect(context.output_folder).toBe("example_data/dfof_results");
    expect(context.plot.series.map((series) => series.label)).toEqual([
      "465nm Signal",
      "405nm Signal",
    ]);
  });

  it("generates the four DFer option titles", async () => {
    const backend = new DemoBackend();
    await backend.start();
    await backend.loadPhotometryFile("example_data/recording_465.csv");
    const options = await backend.generateOptions({ start_s: null, end_s: null });
    expect(options.option_titles).toHaveLength(4);
    expect(options.option_titles[0]).toMatch(/Good noise correction/);
  });

  it("previews a DFer option as signal and fitted control", async () => {
    const backend = new DemoBackend();
    await backend.start();
    const preview = await backend.previewOption(0, "both");
    expect(preview.series[0].label).toBe("465nm");
    expect(preview.series[1].label).toBe("fitted control");
  });

  it("runs the final DFer analysis and returns dF/F and Z-score plots", async () => {
    const backend = new DemoBackend();
    await backend.start();
    await backend.loadPhotometryFile("example_data/recording_465.csv");
    const result = await backend.runDfer({ option: "1", window: { start_s: null, end_s: null } });
    expect(result.result_csv).toBe("example_data/dfof_results/recording_465_Data.csv");
    expect(result.plots.dfof.series.map((series) => series.label)).toEqual([
      "465nm dF/F",
      "405nm dF/F",
    ]);
    expect(result.plots.zscore.series.map((series) => series.label)).toEqual([
      "465nm Z-score",
      "405nm Z-score",
    ]);
  });

  it("runs peak finding and returns a PFer results plot", async () => {
    const backend = new DemoBackend();
    await backend.start();
    await backend.loadPhotometryFile("example_data/recording_465.csv");
    const result = await backend.runPfer({
      csv_path: "example_data/dfof_results/recording_465_Data.csv",
      baseline_start: "",
      baseline_end: "",
      prominence: 0.003,
      artifact_threshold: 10,
    });
    expect(result.stats_csv).toBe("example_data/dfof_results/recording_465_Data_Peak_STATS.csv");
    expect(result.plot.series.map((series) => series.label)).toContain("detected peak");
  });

  it("returns a typed failure after shutdown", async () => {
    const backend = new DemoBackend();
    await backend.start();
    await backend.shutdown();
    await expect(backend.ping()).rejects.toMatchObject({
      envelope: { code: "sidecar_not_running" },
    });
  });
});