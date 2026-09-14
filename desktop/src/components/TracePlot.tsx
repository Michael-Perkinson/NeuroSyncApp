import { useRef, useState, type PointerEvent, type WheelEvent } from "react";
import { colorForPlotSeries } from "./plotColors";
import type { PlotSeries, SamplePlotResult } from "../protocol";

export interface PlotMarkers {
  start?: number;
  end?: number;
}

export interface TracePlotProps {
  plot: SamplePlotResult;
  xAxisLabel: string;
  yAxisLabel: string;
  secondaryYAxisLabel?: string;
  dualAxis?: boolean;
  markers?: PlotMarkers;
  emptyText: string;
  ariaLabel: string;
}

interface PlotBounds {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
  secondaryYMin?: number;
  secondaryYMax?: number;
}

interface PlotPoint {
  x: number;
  y: number;
}

interface ZoomSelection {
  start: PlotPoint;
  end: PlotPoint;
}

type InteractionMode = "pan" | "zoom";

const WIDTH = 1000;
const HEIGHT = 480;
const PADDING = { left: 76, right: 76, top: 24, bottom: 62 };
const PLOT_RIGHT = WIDTH - PADDING.right;
const PLOT_BOTTOM = HEIGHT - PADDING.bottom;
const MIN_ZOOM_RATIO = 0.0001;

function finiteExtent(series: PlotSeries[], axis: "x" | "y"): [number, number] | null {
  let minimum = Infinity;
  let maximum = -Infinity;
  for (const item of series) {
    const length = Math.min(item.x.length, item.y.length);
    for (let index = 0; index < length; index += 1) {
      const x = item.x[index];
      const y = item.y[index];
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      const value = axis === "x" ? x : y;
      minimum = Math.min(minimum, value);
      maximum = Math.max(maximum, value);
    }
  }
  return Number.isFinite(minimum) && Number.isFinite(maximum) ? [minimum, maximum] : null;
}

function paddedExtent(minimum: number, maximum: number, ratio: number): [number, number] {
  const span = maximum - minimum;
  const padding = span === 0 ? Math.max(Math.abs(minimum) * ratio, 0.5) : span * ratio;
  return [minimum - padding, maximum + padding];
}

function calculateBounds(plot: SamplePlotResult, dualAxis: boolean): PlotBounds | null {
  if (plot.series.length === 0) return null;
  const xExtent = finiteExtent(plot.series, "x");
  if (!xExtent) return null;

  const primaryExtent = finiteExtent(dualAxis ? [plot.series[0]] : plot.series, "y");
  if (!primaryExtent) return null;
  const primaryY = paddedExtent(primaryExtent[0], primaryExtent[1], 0.05);
  const bounds: PlotBounds = {
    xMin: paddedExtent(xExtent[0], xExtent[1], 0.005)[0],
    xMax: paddedExtent(xExtent[0], xExtent[1], 0.005)[1],
    yMin: primaryY[0],
    yMax: primaryY[1],
  };

  if (dualAxis && plot.series[1]) {
    const secondaryExtent = finiteExtent([plot.series[1]], "y");
    if (secondaryExtent) {
      const secondaryY = paddedExtent(secondaryExtent[0], secondaryExtent[1], 0.05);
      bounds.secondaryYMin = secondaryY[0];
      bounds.secondaryYMax = secondaryY[1];
    }
  }
  return bounds;
}

function niceStep(range: number, targetTickCount: number): number {
  const rough = Math.max(range / targetTickCount, Number.EPSILON);
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const fraction = rough / magnitude;
  const preferred = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
  return preferred * magnitude;
}

function makeTicks(minimum: number, maximum: number, targetTickCount = 6): number[] {
  const step = niceStep(maximum - minimum, targetTickCount);
  const first = Math.ceil(minimum / step - 1e-10) * step;
  const ticks: number[] = [];
  for (let value = first; value <= maximum + step * 1e-8 && ticks.length < 100; value += step) {
    ticks.push(Number(value.toPrecision(12)));
  }
  if (ticks.length < 2) {
    return [minimum, maximum];
  }
  return ticks;
}

