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
        self._line_open = False
        self._disabled = False  # Codex P2 on PR #68: an I/O failure here is cosmetic-only
        if self.stream is None:
            # fd 2 closed at startup leaves sys.stderr as None: stay quiet, as
            # cli_colors.write_status does, instead of raising AttributeError on write.
            self.interactive = False
            self._disabled = True
            return
        try:
            # A stream already closed at construction time (Codex P2 round 2) can raise
            # here too, not only from write()/flush(); treated the same way: go quiet,
            # never raise out of a progress reporter's own setup.
            self.interactive = bool(getattr(self.stream, "isatty", lambda: False)())
        except (OSError, ValueError):
            self.interactive = False
            self._disabled = True

    def _safe_write(self, raw):
        """Write raw text, or quietly stop reporting forever if the stream itself is bad.

        A closed stderr or a downstream pipe that hung up must never escape into
        run_checks(): this is stderr feedback, not a gate, and the checks it decorates
        must keep running and get recorded whether or not anyone is still reading it.
        A stream already closed raises ValueError ("I/O operation on closed file"), not
        OSError, for both a real closed file and a closed io.StringIO/TextIOWrapper
        (Codex P2 on PR #68, round 2) — caught here alongside OSError, and nowhere
        wider: this except only wraps the two stream calls above.
        """
        if self._disabled:
            return False
        try:
            self.stream.write(raw)
            self.stream.flush()
            return True
        except (OSError, ValueError):
            self._disabled = True
            return False

    def _write(self, text):
        self._safe_write(self.style(text) + "\n")

    def _redraw(self, text):
        if self._safe_write("\r" + self.style(text).ljust(_REDRAW_WIDTH)):
            self._line_open = True

    def _clear_redraw(self):
        if self._line_open:
            self._safe_write("\r" + " " * _REDRAW_WIDTH + "\r")
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
