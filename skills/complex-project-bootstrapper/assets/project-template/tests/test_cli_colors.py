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

    def test_force_color_does_not_override_a_non_tty(self):
        self.assertFalse(cli_colors.supports_color(FakeStream(False), env={"FORCE_COLOR": "1"}))

    def test_stream_without_isatty_has_no_color(self):
        class NoIsAtty:
            pass

        self.assertFalse(cli_colors.supports_color(NoIsAtty(), env={}))

    def test_interactive_tty_with_no_color_unset_is_enabled_on_posix(self):
        if sys.platform == "win32":
            self.skipTest("posix-only assertion")
        self.assertTrue(cli_colors.supports_color(FakeStream(True), env={}))

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


if __name__ == "__main__":
    unittest.main()
