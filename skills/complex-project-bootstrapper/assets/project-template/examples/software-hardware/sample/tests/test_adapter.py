"""Unit and simulation checks for the serial adapter with a fake port.

Everything here runs against an in-memory port. It establishes the adapter's host-side
rules and nothing about a physical SYNTH-SENSOR-1; that rung is attested, not executed.

The adapter is framing only: it consumes the transport interface and nothing else, so these
checks speak raw bytes. SYNTH-FRAME-1 layout: TAG(0xA1) LEN PAYLOAD[LEN] XOR-CHECKSUM over
TAG..PAYLOAD; the codec that produces such frames is another packet's interface.
"""
import time
import unittest

from synth_bridge.adapter import SerialAdapter
from synth_bridge.transport import TransportTimeout

WHOLE_FRAME = b"\xa1\x02\x12\x34\x85"  # TAG, LEN=2, payload 0x12 0x34, checksum 0xA1^0x02^0x12^0x34


class FakePort:
    """An in-memory port that honors the read timeout: what is buffered returns at once, and an
    empty buffer waits out `timeout_s` before returning nothing, as a real port would."""

    def __init__(self, replies=(), short_write=False):
        self.buffer = bytearray(b"".join(replies))
        self.written = []
        self.closed = False
        self.short_write = short_write
        self.timeouts = []

    def write(self, data):
        self.written.append(bytes(data))
        return len(data) - 1 if self.short_write else len(data)

    def read(self, size, timeout_s):
        self.timeouts.append(timeout_s)
        if not self.buffer:
            time.sleep(timeout_s)
            return b""
        chunk = bytes(self.buffer[:size])
        del self.buffer[:size]
        return chunk

    def close(self):
        self.closed = True


class TricklePort(FakePort):
    """Returns at most one byte per read, as a slow serial line would."""

    def __init__(self, data):
        super().__init__([data])

    def read(self, size, timeout_s):
        return super().read(min(size, 1), timeout_s)


class BlockingPort(FakePort):
    """A port whose own blocking time is long; it must still honor the timeout it is handed."""

    def read(self, size, timeout_s):
        self.timeouts.append(timeout_s)
        time.sleep(min(1.0, timeout_s))
        return b""


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
        port = FakePort()
        adapter = self.adapter(port)
        with self.assertRaisesRegex(TransportTimeout, "no frame header"):
            adapter.receive(0.02)
        self.assertFalse(port.closed, "no byte of a frame was consumed")

    def test_frame_arriving_in_pieces_is_assembled_to_its_declared_length(self):
        # A serial port may hand back fewer bytes than asked for; the adapter keeps reading.
        adapter = self.adapter(TricklePort(WHOLE_FRAME + b"\xff"))
        self.assertEqual(adapter.receive(0.5), WHOLE_FRAME)

    def test_receive_honors_the_requested_timeout(self):
        # The header arrives, the body never does: the call returns at the caller's deadline,
        # and a longer deadline waits longer, so the argument governs the wait.
        adapter = self.adapter(FakePort([WHOLE_FRAME[:3]]))
        started = time.monotonic()
        with self.assertRaisesRegex(TransportTimeout, "incomplete"):
            adapter.receive(0.05)
        short = time.monotonic() - started
        adapter = self.adapter(FakePort([WHOLE_FRAME[:3]]))
        started = time.monotonic()
        with self.assertRaises(TransportTimeout):
            adapter.receive(0.2)
        self.assertGreater(time.monotonic() - started, short)
        with self.assertRaises(ValueError):
            self.adapter(FakePort()).receive(-1)

    def test_every_port_read_is_bounded_by_the_time_remaining(self):
        # ADR-031: the adapter cannot bound a read it does not control, so the deadline travels
        # into each read. A port that would block for a second returns at the caller's 50 ms.
        port = BlockingPort()
        adapter = self.adapter(port)
        started = time.monotonic()
        with self.assertRaises(TransportTimeout):
            adapter.receive(0.05)
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertTrue(all(0 <= t <= 0.051 for t in port.timeouts), port.timeouts)
        self.assertFalse(port.closed, "nothing was consumed, so the port stays open")

    def test_port_failure_after_a_started_frame_closes_the_port(self):
        # ADR-033: the closure has one owner, so a read that raises (a disconnect) after the
        # header is consumed closes the port too; before any byte is consumed it does not.
        class FailingPort(FakePort):
            def read(self, size, timeout_s):
                if self.buffer:
                    return super().read(size, timeout_s)
                raise OSError("device disconnected")

        port = FailingPort([WHOLE_FRAME[:2]])
        adapter = self.adapter(port)
        with self.assertRaisesRegex(OSError, "disconnected"):
            adapter.receive(0.1)
        self.assertTrue(port.closed)
        self.assertFalse(adapter.is_open)
        port = FailingPort()
        adapter = self.adapter(port)
        with self.assertRaises(OSError):
            adapter.receive(0.1)
        self.assertFalse(port.closed, "nothing was consumed")

    def test_partial_frame_at_timeout_closes_the_port(self):
        # ADR-031: a frame this call started but could not finish never lingers to be read as
        # the next frame's header; the port is closed before the timeout is raised.
        port = FakePort([WHOLE_FRAME[:3]])
        adapter = self.adapter(port)
        with self.assertRaisesRegex(TransportTimeout, "port closed"):
            adapter.receive(0.02)
        self.assertTrue(port.closed)
        self.assertFalse(adapter.is_open)
        port = FakePort([b"\xa1"])  # a lone header byte is a started frame too
        adapter = self.adapter(port)
        with self.assertRaisesRegex(TransportTimeout, "port closed"):
            adapter.receive(0.02)
        self.assertTrue(port.closed)

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
