import { useCallback, useEffect, useMemo, useState } from "react";
import type { BackendAdapter } from "./backend";
import TracePlot from "./components/TracePlot";
import { colorForPlotSeries } from "./components/plotColors";
import {
  BackendError,
  type AnalysisWindow,
  type DferOptionsResult,
  type DferRunResult,
  type DualDisplay,
  type LogEntry,
  type PferRunResult,
  type RawFileContext,
  type SamplePlotResult,
} from "./protocol";
import "./app.css";

type ConnectionState = "connecting" | "ready" | "stopped" | "error";
type GraphTab = "raw" | "options" | "dfer" | "pfer";
type Theme = "light" | "dark" | "paper" | "ocean";

const THEMES: { key: Theme; label: string }[] = [
  { key: "light", label: "Light" },
  { key: "dark", label: "Dark" },
  { key: "paper", label: "Paper" },
  { key: "ocean", label: "Ocean" },
];

const TOOLS = [
  { code: "RA", label: "Analyse Raw Data", active: true },
  { code: "BH", label: "Align Photometry and Behaviour", active: false },
  { code: "TM", label: "Align Telemetry Data", active: false },
  { code: "CB", label: "Combine Data", active: false },
];

const DFER_OPTIONS = [
  { key: "1", label: "1 = standard baseline and noise correction" },
  { key: "2", label: "2 = alternative baseline fit" },
  { key: "3", label: "3 = no noise correction" },
  { key: "4", label: "4 = no noise correction and no activity baseline correction" },
];

function formatError(error: unknown): string {
  if (error instanceof BackendError) return `${error.envelope.code}: ${error.message}`;
  return "The operation did not complete.";
}

