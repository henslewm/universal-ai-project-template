import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "records_due.py"


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def touch_after(path, reference):
    t = Path(reference).stat().st_mtime + 5
    os.utime(path, (t, t))


class RecordsDueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        git(self.root, "config", "commit.gpgsign", "false")
        (self.root / "HANDOFF_CURRENT.md").write_text("h0\n")
        (self.root / "app.py").write_text("a\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "init")
        git(self.root, "checkout", "-q", "-b", "feature")

    def run_hook(self, stdin="{}", *flags, root=None):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root or self.root), *flags],
                              input=stdin, capture_output=True, text=True)

    def test_clean_branch_not_due(self):
        r = self.run_hook()
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_due_without_handoff_update(self):
        (self.root / "app.py").write_text("b\n")
        r = self.run_hook()
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertIn("app.py", out["reason"])
        self.assertIn("/records", out["reason"])

    def test_untracked_file_is_work(self):
        (self.root / "new.py").write_text("x\n")
        self.assertEqual(json.loads(self.run_hook().stdout)["decision"], "block")

    def test_clear_once_handoff_updated_after_work(self):
        (self.root / "app.py").write_text("b\n")
        (self.root / "HANDOFF_CURRENT.md").write_text("h1\n")
        touch_after(self.root / "HANDOFF_CURRENT.md", self.root / "app.py")
        self.assertEqual(self.run_hook().stdout, "")

    def test_due_again_when_work_modified_after_handoff(self):
        (self.root / "app.py").write_text("b\n")
        (self.root / "HANDOFF_CURRENT.md").write_text("h1\n")
        touch_after(self.root / "HANDOFF_CURRENT.md", self.root / "app.py")
        self.assertEqual(self.run_hook().stdout, "")
        (self.root / "app.py").write_text("c\n")
        touch_after(self.root / "app.py", self.root / "HANDOFF_CURRENT.md")
        self.assertEqual(json.loads(self.run_hook().stdout)["decision"], "block")

    def test_record_only_changes_not_due(self):
        (self.root / "CHANGELOG.md").write_text("c\n")
        self.assertEqual(self.run_hook().stdout, "")

    def test_stop_hook_active_is_silent(self):
        (self.root / "app.py").write_text("b\n")
        r = self.run_hook(json.dumps({"stop_hook_active": True}))
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_invalid_stdin_does_not_crash(self):
        (self.root / "app.py").write_text("b\n")
        for stdin in ("not json", "", "[1]"):
            r = self.run_hook(stdin)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)["decision"], "block")

    def test_outside_git_repo_is_silent(self):
        with tempfile.TemporaryDirectory() as plain:
            r = self.run_hook(root=plain)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_session_end_writes_stderr_only(self):
        (self.root / "app.py").write_text("b\n")
        r = self.run_hook("{}", "--session-end")
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertIn("records are behind the work on feature", r.stderr)
        self.assertIn("/records", r.stderr)


if __name__ == "__main__":
    unittest.main()
