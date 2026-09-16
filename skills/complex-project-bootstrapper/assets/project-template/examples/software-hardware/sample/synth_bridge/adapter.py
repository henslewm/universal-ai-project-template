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
    possibly fewer bytes than asked and possibly none; it never blocks past that time. `available`
    reports, without blocking or consuming a byte, how many bytes are buffered right now -- the
    one fact a zero-timeout `receive()` can use to tell bytes that already existed at its poll
    instant from bytes a real device hands over only afterward, since no two of its own read
    calls, however fast, can be assumed to have happened at the same instant."""

    def write(self, data: bytes) -> int: ...

    def read(self, size: int, timeout_s: float) -> bytes: ...

    def available(self) -> int: ...

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
        """Unconditional (ADR-036): the adapter forgets the port before asking the driver to close
        it, so a driver whose close() raises cannot leave the adapter open."""
        port, self._port = self._port, None
        if port is not None:
            port.close()

    @contextlib.contextmanager
    def _wire(self):
        """The one owner of close-on-failure (ADR-035): any exception leaving contact with the
        port — a raising read or write, a short write, an oversized or incomplete frame — closes
        the port before it propagates, so a desynchronized port is never reused."""
        try:
            yield
        except BaseException as failure:
            try:
                self.close()
            except Exception as cleanup:  # the wire failure is the finding; a failing close rides along
                raise failure from cleanup
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
        A zero-timeout call additionally samples `Port.available()` once, before touching the
        port, as a fixed byte budget it never exceeds (ADR-058): a frame already sitting in the
        port is assembled whole however it is chunked, and a byte that only arrives after that
        poll is never returned as part of it.
        """
        if self._port is None:
            raise RuntimeError("adapter is closed")
        if timeout_s < 0:
            raise ValueError("timeout must be non-negative")
        deadline = time.monotonic() + timeout_s
        polled = timeout_s == 0
        with self._wire():
            budget = self._port.available() if polled else 0
            if polled:
                header, budget = self._read_polled(2, budget)
            else:
                header = self._read_within(2, deadline, first_contact=True)
            if not header:
                quiet = True
            else:
                quiet = False
                if len(header) < 2:
                    raise TransportTimeout("frame incomplete at timeout; port closed")
                length = header[1]
                if 2 + length + 1 > self._frame_max:
                    raise RuntimeError("oversized frame; port closed")
                if polled:
                    body, budget = self._read_polled(length + 1, budget)
                else:
                    body = self._read_within(length + 1, deadline, first_contact=False)
                if len(body) < length + 1:
                    raise TransportTimeout("frame incomplete at timeout; port closed")
                return header + body
        if quiet:
            raise TransportTimeout("no frame header")

    def _read_polled(self, size: int, budget: int) -> tuple[bytes, int]:
        """Up to `size` bytes, drawn only from `budget` -- the count `Port.available()` reported
        once, before this receive() touched the port at all (ADR-058). `_read_within`'s wall-clock
        deadline degenerates at timeout_s=0 (deadline == start), so it cannot tell "the rest of
        what a trickling port already held at the poll instant" from "bytes a real device handed
        over only afterward" -- both are an ordinary non-empty read on a second call, however
        fast. `budget` is the one fact that can: sampled once, it is never exceeded, however many
        non-blocking calls a trickling port takes to hand it over, and an empty read spends it
        outright, so a port that stops short of its own reported count is never asked again for
        more.
        """
        buffer = b""
        while len(buffer) < size and budget > 0:
            chunk = self._port.read(min(size - len(buffer), budget), 0.0)
            if not chunk:
                budget = 0
                break
            buffer += chunk
            budget -= len(chunk)
        if len(buffer) < size:
            self._port.read(0, 0.0)  # a call still happens; it can ask for nothing this poll lacked
        return buffer, budget

    def _read_within(self, size: int, deadline: float, first_contact: bool) -> bytes:
        """Up to `size` bytes, each read bounded by the time left; stops short when time runs out.

        Only reached for a positive timeout (ADR-058); `timeout_s == 0` goes through
        `_read_polled` instead. `first_contact` exempts this call's own first port contact from
        the deadline (ADR-042): the header's always does, the body's never does, so once the
        deadline has passed, a further read at either position -- a retry at the same one, or the
        body's own first one -- is refused, so bytes that arrive after a real deadline are never
        returned as a frame received in time.
        """
        buffer = b""
        asked = not first_contact
        while len(buffer) < size:
            remaining = deadline - time.monotonic()
            if asked and remaining <= 0:
                break
            chunk = self._port.read(size - len(buffer), max(remaining, 0.0))
            asked = True
            if chunk:
                buffer += chunk
            elif remaining <= 0:
                break
        return buffer
