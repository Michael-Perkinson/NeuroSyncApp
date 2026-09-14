import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import {
  BackendError,
  type AnalysisWindow,
  type DferOptionsResult,
  type DferRunParams,
  type DferRunResult,
  type DualDisplay,
  type LogEntry,
  MAX_POINTS_PER_SERIES,
  type NativeGrant,
  type NegotiationResult,
  type PferRunParams,
  type PferRunResult,
  type PingResult,
  type PlotSaveParams,
  type PlotSaveResult,
  PROTOCOL_VERSION,
  type RawFileContext,
  type ResponseEnvelope,
  type SamplePlotResult,
  type VersionResult,
} from "./protocol";

export type LogListener = (entry: LogEntry) => void;

export interface BackendAdapter {
  readonly mode: "demo" | "tauri";
  start(): Promise<NegotiationResult>;
  ping(): Promise<PingResult>;
  version(): Promise<VersionResult>;
  samplePlot(maxPoints?: number): Promise<SamplePlotResult>;
  selectGrant(kind: "file" | "folder"): Promise<NativeGrant | null>;
  shutdown(): Promise<void>;
  onLog(listener: LogListener): Promise<() => void>;

  loadPhotometryFile(path: string): Promise<RawFileContext>;
  generateOptions(window: AnalysisWindow): Promise<DferOptionsResult>;
  previewOption(index: number, dualDisplay: DualDisplay): Promise<SamplePlotResult>;
  runDfer(params: DferRunParams): Promise<DferRunResult>;
  runPfer(params: PferRunParams): Promise<PferRunResult>;
  savePlotImage(params: PlotSaveParams): Promise<PlotSaveResult>;
}

const limits = {
  max_frame_bytes: 4 * 1024 * 1024,
  max_points_per_series: MAX_POINTS_PER_SERIES,
  max_points_across_panels: 50_000,
};

const OPTION_TITLES = [
  "Option 1: Good noise correction and bleach correction",
  "Option 2: Assumes shifts in 465 baseline are independent of activity",
  "Option 3: No noise correction",
  "Option 4: No noise correction, no activity-dependent baseline correction",
];

function sampleIndices(sampleCount: number, displayed: number): number[] {
  return Array.from({ length: displayed }, (_, index) =>
    Math.round((index * (sampleCount - 1)) / (displayed - 1)),
  );
}

function seriesValues(
  sampleCount: number,
  displayed: number,
  valueAt: (index: number) => number,
): { sample_indices: number[]; x: number[]; y: number[] } {
  const indices = sampleIndices(sampleCount, displayed);
  return {
    sample_indices: indices,
    x: indices.map((index) => index / 100),
    y: indices.map((index) => Number(valueAt(index).toFixed(6))),
  };
}

function createRawTrace(maxPoints: number): SamplePlotResult {
  const sampleCount = 48_000;
  const displayed = Math.min(Math.max(32, maxPoints), MAX_POINTS_PER_SERIES);
  const signal465 = seriesValues(sampleCount, displayed, (index) =>
    0.32 * Math.sin(index / 1300) + 0.09 * Math.sin(index / 109),
  );
  const signal405 = seriesValues(sampleCount, displayed, (index) =>
    0.12 * Math.cos(index / 1600) + 0.04 * Math.sin(index / 83),
  );
  return {
    plot_id: "raw.single.465",
    title: "Raw Data — single channel",
    x_axis: { label: "Time", unit: "s" },
    sample_count: sampleCount,
    viewport: { start_index: 0, end_index: sampleCount - 1 },
    display_reduced: displayed < sampleCount,
    decimation: "uniform-index-v1",
    series: [
      {
        id: "raw.signal.465",
        signal_id: "465nm",
        label: "465nm Signal",
        unit: "a.u.",
        ...signal465,
      },
      {
        id: "raw.reference.405",
        signal_id: "405nm",
        label: "405nm Signal",
        unit: "a.u.",
        ...signal405,
      },
    ],
  };
}