function formatTick(value: number, step: number): string {
  const decimals = step >= 1 ? 0 : Math.min(8, Math.max(0, Math.ceil(-Math.log10(step))));
  const rounded = Math.abs(value) < step * 1e-8 ? 0 : value;
  return rounded.toFixed(decimals).replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.max(minimum, Math.min(maximum, value));
}

function constrainRange(
  minimum: number,
  maximum: number,
  fullMinimum: number,
  fullMaximum: number,
): [number, number] {
  const fullSpan = fullMaximum - fullMinimum;
  const span = clamp(maximum - minimum, fullSpan * MIN_ZOOM_RATIO, fullSpan);
  const nextMinimum = clamp(minimum, fullMinimum, fullMaximum - span);
  return [nextMinimum, nextMinimum + span];
}

function constrainView(view: PlotBounds, bounds: PlotBounds): PlotBounds {
  const x = constrainRange(view.xMin, view.xMax, bounds.xMin, bounds.xMax);
  const y = constrainRange(view.yMin, view.yMax, bounds.yMin, bounds.yMax);
  const next: PlotBounds = { xMin: x[0], xMax: x[1], yMin: y[0], yMax: y[1] };
  if (
    bounds.secondaryYMin !== undefined &&
    bounds.secondaryYMax !== undefined &&
    view.secondaryYMin !== undefined &&
    view.secondaryYMax !== undefined
  ) {
    const secondary = constrainRange(
      view.secondaryYMin,
      view.secondaryYMax,
      bounds.secondaryYMin,
      bounds.secondaryYMax,
    );
    next.secondaryYMin = secondary[0];
    next.secondaryYMax = secondary[1];
  }
  return next;
}

function scaleX(value: number, view: PlotBounds): number {
  return PADDING.left + ((value - view.xMin) / (view.xMax - view.xMin)) * (PLOT_RIGHT - PADDING.left);
}

function scaleY(value: number, minimum: number, maximum: number): number {
  return PADDING.top + (1 - (value - minimum) / (maximum - minimum)) * (PLOT_BOTTOM - PADDING.top);
}

function toPath(series: PlotSeries, view: PlotBounds, secondaryAxis: boolean): string {
  const minimum = secondaryAxis && view.secondaryYMin !== undefined ? view.secondaryYMin : view.yMin;
  const maximum = secondaryAxis && view.secondaryYMax !== undefined ? view.secondaryYMax : view.yMax;
  const length = Math.min(series.x.length, series.y.length);
  let path = "";
  let connected = false;
  for (let index = 0; index < length; index += 1) {
    const x = series.x[index];
    const y = series.y[index];
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      connected = false;
      continue;
    }
    path += `${connected ? "L" : "M"}${scaleX(x, view).toFixed(2)},${scaleY(y, minimum, maximum).toFixed(2)} `;
    connected = true;
  }
  return path.trim();
}

function isMarkerSeries(series: PlotSeries): boolean {
  const identity = `${series.id} ${series.signal_id} ${series.label}`.toLowerCase();
  return identity.includes("peak") || identity.includes("trough");
}

function markerPoints(series: PlotSeries, view: PlotBounds, secondaryAxis: boolean): PlotPoint[] {
  const minimum = secondaryAxis && view.secondaryYMin !== undefined ? view.secondaryYMin : view.yMin;
  const maximum = secondaryAxis && view.secondaryYMax !== undefined ? view.secondaryYMax : view.yMax;
  const length = Math.min(series.x.length, series.y.length);
  const points: PlotPoint[] = [];
  for (let index = 0; index < length; index += 1) {
    const x = series.x[index];
    const y = series.y[index];
    if (Number.isFinite(x) && Number.isFinite(y)) {
      points.push({ x: scaleX(x, view), y: scaleY(y, minimum, maximum) });
    }
  }
  return points;
}

function dataPointAt(point: PlotPoint, view: PlotBounds): PlotBounds {
  const xRatio = (point.x - PADDING.left) / (PLOT_RIGHT - PADDING.left);
  const yRatio = (point.y - PADDING.top) / (PLOT_BOTTOM - PADDING.top);
  const result: PlotBounds = {
    xMin: view.xMin + xRatio * (view.xMax - view.xMin),
    xMax: view.xMax,
    yMin: view.yMax - yRatio * (view.yMax - view.yMin),
    yMax: view.yMax,
  };
  if (view.secondaryYMin !== undefined && view.secondaryYMax !== undefined) {
    result.secondaryYMin = view.secondaryYMax - yRatio * (view.secondaryYMax - view.secondaryYMin);
    result.secondaryYMax = view.secondaryYMax;
  }
  return result;
}

