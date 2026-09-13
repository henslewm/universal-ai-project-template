"""Transport contract and a loopback implementation. No serial port is opened here."""
from __future__ import annotations

from collections import deque
from typing import Protocol


class Transport(Protocol):
    def send(self, data: bytes) -> None: ...

    def receive(self, timeout_s: float) -> bytes: ...


class TransportTimeout(Exception):
    pass


class LoopbackTransport:
    """Echoes every sent frame back on receive; the simplest simulation rung."""

    def __init__(self) -> None:
        self._queue: deque[bytes] = deque()
        self.sent: list[bytes] = []

    def send(self, data: bytes) -> None:
        self.sent.append(bytes(data))
        self._queue.append(bytes(data))

    def receive(self, timeout_s: float) -> bytes:
        if timeout_s < 0:
            raise ValueError("timeout must be non-negative")
        if not self._queue:
            raise TransportTimeout("nothing to receive")
        return self._queue.popleft()