function createOptionPreview(index: number, dualDisplay: DualDisplay): SamplePlotResult {
  const sampleCount = 48_000;
  const displayed = Math.min(Math.max(32, 900), MAX_POINTS_PER_SERIES);
  const minutes = (i: number) => Number((i / 6000).toFixed(4));
  const indices = sampleIndices(sampleCount, displayed);
  const x = indices.map(minutes);
  const valueAt = (i: number) => 0.32 * Math.sin(i / 1100) + 0.08 * Math.sin(i / 73);
  const offset = index * 0.018;
  const fitted = (i: number) => valueAt(i) + offset + 0.03 * Math.sin(i / 160);
  const mk = (id: string, label: string, fn: (i: number) => number) => ({
    id,
    signal_id: id.split(".")[1],
    label,
    unit: "RFU",
    sample_indices: indices,
    x,
    y: indices.map((i) => Number(fn(i).toFixed(6))),
  });
  const series = [mk(`opt.signal.465`, "465nm", valueAt)];
  if (dualDisplay === "both") {
    series.push(mk(`opt.fit.465`, "fitted control", fitted));
    series.push(mk(`opt.signal.560`, "560nm", (i) => valueAt(i) * 0.9));
    series.push(mk(`opt.fit.560`, "560 fitted", (i) => fitted(i) * 0.9));
  } else {
    series.push(mk(`opt.fit.465`, "fitted control", fitted));
  }
  return {
    plot_id: `raw.option.${index + 1}`,
    title: OPTION_TITLES[index],
    x_axis: { label: "Time", unit: "min" },
    sample_count: sampleCount,
    viewport: { start_index: 0, end_index: sampleCount - 1 },
    display_reduced: true,
    decimation: "uniform-index-v1",
    series,
  };
}

function createDferResultPlots(): DferRunResult["plots"] {
  const sampleCount = 48_000;
  const displayed = Math.min(Math.max(32, 900), MAX_POINTS_PER_SERIES);
  const minutes = (i: number) => Number((i / 6000).toFixed(4));
  const indices = sampleIndices(sampleCount, displayed);
  const x = indices.map(minutes);
  const dfof465 = indices.map((i) => Number((0.28 * Math.sin(i / 1200) + 0.05 * Math.sin(i / 91)).toFixed(6)));
  const dfof405 = indices.map((i) => Number((0.09 * Math.cos(i / 1500) + 0.02 * Math.sin(i / 77)).toFixed(6)));
  const z465 = indices.map((i) => Number((1.6 * Math.sin(i / 1200) + 0.3 * Math.sin(i / 91)).toFixed(6)));
  const z405 = indices.map((i) => Number((0.5 * Math.cos(i / 1500) + 0.12 * Math.sin(i / 77)).toFixed(6)));
  const mk = (id: string, signalId: string, label: string, y: number[]) => ({
    id,
    signal_id: signalId,
    label,
    unit: "a.u.",
    sample_indices: indices,
    x,
    y,
  });
  return {
    dfof: {
      plot_id: "raw.dfer.dfof",
      title: "DFer Results — dF/F",
      x_axis: { label: "Time", unit: "min" },
      sample_count: sampleCount,
      viewport: { start_index: 0, end_index: sampleCount - 1 },
      display_reduced: true,
      decimation: "uniform-index-v1",
      series: [mk("dfer.dfof.465", "465nm", "465nm dF/F", dfof465), mk("dfer.dfof.405", "405nm", "405nm dF/F", dfof405)],
    },
    zscore: {
      plot_id: "raw.dfer.zscore",
      title: "DFer Results — Z-score",
      x_axis: { label: "Time", unit: "min" },
      sample_count: sampleCount,
      viewport: { start_index: 0, end_index: sampleCount - 1 },
      display_reduced: true,
      decimation: "uniform-index-v1",
      series: [mk("dfer.zscore.465", "465nm", "465nm Z-score", z465), mk("dfer.zscore.405", "405nm", "405nm Z-score", z405)],
    },
  };
}

function createPferPlot(): SamplePlotResult {
  const sampleCount = 48_000;
  const displayed = Math.min(Math.max(32, 900), MAX_POINTS_PER_SERIES);
  const minutes = (i: number) => Number((i / 6000).toFixed(4));
  const indices = sampleIndices(sampleCount, displayed);
  const x = indices.map(minutes);
  const signal = indices.map((i) => Number((0.28 * Math.sin(i / 1200) + 0.05 * Math.sin(i / 91)).toFixed(6)));
  const peaks = indices.map((i) =>
    Math.abs(Math.sin(i / 400)) > 0.985 ? Number((0.28 * Math.sin(i / 1200) + 0.05 * Math.sin(i / 91)).toFixed(6)) : Number.NaN,
  );
  return {
    plot_id: "raw.pfer.peaks",
    title: "PFer Results — detected peaks",
    x_axis: { label: "Time", unit: "min" },
    sample_count: sampleCount,
    viewport: { start_index: 0, end_index: sampleCount - 1 },
    display_reduced: true,
    decimation: "uniform-index-v1",
    series: [
      { id: "pfer.signal.465", signal_id: "465nm", label: "465nm dF/F", unit: "a.u.", sample_indices: indices, x, y: signal },
      { id: "pfer.peaks", signal_id: "peaks", label: "detected peak", unit: "a.u.", sample_indices: indices, x, y: peaks },
    ],
  };
}

