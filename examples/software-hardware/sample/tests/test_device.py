"""Contract and simulation checks for the device abstraction against the fake sensor."""
import unittest

from synth_bridge import codec
from synth_bridge.device import DeviceError, SensorDevice
from synth_bridge.fake_device import FakeSensorTransport
from synth_bridge.transport import LoopbackTransport


class SensorDeviceTests(unittest.TestCase):
    def test_reads_scripted_values_from_the_fake_sensor(self):
        device = SensorDevice(FakeSensorTransport([0, 0x1234, 0xFFFF]))
        self.assertEqual([device.read().value for _ in range(3)], [0, 0x1234, 0xFFFF])

    def test_silent_device_surfaces_as_no_reply(self):
        device = SensorDevice(FakeSensorTransport([]))
        with self.assertRaisesRegex(DeviceError, "no reply"):
            device.read()

    def test_corrupted_reply_is_reported_with_the_codec_error_code(self):
        device = SensorDevice(FakeSensorTransport([7, 8], corrupt_every=2))
        self.assertEqual(device.read().value, 7)
        with self.assertRaisesRegex(DeviceError, "BAD_CHECKSUM"):
            device.read()

    def test_loopback_echo_is_not_a_reading(self):
        # The loopback returns the request itself, which is a valid frame but not a reading:
        # a simulation rung that passes here proves sequencing, never sensor behavior.
        device = SensorDevice(LoopbackTransport())
        with self.assertRaisesRegex(DeviceError, "BAD_PAYLOAD"):
            device.read()

    def test_request_frame_sent_is_the_specified_read_command(self):
        transport = LoopbackTransport()
        try:
            SensorDevice(transport).read()
        except DeviceError:
            pass
        self.assertEqual(transport.sent, [codec.encode_read_request()])

    def test_transport_failures_on_send_and_receive_become_device_errors(self):
        # Independent review on PR #34: the contract promises read() returns a Reading or raises
        # DeviceError, so a port that raises (disconnect, short write) is translated at this
        # boundary with its cause chained rather than escaping as OSError or RuntimeError.
        class FailingTransport:
            def __init__(self, on_send=None, on_receive=None):
                self._on_send, self._on_receive = on_send, on_receive

            def send(self, data):
                if self._on_send:
                    raise self._on_send

            def receive(self, timeout_s):
                if self._on_receive:
                    raise self._on_receive
                return b""

        for transport, cause in ((FailingTransport(on_send=OSError("device disconnected")), OSError),
                                 (FailingTransport(on_receive=OSError("device disconnected")), OSError),
                                 (FailingTransport(on_send=RuntimeError("short write; port closed")), RuntimeError),
                                 (FailingTransport(on_receive=RuntimeError("adapter is closed")), RuntimeError)):
            with self.subTest(cause=cause.__name__, on="send" if transport._on_send else "receive"):
                with self.assertRaisesRegex(DeviceError, "transport failure: ") as raised:
                    SensorDevice(transport).read()
                self.assertIsInstance(raised.exception.__cause__, cause)

    def test_programming_errors_are_not_translated(self):
        # A negative timeout is the caller's mistake, not a wire failure; it stays a ValueError.
        with self.assertRaises(ValueError):
            SensorDevice(LoopbackTransport(), timeout_s=-1).read()


if __name__ == "__main__":
    unittest.main()
