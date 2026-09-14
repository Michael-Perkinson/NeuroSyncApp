from __future__ import annotations

import io
import json
import struct
import subprocess
import sys
import unittest
from pathlib import Path

SIDECAR_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIDECAR_ROOT))

from neurosync_sidecar import MAX_FRAME_BYTES  # noqa: E402
from neurosync_sidecar.protocol import FrameError, read_frame, write_frame  # noqa: E402
from neurosync_sidecar.server import serve  # noqa: E402


def request(request_id: str, method: str, params: dict | None = None) -> dict:
    return {"protocol_version": 1, "id": request_id, "method": method, "params": params or {}}


def framed(messages: list[dict]) -> io.BytesIO:
    stream = io.BytesIO()
    for message in messages:
        write_frame(stream, message)
    stream.seek(0)
    return stream


def responses(stream: io.BytesIO) -> list[dict]:
    stream.seek(0)
    values = []
    while (payload := read_frame(stream)) is not None:
        values.append(json.loads(payload))
    return values


class ChunkedReader(io.BytesIO):
    def read(self, size: int = -1) -> bytes:
        return super().read(min(size, 3))


class FramingTests(unittest.TestCase):
    def test_partial_reads_and_coalesced_frames(self) -> None:
        source = framed([{"value": 1}, {"value": 2}]).getvalue()
        reader = ChunkedReader(source)
        self.assertEqual(json.loads(read_frame(reader)), {"value": 1})
        self.assertEqual(json.loads(read_frame(reader)), {"value": 2})
        self.assertIsNone(read_frame(reader))

    def test_oversized_frame_is_rejected_before_payload_read(self) -> None:
        with self.assertRaisesRegex(FrameError, "frame_too_large"):
            read_frame(io.BytesIO(struct.pack(">I", MAX_FRAME_BYTES + 1)))


class ServerTests(unittest.TestCase):
    def test_oversized_frame_returns_typed_error_then_stops(self) -> None:
        output = io.BytesIO()
        exit_code = serve(
            io.BytesIO(struct.pack(">I", MAX_FRAME_BYTES + 1)),
            output,
            io.StringIO(),
        )
        error = responses(output)[0]["error"]
        self.assertEqual(exit_code, 2)
        self.assertEqual(error["code"], "frame_too_large")
        self.assertEqual(error["recovery"], "restart_sidecar")

    def test_negotiation_ping_plot_and_shutdown(self) -> None:
        incoming = framed([
            request("n", "protocol.negotiate", {"supported_versions": [1], "client": {"name": "test", "version": "1"}}),
            request("p", "sidecar.ping"),
            request("v", "sidecar.version"),
            request("s", "plot.sample", {"sample_count": 1_000_000, "viewport": {"start_index": 100, "end_index": 999_999}, "max_points": 10_000}),
            request("x", "sidecar.shutdown"),
        ])
        output = io.BytesIO()
        diagnostics = io.StringIO()
        self.assertEqual(serve(incoming, output, diagnostics), 0)
        result = responses(output)
        self.assertTrue(all(message["ok"] for message in result))
        plot = result[3]["result"]
        self.assertEqual(len(plot["series"]), 2)
        self.assertEqual(len(plot["series"][0]["y"]), 10_000)
        self.assertEqual(plot["series"][0]["sample_indices"][0], 100)
        self.assertEqual(plot["series"][0]["sample_indices"][-1], 999_999)
        self.assertLessEqual(sum(len(series["y"]) for series in plot["series"]), 50_000)
        self.assertEqual(output.getvalue().count(b"sidecar control loop"), 0)
        self.assertIn("sidecar control loop", diagnostics.getvalue())

    def test_malformed_json_has_typed_error_and_server_continues(self) -> None:
        bad = struct.pack(">I", 1) + b"{"
        following = framed([
            request("n", "protocol.negotiate", {"supported_versions": [1]}),
            request("x", "sidecar.shutdown"),
        ]).getvalue()
        output = io.BytesIO()
        self.assertEqual(serve(io.BytesIO(bad + following), output, io.StringIO()), 0)
        result = responses(output)
        self.assertEqual(result[0]["error"]["code"], "invalid_json")
        self.assertEqual(set(result[0]["error"]), {"code", "user_text", "recovery", "details"})
        self.assertTrue(result[1]["ok"])

    def test_unknown_method_does_not_expose_exception(self) -> None:
        incoming = framed([
            request("n", "protocol.negotiate", {"supported_versions": [1]}),
            request("bad", "not.real"),
            request("x", "sidecar.shutdown"),
        ])
        output = io.BytesIO()
        serve(incoming, output, io.StringIO())
        error = responses(output)[1]["error"]
        self.assertEqual(error["code"], "unknown_method")
        self.assertNotIn("Exception", error["user_text"])

    def test_real_subprocess_reserves_stdout_and_does_not_import_pyside6(self) -> None:
        process = subprocess.Popen(
            [sys.executable, "-m", "neurosync_sidecar"], cwd=SIDECAR_ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        assert process.stdin and process.stdout and process.stderr
        write_frame(process.stdin, request("n", "protocol.negotiate", {"supported_versions": [1]}))
        write_frame(process.stdin, request("x", "sidecar.shutdown"))
        first = json.loads(read_frame(process.stdout))
        second = json.loads(read_frame(process.stdout))
        process.stdin.close()
        self.assertEqual(process.wait(timeout=3), 0)
        self.assertTrue(first["ok"] and second["ok"])
        self.assertIn(b"control loop", process.stderr.read())
        self.assertNotIn("PySide6", sys.modules)
        process.stdout.close()
        process.stderr.close()


if __name__ == "__main__":
    unittest.main()
