from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from neurosync_sidecar.protocol import read_frame, write_frame

SIDECAR_DIR = Path(__file__).resolve().parents[1]


class RawWorkflowE2ETests(unittest.TestCase):
    process: subprocess.Popen[bytes] | None = None

    def tearDown(self) -> None:
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=10)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None:
                    stream.close()
        self.process = None

    def request(self, request_id: str, method: str, params: dict | None = None) -> dict:
        assert self.process is not None
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        write_frame(
            self.process.stdin,
            {
                "protocol_version": 1,
                "id": request_id,
                "method": method,
                "params": params or {},
            },
        )
        payload = read_frame(self.process.stdout)
        self.assertIsNotNone(payload)
        response = json.loads(payload)
        self.assertEqual(response["id"], request_id)
        return response

    def start(self) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "neurosync_sidecar"],
            cwd=SIDECAR_DIR,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        response = self.request("negotiate", "protocol.negotiate", {"supported_versions": [1]})
        self.assertTrue(response["ok"])
        self.assertIn("raw_photometry", response["result"]["capabilities"])

    def make_single_file(self, directory: Path) -> Path:
        time_s = np.arange(0, 180, 0.1)
        control = 1000 + 2 * np.sin(time_s / 30)
        signal = control + 100 * np.exp(-((time_s - 60) / 3) ** 2) + 100 * np.exp(-((time_s - 120) / 3) ** 2)
        path = directory / "recording.csv"
        pd.DataFrame({"#time(seconds)": time_s, "405nm": control, "465nm": signal}).to_csv(path, index=False)
        return path

    def make_dual_file(self, directory: Path) -> Path:
        time_s = np.arange(0, 180, 0.1)
        base = 1000 + 2 * np.sin(time_s / 30)
        path = directory / "dual" / "Fluorescence.csv"
        path.parent.mkdir()
        pd.DataFrame(
            {
                "TimeStamp": time_s * 1000,
                "CH1-410": base,
                "CH1-470": base + 100 * np.exp(-((time_s - 60) / 3) ** 2),
                "CH1-560": base + 60 * np.exp(-((time_s - 120) / 3) ** 2),
            }
        ).to_csv(path, index=False)
        return path

    def test_single_raw_file_runs_dfer_pfer_and_png_export_over_ipc(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw_path = self.make_single_file(Path(temporary))
            self.start()

            loaded = self.request("load", "raw.load_file", {"path": str(raw_path)})
            self.assertTrue(loaded["ok"])
            self.assertEqual(loaded["result"]["file_type"], "single")
            self.assertEqual(loaded["result"]["signal_columns"], ["405nm", "465nm"])

            options = self.request("options", "raw.generate_options", {"window": {"start_s": None, "end_s": None}})
            self.assertTrue(options["ok"])
            self.assertEqual(len(options["result"]["option_titles"]), 4)

            preview = self.request("preview", "raw.preview_option", {"index": 0, "dual_display": "both"})
            self.assertTrue(preview["ok"])
            self.assertEqual(len(preview["result"]["series"]), 2)

            dfer = self.request("dfer", "raw.run_dfer", {"option": "1", "window": {"start_s": None, "end_s": None}})
            self.assertTrue(dfer["ok"])
            dfer_csv = Path(dfer["result"]["result_csv"])
            self.assertTrue(dfer_csv.is_file())
            self.assertEqual(len(dfer["result"]["plots"]["dfof"]["series"]), 2)

            pfer = self.request(
                "pfer",
                "raw.run_pfer",
                {
                    "csv_path": str(dfer_csv),
                    "baseline_start": "",
                    "baseline_end": "",
                    "prominence": 0.003,
                    "artifact_threshold": 10,
                },
            )
            self.assertTrue(pfer["ok"])
            stats_paths = [Path(value) for value in pfer["result"]["stats_csv"].splitlines()]
            self.assertEqual(len(stats_paths), 1)
            self.assertTrue(stats_paths[0].is_file())

            saved_dfer = self.request("save-dfer", "raw.save_plot", {"kind": "dfer", "graph": "dfof", "show_405": True})
            self.assertTrue(saved_dfer["ok"])
            self.assertTrue(Path(saved_dfer["result"]["path"]).is_file())
            saved_pfer = self.request("save-pfer", "raw.save_plot", {"kind": "pfer"})
            self.assertTrue(saved_pfer["ok"])
            self.assertTrue(Path(saved_pfer["result"]["path"]).is_file())

            self.assertTrue(self.request("shutdown", "sidecar.shutdown")["ok"])
            assert self.process is not None
            self.assertEqual(self.process.wait(timeout=15), 0)

    def test_dual_raw_file_preserves_channels_through_dfer_and_pfer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw_path = self.make_dual_file(Path(temporary))
            self.start()

            loaded = self.request("load", "raw.load_file", {"path": str(raw_path)})
            self.assertTrue(loaded["ok"])
            self.assertEqual(loaded["result"]["file_type"], "dual")

            self.assertTrue(
                self.request("options", "raw.generate_options", {"window": {"start_s": None, "end_s": None}})["ok"]
            )
            preview = self.request("preview", "raw.preview_option", {"index": 1, "dual_display": "both"})
            self.assertTrue(preview["ok"])
            self.assertEqual(len(preview["result"]["series"]), 4)

            dfer = self.request("dfer", "raw.run_dfer", {"option": "2", "window": {"start_s": None, "end_s": None}})
            self.assertTrue(dfer["ok"])
            dfer_csv = Path(dfer["result"]["result_csv"])
            self.assertTrue(dfer_csv.is_file())
            self.assertEqual(len(dfer["result"]["plots"]["dfof"]["series"]), 2)

            pfer = self.request(
                "pfer",
                "raw.run_pfer",
                {"csv_path": str(dfer_csv), "baseline_start": "", "baseline_end": "", "prominence": 0.003, "artifact_threshold": 10},
            )
            self.assertTrue(pfer["ok"])
            stats_paths = [Path(value) for value in pfer["result"]["stats_csv"].splitlines()]
            self.assertEqual(len(stats_paths), 2)
            self.assertTrue(all(path.is_file() for path in stats_paths))
            self.assertEqual(len(pfer["result"]["plot"]["series"]), 6)

            self.assertTrue(self.request("shutdown", "sidecar.shutdown")["ok"])
            assert self.process is not None
            self.assertEqual(self.process.wait(timeout=15), 0)


if __name__ == "__main__":
    unittest.main()
