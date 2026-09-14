import type { PlotSeries } from "../protocol";

export function colorForPlotSeries(series: PlotSeries): string {
  const identity = `${series.id} ${series.signal_id} ${series.label}`.toLowerCase();
  if (identity.includes("405")) return "#800080";
  if (identity.includes("560")) return "#d62728";
  if (identity.includes("peak") || identity.includes("fit")) return "#d62728";
  if (identity.includes("trough")) return "#2563eb";
  return "#008000";
}
