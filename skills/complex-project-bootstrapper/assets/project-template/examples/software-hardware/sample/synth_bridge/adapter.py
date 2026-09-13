"""Hardware adapter: binds the transport contract to a real port through an injected opener.

The opener is injected so every host-side rule (framing, timeouts, close on error) is testable
with a fake port. Whether the adapter works against a physical SYNTH-SENSOR-1 is a
hardware-in-loop observation an operator records; nothing in this module can establish it.
"""
from __future__ import annotations

from typing import Callable, Protocol

from .transport import TransportTimeout


class Port(Protocol):
    def write(self, data: bytes) -> int: ...

    def read(self, size: int) -> bytes: ...

    def close(self) -> None: ...


class SerialAdapter:
    def __init__(self, port_name: str, opener: Callable[[str], Port], frame_max: int = 19) -> None:
        self._port_name = port_name
        self._opener = opener
        self._frame_max = frame_max
        self._port: Port | None = None

    @property
    def is_open(self) -> bool:
        return self._port is not None

    def open(self) -> None:
        if self._port is None:
            self._port = self._opener(self._port_name)

    def close(self) -> None:
        if self._port is not None:
            self._port.close()
            self._port = None

    def send(self, data: bytes) -> None:
        if self._port is None:
            raise RuntimeError("adapter is closed")
        written = self._port.write(bytes(data))
        if written != len(data):
            self.close()
            raise RuntimeError("short write; port closed")

    def receive(self, timeout_s: float) -> bytes:
        if self._port is None:
            raise RuntimeError("adapter is closed")
        header = self._port.read(2)
        if len(header) < 2:
            raise TransportTimeout("no frame header")
        length = header[1]
        rest = self._port.read(length + 1)
        frame = header + rest
        if len(frame) > self._frame_max:
            self.close()
            raise RuntimeError("oversized frame; port closed")
        return frame
