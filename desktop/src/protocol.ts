export const PROTOCOL_VERSION = 1 as const;
export const MAX_POINTS_PER_SERIES = 10_000;
export const MAX_POINTS_ACROSS_PANELS = 50_000;

export type Recovery = "none" | "retry" | "restart_sidecar" | "change_input";

export interface ProtocolError {
  code: string;
  user_text: string;
  recovery: Recovery;
  details: Record<string, unknown>;
}

export interface ResponseEnvelope<T> {
  protocol_version: number;
  id: string | null;
  ok: boolean;
  result?: T;
  error?: ProtocolError;
}

export interface NegotiationResult {
  protocol_version: number;
  sidecar: { name: string; version: string; app_version: string };
  capabilities: string[];
  limits: {
    max_frame_bytes: number;
    max_points_per_series: number;
    max_points_across_panels: number;
  };
}

export interface PingResult {
  status: "ready";
  protocol_version: number;
  sequence: number;
}

export interface VersionResult {
  sidecar_version: string;
  app_version: string;
  python_version: string;
  protocol_version: number;
  scientific_runtime: Record<string, boolean>;
}

export interface PlotSeries {
  id: string;
  signal_id: string;
  label: string;
  unit: string;
  sample_indices: number[];
  x: number[];
  y: number[];
}

export interface SamplePlotResult {
  plot_id: string;
  title: string;
  x_axis: { label: string; unit: string };
  sample_count: number;
  viewport: { start_index: number; end_index: number };
  display_reduced: boolean;
  decimation: string;
  series: PlotSeries[];
}

export interface NativeGrant {
  grant_id: string;
  kind: "file" | "folder";
  display_name: string;
  /** Absolute path retained by the native host for the sidecar request. */
  path: string;
}

export interface LogEntry {
  level: "info" | "warning" | "error";
  message: string;
}

export class BackendError extends Error {
  readonly envelope: ProtocolError;

  constructor(envelope: ProtocolError) {
    super(envelope.user_text);
    this.name = "BackendError";
    this.envelope = envelope;
  }
}

// ---------------------------------------------------------------------------
// Raw photometry parity surface
// ---------------------------------------------------------------------------

export type DualDisplay = "both" | "470" | "560";

/** Analysis window in seconds. A null endpoint means the recording bound. */
export interface AnalysisWindow {
  start_s: number | null;
  end_s: number | null;
}

/** Detected context for a raw photometry CSV, mirroring detect_photometry_file_type. */
export interface RawFileContext {
  file_path: string;
  file_type: "single" | "dual";
  signal_label: string;
  signal_columns: string[];
  output_folder: string;
  sample_count: number;
  duration_s: number;
  plot: SamplePlotResult;
}

/** DFer option preview metadata (titles come from src/features/raw_photometry/plotting.py). */
export interface DferOptionsResult {
  file_type: "single" | "dual";
  signal_label: string;
  option_titles: string[];
}

export interface DferRunParams {
  option: string;
  window: AnalysisWindow;
}

export interface DferRunResult {
  result_csv: string;
  output_folder: string;
  plots: { dfof: SamplePlotResult; zscore: SamplePlotResult };
}

export interface PferRunParams {
  csv_path: string;
  baseline_start: string;
  baseline_end: string;
  prominence: number;
  artifact_threshold: number;
}

export interface PferRunResult {
  stats_csv: string;
  plot: SamplePlotResult;
}

export interface PlotSaveParams {
  kind: "dfer" | "pfer";
  graph?: "dfof" | "zscore";
  show_405?: boolean;
}

export interface PlotSaveResult {
  path: string;
}
