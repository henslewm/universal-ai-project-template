"""A fake SYNTH-SENSOR-1: answers read requests with scripted readings.

This is a simulator. Passing against it says nothing about a physical sensor.
"""
from __future__ import annotations

from collections import deque

from . import codec
from .transport import TransportTimeout


class FakeSensorTransport:
    def __init__(self, readings: list[int], corrupt_every: int = 0) -> None:
        self._readings = deque(readings)
        self._replies: deque[bytes] = deque()
        self._corrupt_every = corrupt_every
        self._count = 0

    def send(self, data: bytes) -> None:
        payload, error = codec.decode(data)
        if error is not None or payload != bytes([codec.CMD_READ]):
            return  # A real device would stay silent on garbage; so does the fake.
        if not self._readings:
            return
        value = self._readings.popleft()
        frame = codec.encode(bytes([(value >> 8) & 0xFF, value & 0xFF]))
        self._count += 1
        if self._corrupt_every and self._count % self._corrupt_every == 0:
            frame = frame[:-1] + bytes([frame[-1] ^ 0xFF])
        self._replies.append(frame)

    def receive(self, timeout_s: float) -> bytes:
        if not self._replies:
            raise TransportTimeout("fake sensor produced no reply")
        return self._replies.popleft()
