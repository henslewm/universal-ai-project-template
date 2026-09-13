"""Device abstraction over any Transport: the only place request/reply sequencing lives."""
from __future__ import annotations

from . import codec
from .transport import Transport, TransportTimeout


class DeviceError(Exception):
    pass


class SensorDevice:
    def __init__(self, transport: Transport, timeout_s: float = 0.5) -> None:
        self._transport = transport
        self._timeout = timeout_s

    def read(self) -> codec.Reading:
        self._transport.send(codec.encode_read_request())
        try:
            frame = self._transport.receive(self._timeout)
        except TransportTimeout as exc:
            raise DeviceError("no reply") from exc
        result = codec.decode_reading(frame)
        if isinstance(result, codec.FrameError):
            raise DeviceError(f"invalid reply: {result.code}")
        return result
