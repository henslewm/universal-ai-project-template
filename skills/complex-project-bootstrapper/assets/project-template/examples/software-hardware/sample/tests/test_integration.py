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

    def read(self, size, timeout_s):
        chunk, self._pending = self._pending[:size], self._pending[size:]
        return chunk

    def available(self):
        return len(self._pending)

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

    def test_device_reads_through_the_adapter_over_a_fake_port(self):
        # Composition of the device and adapter interfaces: the adapter packet's own checks stay
        # at the transport boundary, so this crossing is exercised here.
        adapter = SerialAdapter("SYNTH0", lambda name: FakeSensorPort([42]))
        adapter.open()
        self.assertEqual(SensorDevice(adapter).read().value, 42)

    def test_port_failures_reach_the_workflow_as_device_errors_and_close_the_adapter(self):
        # Independent review on PR #34: a disconnect on write or read, or a short write, used to
        # escape the device as OSError or RuntimeError and abort the workflow's
        # `except DeviceError` path with an empty log. Through the real adapter each one now logs
        # an ERROR, the adapter is closed (ADR-035), and the next read reports the closed adapter.
        class BrokenPort(FakeSensorPort):
            def __init__(self, readings, fail):
                super().__init__(readings)
                self._fail = fail

            def write(self, data):
                if self._fail == "write-raises":
                    raise OSError("device disconnected")
                written = super().write(data)
                return written - 1 if self._fail == "short-write" else written

            def read(self, size, timeout_s):
                if self._fail == "read-raises":
                    raise OSError("device disconnected")
                return super().read(size, timeout_s)

        for fail, message in (("write-raises", "device disconnected"),
                              ("read-raises", "device disconnected"),
                              ("short-write", "short write; port closed")):
            with self.subTest(fail=fail):
                port = BrokenPort([5], fail)
                adapter = SerialAdapter("SYNTH0", lambda name: port)
                adapter.open()
                device = SensorDevice(adapter)
                log = []
                for _ in range(2):
                    try:
                        log.append(f"READING {device.read().value}")
                    except DeviceError as exc:
                        log.append(f"ERROR {str(exc).split(': ', 1)[-1]}")
                self.assertEqual(log, [f"ERROR {message}", "ERROR adapter is closed"])
                self.assertTrue(port.closed)
                self.assertFalse(adapter.is_open)


if __name__ == "__main__":
    unittest.main()
