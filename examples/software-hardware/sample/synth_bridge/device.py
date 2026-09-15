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
        """One reading, or a DeviceError: nothing the transport does on the wire leaves this
        boundary as anything else. Silence is `no reply`; a port that raised on send or receive
        (a disconnect, a short write, a closed adapter) is `transport failure` with the cause
        chained; a frame that decoded badly names the codec error code. A programming error
        (a negative timeout, a wrong type) is not a wire failure and is not translated."""
        try:
            self._transport.send(codec.encode_read_request())
            frame = self._transport.receive(self._timeout)
        except TransportTimeout as exc:
            raise DeviceError("no reply") from exc
        except (OSError, RuntimeError) as exc:
            raise DeviceError(f"transport failure: {exc}") from exc
        result = codec.decode_reading(frame)
        if isinstance(result, codec.FrameError):
            raise DeviceError(f"invalid reply: {result.code}")
        return result
