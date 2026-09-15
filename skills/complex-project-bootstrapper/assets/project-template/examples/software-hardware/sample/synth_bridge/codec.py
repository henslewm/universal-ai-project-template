"""SYNTH-FRAME-1 protocol codec: pure functions, no I/O, no device.

Frame layout (fictional): TAG(0xA1) LEN PAYLOAD[LEN] XOR-CHECKSUM over TAG..PAYLOAD.
Request frames carry a one-byte command; reply frames carry a two-byte big-endian reading.
"""
from __future__ import annotations

from dataclasses import dataclass

TAG = 0xA1
CMD_READ = 0x01
MAX_PAYLOAD = 16


@dataclass(frozen=True)
class Reading:
    value: int  # 0..65535, synthetic units


@dataclass(frozen=True)
class FrameError:
    code: str  # SHORT, BAD_TAG, BAD_LENGTH, BAD_CHECKSUM, BAD_PAYLOAD


def checksum(data: bytes) -> int:
    total = 0
    for byte in data:
        total ^= byte
    return total


def encode(payload: bytes) -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload exceeds the fixture maximum")
    body = bytes([TAG, len(payload)]) + bytes(payload)
    return body + bytes([checksum(body)])


def encode_read_request() -> bytes:
    return encode(bytes([CMD_READ]))


def decode(frame: bytes) -> tuple[bytes | None, FrameError | None]:
    """Split a raw frame into its payload, or explain exactly why it is invalid."""
    if len(frame) < 3:
        return None, FrameError("SHORT")
    if frame[0] != TAG:
        return None, FrameError("BAD_TAG")
    length = frame[1]
    if length > MAX_PAYLOAD or len(frame) != length + 3:
        return None, FrameError("BAD_LENGTH")
    if checksum(frame[:-1]) != frame[-1]:
        return None, FrameError("BAD_CHECKSUM")
    return bytes(frame[2:-1]), None


def decode_reading(frame: bytes) -> Reading | FrameError:
    payload, error = decode(frame)
    if error is not None:
        return error
    if len(payload) != 2:
        return FrameError("BAD_PAYLOAD")
    return Reading((payload[0] << 8) | payload[1])