function formatDuration(seconds: number): string {
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

interface ResolvedWindow {
  start: number;
  end: number;
  duration: number;
  valid: boolean;
}

function resolveWindow(startText: string, endText: string, tMin: number, tMax: number): ResolvedWindow {
  const parse = (text: string, fallback: number, aliases: readonly string[]): number => {
    const value = text.trim().toLowerCase();
    if (!value || aliases.includes(value)) return fallback;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : Number.NaN;
  };
  const start = parse(startText, tMin, ["start", "min"]);
  const end = parse(endText, tMax, ["end", "max"]);
  if (!Number.isFinite(start) || !Number.isFinite(end)) {
    return { start: 0, end: 0, duration: 0, valid: false };
  }
  const clampedStart = Math.max(start, tMin);
  const clampedEnd = Math.min(end, tMax);
  if (clampedEnd <= clampedStart) {
    return { start: 0, end: 0, duration: 0, valid: false };
  }
  return { start: clampedStart, end: clampedEnd, duration: clampedEnd - clampedStart, valid: true };
}

function windowToRange(startText: string, endText: string): AnalysisWindow {
  const blank = (text: string, aliases: readonly string[]): number | null => {
    const value = text.trim().toLowerCase();
    if (!value || aliases.includes(value)) return null;
    const parsed = Number(text.trim());
    return Number.isFinite(parsed) ? parsed : null;
  };
  return {
    start_s: blank(startText, ["start", "min"]),
    end_s: blank(endText, ["end", "max"]),
  };
}

function basename(path: string): string {
  const trimmed = path.replace(/\\/g, "/");
  return trimmed.slice(trimmed.lastIndexOf("/") + 1);
}

function dirname(path: string): string {
  const trimmed = path.replace(/\\/g, "/");
  const slash = trimmed.lastIndexOf("/");
  return slash >= 0 ? trimmed.slice(0, slash) : ".";
}

export default function App({ backend }: { backend: BackendAdapter }) {
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [version, setVersion] = useState("");
  const [operation, setOperation] = useState("Connecting to the processing service…");
  const [filePath, setFilePath] = useState<string | null>(null);
  const [fileContext, setFileContext] = useState<RawFileContext | null>(null);

  const [startText, setStartText] = useState("");
  const [endText, setEndText] = useState("");
  const [appliedWindow, setAppliedWindow] = useState<{ start: number; end: number } | null>(null);

  const [options, setOptions] = useState<DferOptionsResult | null>(null);
  const [optionIndex, setOptionIndex] = useState(0);
  const [dualDisplay, setDualDisplay] = useState<DualDisplay>("both");
  const [optionPreview, setOptionPreview] = useState<SamplePlotResult | null>(null);

  const [selectedOption, setSelectedOption] = useState("1");
  const [dferResult, setDferResult] = useState<DferRunResult | null>(null);
  const [dferChannel, setDferChannel] = useState<"dfof" | "zscore">("dfof");
  const [show405, setShow405] = useState(true);

  const [pferCsv, setPferCsv] = useState<string | null>(null);
  const [pferBaselineStart, setPferBaselineStart] = useState("");
  const [pferBaselineEnd, setPferBaselineEnd] = useState("");
  const [prominence, setProminence] = useState(0.003);
  const [artifact, setArtifact] = useState(10);
  const [pferResult, setPferResult] = useState<PferRunResult | null>(null);

  const [activeTab, setActiveTab] = useState<GraphTab>("raw");
  const [busy, setBusy] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [plotSaveCounts, setPlotSaveCounts] = useState<Record<string, number>>({});
  const [theme, setTheme] = useState<Theme>("light");
  const [settingsTab, setSettingsTab] = useState<"dfer" | "pfer">("dfer");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const appendLog = useCallback((entry: LogEntry) => {
    setLogs((current) => [...current, entry].slice(-100));
    setOperation(entry.message);
  }, []);

  const start = useCallback(async () => {
    setConnection("connecting");
    setOperation("Connecting to the processing service…");
    try {
      const negotiated = await backend.start();
      const sidecarVersion = await backend.version();
      setVersion(`${negotiated.sidecar.name} ${sidecarVersion.sidecar_version} · app ${sidecarVersion.app_version}`);
      setConnection("ready");
      appendLog({ level: "info", message: "Ready. Select a raw photometry CSV to begin." });
    } catch (error) {
      setConnection("error");
      setOperation(formatError(error));
      appendLog({ level: "error", message: formatError(error) });
    }
  }, [appendLog, backend]);

  useEffect(() => {
    let dispose: (() => void) | undefined;
    let disposed = false;
    void (async () => {
      const callback = await backend.onLog(appendLog);
      if (disposed) {
        callback();
        return;
      }
      dispose = callback;
      await start();
    })();
    return () => {
      disposed = true;
      dispose?.();
    };
  }, [appendLog, backend, start]);

  const loadFile = useCallback(
    async (path: string) => {
      setBusy(true);
      try {
        const context = await backend.loadPhotometryFile(path);
        setFilePath(path);
        setFileContext(context);
        setOptions(null);
        setOptionIndex(0);
        setOptionPreview(null);
        setDferResult(null);
        setPferResult(null);
        setPferCsv(null);
        setShow405(true);
        setStartText("");
        setEndText("");
        setAppliedWindow({ start: 0, end: context.duration_s });
        setActiveTab("raw");
        setSettingsTab("dfer");
        const opts = await backend.generateOptions({ start_s: null, end_s: null });
        setOptions(opts);
        setDualDisplay("both");
        const preview = await backend.previewOption(0, opts.file_type === "dual" ? "both" : "both");
        setOptionPreview(preview);
        appendLog({
          level: "info",
          message: `Loaded ${context.signal_columns.join(", ")} from ${basename(path)}`,
        });
      } catch (error) {
        setOperation(formatError(error));
        appendLog({ level: "error", message: formatError(error) });
      } finally {
        setBusy(false);
      }
    },
    [appendLog, backend],
  );

  const selectFolder = async () => {
    try {
      const grant = await backend.selectGrant("folder");
      if (grant) appendLog({ level: "info", message: `Default data folder: ${grant.display_name}` });
    } catch (error) {
      setOperation(formatError(error));
    }
  };

  const selectFile = async () => {
    try {
      const grant = await backend.selectGrant("file");
      if (grant) await loadFile(grant.path || grant.display_name);
    } catch (error) {
      setOperation(formatError(error));
    }
  };

  const applyWindow = async () => {
    if (!fileContext) {
      setOperation("Please select a raw photometry CSV first.");
      return;
    }
    const resolved = resolveWindow(startText, endText, 0, fileContext.duration_s);
    if (!resolved.valid) {
      setOperation("Invalid analysis window.");
      return;
    }
    setAppliedWindow({ start: resolved.start, end: resolved.end });
    setBusy(true);
    try {
      const range = windowToRange(startText, endText);
      const opts = await backend.generateOptions(range);
      setOptions(opts);
      const preview = await backend.previewOption(optionIndex, opts.file_type === "dual" ? dualDisplay : "both");
      setOptionPreview(preview);
      appendLog({
        level: "info",
        message: `Analysis window ${resolved.start.toFixed(1)} to ${resolved.end.toFixed(1)} s applied.`,
      });
    } catch (error) {
      setOperation(formatError(error));
    } finally {
      setBusy(false);
    }
  };

  const changeOption = async (index: number) => {
    setOptionIndex(index);
    if (!options) return;
    setBusy(true);
    try {
      const display = options.file_type === "dual" ? dualDisplay : "both";
      const preview = await backend.previewOption(index, display);
      setOptionPreview(preview);
    } catch (error) {
      setOperation(formatError(error));
    } finally {
      setBusy(false);
    }
  };

  const changeDualDisplay = async (value: DualDisplay) => {
    setDualDisplay(value);
    setBusy(true);
    try {
      const preview = await backend.previewOption(optionIndex, value);
      setOptionPreview(preview);
    } catch (error) {
      setOperation(formatError(error));
    } finally {
      setBusy(false);
    }
  };

  const runDfer = async () => {
    if (!fileContext) {
      setOperation("Please select a raw photometry CSV first.");
      return;
    }
    setBusy(true);
    try {
      const result = await backend.runDfer({
        option: selectedOption,
        window: windowToRange(startText, endText),
      });
      setDferResult(result);
      setShow405(true);
      setDferChannel("dfof");
      setPferCsv(result.result_csv);
      setPferResult(null);
      setActiveTab("dfer");
      appendLog({ level: "info", message: `DFer analysis complete: ${result.result_csv}` });
    } catch (error) {
      setOperation(formatError(error));
      appendLog({ level: "error", message: formatError(error) });
    } finally {
      setBusy(false);
    }
  };

  const selectPferCsv = async () => {
    try {
      const grant = await backend.selectGrant("file");
      if (grant) {
        const path = grant.path || grant.display_name;
        setPferCsv(path);
        setPferResult(null);
        appendLog({ level: "info", message: `Selected DFer result: ${grant.display_name}` });
      }
    } catch (error) {
      setOperation(formatError(error));
    }
  };

  const runPfer = async () => {
    if (!pferCsv) {
      setOperation("Please select a DFer output CSV first.");
      return;
    }
    setBusy(true);
    try {
      const result = await backend.runPfer({
        csv_path: pferCsv,
        baseline_start: pferBaselineStart,
        baseline_end: pferBaselineEnd,
        prominence,
        artifact_threshold: artifact,
      });
      setPferResult(result);
      setActiveTab("pfer");
      appendLog({ level: "info", message: `Peak finding complete: ${result.stats_csv}` });
    } catch (error) {
      setOperation(formatError(error));
      appendLog({ level: "error", message: formatError(error) });
    } finally {
      setBusy(false);
    }
  };

  const savePlotImage = async (defaultStem: string) => {
    if (backend.mode === "tauri") {
      const kind = defaultStem === "pfer_result" ? "pfer" : "dfer";
      setBusy(true);
      try {
        const saved = await backend.savePlotImage(
          kind === "dfer"
            ? { kind, graph: dferChannel, show_405: show405 }
            : { kind },
        );
        appendLog({ level: "info", message: `INFO  [Plot] Saved image: ${saved.path}` });
        setOperation(`Plot image saved to ${saved.path}`);
      } catch (error) {
        setOperation(formatError(error));
        appendLog({ level: "error", message: formatError(error) });
      } finally {
        setBusy(false);
      }
      return;
    }

    const recording =
      fileContext ? basename(fileContext.file_path).replace(/\.csv$/i, "") : "recording";
    const count = (plotSaveCounts[defaultStem] ?? 0) + 1;
    setPlotSaveCounts((current) => ({ ...current, [defaultStem]: count }));
    const outputFolder = fileContext?.output_folder ?? "dfof_results";
    const plotsRoot = dirname(outputFolder);
    appendLog({
      level: "info",
      message: `INFO  [Plot] Saved image: ${plotsRoot}/plots/${recording}/${defaultStem}_plot_${count}.png`,
    });
    setOperation(`Plot image saved to plots/${recording}/.`);
  };

  const durationInfo = useMemo(() => {
    if (!fileContext) return null;
    return resolveWindow(startText, endText, 0, fileContext.duration_s);
  }, [fileContext, startText, endText]);

  const dferActivePlot = useMemo(() => {
    if (!dferResult) return null;
    const plot = dferChannel === "dfof" ? dferResult.plots.dfof : dferResult.plots.zscore;
    if (show405) return plot;
    return { ...plot, series: plot.series.filter((series) => series.signal_id !== "405nm") };
  }, [dferChannel, dferResult, show405]);

  const dferHas405 = Boolean(dferActivePlot?.series.some((series) => series.signal_id === "405nm"));

  const activePlot: SamplePlotResult | null =
    activeTab === "raw"
      ? (fileContext?.plot ?? null)
      : activeTab === "options"
        ? optionPreview
        : activeTab === "dfer"
          ? dferActivePlot
          : (pferResult?.plot ?? null);

  const graphTitle =
    activeTab === "raw"
      ? "Raw Data"
      : activeTab === "options"
        ? "DFer Options"
        : activeTab === "dfer"
          ? "DFer Results"
          : "PFer Results";

  const emptyText =
    activeTab === "raw"
      ? "Select a raw photometry CSV to draw the raw trace."
      : activeTab === "options"
        ? "Run the analysis window to generate DFer option previews."
        : activeTab === "dfer"
          ? "Run the final DFer analysis to see results."
          : "Run peak finding to see detected peaks.";

  const xAxisLabel =
    activeTab === "raw"
      ? `Time (${fileContext?.plot.x_axis.unit ?? "s"})`
      : "Time (min)";

  const dualAxis = activeTab === "raw" && fileContext?.file_type === "single";

  const yAxisLabel =
    activeTab === "raw" && dualAxis
      ? activePlot?.series[0]?.label ?? "465nm Signal"
      : activeTab === "raw" || activeTab === "options"
        ? "RFU"
        : activeTab === "dfer" && dferChannel === "zscore"
          ? "Z-score"
          : "dF/F";

  const secondaryYAxisLabel = dualAxis ? activePlot?.series[1]?.label ?? "405nm Signal" : undefined;

  const ariaLabel =
    activeTab === "raw"
      ? "Raw photometry trace"
      : activeTab === "options"
        ? "DFer option preview"
        : activeTab === "dfer"
          ? "DFer results"
          : "PFer peak results";

  const statusLabel =
    connection === "connecting"
      ? "Connecting…"
      : connection === "ready"
        ? backend.mode === "demo"
          ? "Demo data source ready"
          : "Sidecar ready"
        : connection === "stopped"
          ? "Stopped"
          : "Error";

  return (
    <div className="workstation">
      <aside className="workflow-rail" aria-label="Analysis tools">
        <div className="brand-mark" aria-label="NeuroSyncApp">N</div>
        <div className="rail-tools">
          {TOOLS.map((tool) => (
            <button
              className={`rail-tool ${tool.active ? "active" : ""}`}
              key={tool.code}
              title={tool.label}
              aria-label={tool.label}
              disabled={!tool.active}
            >
              {tool.code}
            </button>
          ))}
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <div className="eyebrow">NEUROSYNCAPP / RAW PHOTOMETRY</div>
            <h1>Analyse Raw Data</h1>
          </div>
          <div className="topbar-actions">
            <div className="theme-control">
              <label htmlFor="theme-select">Theme</label>
              <select
                id="theme-select"
                value={theme}
                onChange={(event) => setTheme(event.target.value as Theme)}
              >
                {THEMES.map((item) => (
                  <option key={item.key} value={item.key}>{item.label}</option>
                ))}
              </select>
            </div>
            <div
              className={`status-pill ${connection}`}
              title={version ? `${operation}\n${version}` : operation}
            >
              <span className="status-dot" />
              {statusLabel}
            </div>
          </div>
        </header>

        <section
          className="panels-top"
          aria-label="File and input selection"
        >
          <div className="panel" aria-label="Data Selection">
            <div className="panel-heading">
              <span className="panel-kicker">INPUT</span>
              <h2>Data Selection</h2>
            </div>
            <div className="panel-body">
              <div className="file-row">
                <button className="btn" onClick={() => void selectFolder()}>Select Folder</button>
                <button className="btn primary" onClick={() => void selectFile()} disabled={busy}>Raw Photometry File</button>
              </div>
              <div className={`path-field ${filePath ? "has-value" : ""}`}>
                {filePath ?? <span className="muted">Single-channel (405/465 nm) or dual-channel (470/560 nm) CSV</span>}
              </div>
            </div>
          </div>

          <div className="panel" aria-label="Analysis Window">
            <div className="panel-heading">
              <span className="panel-kicker">WINDOW</span>
              <h2>Analysis Window</h2>
            </div>
            <div className="panel-body window-row">
              <label className="field">
                Start (s)
                <input value={startText} onChange={(event) => setStartText(event.target.value)} placeholder="start" />
              </label>
              <label className="field">
                End (s)
                <input value={endText} onChange={(event) => setEndText(event.target.value)} placeholder="end" />
              </label>
              <div className="duration">
                <span>Duration</span>
                <strong className={durationInfo && !durationInfo.valid ? "invalid" : ""}>
                  {durationInfo ? (durationInfo.valid ? formatDuration(durationInfo.duration) : "Invalid") : "—"}
                </strong>
              </div>
              <button className="btn primary" onClick={() => void applyWindow()} disabled={busy || !fileContext}>Apply</button>
            </div>
          </div>
        </section>

        <section className="main-split">
          <div className="graph-card" aria-label="Plot and results">
            <div className="graph-tabs" role="tablist" aria-label="Plot tabs">
              <button
                role="tab"
                aria-selected={activeTab === "raw"}
                className={activeTab === "raw" ? "active" : ""}
                onClick={() => setActiveTab("raw")}
              >
                Raw Data
              </button>
              <button
                role="tab"
                aria-selected={activeTab === "options"}
                className={activeTab === "options" ? "active" : ""}
                disabled={!options}
                onClick={() => setActiveTab("options")}
              >
                DFer Options
              </button>
              <button
                role="tab"
                aria-selected={activeTab === "dfer"}
                className={activeTab === "dfer" ? "active" : ""}
                disabled={!dferResult}
                onClick={() => setActiveTab("dfer")}
              >
                DFer Results
              </button>
              <button
                role="tab"
                aria-selected={activeTab === "pfer"}
                className={activeTab === "pfer" ? "active" : ""}
                disabled={!pferResult}
                onClick={() => setActiveTab("pfer")}
              >
                PFer Results
              </button>
            </div>

            {activeTab === "options" && options ? (
              <div className="graph-bar">
                <label>Preview option</label>
                <select
                  value={optionIndex}
                  onChange={(event) => void changeOption(Number(event.target.value))}
                  aria-label="Preview option"
                >
                  {options.option_titles.map((title, index) => (
                    <option key={title} value={index}>{title}</option>
                  ))}
                </select>
                <label>Signals</label>
                {options.file_type === "dual" ? (
                  <select
                    value={dualDisplay}
                    onChange={(event) => void changeDualDisplay(event.target.value as DualDisplay)}
                    aria-label="Signals"
                  >
                    <option value="both">Both</option>
                    <option value="470">470nm</option>
                    <option value="560">560nm</option>
                  </select>
                ) : (
                  <select disabled value="465" aria-label="Signals">
                    <option value="465">{options.signal_label}</option>
                  </select>
                )}
              </div>
            ) : activeTab === "dfer" && dferResult ? (
              <div className="graph-bar">
                <label>Channel</label>
                <select
                  value={dferChannel}
                  onChange={(event) => setDferChannel(event.target.value as "dfof" | "zscore")}
                  aria-label="Channel"
                >
                  <option value="dfof">dF/F</option>
                  <option value="zscore">Z-score</option>
                </select>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={show405}
                    disabled={!dferHas405}
                    onChange={(event) => setShow405(event.target.checked)}
                  />
                  Show 405
                </label>
                <button className="btn" onClick={() => savePlotImage("dfer_result")}>Save image</button>
              </div>
            ) : activeTab === "pfer" && pferResult ? (
              <div className="graph-bar">
                <span className="spacer" />
                <button className="btn" onClick={() => savePlotImage("pfer_result")}>Save image</button>
              </div>
            ) : null}

            <div className="panel-heading graph-heading">
              <div>
                <span className="panel-kicker">{graphTitle}</span>
                <h2>{activePlot?.title ?? (fileContext ? "Raw photometry" : "No recording loaded")}</h2>
              </div>
              <div className="plot-legend">
                {activePlot?.series.map((series) => (
                  <span key={series.id}>
                    <i className="legend-swatch" style={{ background: colorForPlotSeries(series) }} />
                    {series.label}
                  </span>
                ))}
              </div>
            </div>

            <div className="trace-stage">
              {activePlot ? (
                <TracePlot
                  plot={activePlot}
                  xAxisLabel={xAxisLabel}
                  yAxisLabel={yAxisLabel}
                  secondaryYAxisLabel={secondaryYAxisLabel}
                  dualAxis={dualAxis}
                  markers={activeTab === "raw" ? appliedWindow ?? undefined : undefined}
                  emptyText={emptyText}
                  ariaLabel={ariaLabel}
                />
              ) : (
                <div className="plot-empty">{emptyText}</div>
              )}
            </div>

            <div className="plot-footer">
              <span>{activePlot?.sample_count.toLocaleString() ?? "—"} source samples</span>
              <span>{activePlot?.series[0]?.x.length.toLocaleString() ?? "—"} displayed / series</span>
              <span>sample indices retained</span>
              <span className="reduced">
                ● {activePlot?.display_reduced ? "DISPLAY REDUCED" : "FULL DISPLAY"}
              </span>
            </div>
          </div>

          <aside className="settings-side" aria-label="Signals and processing controls">
            <div className="panel" aria-label="Signals and file context">
              <div className="panel-heading">
                <span className="panel-kicker">SIGNALS</span>
                <h2>Signals</h2>
              </div>
              <div className="panel-body">
                <div className="context-row">
                  <label>File type</label>
                  <strong>
                    {fileContext
                      ? fileContext.file_type === "dual"
                        ? "Dual-channel (470/560 nm)"
                        : "Single-channel (405/465 nm)"
                      : "—"}
                  </strong>
                </div>
                <div className="context-row">
                  <label>Signal columns</label>
                  <strong>{fileContext ? fileContext.signal_columns.join(", ") : "—"}</strong>
                </div>
                <div className="context-row">
                  <label>Output folder</label>
                  <strong className="wrap">{fileContext?.output_folder ?? "—"}</strong>
                </div>
              </div>
            </div>

            <div className="processing-settings" aria-label="Processing settings">
              <div className="settings-tabs" role="tablist" aria-label="Processing settings tabs">
                <button
                  id="dfer-settings-tab"
                  className={`settings-tab ${settingsTab === "dfer" ? "active" : ""}`}
                  role="tab"
                  aria-label="DFer"
                  aria-selected={settingsTab === "dfer"}
                  aria-controls="dfer-settings-panel"
                  onClick={() => setSettingsTab("dfer")}
                >
                  <span className="settings-tab-kicker">DFER</span>
                  <span>DFer</span>
                </button>
                <button
                  id="pfer-settings-tab"
                  className={`settings-tab ${settingsTab === "pfer" ? "active" : ""}`}
                  role="tab"
                  aria-label="PFer"
                  aria-selected={settingsTab === "pfer"}
                  aria-controls="pfer-settings-panel"
                  onClick={() => setSettingsTab("pfer")}
                >
                  <span className="settings-tab-kicker">PFER</span>
                  <span>PFer</span>
                </button>
              </div>

              <section
                className="panel settings-tab-panel"
                id="dfer-settings-panel"
                role="tabpanel"
                aria-labelledby="dfer-settings-heading"
                aria-label="DFer Settings"
                hidden={settingsTab !== "dfer"}
              >
                <div className="panel-heading">
                  <span className="panel-kicker">DFER</span>
                  <h2 id="dfer-settings-heading">DFer Settings</h2>
                </div>
                <div className="panel-body settings-body">
                  <div className="settings-content">
                    <div className="section-title">Choose DFer option</div>
                    {DFER_OPTIONS.map((option) => (
                      <label className="radio" key={option.key}>
                        <input
                          type="radio"
                          name="dfer-option"
                          value={option.key}
                          checked={selectedOption === option.key}
                          onChange={() => setSelectedOption(option.key)}
                        />
                        <span>{option.label}</span>
                      </label>
                    ))}
                  </div>
                  <div className="settings-action">
                    <div className="section-title">Run final DFer analysis</div>
                    <button className="btn primary block" onClick={() => void runDfer()} disabled={busy || !fileContext}>
                      Run final analysis
                    </button>
                    <div className="result-label">
                      {dferResult ? `Saved: ${basename(dferResult.result_csv)}` : "No result yet."}
                    </div>
                  </div>
                </div>
              </section>

              <section
                className="panel settings-tab-panel"
                id="pfer-settings-panel"
                role="tabpanel"
                aria-labelledby="pfer-settings-heading"
                aria-label="PFer Settings"
                hidden={settingsTab !== "pfer"}
              >
                <div className="panel-heading">
                  <span className="panel-kicker">PFER</span>
                  <h2 id="pfer-settings-heading">PFer Settings</h2>
                </div>
                <div className="panel-body settings-body">
                  <div className="settings-content">
                    <button className="btn block" onClick={() => void selectPferCsv()}>Select DFer CSV…</button>
                    <div className="result-label">
                      {pferCsv ? basename(pferCsv) : "No DFer result selected"}
                    </div>
                    <div className="muted help">
                      Select an existing DFer result, or run DFer to use its output.
                    </div>
                    <div className="section-title">Baseline window for PFer normalization (seconds, optional)</div>
                    <div className="two-col">
                      <label className="field">
                        Start
                        <input
                          value={pferBaselineStart}
                          onChange={(event) => setPferBaselineStart(event.target.value)}
                          placeholder="blank = use full trace"
                        />
                      </label>
                      <label className="field">
                        End
                        <input
                          value={pferBaselineEnd}
                          onChange={(event) => setPferBaselineEnd(event.target.value)}
                          placeholder="blank = use full trace"
                        />
                      </label>
                    </div>
                    <div className="section-title">Peak-finding parameters</div>
                    <div className="muted help">
                      Troughs mark the lowest point between retained peaks. The first trough uses the recording
                      start to the first retained peak.
                    </div>
                    <label className="field">
                      Prominence
                      <input
                        type="number"
                        min={0.0001}
                        max={1}
                        step={0.001}
                        value={prominence}
                        onChange={(event) => {
                          const value = Number(event.target.value);
                          if (Number.isFinite(value)) setProminence(value);
                        }}
                      />
                    </label>
                    <label className="field">
                      Artifact threshold
                      <input
                        type="number"
                        min={1}
                        max={500}
                        step={1}
                        value={artifact}
                        onChange={(event) => {
                          const value = Number(event.target.value);
                          if (Number.isFinite(value)) setArtifact(value);
                        }}
                      />
                    </label>
                  </div>
                  <div className="settings-action">
                    <div className="section-title">Run PFer</div>
                    <button className="btn primary block" onClick={() => void runPfer()} disabled={busy || !pferCsv}>
                      Run peak finder
                    </button>
                  </div>
                </div>
              </section>
            </div>

            <div className="panel activity-log-panel" aria-label="Activity log">
              <div className="panel-heading">
                <span className="panel-kicker">ACTIVITY</span>
                <h2>Log</h2>
              </div>
              <div className="activity-log" role="log" aria-label="Activity log" aria-live="polite">
                {logs.length === 0 ? (
                  <div className="log-empty">Waiting for activity…</div>
                ) : (
                  logs.slice(-5).map((entry, index) => (
                    <div className={`log-entry ${entry.level}`} key={`${index}-${entry.message}`}>
                      {entry.message}
                    </div>
                  ))
                )}
              </div>
            </div>
          </aside>
        </section>
      </main>
    </div>
  );
}