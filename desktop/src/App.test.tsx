import { createEvent, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { DemoBackend } from "./backend";

describe("Analyse Raw Data screen", () => {
  it("renders the file, window, settings, plot, and status regions", async () => {
    render(<App backend={new DemoBackend()} />);
    expect(screen.getByRole("heading", { name: "Analyse Raw Data" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Analysis tools" })).toBeInTheDocument();
    expect(screen.getByText("Data Selection")).toBeInTheDocument();
    expect(screen.getByText("Analysis Window")).toBeInTheDocument();
    expect(screen.getByRole("log", { name: "Activity log" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Studio" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Immersive" })).toBeNull();
    expect(screen.getByRole("tablist", { name: "Processing settings tabs" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "DFer" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "DFer Settings" })).toBeInTheDocument();
    expect(screen.queryByRole("tabpanel", { name: "PFer Settings" })).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: "PFer" }));
    expect(screen.getByRole("tab", { name: "PFer" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "PFer Settings" })).toBeInTheDocument();
    expect(await screen.findByText(/Demo data source ready/)).toBeInTheDocument();
  });

  it("does not expose Gate 0 diagnostic jargon", async () => {
    render(<App backend={new DemoBackend()} />);
    await screen.findByText(/Demo data source ready/);
    expect(screen.queryByText(/gate 0/i)).toBeNull();
    expect(screen.queryByText(/protocol inspector/i)).toBeNull();
    expect(screen.queryByText(/native grants/i)).toBeNull();
    expect(screen.queryByText(/diagnostic trace/i)).toBeNull();
  });

  it("loads a raw photometry CSV and unlocks the DFer options tab", async () => {
    render(<App backend={new DemoBackend()} />);
    await screen.findByText(/Demo data source ready/);
    fireEvent.click(screen.getByRole("button", { name: "Raw Photometry File" }));
    expect(await screen.findByRole("img", { name: "Raw photometry trace" })).toBeInTheDocument();
    expect(screen.getByText("Single-channel (405/465 nm)")).toBeInTheDocument();
    expect(screen.getByText("405nm, 465nm")).toBeInTheDocument();
    expect(screen.getAllByText("example_data/dfof_results").length).toBeGreaterThan(0);
    expect(screen.getByRole("tab", { name: "DFer Options" })).toBeEnabled();
    expect(screen.getByRole("tab", { name: "DFer Results" })).toBeDisabled();
  });

  it("renders numeric Matplotlib-style axes and plot controls", async () => {
    render(<App backend={new DemoBackend()} />);
    await screen.findByText(/Demo data source ready/);
    fireEvent.click(screen.getByRole("button", { name: "Raw Photometry File" }));
    const svg = await screen.findByRole("img", { name: "Raw photometry trace" });

    expect(svg.querySelectorAll(".axis-line")).toHaveLength(3);
    expect(svg.querySelectorAll(".axis-tick").length).toBeGreaterThan(6);
    expect(getComputedStyle(document.documentElement).overflow).toBe("hidden");
    expect(getComputedStyle(document.body).overflow).toBe("hidden");
    expect(svg.querySelectorAll(".axis-title")).toHaveLength(3);
    expect(svg.querySelector(".axis-title[transform]")?.getAttribute("transform")).toMatch(/^rotate\(-90 /);
    expect(screen.getByRole("button", { name: "Pan" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Zoom$/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Zoom in" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Zoom out" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset" })).toBeInTheDocument();
  });

  it("supports wheel zoom, rectangle zoom, and resetting the view", async () => {
    render(<App backend={new DemoBackend()} />);
    await screen.findByText(/Demo data source ready/);
    fireEvent.click(screen.getByRole("button", { name: "Raw Photometry File" }));
    const svg = await screen.findByRole("img", { name: "Raw photometry trace" });
    Object.defineProperty(svg, "getBoundingClientRect", {
      configurable: true,
      value: () => ({ left: 0, top: 0, width: 1000, height: 480 }),
    });
    const path = () => svg.querySelector("path")?.getAttribute("d");
    const initialPath = path();

    const wheel = createEvent.wheel(svg, { clientX: 500, clientY: 240, deltaY: -120 });
    const preventDefault = vi.spyOn(wheel, "preventDefault");
    fireEvent(svg, wheel);
    expect(preventDefault).toHaveBeenCalled();
    expect(path()).not.toBe(initialPath);

    const marginWheel = createEvent.wheel(svg, { clientX: 10, clientY: 10, deltaY: -120 });
    const marginPreventDefault = vi.spyOn(marginWheel, "preventDefault");
    fireEvent(svg, marginWheel);
    expect(marginPreventDefault).toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /^Zoom$/ }));
    fireEvent.pointerDown(svg, { button: 0, pointerId: 1, clientX: 200, clientY: 100 });
    fireEvent.pointerMove(svg, { pointerId: 1, clientX: 700, clientY: 350 });
    fireEvent.pointerUp(svg, { pointerId: 1, clientX: 700, clientY: 350 });
    expect(path()).not.toBe(initialPath);

    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(path()).toBe(initialPath);
  });

  it("updates the analysis window duration from aliases and numeric input", async () => {
    render(<App backend={new DemoBackend()} />);
    await screen.findByText(/Demo data source ready/);
    fireEvent.click(screen.getByRole("button", { name: "Raw Photometry File" }));
    await screen.findByRole("img", { name: "Raw photometry trace" });
    fireEvent.change(screen.getByPlaceholderText("start"), { target: { value: "10" } });
    fireEvent.change(screen.getByPlaceholderText("end"), { target: { value: "100" } });
    expect(screen.getByText("1m 30s")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  });

  it("runs the final DFer analysis and auto-selects its result for PFer", async () => {
    render(<App backend={new DemoBackend()} />);
    await screen.findByText(/Demo data source ready/);
    fireEvent.click(screen.getByRole("button", { name: "Raw Photometry File" }));
    await screen.findByRole("img", { name: "Raw photometry trace" });
    fireEvent.click(screen.getByRole("button", { name: "Run final analysis" }));
    expect(await screen.findByRole("img", { name: "DFer results" })).toBeInTheDocument();
    expect(screen.getByText(/Saved: recording_465_Data.csv/)).toBeInTheDocument();
    expect(screen.getByText("recording_465_Data.csv")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "PFer" }));
    expect(screen.getByRole("button", { name: "Run peak finder" })).toBeEnabled();
  });

  it("runs peak finding and unlocks the PFer results tab", async () => {
    render(<App backend={new DemoBackend()} />);
    await screen.findByText(/Demo data source ready/);
    fireEvent.click(screen.getByRole("button", { name: "Raw Photometry File" }));
    await screen.findByRole("img", { name: "Raw photometry trace" });
    fireEvent.click(screen.getByRole("button", { name: "Run final analysis" }));
    await screen.findByRole("img", { name: "DFer results" });
    fireEvent.click(screen.getByRole("tab", { name: "PFer" }));
    fireEvent.click(screen.getByRole("button", { name: "Run peak finder" }));
    expect(await screen.findByRole("img", { name: "PFer peak results" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "PFer Results" })).toBeEnabled();
  });
});