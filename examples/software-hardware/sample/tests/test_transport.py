"""Unit and loopback simulation checks for the transport contract."""
import unittest

from synth_bridge.transport import LoopbackTransport, TransportTimeout


class LoopbackTransportTests(unittest.TestCase):
    def test_loopback_returns_frames_in_order(self):
        transport = LoopbackTransport()
        transport.send(b"\x01")
        transport.send(b"\x02")
        self.assertEqual(transport.receive(0.1), b"\x01")
        self.assertEqual(transport.receive(0.1), b"\x02")
        self.assertEqual(transport.sent, [b"\x01", b"\x02"])

    def test_empty_receive_times_out_instead_of_blocking(self):
        with self.assertRaises(TransportTimeout):
            LoopbackTransport().receive(0.0)

    def test_negative_timeout_is_refused(self):
        with self.assertRaises(ValueError):
            LoopbackTransport().receive(-1)

    def test_sent_bytes_are_copied_not_aliased(self):
        transport = LoopbackTransport()
        buffer = bytearray(b"\x05")
        transport.send(buffer)
        buffer[0] = 0x06
        self.assertEqual(transport.receive(0.1), b"\x05")


if __name__ == "__main__":
    unittest.main()