function zoomAround(
  view: PlotBounds,
  factor: number,
  bounds: PlotBounds,
  anchor?: PlotBounds,
): PlotBounds {
  const xAnchor = anchor?.xMin ?? (view.xMin + view.xMax) / 2;
  const yAnchor = anchor?.yMin ?? (view.yMin + view.yMax) / 2;
  const next: PlotBounds = {
    xMin: xAnchor - (xAnchor - view.xMin) * factor,
    xMax: xAnchor + (view.xMax - xAnchor) * factor,
    yMin: yAnchor - (yAnchor - view.yMin) * factor,
    yMax: yAnchor + (view.yMax - yAnchor) * factor,
  };
  if (
    view.secondaryYMin !== undefined &&
    view.secondaryYMax !== undefined &&
    anchor?.secondaryYMin !== undefined &&
    anchor.secondaryYMax !== undefined
  ) {
    const secondaryAnchor = anchor.secondaryYMin;
    next.secondaryYMin = secondaryAnchor - (secondaryAnchor - view.secondaryYMin) * factor;
    next.secondaryYMax = secondaryAnchor + (view.secondaryYMax - secondaryAnchor) * factor;
  }
  return constrainView(next, bounds);
}

function svgPoint(svg: SVGSVGElement, clientX: number, clientY: number): PlotPoint {
  const rect = svg.getBoundingClientRect();
  return {
    x: ((clientX - rect.left) / Math.max(rect.width, 1)) * WIDTH,
    y: ((clientY - rect.top) / Math.max(rect.height, 1)) * HEIGHT,
  };
}

function insidePlot(point: PlotPoint): boolean {
  return point.x >= PADDING.left && point.x <= PLOT_RIGHT && point.y >= PADDING.top && point.y <= PLOT_BOTTOM;
}

function clampToPlot(point: PlotPoint): PlotPoint {
  return {
    x: clamp(point.x, PADDING.left, PLOT_RIGHT),
    y: clamp(point.y, PADDING.top, PLOT_BOTTOM),
  };
}

