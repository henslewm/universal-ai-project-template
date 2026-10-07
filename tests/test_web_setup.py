"""web_setup.py: one zip and one clipboard copy per web client, read from each client's own list."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import web_setup

EXPECTED_COUNTS = {"chatgpt": 10, "claude": 10, "mistral": 12}


class WebSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "assets", "__pycache__", "*.zip"))

    def run_cli(self, *args):
        # An empty PATH leaves no clipboard tool, so the run is deterministic and touches no real clipboard.
        env = {**os.environ, "PYTHONUTF8": "1", "PATH": ""}
        return subprocess.run([sys.executable, str(ROOT / "scripts/web_setup.py"), *args, "--root", str(self.root)],
                              capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)

    def test_each_client_zip_holds_exactly_its_listed_files(self):
        for client, (_, list_name, _) in web_setup.CLIENTS.items():
            with self.subTest(client=client):
                names = web_setup.listed_files(ROOT / list_name)
                self.assertEqual(len(names), EXPECTED_COUNTS[client])
                result = self.run_cli("--client", client)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                with zipfile.ZipFile(self.root / f"web-setup-{client}.zip") as bundle:
                    self.assertEqual(sorted(bundle.namelist()), sorted(names))
                # No clipboard tool: the user is told which file to paste from.
                self.assertIn("Paste the contents of", result.stdout)

    def test_missing_listed_file_is_refused(self):
        (self.root / "SKILL_PLAN.md").unlink()
        result = self.run_cli("--client", "chatgpt")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Web setup refused: missing SKILL_PLAN.md", result.stdout)
        self.assertFalse((self.root / "web-setup-chatgpt.zip").exists())

    def test_paths_outside_the_project_are_refused(self):
        outside = Path(self.temp.name) / "secret.txt"
        outside.write_text("credential", encoding="utf-8")
        listing = self.root / ".chatgpt/PROJECT_FILES.md"
        original = listing.read_text(encoding="utf-8")
        for entry in (str(outside), "../secret.txt"):
            with self.subTest(entry=entry):
                listing.write_text(original + f"\n11. `{entry}`\n", encoding="utf-8")
                result = self.run_cli("--client", "chatgpt")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("outside the project", result.stdout)
                self.assertFalse((self.root / "web-setup-chatgpt.zip").exists())

    def test_symlinked_listed_file_is_refused(self):
        outside = Path(self.temp.name) / "secret.txt"
        outside.write_text("credential", encoding="utf-8")
        target = self.root / "SKILL_PLAN.md"
        target.unlink()
        try:
            target.symlink_to(outside)
        except OSError:
            self.skipTest("symlinks are not available on this system")
        result = self.run_cli("--client", "chatgpt")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("SKILL_PLAN.md", result.stdout)

    def test_symlinked_archive_destination_is_refused_and_target_untouched(self):
        outside = Path(self.temp.name) / "important.txt"
        outside.write_text("keep me", encoding="utf-8")
        try:
            (self.root / "web-setup-chatgpt.zip").symlink_to(outside)
        except OSError:
            self.skipTest("symlinks are not available on this system")
        result = self.run_cli("--client", "chatgpt")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("is a link", result.stdout)
        self.assertEqual(outside.read_text(encoding="utf-8"), "keep me")
        self.assertEqual(list(self.root.glob(".web-setup-*")), [])

    def test_rerun_replaces_the_archive(self):
        self.assertEqual(self.run_cli("--client", "claude").returncode, 0)
        result = self.run_cli("--client", "claude")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(list(self.root.glob(".web-setup-*")), [])

    def test_clipboard_copy_uses_the_platform_tool(self):
        with mock.patch.object(web_setup.shutil, "which", return_value="tool"), \
                mock.patch.object(web_setup.subprocess, "run") as run:
            run.return_value.returncode = 0
            self.assertTrue(web_setup.copy_to_clipboard("instructions"))
        sent = run.call_args.kwargs["input"]
        self.assertIn(sent, ("instructions".encode("utf-16"), b"instructions"))

    def test_no_clipboard_tool_reports_false(self):
        with mock.patch.object(web_setup.shutil, "which", return_value=None):
            self.assertFalse(web_setup.copy_to_clipboard("instructions"))


if __name__ == "__main__":
    unittest.main()
