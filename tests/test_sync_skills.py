"""Payload synchronization: obsolete mirror files and worktree `.git` pointers (#49)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import sync_skills


class SyncSkillsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        # A worktree-shaped layout: `.git` is a pointer file, not a directory.
        (self.root / ".git").write_text("gitdir: /elsewhere/.git/worktrees/example\n", encoding="utf-8")
        (self.root / "scripts").mkdir()
        for name in ("bootstrap_project.py", "bootstrap_gate.py", "validate_bootstrap.py", "validate_project.py"):
            (self.root / "scripts" / name).write_text(f"# {name}\n", encoding="utf-8")
        self.skill = self.root / "skills/complex-project-bootstrapper"
        (self.skill / "assets/project-template").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
        (self.root / "README.md").write_text("# Template\n", encoding="utf-8")
        for name, value in (("ROOT", self.root), ("SKILL", self.skill)):
            patch = mock.patch.object(sync_skills, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        sync_skills.sync()

    def test_a_worktree_git_pointer_is_never_payload(self):
        self.assertFalse((self.skill / "assets/project-template/.git").exists())
        self.assertEqual(sync_skills.sync(check=True), [])

    def test_every_file_the_copy_filters_would_skip_is_pruned(self):
        # Pruning inspects every file already in a mirror, independent of the copy filters: a
        # `.git` pointer copied before the fix (PR #61 round 1), and local bootstrap state or build
        # artifacts in the payload or a native mirror (round 2), are all obsolete.
        asset = self.skill / "assets/project-template"
        native = self.root / ".agents/skills/complex-project-bootstrapper"
        stale = [asset / ".git", asset / "config/bootstrap.json", asset / "BOOTSTRAP_REVIEW.md",
                 asset / "bootstrap-answers.local.json", asset / "stray.pyc", native / "bundle.zip"]
        for path in stale:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("stale\n", encoding="utf-8")
        drift = sync_skills.sync(check=True)
        self.assertEqual(sorted(drift), sorted(path.relative_to(self.root).as_posix() for path in stale))
        self.assertTrue(all(path.exists() for path in stale), "--check must not write")
        sync_skills.sync()
        self.assertFalse(any(path.exists() for path in stale))
        self.assertEqual(sync_skills.sync(check=True), [])

    def test_obsolete_mirror_files_are_reported_and_removed(self):
        asset = self.skill / "assets/project-template"
        native = self.root / ".claude/skills/complex-project-bootstrapper"
        self.assertTrue((asset / "README.md").exists())
        self.assertTrue((native / "SKILL.md").exists())
        # A file deleted at the source stays in the mirrors unless sync detects it.
        (self.root / "README.md").unlink()
        (native / "references").mkdir()
        (native / "references/renamed.md").write_text("old\n", encoding="utf-8")
        drift = sync_skills.sync(check=True)
        self.assertIn("skills/complex-project-bootstrapper/assets/project-template/README.md", drift)
        self.assertIn(".claude/skills/complex-project-bootstrapper/references/renamed.md", drift)
        self.assertTrue((asset / "README.md").exists(), "--check must not write")
        sync_skills.sync()
        self.assertFalse((asset / "README.md").exists())
        self.assertFalse((native / "references/renamed.md").exists())
        self.assertEqual(sync_skills.sync(check=True), [])


if __name__ == "__main__":
    unittest.main()
