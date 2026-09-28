from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_project  # noqa: E402


def tracked_copy(destination: Path) -> None:
    """Copy only Git-tracked files into destination, mirroring a clean checkout."""
    listing = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.splitlines()
    for rel in listing:
        source = ROOT / rel
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


class MistralWiringTests(unittest.TestCase):
    """Issue #46: the restored Mistral Vibe platform files must be wired in,
    not merely present. https://github.com/henslewm/universal-ai-project-template/issues/46
    """

    def test_mistral_master_and_project_files_are_required(self) -> None:
        required = set(validate_project.REQUIRED)
        for rel in (
            "MASTER_MISTRAL.md",
            ".mistral/PROJECT_INSTRUCTIONS.md",
            ".mistral/PROJECT_KNOWLEDGE.md",
        ):
            self.assertIn(rel, required, f"{rel} must be a required path")

    def test_mistral_master_named_in_authority_order(self) -> None:
        text = (ROOT / "MASTER_INSTRUCTIONS.md").read_text(encoding="utf-8")
        match = re.search(r"^5\. The active platform master: (.+)$", text, flags=re.M)
        self.assertIsNotNone(match, "authority-order item 5 not found")
        self.assertIn("MASTER_MISTRAL.md", match.group(1))

    def test_validator_refuses_a_checkout_missing_the_mistral_master(self) -> None:
        # Before this fix, REQUIRED omitted MASTER_MISTRAL.md, so deleting it from a
        # checkout passed validation. Prove the enforcement is real: build a disposable
        # tracked-files checkout, delete the master there, and show the validator now
        # refuses it by name.
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "checkout"
            tracked_copy(destination)
            (destination / "MASTER_MISTRAL.md").unlink()
            result = subprocess.run(
                [sys.executable, str(destination / "scripts/validate_project.py")],
                cwd=destination,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("MASTER_MISTRAL.md", result.stdout)

    def test_repository_validates(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_project.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
