"""Payload synchronization: obsolete mirror files and worktree `.git` pointers (#49)."""
from __future__ import annotations

import os
import shutil
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
        for name in ("bootstrap_project.py", "bootstrap_gate.py", "validate_bootstrap.py", "validate_project.py", "cli_exit.py"):
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

    def test_a_junction_mirror_ancestor_is_refused(self):
        # PR #61 round 10: a Windows junction is not reported by Path.is_symlink(), so the
        # preflight must also check is_junction(), or a junction root/ancestor would go
        # untouched by this guard exactly like a symlink root would (round 5). Junctions cannot
        # be created on this host, so is_junction() is faked true for one real path instead.
        linked = self.root / ".agents/skills/complex-project-bootstrapper"
        with mock.patch.object(sync_skills, "is_junction", lambda path: path == linked):
            for check in (True, False):
                with self.assertRaisesRegex(ValueError, "Refusing to sync through a link"):
                    sync_skills.sync(check=check)
        self.assertEqual(sync_skills.sync(check=True), [])

    def test_a_junction_in_a_mirror_is_detected_and_removed(self):
        # A junction inside a mirror is exactly as much drift as a symlink there (round 4), but
        # os.walk does not stop at one on its own; unlink_all must detect it via is_junction()
        # before prune's directory walk could otherwise reach it.
        asset = self.skill / "assets/project-template"
        junction = asset / "linked-dir-junction"
        junction.mkdir()
        with mock.patch.object(sync_skills, "is_junction", lambda path: path == junction):
            drift = sync_skills.sync(check=True)
            # Nothing is deleted under --check, so the same still-present junction is found by
            # both unlink_all's sweep and prune's own pass over the same mirror; it must collapse
            # to one reported entry (self-review finding), not the bare path and a trailing-slash
            # "directory" spelling of it counted as two different drift items.
            self.assertEqual(drift.count(junction.relative_to(self.root).as_posix()), 1)
            self.assertNotIn(junction.relative_to(self.root).as_posix() + "/", drift)
            self.assertTrue(junction.exists(), "--check must not write")
            sync_skills.sync()
            self.assertFalse(junction.exists())
        self.assertEqual(sync_skills.sync(check=True), [])

    def test_prune_never_rmtrees_a_junction_either(self):
        # prune()'s own obsolete-directory walk must refuse to shutil.rmtree a junction on its
        # own terms too, not rely solely on unlink_all's earlier sweep of the same tree (which
        # would ordinarily remove it first) -- simulated here as having missed it, the same way
        # as the ancestor test above (self-review finding).
        asset = self.skill / "assets/project-template"
        junction = asset / "leftover-junction"
        junction.mkdir()
        real_links_under = sync_skills.links_under

        def links_under_missing_junction(root):
            return (path for path in real_links_under(root) if path != junction)

        original_rmtree = shutil.rmtree

        def guarded_rmtree(path, *args, **kwargs):
            if Path(path) == junction:
                raise AssertionError("prune() must never rmtree a junction")
            return original_rmtree(path, *args, **kwargs)

        with mock.patch.object(sync_skills, "is_junction", lambda path: path == junction), \
                mock.patch.object(sync_skills, "links_under", links_under_missing_junction), \
                mock.patch("shutil.rmtree", guarded_rmtree):
            sync_skills.sync()
        self.assertFalse(junction.exists())

    def test_a_junction_ancestor_of_a_copy_target_is_removed_first(self):
        # A junction ancestor reports is_dir() = True and is_symlink() = False, so it defeats the
        # pre-existing "wrong type" ancestor check (which only catches a non-directory in the
        # chain, round 6): without is_junction() there, the copy would write straight through a
        # real junction into its external target instead of ever removing it. copy()'s own check
        # must catch this independently of unlink_all's earlier sweep of the same tree -- which
        # would ordinarily remove it first -- so that sweep is simulated as having missed it here
        # (self-review finding: without this, the test passed even with copy()'s own check
        # reverted, because unlink_all alone was already satisfying the assertion).
        asset = self.skill / "assets/project-template"
        ancestor = asset / "scripts"
        self.assertTrue(ancestor.is_dir())
        calls = []
        real_links_under = sync_skills.links_under

        def links_under_missing_ancestor(root):
            return (path for path in real_links_under(root) if path != ancestor)

        with mock.patch.object(sync_skills, "is_junction", lambda path: path == ancestor), \
                mock.patch.object(sync_skills, "links_under", links_under_missing_ancestor), \
                mock.patch.object(sync_skills, "remove_link", lambda path: calls.append(path)):
            sync_skills.sync()
        self.assertIn(ancestor, calls, "a junction ancestor must be removed, not written through")
        self.assertEqual((ancestor / "bootstrap_project.py").read_text(encoding="utf-8"),
                          "# bootstrap_project.py\n")

    @unittest.skipIf(os.name == "nt", "Windows has no POSIX executable bit for chmod to set")
    def test_the_fast_path_also_compares_permission_bits(self):
        # An unchanged-bytes fast path that ignores mode bits would leave a mirror file's
        # permissions stale after the source's executable bit changes with no content change.
        source = self.root / "scripts/bootstrap_project.py"
        target = self.skill / "scripts/bootstrap_project.py"
        self.assertEqual(source.read_bytes(), target.read_bytes())
        source.chmod(source.stat().st_mode | 0o111)
        drift = sync_skills.sync(check=True)
        self.assertIn(target.relative_to(self.root).as_posix(), drift)
        sync_skills.sync()
        self.assertTrue(target.stat().st_mode & 0o111)

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

    def test_the_temp_write_name_never_collides_with_a_real_source(self):
        # PR #61 round 11: a fixed target-name-derived temp path can collide with an actual
        # tracked file that happens to share that literal name. The entrypoint copy into SKILL
        # runs before the files_under(SKILL) loop that would otherwise treat this file as a
        # legitimate source of its own; a collision destroys it before that loop ever sees it.
        colliding = self.skill / "scripts/bootstrap_project.py.sync-tmp"
        colliding.write_text("do not lose me\n", encoding="utf-8")
        (self.root / "scripts/bootstrap_project.py").write_text("# changed\n", encoding="utf-8")
        sync_skills.sync()
        self.assertEqual(colliding.read_text(encoding="utf-8"), "do not lose me\n")
        for native in (".agents/skills", ".claude/skills"):
            mirrored = self.root / native / "complex-project-bootstrapper/scripts/bootstrap_project.py.sync-tmp"
            self.assertTrue(mirrored.exists())
            self.assertEqual(mirrored.read_text(encoding="utf-8"), "do not lose me\n")

    def test_wrong_type_entries_are_reported_without_reading_and_replaced(self):
        # PR #61 round 7: a directory where a file belongs crashed both modes with
        # IsADirectoryError, and a file where a directory belongs would crash the write.
        asset = self.skill / "assets/project-template"
        (asset / "README.md").unlink()
        (asset / "README.md").mkdir()
        (asset / "README.md/inner.txt").write_text("stale\n", encoding="utf-8")
        native = self.root / ".claude/skills/complex-project-bootstrapper"
        (self.skill / "references").mkdir()
        (self.skill / "references/guide.md").write_text("# Guide\n", encoding="utf-8")
        (native / "references").write_text("a file where a directory belongs\n", encoding="utf-8")
        drift = sync_skills.sync(check=True)
        self.assertIn("skills/complex-project-bootstrapper/assets/project-template/README.md", drift)
        self.assertIn(".claude/skills/complex-project-bootstrapper/references/guide.md", drift)
        self.assertTrue((asset / "README.md").is_dir(), "--check must not write")
        sync_skills.sync()
        self.assertEqual((asset / "README.md").read_text(encoding="utf-8"), "# Template\n")
        self.assertEqual((native / "references/guide.md").read_text(encoding="utf-8"), "# Guide\n")
        self.assertEqual(sync_skills.sync(check=True), [])

    def test_check_mode_never_reads_through_a_link_at_an_expected_path(self):
        # PR #61 round 7: --check reported the link, then compared contents by reading its target.
        outside = self.root.parent / (self.root.name + "-outside-read")
        outside.mkdir()
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        secret = outside / "unreadable.md"
        secret.write_text("outside\n", encoding="utf-8")
        link = self.skill / "assets/project-template/README.md"
        link.unlink()
        try:
            link.symlink_to(secret)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable on this host")
        original = Path.read_bytes

        def guarded(path):
            if Path(path).resolve() == secret.resolve():
                raise AssertionError("check mode read through a link")
            return original(path)

        with mock.patch.object(Path, "read_bytes", guarded):
            drift = sync_skills.sync(check=True)
        self.assertIn("skills/complex-project-bootstrapper/assets/project-template/README.md", drift)

    def test_check_mode_reports_drift_instead_of_crashing_on_an_unreadable_stale_source(self):
        # PR #61 round 14: a native mirror can hold a stale regular file that prune() already
        # detects (not part of `expected`) but --check leaves in place. files_under(ROOT)'s later
        # asset-copy pass still walks the whole repository and can pick up that same stale file
        # as a "source"; with a same-type file already at the colliding payload path (so the
        # target is not "blocking" and the fast path runs), an unreadable source must report the
        # already-known drift rather than raise.
        stale = self.root / ".agents/skills/complex-project-bootstrapper/stray.md"
        stale.write_text("stray\n", encoding="utf-8")
        asset_copy = self.skill / "assets/project-template/.agents/skills/complex-project-bootstrapper/stray.md"
        asset_copy.parent.mkdir(parents=True, exist_ok=True)
        asset_copy.write_text("stray\n", encoding="utf-8")
        original = Path.read_bytes

        def guarded(path):
            if Path(path) == stale:
                raise OSError("simulated unreadable native entry")
            return original(path)

        with mock.patch.object(Path, "read_bytes", guarded):
            drift = sync_skills.sync(check=True)
        self.assertIn(stale.relative_to(self.root).as_posix(), drift)

    def test_a_native_mirror_file_link_is_never_read_as_an_asset_source(self):
        # PR #61 round 13: files_under(ROOT) walks the whole repository, which includes the
        # native mirror directories -- unlink_all reports a link there under --check but does not
        # yet remove it, so the later files_under(ROOT)/asset copy pass could pick that same link
        # up as a "source" and read through it via the fast path's source.read_bytes().
        outside = self.root.parent / (self.root.name + "-outside-source-read")
        outside.mkdir()
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        secret = outside / "unreadable.md"
        secret.write_text("outside\n", encoding="utf-8")
        native = self.root / ".agents/skills/complex-project-bootstrapper/SKILL.md"
        native.unlink()
        try:
            native.symlink_to(secret)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable on this host")
        original = Path.read_bytes

        def guarded(path):
            if Path(path).resolve() == secret.resolve():
                raise AssertionError("check mode read through a link used as a copy source")
            return original(path)

        with mock.patch.object(Path, "read_bytes", guarded):
            drift = sync_skills.sync(check=True)
        self.assertIn(native.relative_to(self.root).as_posix(), drift)

    def test_a_hard_linked_target_is_replaced_not_written_through(self):
        # A mirror file sharing its inode with another name must not change that other file (#62).
        target = self.skill / "assets/project-template/README.md"
        sibling = self.root.parent / (self.root.name + "-hardlink-sibling.md")
        self.addCleanup(lambda: sibling.unlink() if sibling.exists() else None)
        target.unlink()
        sibling.write_text("keep me\n", encoding="utf-8")
        try:
            __import__("os").link(sibling, target)
        except (OSError, NotImplementedError):
            self.skipTest("Hard links are unavailable on this host")
        sync_skills.sync()
        self.assertEqual(target.read_text(encoding="utf-8"), "# Template\n")
        self.assertEqual(sibling.read_text(encoding="utf-8"), "keep me\n")

    def test_a_hard_linked_target_with_matching_content_is_still_replaced(self):
        # A mirror file whose content already equals the source, but which shares its inode with
        # another name, must still be reported and replaced: leaving it linked means a later write
        # through the sibling would silently change this mirror file too, with no drift ever shown.
        target = self.skill / "assets/project-template/README.md"
        sibling = self.root.parent / (self.root.name + "-hardlink-sibling-matching.md")
        self.addCleanup(lambda: sibling.unlink() if sibling.exists() else None)
        target.unlink()
        sibling.write_text("# Template\n", encoding="utf-8")
        try:
            __import__("os").link(sibling, target)
        except (OSError, NotImplementedError):
            self.skipTest("Hard links are unavailable on this host")
        self.assertEqual(target.stat().st_ino, sibling.stat().st_ino)
        drift = sync_skills.sync(check=True)
        self.assertIn("skills/complex-project-bootstrapper/assets/project-template/README.md", drift)
        sync_skills.sync()
        self.assertNotEqual(target.stat().st_ino, sibling.stat().st_ino)
        self.assertEqual(target.stat().st_nlink, 1)
        self.assertEqual(target.read_text(encoding="utf-8"), "# Template\n")
        self.assertEqual(sibling.read_text(encoding="utf-8"), "# Template\n")

    @unittest.skipIf(os.name == "nt", "Windows has no POSIX executable bit for chmod to set")
    def test_a_replaced_file_keeps_the_sources_executable_bit(self):
        # The write path replaces the target via a temp file; the temp file's own (umask) mode
        # must not silently drop the source's executable bit onto the mirror.
        source = self.root / "scripts/bootstrap_project.py"
        source.write_text("# bootstrap_project.py\nexecutable\n", encoding="utf-8")
        source.chmod(source.stat().st_mode | 0o111)
        target = self.skill / "scripts/bootstrap_project.py"
        sync_skills.sync()
        self.assertTrue(target.stat().st_mode & 0o111, "executable bit was not copied onto the mirror")

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
