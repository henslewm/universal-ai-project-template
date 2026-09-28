"""Optional, dependency-free ANSI styling for human-facing CLI status lines.

Every CLI in this repository prints its machine-readable result as JSON on stdout;
that output is automation's contract and this module never touches it. Styling is
strictly a supplementary line on stderr: an explicit text label plus, only when the
terminal supports it, a color. The label is never omitted, so color is never the
only signal, and losing color (a plain terminal, a redirect, ``NO_COLOR``) loses
nothing but the color.

A CLI is not required to use this module. It exists for commands whose status is
easy to misread from JSON alone -- a controller's own ACCEPTED/REJECTED/PENDING
family of ledger states, a harness's PREPARED/HARNESS_UNAVAILABLE, an abandoned
attempt -- where a wrong glance (a "prepared" report looks green, a refusal looks
like the rest) has already made a real report harder to read at speed.
"""

from __future__ import annotations

import os
import sys

# https://no-color.org
_NO_COLOR_ENV = "NO_COLOR"

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"

# Every recognized status kind and the (ANSI color code, fixed text label) it maps to.
# The label is explicit and printed unconditionally; only the surrounding ANSI codes
# are conditional. Never map anything to SUCCESS unless the work is actually accepted:
# a prepared, dispatched, or merely schema-valid report belongs under PENDING.
SUCCESS = "success"
PENDING = "pending"
REFUSAL = "refusal"
ABANDONED = "abandoned"

_STYLES = {
    SUCCESS: ("32", "OK"),        # green
    PENDING: ("33", "PENDING"),   # yellow
    REFUSAL: ("31", "REFUSED"),   # red
    ABANDONED: ("35", "ABANDONED"),  # magenta
}


def _windows_vt_enabled(stream) -> bool:
    """Best-effort: turn on ANSI processing for a Windows console handle.

    Returns True if the stream can be expected to render ANSI escapes afterward
    (either it already could, or the mode was just enabled); False if not, in
    which case the caller must fall back to plain text rather than emit escapes
    a legacy console would print as literal garbage.
    """
    try:
        import ctypes

        handle = -12 if stream is sys.stderr else -11
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        std_handle = kernel32.GetStdHandle(handle)
        if std_handle == 0 or std_handle == -1:
            return False
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(std_handle, ctypes.byref(mode)):
            return False
        enable_virtual_terminal_processing = 0x0004
        if mode.value & enable_virtual_terminal_processing:
            return True
        new_mode = mode.value | enable_virtual_terminal_processing
        return bool(kernel32.SetConsoleMode(std_handle, new_mode))
    except (AttributeError, OSError, ValueError):
        return False


def supports_color(stream=None, *, env=None) -> bool:
    """True only when styling `stream` (default stderr) is safe and wanted.

    Honors NO_COLOR (any non-empty value disables, per no-color.org) ahead of
    everything else, and requires an interactive TTY regardless of NO_COLOR.
    TERM=dumb is treated as no ANSI support even on a reported TTY, matching
    every other terminal-capability check (this is the standard "cannot render
    escapes" signal, distinct from "not a TTY at all"). On Windows, a TTY only
    counts once VT processing is confirmed enabled; otherwise this reports no
    color support rather than emit escapes a legacy console cannot render.
    """
    stream = sys.stderr if stream is None else stream
    env = os.environ if env is None else env
    if env.get(_NO_COLOR_ENV):
        return False
    if env.get("TERM") == "dumb":
        return False
    try:
        is_tty = bool(stream.isatty())
    except (AttributeError, ValueError):
        is_tty = False
    if not is_tty:
        return False
    if sys.platform == "win32":
        return _windows_vt_enabled(stream)
    return True


def label(kind: str) -> str:
    """The fixed, uncolored text label for a status kind. Always safe to print."""
    if kind not in _STYLES:
        raise ValueError(f"Unrecognized CLI status kind: {kind!r}")
    return _STYLES[kind][1]


def style(kind: str, text: str, *, enabled: bool) -> str:
    """Wrap `text` in the ANSI color for `kind` when `enabled`, else return it as is."""
    if kind not in _STYLES:
        raise ValueError(f"Unrecognized CLI status kind: {kind!r}")
    if not enabled:
        return text
    code, _ = _STYLES[kind]
    return f"{_BOLD}\x1b[{code}m{text}{_RESET}"


def status_line(kind: str, message: str, *, enabled: bool | None = None, stream=None) -> str:
    """Build one status line: an always-present bracketed label plus the message.

    `[OK] <message>` in plain text, or the same text with `[OK]` colored when
    `enabled` (or, if not given, `supports_color(stream)`) allows it. The message
    itself is never colored or altered, only the label bracket around it.
    """
    stream = sys.stderr if stream is None else stream
    if enabled is None:
        enabled = supports_color(stream)
    tag = style(kind, f"[{label(kind)}]", enabled=enabled)
    return f"{tag} {message}"


def write_status(kind: str, message: str, *, stream=None, enabled: bool | None = None) -> None:
    """Print one status line to `stream` (default stderr), best-effort. Never writes to stdout.

    A closed stderr is None, and print(file=None) would write to stdout; an unwritable one
    must not change the command's exit code (ADR-072), so both are silently skipped.
    """
    stream = sys.stderr if stream is None else stream
    if stream is None:
        return
    try:
        print(status_line(kind, message, enabled=enabled, stream=stream), file=stream)
    except (OSError, ValueError):
        pass
