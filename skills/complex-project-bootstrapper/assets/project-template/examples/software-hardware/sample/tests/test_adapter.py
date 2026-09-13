"""Unit and simulation checks for the serial adapter with a fake port.

Everything here runs against an in-memory port. It establishes the adapter's host-side
rules and nothing about a physical SYNTH-SENSOR-1; that rung is attested, not executed.
"""
import unittest

from synth_bridge import codec
from synth_bridge.adapter import SerialAdapter
from synth_bridge.device import SensorDevice
from synth_bridge.transport import TransportTimeout


class FakePort:
    def __init__(self, replies=(), short_write=False):
        self.buffer = bytearray(b"".join(replies))
        self.written = []
        self.closed = False
        self.short_write = short_write

    def write(self, data):
        self.written.append(bytes(data))
        return len(data) - 1 if self.short_write else len(data)

    def read(self, size):
        chunk = bytes(self.buffer[:size])
        del self.buffer[:size]
        return chunk

    def close(self):
        self.closed = True


class SerialAdapterTests(unittest.TestCase):
    def opener(self, port):
        self.ports.append(port)
        return port

    def setUp(self):
        self.ports = []

    def adapter(self, port):
        adapter = SerialAdapter("SYNTH0", lambda name: self.opener(port))
        adapter.open()
        return adapter

    def test_open_is_idempotent_and_close_releases_the_port(self):
        port = FakePort()
        adapter = self.adapter(port)
        adapter.open()
        self.assertEqual(len(self.ports), 1)
        adapter.close()
        self.assertTrue(port.closed)
        self.assertFalse(adapter.is_open)

    def test_reads_one_whole_frame_by_its_declared_length(self):
        reply = codec.encode(bytes([0x12, 0x34]))
        adapter = self.adapter(FakePort([reply, b"\xff"]))
        self.assertEqual(adapter.receive(0.1), reply)

    def test_missing_header_is_a_timeout_not_a_crash(self):
        adapter = self.adapter(FakePort([b"\xa1"]))
        with self.assertRaises(TransportTimeout):
            adapter.receive(0.1)

    def test_oversized_frame_closes_the_port(self):
        port = FakePort([bytes([0xA1, 0xFF]) + bytes(256)])
        adapter = self.adapter(port)
        with self.assertRaisesRegex(RuntimeError, "oversized"):
            adapter.receive(0.1)
        self.assertTrue(port.closed)

    def test_short_write_closes_the_port(self):
        port = FakePort(short_write=True)
        adapter = self.adapter(port)
        with self.assertRaisesRegex(RuntimeError, "short write"):
            adapter.send(b"\x01\x02")
        self.assertTrue(port.closed)

    def test_closed_adapter_refuses_io(self):
        adapter = SerialAdapter("SYNTH0", lambda name: FakePort())
        with self.assertRaises(RuntimeError):
            adapter.send(b"\x01")
        with self.assertRaises(RuntimeError):
            adapter.receive(0.1)

    def test_device_reads_through_the_adapter_over_a_fake_port(self):
        port = FakePort([codec.encode(bytes([0x00, 0x2A]))])
        adapter = self.adapter(port)
        self.assertEqual(SensorDevice(adapter).read().value, 42)
        self.assertEqual(port.written, [codec.encode_read_request()])


if __name__ == "__main__":
    unittest.main()
