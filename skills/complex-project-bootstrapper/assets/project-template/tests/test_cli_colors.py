import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import cli_colors  # noqa: E402


class FakeStream(io.StringIO):
    def __init__(self, is_tty):
        super().__init__()
        self._is_tty = is_tty

    def isatty(self):
        return self._is_tty


class SupportsColorTests(unittest.TestCase):
    def test_no_color_env_disables_even_on_a_tty(self):
        self.assertFalse(cli_colors.supports_color(FakeStream(True), env={"NO_COLOR": "1"}))

    def test_no_color_any_nonempty_value_disables(self):
        self.assertFalse(cli_colors.supports_color(FakeStream(True), env={"NO_COLOR": "0"}))

    def test_redirected_non_tty_has_no_color(self):
        self.assertFalse(cli_colors.supports_color(FakeStream(False), env={}))

    def test_only_no_color_is_inspected_other_env_vars_never_force_a_non_tty(self):
        # supports_color reads NO_COLOR only; an unrelated env var (even one that
        # looks like it might mean "force color") has no effect on a non-TTY stream.
        self.assertFalse(cli_colors.supports_color(FakeStream(False), env={"FORCE_COLOR": "1"}))

    def test_stream_without_isatty_has_no_color(self):
        class NoIsAtty:
            pass

        self.assertFalse(cli_colors.supports_color(NoIsAtty(), env={}))

    def test_interactive_tty_with_no_color_unset_is_enabled_on_posix(self):
        if sys.platform == "win32":
            self.skipTest("posix-only assertion")
        self.assertTrue(cli_colors.supports_color(FakeStream(True), env={}))

    def test_term_dumb_disables_color_even_on_a_reported_tty(self):
        # Codex review round 5 of PR #67: a "dumb" terminal (e.g. some CI runners,
        # `emacs -nw`'s shell) can report isatty() True but cannot render ANSI.
        self.assertFalse(cli_colors.supports_color(FakeStream(True), env={"TERM": "dumb"}))

    def test_windows_tty_falls_back_to_plain_when_vt_mode_cannot_be_enabled(self):
        # On a non-Windows test host, `ctypes.windll` does not exist, so this
        # exercises the same AttributeError fallback a real legacy console takes.
        original_platform = sys.platform
        sys.platform = "win32"
        try:
            self.assertFalse(cli_colors.supports_color(FakeStream(True), env={}))
        finally:
            sys.platform = original_platform


class LabelAndStyleTests(unittest.TestCase):
    def test_every_kind_has_a_fixed_uppercase_label(self):
        for kind in (cli_colors.SUCCESS, cli_colors.PENDING, cli_colors.REFUSAL, cli_colors.ABANDONED):
            self.assertTrue(cli_colors.label(kind).isupper())

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            cli_colors.label("nonsense")
        with self.assertRaises(ValueError):
            cli_colors.style("nonsense", "text", enabled=True)

    def test_style_disabled_returns_plain_text_unchanged(self):
        self.assertEqual(cli_colors.style(cli_colors.SUCCESS, "hello", enabled=False), "hello")

    def test_style_enabled_wraps_in_ansi_and_preserves_the_text(self):
        styled = cli_colors.style(cli_colors.REFUSAL, "hello", enabled=True)
        self.assertNotEqual(styled, "hello")
        self.assertIn("hello", styled)
        self.assertTrue(styled.startswith("\x1b["))
        self.assertTrue(styled.endswith("\x1b[0m"))


class StatusLineTests(unittest.TestCase):
    def test_plain_line_always_carries_the_explicit_text_label(self):
        line = cli_colors.status_line(cli_colors.PENDING, "verify-report: valid, not accepted", enabled=False)
        self.assertEqual(line, "[PENDING] verify-report: valid, not accepted")

    def test_colored_line_still_contains_the_plain_label_and_message(self):
        line = cli_colors.status_line(cli_colors.ABANDONED, "attempt closed", enabled=True)
        self.assertIn("ABANDONED", line)
        self.assertIn("attempt closed", line)

    def test_write_status_goes_to_stderr_not_stdout(self):
        out = io.StringIO()
        err = FakeStream(False)
        old_stdout = sys.stdout
        sys.stdout = out
        try:
            cli_colors.write_status(cli_colors.SUCCESS, "done", stream=err)
        finally:
            sys.stdout = old_stdout
        self.assertEqual(out.getvalue(), "")
        self.assertIn("[OK] done", err.getvalue())

    def test_write_status_never_falls_through_to_stdout_when_stderr_is_absent(self):
        # With fd 2 closed at startup Python sets sys.stderr to None, and print(file=None)
        # writes to stdout -- which would corrupt the JSON result there.
        out = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, None
        try:
            cli_colors.write_status(cli_colors.SUCCESS, "done")
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
        self.assertEqual(out.getvalue(), "")

    def test_write_status_is_best_effort_on_an_unwritable_stream(self):
        # ADR-072: a stderr that cannot be written must never change a command's exit code.
        class Broken:
            def isatty(self):
                return False

            def write(self, _text):
                raise OSError("No space left on device")

            def flush(self):
                raise OSError("No space left on device")

        for error in (OSError, ValueError):
            with self.subTest(error=error.__name__):
                stream = Broken()
                stream.write = lambda _text, error=error: (_ for _ in ()).throw(error("closed"))
                cli_colors.write_status(cli_colors.REFUSAL, "refused", stream=stream)


if __name__ == "__main__":
    unittest.main()
