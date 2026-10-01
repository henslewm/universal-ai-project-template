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

# Matches scripts/sync_skills.py's EXCLUDED: caches, local venvs, and the
# nested payload mirror under 'assets', none of which validate_project.py
# requires. Independent of Git metadata so this also exercises the checkout
# shape a --no-git generated project or a source-archive extraction has.
EXCLUDED_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "dist", "build", "assets"}


def repository_copy(destination: Path) -> None:
    """Copy the repository tree into destination without relying on Git."""

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in EXCLUDED_DIR_NAMES}

    shutil.copytree(ROOT, destination, ignore=ignore)


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

    def test_mistral_row_in_bootstrapper_platform_map(self) -> None:
        # Codex round 2: bootstrap_project.py's default ai_clients now offers
        # "mistral", but the bootstrap workflow (SKILL.md step 6) applies
        # references/platform-map.md to wire each client's native discovery
        # mechanism. Without a Mistral row there, following that workflow could
        # declare Mistral supported without ever pasting its Project
        # instructions or connecting its knowledge source.
        text = (ROOT / "skills/complex-project-bootstrapper/references/platform-map.md").read_text(encoding="utf-8")
        self.assertIn("Mistral", text)
        self.assertIn(".mistral/PROJECT_INSTRUCTIONS.md", text)

    def test_validator_refuses_a_checkout_missing_the_mistral_master(self) -> None:
        # Before this fix, REQUIRED omitted MASTER_MISTRAL.md, so deleting it from a
        # checkout passed validation. Prove the enforcement is real: build a disposable
        # checkout, delete the master there, and show the validator now refuses it by
        # name.
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "checkout"
            repository_copy(destination)
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


class IssueTemplateGuidanceTests(unittest.TestCase):
    def test_evidence_gap_template_warns_against_placeholder_reports(self) -> None:
        canonical = ROOT / ".github/ISSUE_TEMPLATE/evidence-gap.yml"
        mirrored = ROOT / "skills/complex-project-bootstrapper/assets/project-template/.github/ISSUE_TEMPLATE/evidence-gap.yml"
        text = canonical.read_text(encoding="utf-8")
        self.assertIn("Do not submit placeholder text such as `Blocker`, `unknown`", text)
        self.assertIn("If you cannot name the canonical task, master issue, packet binding", text)
        self.assertIn("contract_sha256: <64-hex sha256>", text)
        self.assertIn("https://github.com/henslewm/universal-ai-project-template/issues/11", text)
        self.assertIn("Missing evidence: signed order entered on 2026-09-21", text)
        self.assertIn("Search 2026-09-28 05:30 UTC: county eCourts portal query", text)
        self.assertIn("Required source: county clerk docket export or filed PDF", text)
        self.assertIn("Owner: Winston", text)
        self.assertEqual(text, mirrored.read_text(encoding="utf-8"))


class ArchiveHistoryTests(unittest.TestCase):
    """ADR-081: the archives hold the ADR rows and changelog entries moved out of the
    startup files, so a missing or zero-byte archive must fail validation (PR #99)."""

    def _validate_with_archive(self, name: str, empty: bool) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "checkout"
            repository_copy(destination)
            target = destination / "archive" / name
            if empty:
                target.write_text("", encoding="utf-8")
            else:
                target.unlink()
            return subprocess.run([sys.executable, str(destination / "scripts/validate_project.py")],
                                  cwd=destination, text=True, capture_output=True)

    def test_validator_refuses_missing_or_empty_archives(self) -> None:
        for name in validate_project.TEMPLATE_ONLY_REQUIRED:
            for empty in (False, True):
                with self.subTest(archive=name, empty=empty):
                    result = self._validate_with_archive(Path(name).name, empty)
                    self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
                    self.assertIn(name, result.stdout)


class VibeCliConfigTests(unittest.TestCase):
    """The Mistral Vibe CLI reads ./.vibe/config.toml (docs.mistral.ai/vibe/code/cli/configuration)."""

    def test_project_config_is_valid_toml_that_keeps_approval_prompts(self) -> None:
        import tomllib

        data = tomllib.loads((ROOT / ".vibe/config.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["default_agent"], "default", "default asks before running tools")
        self.assertEqual(data["tools"]["bash"]["permission"], "ask")
        self.assertIn(".vibe/config.toml", validate_project.REQUIRED)


if __name__ == "__main__":
    unittest.main()