function demoDirname(path: string): string {
  const trimmed = path.replace(/\\/g, "/");
  const slash = trimmed.lastIndexOf("/");
  return slash >= 0 ? trimmed.slice(0, slash) : ".";
}

function demoOutputFolder(path: string): string {
  return `${demoDirname(path)}/dfof_results`;
}

function demoStem(path: string): string {
  const trimmed = path.replace(/\\/g, "/");
  const base = trimmed.slice(trimmed.lastIndexOf("/") + 1);
  return base.replace(/\.csv$/i, "");
}

export class DemoBackend implements BackendAdapter {
  readonly mode = "demo" as const;
  private sequence = 0;
  private listeners = new Set<LogListener>();
  private running = false;
  private fileType: "single" | "dual" = "single";
  private loadedPath: string | null = null;

  async start(): Promise<NegotiationResult> {
    this.running = true;
    this.log("info", "Demo data source online.");
    return {
      protocol_version: PROTOCOL_VERSION,
      sidecar: { name: "browser-demo", version: "0.1.0", app_version: "3.0.0" },
      capabilities: ["ping", "version", "sample_plot", "shutdown", "raw_photometry"],
      limits,
    };
  }

  async ping(): Promise<PingResult> {
    this.requireRunning();
    this.sequence += 1;
    this.log("info", `Ping ${this.sequence} completed in demo mode.`);
    return { status: "ready", protocol_version: PROTOCOL_VERSION, sequence: this.sequence };
  }

  async version(): Promise<VersionResult> {
    this.requireRunning();
    return {
      sidecar_version: "0.1.0-demo",
      app_version: "3.0.0",
      python_version: "not used in browser demo",
      protocol_version: PROTOCOL_VERSION,
      scientific_runtime: {},
    };
  }

  async samplePlot(maxPoints = 900): Promise<SamplePlotResult> {
    this.requireRunning();
    const plot = createRawTrace(maxPoints);
    this.log("info", `Raw trace ready with ${plot.series[0].x.length} displayed points per series.`);
    return plot;
  }

  async selectGrant(kind: "file" | "folder"): Promise<NativeGrant> {
    this.requireRunning();
    const noun = kind === "file" ? "example_data/recording_465.csv" : "Example data folder";
    this.log("info", `Selected ${kind === "file" ? "raw photometry file" : "data folder"}: ${noun}`);
    return { grant_id: `demo-${kind}-grant`, kind, display_name: noun, path: noun };
  }

  async loadPhotometryFile(path: string): Promise<RawFileContext> {
    this.requireRunning();
    const plot = createRawTrace(900);
    const outputFolder = demoOutputFolder(path);
    this.loadedPath = path;
    this.log("info", `INFO  [DFer] Selected: ${path}`);
    this.log("info", "Raw trace drawn. Set the analysis window, then generate options.");
    return {
      file_path: path,
      file_type: "single",
      signal_label: "465nm",
      signal_columns: ["405nm", "465nm"],
      output_folder: outputFolder,
      sample_count: plot.sample_count,
      duration_s: (plot.sample_count - 1) / 100,
      plot,
    };
  }

  async generateOptions(_window: AnalysisWindow): Promise<DferOptionsResult> {
    void _window;
    this.requireRunning();
    this.log("info", "INFO  [DFer] Preview complete. Choose option 1-4, then run final.");
    return { file_type: this.fileType, signal_label: "465nm", option_titles: OPTION_TITLES };
  }

  async previewOption(index: number, dualDisplay: DualDisplay): Promise<SamplePlotResult> {
    this.requireRunning();
    return createOptionPreview(index, dualDisplay);
  }

  async runDfer(params: DferRunParams): Promise<DferRunResult> {
    this.requireRunning();
    const path = this.loadedPath ?? "example_data/recording_465.csv";
    const stem = demoStem(path);
    const outputFolder = demoOutputFolder(path);
    const resultCsv = `${outputFolder}/${stem}_Data.csv`;
    this.log("info", `INFO  [DFer] Final analysis complete (option ${params.option}).`);
    this.log("info", `INFO  [DFer] Saved: ${resultCsv}`);
    return { result_csv: resultCsv, output_folder: outputFolder, plots: createDferResultPlots() };
  }

