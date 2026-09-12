#!/usr/bin/env python3
"""Standard-library tests for the common bootstrap gate."""
from __future__ import annotations

import importlib.util
import copy
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

    def approve(self, data):
        data["state"] = "ACTIVE"
        data["approval"] = {"approved": True, "approved_by": "Synthetic test user", "approved_at": "2026-09-12T01:00:00Z", "architecture_fingerprint": MODULE.architecture_fingerprint(data)}
        return data

    def test_every_approval_bound_section_invalidates_active_state(self):
        original = self.approve(self.load("config/bootstrap.example.json"))
        for field in MODULE.FINGERPRINT_FIELDS:
            with self.subTest(field=field):
                data = copy.deepcopy(original)
                value = data[field]
                if isinstance(value, dict):
                    value["changed_after_approval"] = True
                elif isinstance(value, list):
                    value.append("Changed after approval")
                else:
                    data[field] = value + " changed"
                self.assertTrue(MODULE.validate(data))

    def test_blank_placeholder_and_wrong_types_cannot_activate_with_fresh_hash(self):
        paths = [("project", "name"), ("project", "objective"), ("architecture", "summary"), ("routing", "policy"), ("workflow", "policy")]
        arrays = [("project", "definition_of_done"), ("architecture", "boundaries"), ("architecture", "milestones"), ("sources",), ("risks",), ("human_gates",)]
        for path in paths + arrays:
            for invalid in ("", "   ", "{{UNRESOLVED}}", "TBD", "TBD later", "TODO: fill this in", "[TBD] architecture", "To be determined after intake", {}, 123, None):
                with self.subTest(path=path, invalid=invalid):
                    data = self.load("config/bootstrap.example.json")
                    container = data if len(path) == 1 else data[path[0]]
                    container[path[-1]] = [invalid] if path in arrays else invalid
                    self.assertTrue(MODULE.validate(self.approve(data)))

    def test_malformed_shapes_return_errors(self):
        for malformed in (None, [], "ACTIVE", 42):
            self.assertTrue(MODULE.validate(malformed))
        for field in ("domain_profile", "state", "project", "architecture", "approval", "domain", "configuration", "documents"):
            with self.subTest(field=field):
                data = self.load("config/bootstrap.example.json")
                data[field] = []
                self.assertTrue(MODULE.validate(data))

    def test_invalid_approval_metadata_and_inactive_approval_are_rejected(self):
        for field, values in {"approved_by": ["", "  ", {}, 123], "approved_at": ["unknown", "2026-09-12", "2026-09-12T01:00:00", "2026-09-12T01:00:00-04:00", 123]}.items():
            for value in values:
                data = self.approve(self.load("config/bootstrap.example.json"))
                data["approval"][field] = value
                self.assertTrue(MODULE.validate(data))
        for state in MODULE.STATES - {"ACTIVE"}:
            data = self.approve(self.load("config/bootstrap.example.json"))
            data["state"] = state
            self.assertTrue(MODULE.validate(data))

    def test_domain_orientation_and_unresolved_blockers_gate_review(self):
        for rel in ("config/bootstrap.example.json", "tests/fixtures/bootstrap-family-law-awaiting.json", "tests/fixtures/bootstrap-civil-rights-awaiting.json"):
            data = self.load(rel)
            for field in MODULE.DOMAIN_FIELDS[data["domain_profile"]]:
                changed = copy.deepcopy(data)
                changed["domain"][field] = ""
                self.assertTrue(MODULE.validate(changed))
                self.assertTrue(MODULE.validate(self.approve(changed)))
            data["unresolved"] = ["Material decision pending"]
            self.assertTrue(MODULE.validate(self.approve(data)))

    def test_milestone_dependencies_reject_cycles_and_unknown_nodes(self):
        for edges in (["Baseline -> Missing"], ["Baseline -> Baseline"], ["Baseline -> Implementation", "Implementation -> Baseline"]):
            data = self.load("config/bootstrap.example.json")
            data["architecture"]["dependencies"] = edges
            self.assertTrue(MODULE.validate(data))

    def test_empty_risk_assessment_cannot_be_reviewed_or_activated(self):
        data = self.load("config/bootstrap.example.json")
        data["risks"] = []
        self.assertTrue(MODULE.validate(data))
        self.assertTrue(MODULE.validate(self.approve(data)))

    def test_unknowns_can_be_described_in_a_concrete_risk_assessment(self):
        self.assertTrue(MODULE.meaningful("Unknown hardware behavior requires simulator evidence and physical verification."))


if __name__ == "__main__":
    unittest.main()
