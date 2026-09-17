"""Read raw fluorescence recordings stored in OFRS_RWD files."""

from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Any

import msgpack
import pandas as pd

_MAGIC = b"OFRS_RWD"
_BLOCK_EXT_CODE = 98
_CHANNEL_INDICES = (4, 5, 6)
_MAX_BLOCK_SIZE = 64 * 1024 * 1024


def _read_lz4_block(compressed: bytes, expected_length: int) -> bytes:
    """Decompress one raw LZ4 block and verify its declared size."""
    if expected_length <= 0 or expected_length > _MAX_BLOCK_SIZE:
        raise ValueError(f"Invalid OFRS decompressed block length: {expected_length}")

    source_index = 0
    output = bytearray()
    source_length = len(compressed)
    while source_index < source_length:
        token = compressed[source_index]
        source_index += 1
        literal_length = token >> 4
        if literal_length == 15:
            while True:
                if source_index >= source_length:
                    raise ValueError("Truncated OFRS LZ4 literal length")
                extension = compressed[source_index]
                source_index += 1
                literal_length += extension
                if extension != 255:
                    break
        literal_end = source_index + literal_length
        if literal_end > source_length:
            raise ValueError("Truncated OFRS LZ4 literal payload")
        output.extend(compressed[source_index:literal_end])
        source_index = literal_end
        if source_index == source_length:
            break
        if source_index + 2 > source_length:
            raise ValueError("Truncated OFRS LZ4 match offset")

        offset = compressed[source_index] | (compressed[source_index + 1] << 8)
        source_index += 2
        if offset == 0 or offset > len(output):
            raise ValueError("Invalid OFRS LZ4 match offset")
        match_length = token & 0x0F
        if match_length == 15:
            while True:
                if source_index >= source_length:
                    raise ValueError("Truncated OFRS LZ4 match length")
                extension = compressed[source_index]
                source_index += 1
                match_length += extension
                if extension != 255:
                    break
        for _ in range(match_length + 4):
            output.append(output[-offset])
        if len(output) > expected_length:
            raise ValueError("OFRS LZ4 block exceeds its declared length")

    if len(output) != expected_length:
        raise ValueError(
            "OFRS LZ4 block length does not match its declaration: "
            f"expected {expected_length}, got {len(output)}"
        )
    return bytes(output)


def _unpack_descriptor_lengths(descriptor: msgpack.ExtType) -> list[int]:
    """Decode the MessagePack integer lengths carried by ext type 98."""
    unpacker = msgpack.Unpacker(raw=False, strict_map_key=False)
    unpacker.feed(descriptor.data)
    lengths: list[int] = []
    try:
        while True:
            length = next(unpacker)
            if isinstance(length, bool) or not isinstance(length, int):
                raise TypeError("descriptor lengths must be integers")
            lengths.append(length)
    except StopIteration:
        pass
    except (
        msgpack.exceptions.UnpackException,
        TypeError,
        ValueError,
        OverflowError,
    ) as exc:
        raise ValueError("Invalid OFRS block length descriptor") from exc
    if not lengths or unpacker.tell() != len(descriptor.data):
        raise ValueError("Invalid OFRS block length descriptor")
    return lengths


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _decode_candidate(
    candidate: Any,
) -> tuple[list[list[float]], list[float]] | None:
    """Decode and validate one possible OFRS data frame."""
    if not isinstance(candidate, list) or not candidate:
        return None
    descriptor = candidate[0]
    if (
        not isinstance(descriptor, msgpack.ExtType)
        or descriptor.code != _BLOCK_EXT_CODE
    ):
        return None
    if len(candidate) not in (2, 3):
        raise ValueError("Invalid OFRS data block structure")
    payloads = candidate[1:]
    if not all(isinstance(payload, bytes) for payload in payloads):
        raise ValueError("Invalid OFRS data block payloads")

    expected_lengths = _unpack_descriptor_lengths(descriptor)
    if len(expected_lengths) != len(payloads):
        raise ValueError("OFRS descriptor and payload counts differ")
    decoded_stream = b"".join(
        _read_lz4_block(payload, expected_length)
        for payload, expected_length in zip(payloads, expected_lengths)
    )
    try:
        unpacked = msgpack.unpackb(decoded_stream, raw=False, strict_map_key=False)
    except (msgpack.exceptions.UnpackException, ValueError, TypeError) as exc:
        raise ValueError("OFRS data block contains invalid MessagePack") from exc

    if not isinstance(unpacked, list) or not unpacked:
        raise ValueError("OFRS data block has an invalid container")
    container = unpacked[0]
    if not isinstance(container, list) or not container:
        raise ValueError("OFRS data block has an invalid root")
    root = container[0]
    if not isinstance(root, list) or max(_CHANNEL_INDICES) >= len(root):
        raise ValueError("OFRS data block is missing required channels")

    channels: list[list[float]] = []
    timestamps: list[float] = []
    for channel_index in _CHANNEL_INDICES:
        records = root[channel_index]
        if not isinstance(records, list) or not records:
            raise ValueError("OFRS data block has invalid channel records")
        if len(channels) > 0 and len(records) != len(timestamps):
            raise ValueError("OFRS data block channel lengths differ")
        channel_values: list[float] = []
        for row_index, record in enumerate(records):
            if not isinstance(record, list) or len(record) < 3:
                raise ValueError("OFRS data block has an invalid record")
            value, shared_timestamp, channel_timestamp = record[:3]
            if not all(
                _is_finite_number(item)
                for item in (value, shared_timestamp, channel_timestamp)
            ):
                raise ValueError("OFRS data block contains a non-finite value")
            shared_timestamp_float = float(shared_timestamp)
            if channel_index == _CHANNEL_INDICES[0]:
                timestamps.append(shared_timestamp_float)
            elif shared_timestamp_float != timestamps[row_index]:
                raise ValueError("OFRS data block timestamps differ")
            channel_values.append(float(value))
        channels.append(channel_values)
    return channels, timestamps