  async runPfer(params: PferRunParams): Promise<PferRunResult> {
    this.requireRunning();
    const stem = demoStem(params.csv_path);
    const outputFolder = demoDirname(params.csv_path);
    const statsCsv = `${outputFolder}/${stem}_Peak_STATS.csv`;
    this.log("info", "INFO  [PFer] Peak finding complete.");
    this.log("info", `INFO  [PFer] Saved: ${statsCsv}`);
    return { stats_csv: statsCsv, plot: createPferPlot() };
  }

  async savePlotImage(_params: PlotSaveParams): Promise<PlotSaveResult> {
    this.requireRunning();
    const path = this.loadedPath ?? "example_data/recording_465.csv";
    const stem = demoStem(path);
    this.log("info", `INFO  [Plot] Saved image: example_data/plots/${stem}/${stem}_plot_1.png (demo)`);
    return { path: `example_data/plots/${stem}/${stem}_plot_1.png` };
  }

  async shutdown(): Promise<void> {
    this.running = false;
    this.log("warning", "Demo data source stopped.");
  }

  async onLog(listener: LogListener): Promise<() => void> {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private requireRunning(): void {
    if (!this.running) {
      throw new BackendError({
        code: "sidecar_not_running",
        user_text: "The processing service is not running.",
        recovery: "restart_sidecar",
        details: {},
      });
    }
  }

  private log(level: LogEntry["level"], message: string): void {
    this.listeners.forEach((listener) => listener({ level, message }));
  }
}

export class TauriBackend implements BackendAdapter {
  readonly mode = "tauri" as const;
  private requestSequence = 0;

  async start(): Promise<NegotiationResult> {
    return invoke<NegotiationResult>("start_sidecar");
  }

  ping(): Promise<PingResult> {
    return this.request<PingResult>("sidecar.ping", {});
  }

  version(): Promise<VersionResult> {
    return this.request<VersionResult>("sidecar.version", {});
  }

  samplePlot(maxPoints = 900): Promise<SamplePlotResult> {
    return this.request<SamplePlotResult>("plot.sample", {
      sample_count: 48_000,
      viewport: { start_index: 0, end_index: 47_999 },
      max_points: maxPoints,
    });
  }

  selectGrant(kind: "file" | "folder"): Promise<NativeGrant | null> {
    return invoke<NativeGrant | null>("select_native_grant", { kind });
  }

  loadPhotometryFile(path: string): Promise<RawFileContext> {
    return this.request<RawFileContext>("raw.load_file", { path });
  }

  generateOptions(window: AnalysisWindow): Promise<DferOptionsResult> {
    return this.request<DferOptionsResult>("raw.generate_options", { window });
  }

  previewOption(index: number, dualDisplay: DualDisplay): Promise<SamplePlotResult> {
    return this.request<SamplePlotResult>("raw.preview_option", { index, dual_display: dualDisplay });
  }

  runDfer(params: DferRunParams): Promise<DferRunResult> {
    return this.request<DferRunResult>("raw.run_dfer", params);
  }

  runPfer(params: PferRunParams): Promise<PferRunResult> {
    return this.request<PferRunResult>("raw.run_pfer", params);
  }

  savePlotImage(params: PlotSaveParams): Promise<PlotSaveResult> {
    return this.request<PlotSaveResult>("raw.save_plot", params);
  }

  async shutdown(): Promise<void> {
    await invoke("shutdown_sidecar");
  }

  async onLog(listener: LogListener): Promise<UnlistenFn> {
    return listen<LogEntry>("sidecar-log", (event) => listener(event.payload));
  }

  private async request<T>(method: string, params: object): Promise<T> {
    this.requestSequence += 1;
    const response = await invoke<ResponseEnvelope<T>>("proxy_sidecar_request", {
      request: {
        protocol_version: PROTOCOL_VERSION,
        id: `ui-${this.requestSequence}`,
        method,
        params,
      },
    });
    if (!response.ok || response.result === undefined) {
      throw new BackendError(
        response.error ?? {
          code: "invalid_response",
          user_text: "The processing service returned an invalid response.",
          recovery: "restart_sidecar",
          details: {},
        },
      );
    }
    return response.result;
  }
}

export function createBackend(mode: string = import.meta.env.VITE_BACKEND_MODE): BackendAdapter {
  if (mode === "demo") return new DemoBackend();
  if (mode === "tauri") return new TauriBackend();
  throw new Error(`Unsupported VITE_BACKEND_MODE: ${mode}`);
}