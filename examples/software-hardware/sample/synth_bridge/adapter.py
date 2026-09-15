"""Hardware adapter: binds the transport contract to a real port through an injected opener.

The opener is injected so every host-side rule (framing, timeouts, close on error) is testable
with a fake port. Whether the adapter works against a physical SYNTH-SENSOR-1 is a
hardware-in-loop observation an operator records; nothing in this module can establish it.
"""
from __future__ import annotations

import time
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
        """One whole frame by its declared length, or TransportTimeout when it does not arrive in time.

        A port read may return fewer bytes than asked for (the SHB-04 port assumption: read(size)
        returns what has arrived), so the frame is assembled across reads until it is complete or
        the caller's timeout expires. Bytes already read stay consumed: a timeout mid-frame is a
        transport failure the caller sees, not a corrupted next frame.
        """
        if self._port is None:
            raise RuntimeError("adapter is closed")
        if timeout_s < 0:
            raise ValueError("timeout must be non-negative")
        deadline = time.monotonic() + timeout_s
        header = self._read_exactly(2, deadline, "no frame header")
        length = header[1]
        if 2 + length + 1 > self._frame_max:
            self.close()
            raise RuntimeError("oversized frame; port closed")
        return header + self._read_exactly(length + 1, deadline, "frame incomplete at timeout")

    def _read_exactly(self, size: int, deadline: float, why: str) -> bytes:
        buffer = b""
        while len(buffer) < size:
            chunk = self._port.read(size - len(buffer))
            if chunk:
                buffer += chunk
                continue
            if time.monotonic() >= deadline:
                raise TransportTimeout(why)
            time.sleep(0.001)
        return buffer
