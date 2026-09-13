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


if __name__ == "__main__":
    unittest.main()
