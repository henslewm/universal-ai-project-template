#!/usr/bin/env python3
"""Standard-library tests for the common bootstrap gate."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("validate_bootstrap", ROOT / "scripts" / "validate_bootstrap.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class BootstrapGateTests(unittest.TestCase):
    def load(self, rel: str) -> dict:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_software_hardware_awaiting_is_valid_but_not_active(self) -> None:
        data = self.load("config/bootstrap.example.json")
        self.assertEqual([], MODULE.validate(data))
        self.assertEqual("AWAITING_APPROVAL", data["state"])

    def test_family_law_awaiting_is_valid(self) -> None:
        data = self.load("tests/fixtures/bootstrap-family-law-awaiting.json")
        self.assertEqual([], MODULE.validate(data))

    def test_civil_rights_awaiting_is_valid(self) -> None:
        data = self.load("tests/fixtures/bootstrap-civil-rights-awaiting.json")
        self.assertEqual([], MODULE.validate(data))

    def test_active_without_approval_is_rejected(self) -> None:
        data = self.load("tests/fixtures/bootstrap-active-missing-approval.json")
        errors = MODULE.validate(data)
        self.assertTrue(any("approval.approved=true" in item for item in errors))

    def test_active_with_matching_fingerprint_is_valid(self) -> None:
        data = self.load("config/bootstrap.example.json")
        data["state"] = "ACTIVE"
        data["approval"] = {
            "approved": True,
            "approved_by": "test-user",
            "approved_at": "2026-09-12T01:00:00+00:00",
            "architecture_fingerprint": MODULE.architecture_fingerprint(data),
        }
        self.assertEqual([], MODULE.validate(data))

    def test_material_change_after_approval_is_rejected(self) -> None:
        data = self.load("config/bootstrap.example.json")
        data["state"] = "ACTIVE"
        data["approval"] = {
            "approved": True,
            "approved_by": "test-user",
            "approved_at": "2026-09-12T01:00:00+00:00",
            "architecture_fingerprint": MODULE.architecture_fingerprint(data),
        }
        data["architecture"]["boundaries"].append("Changed after approval")
        errors = MODULE.validate(data)
        self.assertTrue(any("fingerprint" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
