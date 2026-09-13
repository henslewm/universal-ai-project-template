"""Integration rung: the whole bridge end to end over the fake sensor.

This is the highest machine-runnable rung. A pass here is still simulated success; the
field-workflow rung above it is an operator observation on physical hardware.
"""
import unittest

from synth_bridge import codec
from synth_bridge.adapter import SerialAdapter
from synth_bridge.device import DeviceError, SensorDevice
from synth_bridge.fake_device import FakeSensorTransport
from synth_bridge.telemetry import summarize


class FakeSensorPort:
    """Presents the fake sensor as a byte port so the adapter path is exercised too."""

    def __init__(self, readings, corrupt_every=0):
        self._sensor = FakeSensorTransport(readings, corrupt_every)
        self._pending = b""
        self.closed = False

    def write(self, data):
        self._sensor.send(data)
        try:
            self._pending += self._sensor.receive(0)
        except Exception:
            pass
        return len(data)

    def read(self, size):
        chunk, self._pending = self._pending[:size], self._pending[size:]
        return chunk

    def close(self):
        self.closed = True


class BridgeIntegrationTests(unittest.TestCase):
    def test_representative_workflow_over_the_fake_sensor(self):
        adapter = SerialAdapter("SYNTH0", lambda name: FakeSensorPort([10, 20, 30, 40], corrupt_every=3))
        adapter.open()
        device = SensorDevice(adapter)
        log = []
        for _ in range(4):
            try:
                log.append(f"READING {device.read().value}")
            except DeviceError as exc:
                log.append(f"ERROR {str(exc).split(': ')[-1]}")
        adapter.close()
        self.assertEqual(log, ["READING 10", "READING 20", "ERROR BAD_CHECKSUM", "READING 40"])
        self.assertEqual(summarize(log), {"counts": {"ERROR": 1, "READING": 3},
                                          "reading_min": 10, "reading_max": 40})

    def test_request_on_the_wire_matches_the_specification(self):
        port = FakeSensorPort([1])
        adapter = SerialAdapter("SYNTH0", lambda name: port)
        adapter.open()
        adapter.send(codec.encode_read_request())
        self.assertEqual(adapter.receive(0.1), codec.encode(bytes([0, 1])))


if __name__ == "__main__":
    unittest.main()
