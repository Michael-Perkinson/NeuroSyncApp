from __future__ import annotations

import struct
from pathlib import Path

import msgpack
import pandas as pd
import pytest

from src.dfer import compute_options
from src.dfer.df_common import detect_photometry_file_type, load_dual_photometry
from src.file_management.ofrs_reader import _read_lz4_block, read_ofrs

_REAL_SAMPLE = Path(r"E:\CFD4 late preg test 260819\Fluorescence.ofrs")


def _literal_lz4(payload: bytes) -> bytes:
    length = len(payload)
    if length < 15:
        return bytes([length << 4]) + payload
    extension_length = length - 15
    extensions = bytes([255]) * (extension_length // 255)
    extensions += bytes([extension_length % 255])
    return b"\xf0" + extensions + payload


def _root(rows: list[tuple[float, float]]) -> list[list[object]]:
    root: list[object] = [None, [0] * 4, [0.0] * 4, [0.0] * 4, [], [], [], []]
    root[4] = [[value, timestamp, timestamp] for value, timestamp in rows]
    root[5] = [[value + 10, timestamp, timestamp + 33.333] for value, timestamp in rows]
    root[6] = [[value + 20, timestamp, timestamp + 66.667] for value, timestamp in rows]
    return [root]  # type: ignore[list-item]


def _data_frame(rows: list[tuple[float, float]], split: int | None = None) -> bytes:
    payload = msgpack.packb([_root(rows), []], use_bin_type=True)
    parts: list[bytes]
    if split is None:
        parts = [payload]
    else:
        parts = [payload[:split], payload[split:]]
    descriptor = b"".join(msgpack.packb(len(part)) for part in parts)
    packed = msgpack.packb(
        [msgpack.ExtType(98, descriptor), *[_literal_lz4(part) for part in parts]],
        use_bin_type=True,
    )
    return struct.pack("<I", len(packed)) + packed


def _synthetic_ofrs(path: Path) -> None:
    metadata = msgpack.packb(["metadata"], use_bin_type=True)
    header = b"OFRS_RWD" + (b"\x00" * 16) + struct.pack("<I", len(metadata))
    path.write_bytes(
        header
        + metadata
        + _data_frame([(1.25, 0.0), (2.5, 100.0)], split=17)
        + _data_frame([(3.75, 200.0)])
    )


def _full_length_synthetic_ofrs(path: Path) -> None:
    metadata = msgpack.packb(["metadata"], use_bin_type=True)
    header = b"OFRS_RWD" + (b"\x00" * 16) + struct.pack("<I", len(metadata))
    data = bytearray(header + metadata)
    row_index = 0
    for row_count in [51] * 790 + [50] * 36:
        rows = [
            (float(row_index + offset + 1), float((row_index + offset) * 100))
            for offset in range(row_count)
        ]
        payload = msgpack.packb([_root(rows), []], use_bin_type=True)
        data.extend(_data_frame(rows, split=len(payload) // 2))
        row_index += row_count

    final_rows = [
        (float(row_index + offset + 1), float((row_index + offset) * 100))
        for offset in range(28)
    ]
    data.extend(_data_frame(final_rows))
    path.write_bytes(data)


def test_read_ofrs_decodes_framed_normal_and_final_blocks(tmp_path):
    path = tmp_path / "Fluorescence.ofrs"
    _synthetic_ofrs(path)

    result = read_ofrs(path)

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["TimeStamp", "CH1-410", "CH1-470", "CH1-560"]
    assert result["TimeStamp"].tolist() == [0.0, 100.0, 200.0]
    assert result["CH1-410"].tolist() == [1.25, 2.5, 3.75]
    assert result["CH1-470"].tolist() == [11.25, 12.5, 13.75]
    assert result["CH1-560"].tolist() == [21.25, 22.5, 23.75]


def test_read_lz4_block_rejects_declared_length_mismatch():
    with pytest.raises(ValueError, match="does not match its declaration"):
        _read_lz4_block(b"\x00", 1)


def test_read_ofrs_rejects_invalid_magic(tmp_path):
    path = tmp_path / "invalid.ofrs"
    path.write_bytes(b"not-an-ofrs-file")

    with pytest.raises(ValueError, match="missing OFRS_RWD magic"):
        read_ofrs(path)


def test_read_ofrs_rejects_truncated_length_descriptor(tmp_path):
    metadata = msgpack.packb(["metadata"], use_bin_type=True)
    header = b"OFRS_RWD" + (b"\x00" * 16) + struct.pack("<I", len(metadata))
    packed = msgpack.packb(
        [msgpack.ExtType(98, b"\xcd"), b"\x00"],
        use_bin_type=True,
    )
    path = tmp_path / "truncated-descriptor.ofrs"
    path.write_bytes(header + metadata + struct.pack("<I", len(packed)) + packed)

    with pytest.raises(ValueError, match="Invalid OFRS data block"):
        read_ofrs(path)


def test_read_ofrs_rejects_malformed_block_after_valid_data(tmp_path):
    metadata = msgpack.packb(["metadata"], use_bin_type=True)
    header = b"OFRS_RWD" + (b"\x00" * 16) + struct.pack("<I", len(metadata))
    malformed = msgpack.packb(
        [msgpack.ExtType(98, msgpack.packb(1)), b"\x00", b"\x00"],
        use_bin_type=True,
    )
    path = tmp_path / "malformed-after-valid.ofrs"
    path.write_bytes(
        header
        + metadata
        + _data_frame([(1.0, 0.0)])
        + struct.pack("<I", len(malformed))
        + malformed
    )

    with pytest.raises(ValueError, match="Invalid OFRS data block"):
        read_ofrs(path)


@pytest.mark.parametrize("descriptor_value", [True, 1.0])
def test_read_ofrs_rejects_non_integer_descriptor_lengths(tmp_path, descriptor_value):
    metadata = msgpack.packb(["metadata"], use_bin_type=True)
    header = b"OFRS_RWD" + (b"\x00" * 16) + struct.pack("<I", len(metadata))
    packed = msgpack.packb(
        [
            msgpack.ExtType(98, msgpack.packb(descriptor_value)),
            b"\x00",
        ],
        use_bin_type=True,
    )
    path = tmp_path / "non-integer-descriptor.ofrs"
    path.write_bytes(header + metadata + struct.pack("<I", len(packed)) + packed)

    with pytest.raises(ValueError, match="Invalid OFRS data block"):
        read_ofrs(path)


def test_read_ofrs_rejects_truncated_frame(tmp_path):
    path = tmp_path / "truncated.ofrs"
    path.write_bytes(
        b"OFRS_RWD"
        + (b"\x00" * 16)
        + struct.pack("<I", 1)
        + b"\xc0"
        + struct.pack("<I", 10)
        + b"\xc0"
    )

    with pytest.raises(ValueError, match="Truncated OFRS serialized block"):
        read_ofrs(path)


def test_full_length_synthetic_recording_exercises_dual_dfer_route(tmp_path):
    path = tmp_path / "full-length.ofrs"
    _full_length_synthetic_ofrs(path)

    assert detect_photometry_file_type(path) == ("dual", 0)
    loaded = load_dual_photometry(path)
    assert loaded.shape == (42118, 4)
    assert loaded.iloc[-1].to_dict() == {
        "TimeStamp": pytest.approx(4211700.0),
        "CH1-410": pytest.approx(42118.0),
        "CH1-470": pytest.approx(42128.0),
        "CH1-560": pytest.approx(42138.0),
    }

    options = compute_options(path)
    assert options["file_type"] == "dual"
    assert len(options["t_min"]) == 42118
    assert len(options["p470"]["target_smooth"]) == 42118
    assert len(options["p560"]["target_smooth"]) == 42118


@pytest.mark.skipif(
    not _REAL_SAMPLE.exists(), reason="external OFRS sample is unavailable"
)
def test_read_real_ofrs_sample_without_exported_csvs():
    result = read_ofrs(_REAL_SAMPLE)

    assert result.shape == (42118, 4)
    assert list(result.columns) == ["TimeStamp", "CH1-410", "CH1-470", "CH1-560"]
    assert result["TimeStamp"].is_monotonic_increasing
    assert result.iloc[0].to_dict() == {
        "TimeStamp": pytest.approx(0.0),
        "CH1-410": pytest.approx(72.07348815819729),
        "CH1-470": pytest.approx(20.869211312945506),
        "CH1-560": pytest.approx(62.02874223959531),
    }
    assert result.iloc[-1].to_dict() == {
        "TimeStamp": pytest.approx(4211699.9997430025),
        "CH1-410": pytest.approx(71.68802023453668),
        "CH1-470": pytest.approx(18.187951253161646),
        "CH1-560": pytest.approx(29.99944814899977),
    }
