import type { PlotSeries, SamplePlotResult } from "./protocol";

export interface TracePoint {
  x: number;
  y: number;
}

export interface TraceSeries {
  id: string;
  label: string;
  color: string;
  points: TracePoint[];
  dashed?: boolean;
  opacity?: number;
}

export const OPTION_TITLES = [
  "Option 1: Good noise correction and bleach correction",
  "Option 2: Assumes shifts in 465 baseline are independent of activity",
  "Option 3: No noise correction",
  "Option 4: No noise correction, no activity-dependent baseline correction",
];

export const DFER_OPTION_LABELS: Record<string, string> = {
  "1": "1 = standard baseline and noise correction",
  "2": "2 = alternative baseline fit",
  "3": "3 = no noise correction",
  "4": "4 = no noise correction and no activity baseline correction",
};

export const START_ALIASES = new Set(["start", "min"]);
export const END_ALIASES = new Set(["end", "max"]);

export type SignalFormat = "single" | "dual";

export interface SignalContext {
  fileType: SignalFormat;
  primary: PlotSeries;
  reference: PlotSeries | null;
  primaryLabel: string;
  referenceLabel: string;
  signalOptions: string[];
}

export interface ResolvedWindow {
  start: number;
  end: number;
  duration: number;
  valid: boolean;
}

export interface DfofResult {
  time: number[];
  primary: number[];
  reference: number[];
  primaryLabel: string;
  referenceLabel: string;
}

export interface PeakMarker {
  index: number;
  time: number;
  value: number;
}

export function formatDuration(seconds: number): string {
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remaining = total % 60;
  if (hours > 0) return `${hours}h ${minutes}m ${remaining}s`;
  if (minutes > 0) return `${minutes}m ${remaining}s`;
  return `${remaining}s`;
}

export function normaliseWindowInput(text: string, aliases: Set<string>): string {
  const value = text.trim();
  if (!value || aliases.has(value.toLowerCase())) return "";
  return value;
}

export function parseWindowEndpoint(
  text: string,
  fallback: number,
  aliases: Set<string>,
): number {
  const value = text.trim().toLowerCase();
  if (!value || aliases.has(value)) return fallback;
  return Number(value);
}

export function resolveWindow(
  startText: string,
  endText: string,
  minimum: number,
  maximum: number,
): ResolvedWindow {
  const start = parseWindowEndpoint(startText, minimum, START_ALIASES);
  const end = parseWindowEndpoint(endText, maximum, END_ALIASES);
  if (!Number.isFinite(start) || !Number.isFinite(end)) {
    return { start: minimum, end: maximum, duration: maximum - minimum, valid: false };
  }
  const clampedStart = Math.max(start, minimum);
  const clampedEnd = Math.min(end, maximum);
  if (clampedEnd <= clampedStart) {
    return { start: minimum, end: maximum, duration: maximum - minimum, valid: false };
  }
  return {
    start: clampedStart,
    end: clampedEnd,
    duration: clampedEnd - clampedStart,
    valid: true,
  };
}

function shortLabel(label: string): string {
  return label
    .replace(/\s*signal$/i, "")
    .replace(/\s*reference$/i, "")
    .replace(/\s+/g, "");
}

function isDualSeries(series: PlotSeries[]): boolean {
  const haystack = series.map((item) => `${item.label} ${item.signal_id}`).join(" ");
  return /470|560/.test(haystack);
}

export function classifySignals(plot: SamplePlotResult): SignalContext {
  const dual = isDualSeries(plot.series);
  const primary = plot.series[0];
  const reference = plot.series[1] ?? null;
  if (dual) {
    return {
      fileType: "dual",
      primary,
      reference,
      primaryLabel: "470nm",
      referenceLabel: "560nm",
      signalOptions: ["Both", "470nm", "560nm"],
    };
  }
  return {
    fileType: "single",
    primary,
    reference,
    primaryLabel: shortLabel(primary?.label ?? "465nm"),
    referenceLabel: shortLabel(reference?.label ?? "405nm"),
    signalOptions: [shortLabel(primary?.label ?? "465nm")],
  };
}

export function zipPoints(x: number[], y: number[]): TracePoint[] {
  const length = Math.min(x.length, y.length);
  const points: TracePoint[] = [];
  for (let index = 0; index < length; index += 1) {
    points.push({ x: x[index], y: y[index] });
  }
  return points;
}

export function buildRawTrace(context: SignalContext, signalDisplay: string): TraceSeries[] {
  const trace: TraceSeries[] = [];
  if (context.fileType === "single") {
    trace.push({
      id: context.primary.id,
      label: context.primaryLabel,
      color: "var(--accent)",
      points: zipPoints(context.primary.x, context.primary.y),
    });
    if (context.reference) {
      trace.push({
        id: context.reference.id,
        label: context.referenceLabel,
        color: "var(--warn)",
        points: zipPoints(context.reference.x, context.reference.y),
        opacity: 0.8,
      });
    }
    return trace;
  }
  if (signalDisplay !== "560nm") {
    trace.push({
      id: context.primary.id,
      label: "470nm",
      color: "var(--accent)",
      points: zipPoints(context.primary.x, context.primary.y),
    });
  }
  if (signalDisplay !== "470nm" && context.reference) {
    trace.push({
      id: context.reference.id,
      label: "560nm",
      color: "var(--warn)",
      points: zipPoints(context.reference.x, context.reference.y),
      opacity: 0.8,
    });
  }
  return trace;
}

