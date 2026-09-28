#!/usr/bin/env python3
"""Bounded stderr progress reporting for genuinely long-running CLI operations (#27).

`run_checks` in acceptance.py is the intended caller: it runs each contract-declared
command as a real subprocess and can legitimately take a while per check. Nothing here
touches stdout, gates, timeouts, or process ownership; a caller with no reporter (the
default everywhere else in this codebase) sees no behavior change at all.

Deliberately colorless: issue #26 (a shared ANSI color helper) had not landed when this
was written. `StreamProgress` takes an optional `style` hook (defaults to the identity
function) so a later color helper can wrap the printed text without another redesign.
"""
from __future__ import annotations

import contextlib
import sys
import threading
import time

# A check running less than this never grows a ticker or heartbeat line: "prompt
# acknowledgement, not an unconditional spinner for every operation lasting 100 ms" (#27).
TICKER_DELAY_SECONDS = 2.0
# How often an interactive terminal's ticker line is repainted in place.
TICKER_INTERVAL_SECONDS = 1.0
# How often a non-interactive stream gets a new bounded heartbeat line instead.
HEARTBEAT_INTERVAL_SECONDS = 5.0
# Caps a single check's heartbeat lines however long it runs, so a slow check cannot flood
# a redirected log; the check's own configured timeout is the real bound on its duration.
HEARTBEAT_MAX_LINES = 12
_REDRAW_WIDTH = 100  # wide enough to blank any realistic single progress line


def format_elapsed(seconds):
    """A short human-readable duration: "12.3s" under a minute, else "1m02s"."""
    seconds = max(0.0, seconds)
    minutes, secs = divmod(int(seconds), 60)
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{seconds:.1f}s"


def identity(text):
    return text


class NullProgress:
    """No-op reporter: the default, so an unmodified caller sees no output at all."""

    def start(self, total):
        pass

    @contextlib.contextmanager
    def checking(self, index, total, validation_id):
        yield

    def check_result(self, index, total, validation_id, outcome, duration):
        pass

    def finish(self, passed, total, satisfied):
        pass


class StreamProgress:
    """A start message, bounded per-check updates with elapsed time, and a final outcome.

    A live ticker (carriage-return redraws) is used only on an interactive stream and only
    once a check has run past TICKER_DELAY_SECONDS; a fast check never grows one. A
    non-interactive stream (redirected to a file, CI log) instead gets bounded, slower,
    static heartbeat lines — never a redraw, since there is no terminal to redraw on.
    Cleanup (stopping the background thread and blanking any open ticker line) runs on
    every exit from `checking()`: normal completion, a raised refusal, or KeyboardInterrupt.
    """

    def __init__(self, stream=None, clock=time.monotonic, style=identity):
        self.stream = stream if stream is not None else sys.stderr
        self.clock = clock
        self.style = style
        self.interactive = bool(getattr(self.stream, "isatty", lambda: False)())
        self._line_open = False

    def _write(self, text):
        self.stream.write(self.style(text) + "\n")
        self.stream.flush()

    def _redraw(self, text):
        self.stream.write("\r" + self.style(text).ljust(_REDRAW_WIDTH))
        self.stream.flush()
        self._line_open = True

    def _clear_redraw(self):
        if self._line_open:
            self.stream.write("\r" + " " * _REDRAW_WIDTH + "\r")
            self.stream.flush()
            self._line_open = False

    def start(self, total):
        self._started = self.clock()
        self._write(f"Running {total} check(s)...")

    @contextlib.contextmanager
    def checking(self, index, total, validation_id):
        started = self.clock()
        self._write(f"[{index}/{total}] {validation_id}: running")
        stop = threading.Event()
        heartbeats = 0

        def tick():
            nonlocal heartbeats
            interval = TICKER_INTERVAL_SECONDS if self.interactive else HEARTBEAT_INTERVAL_SECONDS
            while not stop.wait(interval):
                elapsed = self.clock() - started
                if elapsed < TICKER_DELAY_SECONDS:
                    continue
                text = f"[{index}/{total}] {validation_id}: running ({format_elapsed(elapsed)})"
                if self.interactive:
                    self._redraw(text)
                    continue
                heartbeats += 1
                if heartbeats <= HEARTBEAT_MAX_LINES:
                    self._write(text)

        ticker = threading.Thread(target=tick, daemon=True)
        ticker.start()
        try:
            yield
        finally:
            stop.set()
            ticker.join(timeout=TICKER_INTERVAL_SECONDS * 2)
            self._clear_redraw()

    def check_result(self, index, total, validation_id, outcome, duration):
        self._write(f"[{index}/{total}] {validation_id}: {outcome} ({format_elapsed(duration)})")

    def finish(self, passed, total, satisfied):
        elapsed = self.clock() - self._started
        verdict = "deterministic gate satisfied" if satisfied else "deterministic gate NOT satisfied"
        self._write(f"run-checks: {passed}/{total} passed, {verdict}, in {format_elapsed(elapsed)}")
