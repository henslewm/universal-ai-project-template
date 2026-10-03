from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "example-complex-matter"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/bootstrap_project.py"),
                    "--answers",
                    str(ROOT / "tests/fixtures/software-project.json"),
                    "--destination",
                    str(destination),
                    "--no-git",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            config = json.loads((destination / "config/project.json").read_text(encoding="utf-8"))
            self.assertFalse(config["template_mode"])
            self.assertEqual(config["project_slug"], "example-complex-matter")
            self.assertIn("source-evidence-ledger", (destination / "SKILL_PLAN.md").read_text(encoding="utf-8"))
            validation = subprocess.run(
                [sys.executable, str(destination / "scripts/validate_project.py")],
                cwd=destination,
                text=True,
                capture_output=True,
            )
            self.assertEqual(validation.returncode, 0, msg=validation.stdout + validation.stderr)

    def test_bootstrap_in_place(self) -> None:
        # In-place bootstrap is refused once a project is generated (bootstrap_project.py
        # rejects existing bootstrap state and template_mode=false), so only a template
        # checkout can exercise it; same mode check as validate_project.py.
        if not json.loads((ROOT / "config/project.json").read_text(encoding="utf-8")).get("template_mode", True):
            self.skipTest("in-place bootstrap only applies to a template checkout")
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "github-template-project"
            shutil.copytree(
                ROOT,
                destination,
                ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(destination / "scripts/bootstrap_project.py"),
                    "--answers",
                    str(destination / "tests/fixtures/software-project.json"),
                    "--template-root",
                    str(destination),
                    "--destination",
                    str(destination),
                    "--no-git",
                ],
                cwd=destination,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            config = json.loads((destination / "config/project.json").read_text(encoding="utf-8"))
            self.assertFalse(config["template_mode"])
            self.assertEqual(config["project_slug"], "example-complex-matter")
            # In place, as by copy, a generated project has no payload, so its inherited CI skips
            # the payload-drift check it could never pass (PR #61 Codex round 1).
            self.assertFalse((destination / "skills/complex-project-bootstrapper/assets/project-template").exists())
            self.assertEqual(sorted(p.name for p in (destination / "docs").glob("*VALIDATION.md")), [])
            validation = subprocess.run(
                [sys.executable, str(destination / "scripts/validate_project.py")],
                cwd=destination,
                text=True,
                capture_output=True,
            )
            self.assertEqual(validation.returncode, 0, msg=validation.stdout + validation.stderr)


if __name__ == "__main__":
    unittest.main()
