"""Tk-specific helpers for embedding matplotlib figures."""

from __future__ import annotations

import tkinter as tk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


def destroy_embedded_figure(figure_canvas, toolbar) -> None:
    """Remove the current embedded figure widgets if they exist."""
    if figure_canvas is not None:
        figure_canvas.get_tk_widget().pack_forget()
        figure_canvas.get_tk_widget().destroy()
    if toolbar is not None:
        toolbar.destroy()


def create_styled_figure(figsize: tuple[float, float] = (6, 4)):
    """Create a matplotlib figure with the standard NeuroSync styling."""
    plt.close()
    fig, ax = plt.subplots(figsize=figsize)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return fig, ax


def embed_figure_in_tk(fig, graph_canvas):
    """Attach *fig* to a Tk container and return the canvas and toolbar."""
    fig_dpi = fig.dpi
    fig_width, fig_height = fig.get_size_inches()
    canvas_width = fig_width * fig_dpi
    canvas_height = fig_height * fig_dpi

    figure_canvas = FigureCanvasTkAgg(fig, master=graph_canvas)
    figure_canvas.get_tk_widget().config(width=canvas_width, height=canvas_height)
    figure_canvas.draw()
    figure_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    figure_canvas.get_tk_widget().configure(borderwidth=0, highlightthickness=0)

    toolbar = NavigationToolbar2Tk(figure_canvas, graph_canvas)
    toolbar.update()
    toolbar.config(background="snow")
    toolbar._message_label.config(background="snow")
    toolbar._message_label.config(foreground="black", font=("Arial", 10))
    toolbar.configure(background="snow", bd=0)
    toolbar._message_label.configure(background="snow", bd=0)
    toolbar.pack(side="top", fill="x")

    return figure_canvas, toolbar
