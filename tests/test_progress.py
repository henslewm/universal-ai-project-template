from __future__ import annotations

import importlib.util
import io
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("progress_under_test", ROOT / "scripts/progress.py")
progress = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(progress)


def noninteractive_stream():
    return io.StringIO()  # StringIO has no isatty(); StreamProgress must treat that as False.


def interactive_stream():
    stream = io.StringIO()
    stream.isatty = lambda: True
    return stream


class BrokenStream:
    """A stream whose write() always raises, as a closed stderr or a hung-up downstream
    pipe would (Codex P2 on PR #68): StreamProgress must treat this as cosmetic-only and
    never let it escape into the caller."""

    def isatty(self):
        return False

    def write(self, _text):
        raise OSError("write failed")

    def flush(self):
        pass


class FormatElapsedTests(unittest.TestCase):
    def test_seconds_under_a_minute(self):
        self.assertEqual(progress.format_elapsed(2.34), "2.3s")

    def test_minutes_and_seconds(self):
        self.assertEqual(progress.format_elapsed(62), "1m02s")
        self.assertEqual(progress.format_elapsed(125.9), "2m05s")

    def test_never_negative(self):
        self.assertEqual(progress.format_elapsed(-5), "0.0s")


class NullProgressTests(unittest.TestCase):
    def test_every_method_is_a_no_op(self):
        reporter = progress.NullProgress()
        reporter.start(3)
        with reporter.checking(1, 3, "VAL-1"):
            pass
        reporter.check_result(1, 3, "VAL-1", "PASSED", 0.1)
        reporter.finish(3, 3, True)


class StreamProgressBasicsTests(unittest.TestCase):
    def test_noninteractive_stream_is_detected(self):
        self.assertFalse(progress.StreamProgress(stream=noninteractive_stream()).interactive)

    def test_interactive_stream_is_detected(self):
        self.assertTrue(progress.StreamProgress(stream=interactive_stream()).interactive)

    def test_start_check_and_finish_lines(self):
        out = noninteractive_stream()
        reporter = progress.StreamProgress(stream=out)
        reporter.start(1)
        with reporter.checking(1, 1, "VAL-1"):
            pass
        reporter.check_result(1, 1, "VAL-1", "PASSED", 1.5)
        reporter.finish(1, 1, True)
        text = out.getvalue()
        self.assertIn("Running 1 check(s)...", text)
        self.assertIn("[1/1] VAL-1: running", text)
        self.assertIn("[1/1] VAL-1: PASSED (1.5s)", text)
        self.assertIn("run-checks: 1/1 passed, deterministic gate satisfied, in", text)

    def test_unsatisfied_finish_names_the_gate_as_not_satisfied(self):
        out = noninteractive_stream()
        reporter = progress.StreamProgress(stream=out)
        reporter.start(2)
        reporter.finish(1, 2, False)
        self.assertIn("run-checks: 1/2 passed, deterministic gate NOT satisfied", out.getvalue())

    def test_style_hook_wraps_every_written_line(self):
        # The identity hook by default (#26's color helper had not landed); a later one plugs
        # in here without any other change to this module.
        out = noninteractive_stream()
        reporter = progress.StreamProgress(stream=out, style=lambda text: f"<{text}>")
        reporter.start(1)
        self.assertIn("<Running 1 check(s)...>", out.getvalue())


class FastCheckTests(unittest.TestCase):
    """'Prompt acknowledgement, not an unconditional spinner for every operation lasting
    100 ms' (#27): a check well under TICKER_DELAY_SECONDS must never grow a second line."""

    def test_fast_check_gets_no_heartbeat_line_when_noninteractive(self):
        out = noninteractive_stream()
        reporter = progress.StreamProgress(stream=out)
        reporter.start(1)
        with reporter.checking(1, 1, "VAL-1"):
            time.sleep(0.05)  # Real TICKER_DELAY_SECONDS (2.0s) is nowhere near reached.
        self.assertEqual(out.getvalue().count("VAL-1"), 1)  # Only the initial "running" line.

    def test_fast_check_gets_no_ticker_redraw_when_interactive(self):
        out = interactive_stream()
        reporter = progress.StreamProgress(stream=out)
        reporter.start(1)
        with reporter.checking(1, 1, "VAL-1"):
            time.sleep(0.05)
        self.assertNotIn("\r", out.getvalue())


