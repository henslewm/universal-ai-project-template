"""Hardware adapter: binds the transport contract to a real port through an injected opener.

The opener is injected so every host-side rule (framing, timeouts, close on error) is testable
with a fake port. Whether the adapter works against a physical SYNTH-SENSOR-1 is a
hardware-in-loop observation an operator records; nothing in this module can establish it.
"""
from __future__ import annotations

import contextlib
import time
from typing import Callable, Protocol

from .transport import TransportTimeout


class Port(Protocol):
    """What the adapter needs from a serial port. `read` returns what arrived within `timeout_s`,
    possibly fewer bytes than asked and possibly none; it never blocks past that time."""

    def write(self, data: bytes) -> int: ...

    def read(self, size: int, timeout_s: float) -> bytes: ...

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

    @contextlib.contextmanager
    def _wire(self):
        """The one owner of close-on-failure (ADR-035): any exception leaving contact with the
        port — a raising read or write, a short write, an oversized or incomplete frame — closes
        the port before it propagates, so a desynchronized port is never reused."""
        try:
            yield
        except BaseException:
            self.close()
            raise

    def send(self, data: bytes) -> None:
        if self._port is None:
            raise RuntimeError("adapter is closed")
        with self._wire():
            written = self._port.write(bytes(data))
            if written != len(data):
                raise RuntimeError("short write; port closed")

    def receive(self, timeout_s: float) -> bytes:
        """One whole frame by its declared length within `timeout_s`, or the port is closed.

        The invariant (ADR-031, owned by `_wire` since ADR-035): every port read is handed the
        time remaining, so the call never outlasts the caller's deadline; and any failure on the
        wire — a frame started but not finished, an oversized declaration, a read that raises —
        closes the port before it propagates, so leftover bytes can never be read as the next
        frame's header. A timeout that consumed nothing is a quiet line and leaves the port open.
        """
        if self._port is None:
            raise RuntimeError("adapter is closed")
        if timeout_s < 0:
            raise ValueError("timeout must be non-negative")
        deadline = time.monotonic() + timeout_s
        with self._wire():
            header = self._read_within(2, deadline)
            if not header:
                quiet = True
            else:
                quiet = False
                if len(header) < 2:
                    raise TransportTimeout("frame incomplete at timeout; port closed")
                length = header[1]
                if 2 + length + 1 > self._frame_max:
                    raise RuntimeError("oversized frame; port closed")
                body = self._read_within(length + 1, deadline)
                if len(body) < length + 1:
                    raise TransportTimeout("frame incomplete at timeout; port closed")
                return header + body
        if quiet:
            raise TransportTimeout("no frame header")

    def _read_within(self, size: int, deadline: float) -> bytes:
        """Up to `size` bytes, each read bounded by the time left; stops short when time runs out."""
        buffer = b""
        while len(buffer) < size:
            remaining = deadline - time.monotonic()
            chunk = self._port.read(size - len(buffer), max(remaining, 0.0))
            if not chunk:
                if remaining <= 0:
                    break
                continue
            buffer += chunk
        return buffer