export function movingAverage(values: number[], window: number): number[] {
  if (values.length === 0) return [];
  const span = Math.max(1, Math.min(Math.round(window), values.length));
  const result = new Array<number>(values.length);
  let running = 0;
  for (let index = 0; index < values.length; index += 1) {
    running += values[index];
    if (index >= span) running -= values[index - span];
    result[index] = running / Math.min(index + 1, span);
  }
  return result;
}

function relativeChange(values: number[], window: number): number[] {
  const baseline = movingAverage(values, window);
  return values.map((value, index) => {
    const reference = baseline[index];
    return (value - reference) / (Math.abs(reference) + 1e-9);
  });
}

export function computeDfof(
  context: SignalContext,
  primaryValues: number[],
  referenceValues: number[] | null,
  window?: number,
): DfofResult {
  const span = window ?? Math.max(1, Math.min(Math.floor(primaryValues.length / 10), 1000));
  return {
    time: context.primary.x.map((value) => value / 60),
    primary: relativeChange(primaryValues, span),
    reference: referenceValues ? relativeChange(referenceValues, span) : [],
    primaryLabel: context.primaryLabel,
    referenceLabel: context.referenceLabel,
  };
}

export function computeZScore(values: number[]): number[] {
  if (values.length === 0) return [];
  const mean = values.reduce((total, value) => total + value, 0) / values.length;
  const variance =
    values.reduce((total, value) => total + (value - mean) ** 2, 0) / values.length;
  const deviation = Math.sqrt(variance) || 1;
  return values.map((value) => (value - mean) / deviation);
}

export function buildDferTrace(
  result: DfofResult,
  channel: "dfof" | "zscore",
  show405: boolean,
): TraceSeries[] {
  const primary = channel === "dfof" ? result.primary : computeZScore(result.primary);
  const suffix = channel === "dfof" ? "dF/F" : "Z-score";
  const trace: TraceSeries[] = [
    {
      id: "primary",
      label: `${result.primaryLabel} ${suffix}`,
      color: "var(--accent)",
      points: zipPoints(result.time, primary),
    },
  ];
  if (show405 && result.reference.length > 0) {
    const reference =
      channel === "dfof" ? result.reference : computeZScore(result.reference);
    trace.push({
      id: "reference",
      label: `${result.referenceLabel} ${suffix}`,
      color: "var(--warn)",
      points: zipPoints(result.time, reference),
      opacity: 0.7,
    });
  }
  return trace;
}

export function buildOptionPreview(
  context: SignalContext,
  primaryValues: number[],
  referenceValues: number[] | null,
  optionIndex: number,
): TraceSeries[] {
  const span = Math.max(1, Math.min(Math.floor(primaryValues.length / 8), 1200));
  const fittedBase = movingAverage(referenceValues ?? primaryValues, span);
  const offset = primaryValues.length > 0 && fittedBase.length > 0
    ? primaryValues[0] - fittedBase[0]
    : 0;
  const time = context.primary.x;
  return [
    {
      id: "primary",
      label: context.primaryLabel,
      color: "var(--accent)",
      points: zipPoints(time, primaryValues),
    },
    {
      id: "fitted",
      label: `Option ${optionIndex + 1} fitted control`,
      color: "var(--warn)",
      points: zipPoints(time, fittedBase.map((value) => value + offset)),
      dashed: true,
      opacity: 0.75,
    },
  ];
}

export function findPeaks(
  values: number[],
  times: number[],
  prominence: number,
  artifactThreshold: number,
): { peaks: PeakMarker[]; troughs: PeakMarker[] } {
  const peaks: PeakMarker[] = [];
  const minimumGap = Math.max(1, Math.round(artifactThreshold));
  for (let index = 1; index < values.length - 1; index += 1) {
    const value = values[index];
    if (value - values[index - 1] <= 0 || value - values[index + 1] < 0) continue;
    if (value < prominence) continue;
    const previous = peaks[peaks.length - 1];
    if (previous && index - previous.index < minimumGap) {
      if (value > previous.value) {
        peaks[peaks.length - 1] = { index, time: times[index], value };
      }
      continue;
    }
    peaks.push({ index, time: times[index], value });
  }

  const troughs: PeakMarker[] = [];
  let cursor = 0;
  for (const peak of peaks) {
    let lowest = cursor;
    for (let index = cursor; index <= peak.index; index += 1) {
      if (values[index] < values[lowest]) lowest = index;
    }
    troughs.push({ index: lowest, time: times[lowest], value: values[lowest] });
    cursor = peak.index;
  }
  return { peaks, troughs };
}