class SlowCheckTests(unittest.TestCase):
    """The delay/interval/cap are patched to millisecond scale so these stay fast and
    deterministic instead of asserting against the real multi-second thresholds."""

    def test_slow_noninteractive_check_gets_bounded_heartbeat_lines(self):
        out = noninteractive_stream()
        with mock.patch.object(progress, "TICKER_DELAY_SECONDS", 0.0), \
             mock.patch.object(progress, "HEARTBEAT_INTERVAL_SECONDS", 0.01), \
             mock.patch.object(progress, "HEARTBEAT_MAX_LINES", 2):
            reporter = progress.StreamProgress(stream=out)
            reporter.start(1)
            with reporter.checking(1, 1, "VAL-1"):
                time.sleep(0.1)  # ~10 intervals; the cap must still hold heartbeats at 2.
        occurrences = out.getvalue().count("VAL-1")
        self.assertGreaterEqual(occurrences, 2)  # The initial line plus at least one heartbeat.
        self.assertLessEqual(occurrences, 3)  # Initial line + HEARTBEAT_MAX_LINES(2), never more.
        self.assertNotIn("\r", out.getvalue())  # Non-interactive never redraws in place.

    def test_slow_interactive_check_redraws_in_place_without_growing_new_lines(self):
        out = interactive_stream()
        with mock.patch.object(progress, "TICKER_DELAY_SECONDS", 0.0), \
             mock.patch.object(progress, "TICKER_INTERVAL_SECONDS", 0.01):
            reporter = progress.StreamProgress(stream=out)
            reporter.start(1)
            with reporter.checking(1, 1, "VAL-1"):
                time.sleep(0.05)
        self.assertIn("\r", out.getvalue())


class CleanupTests(unittest.TestCase):
    """'Any ticker is optional and must clean up on success, refusal and Ctrl+C (130, per
    ADR-072)' (#27). KeyboardInterrupt is just another exception raised into the `with`
    block from the caller's perspective, so a plain exception exercises the same path."""

    def _run_with_ticker_then_raise(self, out):
        with mock.patch.object(progress, "TICKER_DELAY_SECONDS", 0.0), \
             mock.patch.object(progress, "TICKER_INTERVAL_SECONDS", 0.01):
            reporter = progress.StreamProgress(stream=out)
            reporter.start(1)
            with self.assertRaises(ValueError):
                with reporter.checking(1, 1, "VAL-1"):
                    time.sleep(0.05)  # Let the ticker redraw at least once first.
                    raise ValueError("simulated refusal or KeyboardInterrupt")
            return reporter

    def test_open_ticker_line_is_blanked_on_exception(self):
        out = interactive_stream()
        reporter = self._run_with_ticker_then_raise(out)
        self.assertFalse(reporter._line_open)
        self.assertTrue(out.getvalue().endswith("\r" + " " * progress._REDRAW_WIDTH + "\r"))

    def test_ticker_thread_stops_and_writes_nothing_more_after_exception(self):
        out = interactive_stream()
        self._run_with_ticker_then_raise(out)
        length_after_exit = len(out.getvalue())
        time.sleep(0.05)  # A still-alive ticker thread would have redrawn again by now.
        self.assertEqual(len(out.getvalue()), length_after_exit)


