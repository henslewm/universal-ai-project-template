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

    def available(self):
        """How many bytes are sitting in the buffer right now, without consuming any of them --
        a real port's `in_waiting`/`bytesAvailable()` equivalent."""
        return len(self.buffer)


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

    def test_any_port_failure_closes_the_port(self):
        # ADR-033/ADR-035: one guard owns close-on-failure for every port call. A read that
        # raises (a disconnect), before or after the header, closes the port; so does a write
        # that raises after a partial transmission; only a quiet timeout leaves it open.
        class FailingPort(FakePort):
            def __init__(self, replies=(), write_raises=False):
                super().__init__(replies)
                self.write_raises = write_raises

            def read(self, size, timeout_s):
                if self.buffer:
                    return super().read(size, timeout_s)
                raise OSError("device disconnected")

            def write(self, data):
                if self.write_raises:
                    raise OSError("write interrupted after 1 byte")
                return super().write(data)

        for name, port in (("read after header", FailingPort([WHOLE_FRAME[:2]])), ("read before header", FailingPort())):
            with self.subTest(failure=name):
                adapter = self.adapter(port)
                with self.assertRaisesRegex(OSError, "disconnected"):
                    adapter.receive(0.1)
                self.assertTrue(port.closed)
                self.assertFalse(adapter.is_open)
        port = FailingPort(write_raises=True)
        adapter = self.adapter(port)
        with self.assertRaisesRegex(OSError, "interrupted"):
            adapter.send(WHOLE_FRAME)
        self.assertTrue(port.closed)
        self.assertFalse(adapter.is_open)

    def test_a_driver_that_fails_to_close_still_leaves_the_adapter_closed(self):
        # ADR-036: closing is unconditional. The wire failure is what propagates; the failing
        # close is attached as its cause, and the adapter no longer holds the port.
        class StuckPort(FakePort):
            def read(self, size, timeout_s):
                raise OSError("device disconnected")

            def close(self):
                raise OSError("close failed")

        port = StuckPort()
        adapter = self.adapter(port)
        with self.assertRaisesRegex(OSError, "disconnected") as caught:
            adapter.receive(0.1)
        self.assertIsInstance(caught.exception.__cause__, OSError)
        self.assertIn("close failed", str(caught.exception.__cause__))
        self.assertFalse(adapter.is_open)
        with self.assertRaisesRegex(RuntimeError, "adapter is closed"):
            adapter.send(b"\x01")
        adapter = self.adapter(StuckPort())
        with self.assertRaisesRegex(OSError, "close failed"):
            adapter.close()  # an explicit close still reports the driver's failure ...
        self.assertFalse(adapter.is_open)  # ... and the adapter is closed regardless

    def test_bytes_arriving_after_the_deadline_are_not_a_frame_received_in_time(self):
        # Codex round 10 on PR #34: after an empty read that used up the time, the loop must not
        # ask the port again with a zero timeout and return late bytes as if they arrived in time.
        class LatePort(FakePort):
            def read(self, size, timeout_s):
                self.timeouts.append(timeout_s)
                if len(self.timeouts) == 1:
                    time.sleep(timeout_s + 0.02)  # the time is used up ...
                    self.buffer[:] = WHOLE_FRAME     # ... and then the frame arrives
                    return b""
                return super().read(size, timeout_s)

        port = LatePort()
        adapter = self.adapter(port)
        with self.assertRaisesRegex(TransportTimeout, "no frame header"):
            adapter.receive(0.03)
        self.assertEqual(len(port.timeouts), 1, "the port was not asked again after the deadline")
        self.assertFalse(port.closed, "nothing was consumed")
        self.assertEqual(adapter.receive(0.03), WHOLE_FRAME, "the next call, in its own time, may have it")

    def test_a_body_arriving_after_the_deadline_is_not_a_frame_received_in_time(self):
        # Codex round 11 on PR #34 (ADR-042): the one-poll allowance is the receive call's, not
        # each read's. The header returns just before the deadline, processing resumes after it,
        # and the body arrives late: the body read must not poll with a zero timeout and return
        # the frame late. The started frame closes the port (ADR-031).
        class LateBodyPort(FakePort):
            def read(self, size, timeout_s):
                self.timeouts.append(timeout_s)
                if len(self.timeouts) == 1:
                    time.sleep(timeout_s + 0.02)     # the header used up the time ...
                    self.buffer[:] = WHOLE_FRAME[2:]  # ... and the body arrives after the deadline
                    return WHOLE_FRAME[:2]
                return super().read(size, timeout_s)

        port = LateBodyPort()
        adapter = self.adapter(port)
        with self.assertRaisesRegex(TransportTimeout, "frame incomplete at timeout; port closed"):
            adapter.receive(0.03)
        self.assertEqual(len(port.timeouts), 1, "the body was not polled after the deadline")
        self.assertTrue(port.closed, "a started frame closes the port")
        self.assertFalse(adapter.is_open)

    def test_zero_timeout_returns_a_complete_frame_already_buffered(self):
        # Post-merge independent review (ADR-057): ADR-042 made the body's own first read
        # conditional on remaining time, but a zero-timeout receive() never waits at either
        # position -- an instantaneous poll cannot itself return data any later than the instant
        # it was called. A whole frame already sitting in the port must still come back complete,
        # not be split into a header-only read that then refuses to look at the buffered body.
        port = FakePort([WHOLE_FRAME])
        adapter = self.adapter(port)
        self.assertEqual(adapter.receive(0), WHOLE_FRAME)
        self.assertEqual(len(port.timeouts), 2, "header and body were each polled once")
        self.assertTrue(all(t == 0.0 for t in port.timeouts))
        self.assertTrue(adapter.is_open, "a complete frame in time leaves the port open")

    def test_zero_timeout_with_only_the_header_buffered_still_times_out(self):
        # The body's own unconditional first poll (above) must not become a second chance to
        # wait: at timeout_s=0 a body that is not yet buffered still closes the port as an
        # incomplete frame, exactly as a positive timeout does.
        port = FakePort([WHOLE_FRAME[:2]])
        adapter = self.adapter(port)
        with self.assertRaisesRegex(TransportTimeout, "frame incomplete at timeout; port closed"):
            adapter.receive(0)
        self.assertEqual(len(port.timeouts), 2, "header and the one body poll, no retry")
        self.assertTrue(port.closed)

    def test_zero_timeout_drains_an_already_buffered_frame_trickled_in_chunks(self):
        # PR #35 review (ADR-058): a port that can only hand back one byte per call, but whose
        # buffer already holds the whole frame before receive() is ever called, must still be
        # drained completely at timeout_s=0 -- the bytes were all there at the poll instant, so
        # chunking must not turn them into a spurious incomplete-frame timeout.
        port = TricklePort(WHOLE_FRAME)
        adapter = self.adapter(port)
        self.assertEqual(adapter.receive(0), WHOLE_FRAME)
        self.assertEqual(len(port.timeouts), 5, "one non-blocking read per byte of the frame")
        self.assertTrue(all(t == 0.0 for t in port.timeouts))
        self.assertTrue(adapter.is_open, "a complete frame in time leaves the port open")

    def test_zero_timeout_does_not_return_a_body_that_only_arrives_after_the_poll_instant(self):
        # PR #35 review (ADR-058): a header genuinely present when receive(0) polls the port must
        # not license reading a body that only shows up afterward, however fast the two reads
        # happen to be back to back -- no elapsed-wall-clock measurement can tell that apart from
        # the trickled-but-already-buffered case above, so this fake is driven by an explicit call
        # count, never real time, to stay deterministic.
        class LateBodyAfterPollPort(FakePort):
            def __init__(self):
                super().__init__([WHOLE_FRAME[:2]])

            def read(self, size, timeout_s):
                if len(self.timeouts) == 1:
                    # the header's own read has already happened; the body "arrives" only now --
                    # strictly after `available()` reported the poll-instant budget.
                    self.buffer[:] = self.buffer + WHOLE_FRAME[2:]
                return super().read(size, timeout_s)

        port = LateBodyAfterPollPort()
        adapter = self.adapter(port)
        with self.assertRaisesRegex(TransportTimeout, "frame incomplete at timeout; port closed"):
            adapter.receive(0)
        self.assertEqual(len(port.timeouts), 2, "the header, and one zero-sized body poll")
        self.assertTrue(port.closed, "a started frame closes the port")
        self.assertFalse(adapter.is_open)

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
