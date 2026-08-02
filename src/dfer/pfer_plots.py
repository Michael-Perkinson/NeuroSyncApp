from __future__ import annotations

from pathlib import Path

import numpy as np

from src import path_config

from .df_common import set_axis_labels
from .pfer_detection import PFerResult


def build_bokeh_plots(
    filename: str,
    t_vec: np.ndarray,
    signal_specs: list[dict[str, str]],
    traces: dict[str, np.ndarray],
    results: dict[str, PFerResult],
) -> None:
    from bokeh.layouts import column  # lazy
    from bokeh.plotting import figure, output_file, save  # lazy

    figures = []
    for spec in signal_specs:
        signal_name = spec["name"]
        color = spec["color"]
        trace = traces[signal_name]
        result = results[signal_name]

        peak_min = result["peak_min"]
        trough_min = result["trough_min"]
        peak_amp = result["peak_amp"]
        trough_amp = result["trough_amp"]
        sigs = result["sigs"]
        waveform_time = result["waveform_time"]
        mean_wave = result["mean_wave"]

        p1 = figure(width=1000, height=360,
                    title=f"{filename}   Detected peaks ({signal_name})")
        set_axis_labels(p1, "Time (min)", "dF/F")
        p1.line(t_vec, trace, line_color=color, line_width=0.6)
        if len(peak_min) > 0:
            p1.inverted_triangle(peak_min, peak_amp, color="red", size=7)
            p1.triangle(trough_min, trough_amp, color="black", size=7)
        figures.append(p1)

        p2 = figure(width=1000, height=320,
                    title=f"{filename}   Individual peak waveforms ({signal_name})")
        set_axis_labels(p2, "Time (sec)", "dF/F")
        if sigs and waveform_time is not None:
            wave_xs = [waveform_time.tolist() for _ in sigs]
            wave_ys = [sig.tolist() for sig in sigs]
            p2.multi_line(wave_xs, wave_ys, line_color=color, line_width=0.6)
        figures.append(p2)

        p3 = figure(width=1000, height=320,
                    title=f"{filename}   Average waveform ({signal_name})")
        set_axis_labels(p3, "Time (sec)", "dF/F")
        if waveform_time is not None and mean_wave is not None:
            p3.line(waveform_time, mean_wave, line_color=color, line_width=0.6)
        figures.append(p3)

    out_html = Path(path_config.processor) / "PFer_results.html"
    out_html.parent.mkdir(parents=True, exist_ok=True)
    output_file(str(out_html), title=filename)
    save(column(*figures))