def _unpack_framed_block(data: bytes, position: int) -> tuple[Any, int]:
    """Read one little-endian length-prefixed MessagePack frame."""
    if position + 4 > len(data):
        raise ValueError("Truncated OFRS serialized block length")
    frame_length = struct.unpack_from("<I", data, position)[0]
    frame_start = position + 4
    frame_end = frame_start + frame_length
    if frame_length <= 0 or frame_length > _MAX_BLOCK_SIZE:
        raise ValueError(f"Invalid OFRS serialized block length: {frame_length}")
    if frame_end > len(data):
        raise ValueError("Truncated OFRS serialized block")
    try:
        value = msgpack.unpackb(
            data[frame_start:frame_end], raw=False, strict_map_key=False
        )
    except (msgpack.exceptions.UnpackException, ValueError, TypeError) as exc:
        raise ValueError("Invalid OFRS MessagePack block") from exc
    return value, frame_end


def _iter_data_blocks(
    data: bytes,
) -> list[tuple[int, int, list[list[float]], list[float]]]:
    """Read framed OFRS blocks and retain only validated fluorescence data."""
    # The first 20 bytes after the magic are a fixed header.  Its final
    # uint32 gives the length of the initial metadata frame.
    if len(data) < 28:
        raise ValueError("Truncated OFRS header")
    metadata_length = struct.unpack_from("<I", data, 24)[0]
    metadata_start = 28
    metadata_end = metadata_start + metadata_length
    if metadata_length <= 0 or metadata_end > len(data):
        raise ValueError("Invalid OFRS metadata block length")
    try:
        msgpack.unpackb(
            data[metadata_start:metadata_end], raw=False, strict_map_key=False
        )
    except (msgpack.exceptions.UnpackException, ValueError, TypeError) as exc:
        raise ValueError("Invalid OFRS metadata block") from exc

    blocks: list[tuple[int, int, list[list[float]], list[float]]] = []
    position = metadata_end
    while position < len(data):
        candidate, frame_end = _unpack_framed_block(data, position)
        try:
            decoded = _decode_candidate(candidate)
        except ValueError as exc:
            raise ValueError(
                f"Invalid OFRS data block at offset {position + 4}"
            ) from exc
        if decoded is not None:
            channels, timestamps = decoded
            blocks.append((position + 4, frame_end, channels, timestamps))
        position = frame_end

    previous_timestamp: float | None = None
    for _, _, channels, timestamps in blocks:
        if not channels[0] or len(timestamps) != len(channels[0]):
            raise ValueError("Invalid OFRS data block channel lengths")
        for timestamp in timestamps:
            if previous_timestamp is not None and timestamp <= previous_timestamp:
                raise ValueError("OFRS shared timestamps are not strictly increasing")
            previous_timestamp = timestamp
    if not blocks:
        raise ValueError("No valid fluorescence data blocks found in OFRS file")
    return blocks


def read_ofrs(file_path: str | Path) -> pd.DataFrame:
    """Read an OFRS recording as the existing dual-photometry DataFrame."""
    path = Path(file_path).expanduser().resolve()
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"Could not read OFRS file: {path}") from exc
    if not data.startswith(_MAGIC):
        raise ValueError("Invalid OFRS file: missing OFRS_RWD magic header")

    blocks = _iter_data_blocks(data)
    timestamps: list[float] = []
    channels: list[list[float]] = [[], [], []]
    for _, _, block_channels, block_timestamps in blocks:
        timestamps.extend(block_timestamps)
        for index, values in enumerate(block_channels):
            channels[index].extend(values)
    if any(len(values) != len(timestamps) for values in channels):
        raise ValueError("OFRS channel and timestamp lengths do not match")
    return pd.DataFrame(
        {
            "TimeStamp": timestamps,
            "CH1-410": channels[0],
            "CH1-470": channels[1],
            "CH1-560": channels[2],
        }
    )


__all__ = ["read_ofrs"]