class BrokenStreamTests(unittest.TestCase):
    """Codex P2 on PR #68: a closed stderr or a downstream pipe that hangs up must not
    abort the checks this reporter only decorates. Every public method must swallow the
    write failure rather than let OSError/BrokenPipeError escape into the caller."""

    def test_start_does_not_raise_on_a_broken_stream(self):
        progress.StreamProgress(stream=BrokenStream()).start(1)

    def test_checking_does_not_raise_entering_or_exiting(self):
        reporter = progress.StreamProgress(stream=BrokenStream())
        with reporter.checking(1, 1, "VAL-1"):
            pass  # Neither the enter (an immediate "running" line) nor the exit may raise.

    def test_checking_still_propagates_the_caller_s_own_exception(self):
        # A broken progress stream must go quiet, not swallow an unrelated real failure.
        reporter = progress.StreamProgress(stream=BrokenStream())
        with self.assertRaises(ValueError):
            with reporter.checking(1, 1, "VAL-1"):
                raise ValueError("the check itself failed, not the progress stream")

    def test_check_result_and_finish_do_not_raise(self):
        reporter = progress.StreamProgress(stream=BrokenStream())
        reporter.start(1)  # finish() needs its own recorded start time.
        reporter.check_result(1, 1, "VAL-1", "PASSED", 1.0)
        reporter.finish(1, 1, True)

    def test_reporter_goes_quiet_after_the_first_failure_and_stays_quiet(self):
        writes = []

        class CountingBrokenStream(BrokenStream):
            def write(self, text):
                writes.append(text)
                raise OSError("write failed")

        reporter = progress.StreamProgress(stream=CountingBrokenStream())
        reporter.start(1)
        with reporter.checking(1, 1, "VAL-1"):
            pass
        reporter.check_result(1, 1, "VAL-1", "PASSED", 1.0)
        reporter.finish(1, 1, True)
        self.assertEqual(len(writes), 1)  # Only the first write is ever attempted.
        self.assertTrue(reporter._disabled)


class ClosedStreamTests(unittest.TestCase):
    """Codex P2 round 2 on PR #68: an actually closed stream raises ValueError ("I/O
    operation on closed file"), not OSError, for both a real closed file and a closed
    io.StringIO/TextIOWrapper. _safe_write must swallow this too."""

    def closed_stream(self):
        stream = io.StringIO()
        stream.close()
        return stream

    def test_write_on_a_closed_stringio_raises_value_error_not_os_error(self):
        # Documents the exact fresh evidence the finding cites, so this test would fail
        # loudly (not silently pass for the wrong reason) if StringIO's behavior ever changed.
        with self.assertRaises(ValueError):
            self.closed_stream().write("x")

    def test_start_does_not_raise_on_a_closed_stream(self):
        progress.StreamProgress(stream=self.closed_stream()).start(1)

    def test_checking_does_not_raise_on_a_closed_stream(self):
        reporter = progress.StreamProgress(stream=self.closed_stream())
        with reporter.checking(1, 1, "VAL-1"):
            pass

    def test_reporter_is_disabled_after_a_closed_stream_write(self):
        reporter = progress.StreamProgress(stream=self.closed_stream())
        reporter.start(1)
        self.assertTrue(reporter._disabled)


class AbsentStreamTests(unittest.TestCase):
    """With fd 2 closed at startup Python sets sys.stderr to None. The default reporter
    must go quiet rather than raise AttributeError out of run-checks, which turned a passing
    `acceptance.py run-checks … 2>&-` into exit 1 with nothing printed or recorded."""

    def test_a_default_reporter_with_no_stderr_is_quiet_and_never_raises(self):
        out = io.StringIO()
        with mock.patch.object(sys, "stderr", None), mock.patch.object(sys, "stdout", out):
            reporter = progress.StreamProgress()
            reporter.start(1)
            with reporter.checking(1, 1, "VAL-1"):
                pass
            reporter.check_result(1, 1, "VAL-1", "PASSED", 0.0)
            reporter.finish(1, 1, True)
        self.assertTrue(reporter._disabled)
        self.assertFalse(reporter.interactive)
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
