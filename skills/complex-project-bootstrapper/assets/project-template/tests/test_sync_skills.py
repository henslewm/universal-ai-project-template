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
                 asset / "bootstrap-answers.local.json", asset / "stray.pyc", native / "bundle.zip",
                 # ... and anything under a directory the copy never descends into (round 3).
                 asset / "build/stale.txt", asset / "assets/stale.txt", asset / ".venv/stale.txt",
                 native / "dist/stale.txt", native / "assets/stale.txt"]
        for path in stale:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("stale\n", encoding="utf-8")
        drift = sync_skills.sync(check=True)
        # Files are compared exactly; their now-obsolete directories are also reported (with a
        # trailing slash), which the directory test covers.
        self.assertEqual(sorted(entry for entry in drift if not entry.endswith("/")),
                         sorted(path.relative_to(self.root).as_posix() for path in stale))
        self.assertTrue(all(path.exists() for path in stale), "--check must not write")
        sync_skills.sync()
        self.assertFalse(any(path.exists() for path in stale))
        self.assertEqual(sync_skills.sync(check=True), [])

    def test_links_in_a_mirror_are_removed_and_never_followed(self):
        # A directory link in the payload would be dereferenced by the generator's copytree, and a
        # file link at an expected path would be written through by the copy (PR #61 round 4).
        outside = self.root.parent / (self.root.name + "-outside")
        outside.mkdir()
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        (outside / "secret.txt").write_text("outside\n", encoding="utf-8")
        (outside / "README.md").write_text("outside readme\n", encoding="utf-8")
        asset = self.skill / "assets/project-template"
        dir_link, file_link = asset / "linked-dir", asset / "README.md"
        file_link.unlink()
        try:
            dir_link.symlink_to(outside, target_is_directory=True)
            file_link.symlink_to(outside / "README.md")
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable on this host")
        (self.root / "README.md").write_text("# Template, changed\n", encoding="utf-8")
        drift = sync_skills.sync(check=True)
        for path in (dir_link, file_link):
            self.assertIn(path.relative_to(self.root).as_posix(), drift)
        self.assertTrue(dir_link.is_symlink() and file_link.is_symlink(), "--check must not write")
        sync_skills.sync()
        self.assertFalse(dir_link.exists() or dir_link.is_symlink())
        self.assertFalse(file_link.is_symlink())
        self.assertEqual(file_link.read_text(encoding="utf-8"), "# Template, changed\n")
        self.assertEqual((outside / "README.md").read_text(encoding="utf-8"), "outside readme\n",
                         "the copy must never write through a link")
        self.assertTrue((outside / "secret.txt").exists(), "removing a link never touches its target")
        self.assertEqual(sync_skills.sync(check=True), [])

    def test_a_linked_mirror_root_or_ancestor_is_refused_untouched(self):
        # PR #61 round 5: a mirror root that is itself a link would send copies and prunes into its
        # target. The sync refuses before touching anything, in both modes.
        outside = self.root.parent / (self.root.name + "-outside-root")
        outside.mkdir()
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        (outside / "keep.txt").write_text("outside\n", encoding="utf-8")
        for linked in (self.root / ".agents/skills/complex-project-bootstrapper", self.root / ".claude/skills"):
            with self.subTest(linked=linked.relative_to(self.root).as_posix()):
                moved = linked.with_name(linked.name + "-real")
                linked.rename(moved)
                try:
                    linked.symlink_to(outside, target_is_directory=True)
                except (OSError, NotImplementedError):
                    moved.rename(linked)
                    self.skipTest("Symbolic links are unavailable on this host")
                try:
                    for check in (True, False):
                        with self.assertRaisesRegex(ValueError, "Refusing to sync through a link"):
                            sync_skills.sync(check=check)
                    self.assertEqual(sorted(p.name for p in outside.iterdir()), ["keep.txt"])
                finally:
                    sync_skills.remove_link(linked)
                    moved.rename(linked)
        self.assertEqual(sync_skills.sync(check=True), [])

    def test_obsolete_directories_are_pruned_even_when_empty(self):
        # PR #61 round 6: an empty obsolete directory yields no file, so it survived pruning and the
        # generator's copytree then shipped it. So did one emptied by the file prune itself.
        asset = self.skill / "assets/project-template"
        native = self.root / ".claude/skills/complex-project-bootstrapper"
        (asset / "old-docs/nested").mkdir(parents=True)
        (native / "empty").mkdir()
        (asset / "gone").mkdir()
        (asset / "gone/stale.md").write_text("stale\n", encoding="utf-8")
        (asset / "gone/__pycache__").mkdir()
        (asset / "gone/__pycache__/x.pyc").write_text("cache\n", encoding="utf-8")
        drift = sync_skills.sync(check=True)
        for expected in ("skills/complex-project-bootstrapper/assets/project-template/old-docs/",
                         ".claude/skills/complex-project-bootstrapper/empty/",
                         "skills/complex-project-bootstrapper/assets/project-template/gone/"):
            self.assertIn(expected, drift)
        self.assertNotIn("skills/complex-project-bootstrapper/assets/project-template/old-docs/nested/", drift,
                         "the topmost obsolete directory is reported once")
        self.assertTrue((asset / "old-docs/nested").is_dir(), "--check must not write")
        sync_skills.sync()
        for path in (asset / "old-docs", native / "empty", asset / "gone"):
            self.assertFalse(path.exists())
        self.assertTrue((asset / "README.md").exists() and (native / "SKILL.md").exists(), "produced content stays")
        self.assertEqual(sync_skills.sync(check=True), [])

    def test_regenerated_caches_in_a_mirror_are_not_drift(self):
        # Running the suite executes scripts from the native mirrors, which leaves __pycache__
        # there; CI runs the payload check after the tests, so caches must not count as drift.
        native = self.root / ".agents/skills/complex-project-bootstrapper"
        for path in (native / "scripts/__pycache__/x.cpython-312.pyc", native / ".pytest_cache/v/cache"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("cache\n", encoding="utf-8")
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
