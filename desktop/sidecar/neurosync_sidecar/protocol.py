from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from typing import BinaryIO, Any

from . import MAX_FRAME_BYTES, PROTOCOL_VERSION


@dataclass(frozen=True)
class FrameError(Exception):
    code: str
    user_text: str
    recovery: str = "restart_sidecar"


def read_exact(stream: BinaryIO, size: int) -> bytes | None:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = stream.read(size - len(chunks))
        if not chunk:
            if not chunks:
                return None
            raise FrameError("truncated_frame", "The protocol frame ended unexpectedly.")
        chunks.extend(chunk)
    return bytes(chunks)


def read_frame(stream: BinaryIO) -> bytes | None:
    header = read_exact(stream, 4)
    if header is None:
        return None
    (length,) = struct.unpack(">I", header)
    if length == 0:
        raise FrameError("empty_frame", "Protocol frames cannot be empty.")
    if length > MAX_FRAME_BYTES:
        raise FrameError("frame_too_large", "The protocol frame exceeds the 4 MiB limit.")
    payload = read_exact(stream, length)
    if payload is None:
        raise FrameError("truncated_frame", "The protocol frame ended unexpectedly.")
    return payload


def write_frame(stream: BinaryIO, message: dict[str, Any]) -> None:
    payload = json.dumps(message, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_FRAME_BYTES:
        raise FrameError("response_too_large", "The response exceeds the 4 MiB limit.")
    stream.write(struct.pack(">I", len(payload)))
    stream.write(payload)
    stream.flush()


def success(request_id: str | None, result: dict[str, Any]) -> dict[str, Any]:
    return {"protocol_version": PROTOCOL_VERSION, "id": request_id, "ok": True, "result": result}


def failure(
    request_id: str | None,
    code: str,
    user_text: str,
    recovery: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "id": request_id,
        "ok": False,
        "error": {"code": code, "user_text": user_text, "recovery": recovery, "details": details or {}},
    }
