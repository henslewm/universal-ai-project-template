"""Unit and simulation checks for the serial adapter with a fake port.

Everything here runs against an in-memory port. It establishes the adapter's host-side
rules and nothing about a physical SYNTH-SENSOR-1; that rung is attested, not executed.

The adapter is framing only: it consumes the transport interface and nothing else, so these
checks speak raw bytes. SYNTH-FRAME-1 layout: TAG(0xA1) LEN PAYLOAD[LEN] XOR-CHECKSUM over
TAG..PAYLOAD; the codec that produces such frames is another packet's interface.
"""
import unittest

from synth_bridge.adapter import SerialAdapter
from synth_bridge.transport import TransportTimeout

WHOLE_FRAME = b"\xa1\x02\x12\x34\x85"  # TAG, LEN=2, payload 0x12 0x34, checksum 0xA1^0x02^0x12^0x34


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
        adapter = self.adapter(FakePort([WHOLE_FRAME, b"\xff"]))
        self.assertEqual(adapter.receive(0.1), WHOLE_FRAME)

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

    def test_send_writes_the_bytes_it_was_given_unchanged(self):
        port = FakePort()
        adapter = self.adapter(port)
        adapter.send(WHOLE_FRAME)
        self.assertEqual(port.written, [WHOLE_FRAME])


if __name__ == "__main__":
    unittest.main()