export default function TracePlot({
  plot,
  xAxisLabel,
  yAxisLabel,
  secondaryYAxisLabel,
  dualAxis = false,
  markers,
  emptyText,
  ariaLabel,
}: TracePlotProps) {
  const bounds = calculateBounds(plot, dualAxis);
  const boundsKey = bounds ? Object.values(bounds).join("|") : "empty";
  const [viewState, setViewState] = useState<{ boundsKey: string; view: PlotBounds | null }>({ boundsKey, view: bounds });
  const [interactionMode, setInteractionMode] = useState<InteractionMode>("pan");
  const [dragging, setDragging] = useState(false);
  const [zoomSelection, setZoomSelection] = useState<ZoomSelection | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{ mode: InteractionMode; start: PlotPoint; last: PlotPoint; pointerId: number } | null>(null);

  const view = viewState.boundsKey === boundsKey ? viewState.view : bounds;
  const visibleZoomSelection = viewState.boundsKey === boundsKey ? zoomSelection : null;

  if (!bounds || !view) {
    return <div className="plot-empty">{emptyText}</div>;
  }

  const currentView = constrainView(view, bounds);
  const setPlotView = (next: PlotBounds | ((previous: PlotBounds) => PlotBounds)) => {
    setViewState((state) => {
      const previous = state.boundsKey === boundsKey && state.view ? state.view : bounds;
      const resolved = typeof next === "function" ? next(previous) : next;
      return { boundsKey, view: resolved };
    });
  };
  const xStep = niceStep(currentView.xMax - currentView.xMin, 6);
  const yStep = niceStep(currentView.yMax - currentView.yMin, 6);
  const xTicks = makeTicks(currentView.xMin, currentView.xMax);
  const yTicks = makeTicks(currentView.yMin, currentView.yMax);
  const secondaryYMin = currentView.secondaryYMin;
  const secondaryYMax = currentView.secondaryYMax;
  const secondaryStep = secondaryYMin !== undefined && secondaryYMax !== undefined ? niceStep(secondaryYMax - secondaryYMin, 6) : 1;
  const secondaryTicks =
    secondaryYMin !== undefined && secondaryYMax !== undefined
      ? makeTicks(secondaryYMin, secondaryYMax)
      : [];
  const hasSecondaryAxis = dualAxis && secondaryYMin !== undefined && secondaryYMax !== undefined;
  const clipId = `plot-clip-${plot.plot_id.replace(/[^a-zA-Z0-9_-]/g, "-")}`;

  const onWheel = (event: WheelEvent<SVGSVGElement>) => {
    // A wheel over the graph belongs to the plot, not the page. Preventing the
    // browser default also keeps the document from scrolling while zooming.
    event.preventDefault();
    event.stopPropagation();
    const point = svgPoint(event.currentTarget, event.clientX, event.clientY);
    if (!insidePlot(point)) return;
    const anchor = dataPointAt(point, currentView);
    const factor = event.deltaY > 0 ? 1.2 : 0.8;
    setPlotView((previous) => zoomAround(previous, factor, bounds, anchor));
  };

  const onPointerDown = (event: PointerEvent<SVGSVGElement>) => {
    if (event.button !== 0) return;
    const point = svgPoint(event.currentTarget, event.clientX, event.clientY);
    if (!insidePlot(point)) return;
    dragRef.current = { mode: interactionMode, start: point, last: point, pointerId: event.pointerId };
    setDragging(true);
    if (interactionMode === "zoom") setZoomSelection({ start: point, end: point });
    if (event.currentTarget.setPointerCapture) {
      event.currentTarget.setPointerCapture(event.pointerId);
    }
  };

  const onPointerMove = (event: PointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const point = clampToPlot(svgPoint(event.currentTarget, event.clientX, event.clientY));
    if (drag.mode === "pan") {
      const deltaX = point.x - drag.last.x;
      const deltaY = point.y - drag.last.y;
      setPlotView((previous) => {
        const xShift = -(deltaX / (PLOT_RIGHT - PADDING.left)) * (previous.xMax - previous.xMin);
        const yShift = (deltaY / (PLOT_BOTTOM - PADDING.top)) * (previous.yMax - previous.yMin);
        return constrainView(
          {
            ...previous,
            xMin: previous.xMin + xShift,
            xMax: previous.xMax + xShift,
            yMin: previous.yMin + yShift,
            yMax: previous.yMax + yShift,
            secondaryYMin:
              previous.secondaryYMin !== undefined && previous.secondaryYMax !== undefined
                ? previous.secondaryYMin + (deltaY / (PLOT_BOTTOM - PADDING.top)) * (previous.secondaryYMax - previous.secondaryYMin)
                : undefined,
            secondaryYMax:
              previous.secondaryYMin !== undefined && previous.secondaryYMax !== undefined
                ? previous.secondaryYMax + (deltaY / (PLOT_BOTTOM - PADDING.top)) * (previous.secondaryYMax - previous.secondaryYMin)
                : undefined,
          },
          bounds,
        );
      });
    } else {
      setZoomSelection({ start: drag.start, end: point });
    }
    drag.last = point;
  };

  const finishPointer = (event: PointerEvent<SVGSVGElement>, cancelled = false) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const point = clampToPlot(svgPoint(event.currentTarget, event.clientX, event.clientY));
    if (!cancelled && drag.mode === "zoom" && Math.abs(point.x - drag.start.x) > 8 && Math.abs(point.y - drag.start.y) > 8) {
      setPlotView((previous) => {
        const start = dataPointAt(drag.start, previous);
        const end = dataPointAt(point, previous);
        const next: PlotBounds = {
          ...previous,
          xMin: Math.min(start.xMin, end.xMin),
          xMax: Math.max(start.xMin, end.xMin),
          yMin: Math.min(start.yMin, end.yMin),
          yMax: Math.max(start.yMin, end.yMin),
        };
        if (previous.secondaryYMin !== undefined && previous.secondaryYMax !== undefined) {
          next.secondaryYMin = Math.min(start.secondaryYMin ?? previous.secondaryYMin, end.secondaryYMin ?? previous.secondaryYMin);
          next.secondaryYMax = Math.max(start.secondaryYMin ?? previous.secondaryYMax, end.secondaryYMin ?? previous.secondaryYMax);
        }
        return constrainView(next, bounds);
      });
    }
    dragRef.current = null;
    setDragging(false);
    setZoomSelection(null);
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) {
      event.currentTarget.releasePointerCapture?.(event.pointerId);
    }
  };

  const resetView = () => setPlotView(bounds);
  const zoom = (factor: number) => {
    setPlotView((previous) => zoomAround(previous, factor, bounds));
  };

  return (
    <div className="interactive-plot">
      <div className="plot-toolbar">
        <span className="plot-hint">Scroll to zoom · drag to {interactionMode}</span>
        <div className="plot-actions" role="toolbar" aria-label="Plot controls">
          <button
            className={`plot-tool ${interactionMode === "pan" ? "active" : ""}`}
            aria-pressed={interactionMode === "pan"}
            onClick={() => setInteractionMode("pan")}
            title="Drag to move the plot"
          >
            Pan
          </button>
          <button
            className={`plot-tool ${interactionMode === "zoom" ? "active" : ""}`}
            aria-pressed={interactionMode === "zoom"}
            onClick={() => setInteractionMode("zoom")}
            title="Drag a rectangle to zoom"
          >
            Zoom
          </button>
          <button className="plot-tool" onClick={() => zoom(0.8)} aria-label="Zoom in" title="Zoom in">
            +
          </button>
          <button className="plot-tool" onClick={() => zoom(1.2)} aria-label="Zoom out" title="Zoom out">
            −
          </button>
          <button className="plot-tool reset" onClick={resetView} title="Reset the plot view">
            Reset
          </button>
        </div>
      </div>
      <svg
        ref={svgRef}
        className={`interactive-svg mode-${interactionMode} ${dragging ? "dragging" : ""}`}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={ariaLabel}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={finishPointer}
        onPointerCancel={(event) => finishPointer(event, true)}
        onDoubleClick={resetView}
      >
        <defs>
          <clipPath id={clipId}>
            <rect x={PADDING.left} y={PADDING.top} width={PLOT_RIGHT - PADDING.left} height={PLOT_BOTTOM - PADDING.top} />
          </clipPath>
        </defs>

        <rect
          className="plot-surface"
          x={PADDING.left}
          y={PADDING.top}
          width={PLOT_RIGHT - PADDING.left}
          height={PLOT_BOTTOM - PADDING.top}
        />
        <g className="grid-lines">
          {yTicks.map((value) => {
            const y = scaleY(value, currentView.yMin, currentView.yMax);
            const isZero = Math.abs(value) < yStep * 1e-8;
            return <line key={`y-${value}`} className={isZero ? "zero-grid-line" : ""} x1={PADDING.left} x2={PLOT_RIGHT} y1={y} y2={y} />;
          })}
          {xTicks.map((value) => {
            const x = scaleX(value, currentView);
            return <line key={`x-${value}`} x1={x} x2={x} y1={PADDING.top} y2={PLOT_BOTTOM} />;
          })}
        </g>

        <g clipPath={`url(#${clipId})`}>
          {markers?.start !== undefined && Number.isFinite(markers.start) && (
            <line className="marker-start" x1={scaleX(markers.start, currentView)} x2={scaleX(markers.start, currentView)} y1={PADDING.top} y2={PLOT_BOTTOM} />
          )}
          {markers?.end !== undefined && Number.isFinite(markers.end) && (
            <line className="marker-end" x1={scaleX(markers.end, currentView)} x2={scaleX(markers.end, currentView)} y1={PADDING.top} y2={PLOT_BOTTOM} />
          )}
          {plot.series.map((series, index) => {
            const secondaryAxis = Boolean(hasSecondaryAxis && index > 0);
            const color = colorForPlotSeries(series);
            const isFit = series.signal_id.includes("fit") || series.id.includes("fit");
            if (isMarkerSeries(series)) {
              return (
                <g key={series.id} className="trace-markers" fill={color} opacity={series.signal_id.includes("trough") ? 0.75 : 0.95}>
                  {markerPoints(series, currentView, secondaryAxis).map((point, pointIndex) => (
                    <circle key={`${series.id}-${pointIndex}`} className="trace-marker" cx={point.x} cy={point.y} r="3" />
                  ))}
                </g>
              );
            }
            return (
              <path
                key={series.id}
                className={`trace ${isFit ? "trace-dashed" : ""}`}
                d={toPath(series, currentView, secondaryAxis)}
                stroke={color}
                opacity={isFit ? 0.45 : index > 0 ? 0.65 : 1}
              />
            );
          })}
        </g>

        {visibleZoomSelection && (
          <rect
            className="zoom-selection"
            x={Math.min(visibleZoomSelection.start.x, visibleZoomSelection.end.x)}
            y={Math.min(visibleZoomSelection.start.y, visibleZoomSelection.end.y)}
            width={Math.abs(visibleZoomSelection.end.x - visibleZoomSelection.start.x)}
            height={Math.abs(visibleZoomSelection.end.y - visibleZoomSelection.start.y)}
          />
        )}

        <line className="axis-line" x1={PADDING.left} x2={PLOT_RIGHT} y1={PLOT_BOTTOM} y2={PLOT_BOTTOM} />
        <line className="axis-line" x1={PADDING.left} x2={PADDING.left} y1={PADDING.top} y2={PLOT_BOTTOM} />
        {hasSecondaryAxis && <line className="axis-line" x1={PLOT_RIGHT} x2={PLOT_RIGHT} y1={PADDING.top} y2={PLOT_BOTTOM} />}

        {xTicks.map((value) => (
          <g key={`x-axis-tick-${value}`}>
            <line className="axis-tick-mark" x1={scaleX(value, currentView)} x2={scaleX(value, currentView)} y1={PLOT_BOTTOM} y2={PLOT_BOTTOM + 5} />
            <text className="axis-tick" x={scaleX(value, currentView)} y={PLOT_BOTTOM + 24} textAnchor="middle">
              {formatTick(value, xStep)}
            </text>
          </g>
        ))}
        {yTicks.map((value) => (
          <g key={`y-axis-tick-${value}`}>
            <line className="axis-tick-mark" x1={PADDING.left - 5} x2={PADDING.left} y1={scaleY(value, currentView.yMin, currentView.yMax)} y2={scaleY(value, currentView.yMin, currentView.yMax)} />
            <text className="axis-tick" x={PADDING.left - 10} y={scaleY(value, currentView.yMin, currentView.yMax) + 4} textAnchor="end">
              {formatTick(value, yStep)}
            </text>
          </g>
        ))}
        {hasSecondaryAxis && secondaryYMin !== undefined && secondaryYMax !== undefined && (
          secondaryTicks.map((value) => (
            <g key={`secondary-y-axis-tick-${value}`}>
              <line className="axis-tick-mark" x1={PLOT_RIGHT} x2={PLOT_RIGHT + 5} y1={scaleY(value, secondaryYMin, secondaryYMax)} y2={scaleY(value, secondaryYMin, secondaryYMax)} />
              <text className="axis-tick secondary" x={PLOT_RIGHT + 10} y={scaleY(value, secondaryYMin, secondaryYMax) + 4} textAnchor="start">
                {formatTick(value, secondaryStep)}
              </text>
            </g>
          ))
        )}

        <text className="axis-title x-axis-title" x={(PADDING.left + PLOT_RIGHT) / 2} y={HEIGHT - 12} textAnchor="middle">
          {xAxisLabel}
        </text>
        <text className="axis-title y-axis-title" x={17} y={(PADDING.top + PLOT_BOTTOM) / 2} textAnchor="middle" transform={`rotate(-90 17 ${(PADDING.top + PLOT_BOTTOM) / 2})`}>
          {yAxisLabel}
        </text>
        {hasSecondaryAxis && secondaryYAxisLabel && (
          <text className="axis-title secondary-axis-title" x={WIDTH - 15} y={(PADDING.top + PLOT_BOTTOM) / 2} textAnchor="middle" transform={`rotate(90 ${WIDTH - 15} ${(PADDING.top + PLOT_BOTTOM) / 2})`}>
            {secondaryYAxisLabel}
          </text>
        )}
      </svg>
    </div>
  );
}
