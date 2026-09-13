"""Software + hardware domain rules: simulated success never becomes hardware verification."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_acceptance import (ARCHITECT, CONTROLLER, IMPLEMENTERS, AcceptanceBase, acceptance,
                             make_artifact, make_contract, make_packet, make_report, make_result)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("software_hardware_under_test", ROOT / "scripts/software_hardware.py")
domain = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(domain)
wp = acceptance.wp
PROFILE = "software-hardware"
EXAMPLES = ROOT / "examples/software-hardware"
PACKET_FILES = sorted((EXAMPLES / "packets").glob("*.contract.json"))
EVIDENCE = wp.read_json(EXAMPLES / "hardware-evidence.example.json")
SCRIPT = ROOT / "scripts/software_hardware.py"


def example():
    return wp.read_json(ROOT / "examples/work-packets/software-hardware.contract.json")


def errors_for(contract):
    return wp.validate_contract(contract, PROFILE)


def hardware_contract():
    """The example contract with its one check moved to the hardware rung."""
    value = example()
    del value["validation"][0]["command"]
    value["domain"]["validation_levels"]["VAL-FRAMES"] = "hardware_in_loop"
    return value


def local_argv(contract):
    """Run the example packets' declared commands with this interpreter instead of PATH's python."""
    value = copy.deepcopy(contract)
    for check in value["validation"]:
        if "command" in check:
            check["command"]["argv"][0] = sys.executable
    return value


class ContractRuleTests(unittest.TestCase):
    def test_example_contracts_satisfy_the_domain_rules(self):
        self.assertEqual(errors_for(example()), [])
        for path in PACKET_FILES:
            with self.subTest(path=path.name):
                self.assertEqual(errors_for(wp.read_json(path)), [])
        self.assertEqual(len(PACKET_FILES), 6)

    def test_domain_rules_apply_only_to_the_registered_profile(self):
        broken = example()
        broken["domain"] = {"synthetic": True}
        self.assertEqual(wp.validate_contract(broken), [])
        self.assertTrue(any(e.startswith("domain:") for e in errors_for(broken)))
        self.assertIsNone(wp.domain_module("family-law"))

    def test_verified_on_hardware_is_never_authored(self):
        contract = example()
        contract["domain"]["hardware_status"] = "VERIFIED_ON_HARDWARE"
        self.assertTrue(any("hardware_status" in e for e in errors_for(contract)))

    def test_machine_rung_requires_a_command_and_hardware_rung_forbids_one(self):
        contract = example()
        del contract["validation"][0]["command"]
        self.assertTrue(any("must declare a command" in e for e in errors_for(contract)))
        contract = example()
        contract["domain"]["validation_levels"]["VAL-FRAMES"] = "hardware_in_loop"
        self.assertTrue(any("must not declare a command" in e for e in errors_for(contract)))
        self.assertEqual(errors_for(hardware_contract()), [])
        for level in domain.MACHINE_LEVELS:
            contract = example()
            contract["domain"]["validation_levels"]["VAL-FRAMES"] = level
            self.assertEqual(errors_for(contract), [], level)

    def test_every_validation_is_mapped_to_exactly_one_rung(self):
        contract = example()
        contract["domain"]["validation_levels"] = {}
        self.assertTrue(any("validation_levels" in e for e in errors_for(contract)))
        contract["domain"]["validation_levels"] = {"VAL-GHOST": "unit"}
        self.assertTrue(any("unmapped: VAL-FRAMES" in e for e in errors_for(contract)))
        contract = example()
        contract["domain"]["validation_levels"]["VAL-GHOST"] = "unit"
        self.assertTrue(any("does not declare" in e for e in errors_for(contract)))
        contract = example()
        contract["domain"]["validation_levels"]["VAL-FRAMES"] = "compiled"
        self.assertTrue(errors_for(contract))

    def test_hardware_assumptions_and_protocol_references_cite_contract_sources(self):
        contract = example()
        contract["domain"]["hardware_assumptions"][0]["source_id"] = "SRC-NOPE"
        self.assertTrue(any("unknown source SRC-NOPE" in e for e in errors_for(contract)))
        contract = example()
        contract["domain"]["protocol_references"] = ["SRC-NOPE"]
        self.assertTrue(any("protocol_references: unknown source" in e for e in errors_for(contract)))
        contract = example()
        contract["domain"]["protocol_references"] = []
        self.assertTrue(any("must cite its protocol" in e for e in errors_for(contract)))

    def test_status_follows_from_declared_hardware_assumptions(self):
        contract = example()
        contract["domain"]["hardware_status"] = "NOT_HARDWARE_FACING"
        self.assertTrue(any("is UNVERIFIED_ON_HARDWARE until" in e for e in errors_for(contract)))
        contract = example()
        contract["domain"]["hardware_assumptions"] = []
        self.assertTrue(any("is NOT_HARDWARE_FACING" in e for e in errors_for(contract)))
        contract["domain"]["hardware_status"] = "NOT_HARDWARE_FACING"
        contract["domain"]["protocol_references"] = []
        self.assertEqual(errors_for(contract), [])
        contract["domain"]["validation_levels"]["VAL-FRAMES"] = "field"
        del contract["validation"][0]["command"]
        self.assertTrue(any("cannot carry a hardware-rung check" in e for e in errors_for(contract)))

    def test_hardware_adapter_without_assumptions_is_a_contradiction(self):
        contract = example()
        contract["domain"].update(component="hardware_adapter", hardware_assumptions=[],
                                  hardware_status="NOT_HARDWARE_FACING", protocol_references=[])
        self.assertTrue(any("hardware adapter without" in e for e in errors_for(contract)))
        contract["domain"]["component"] = "firmware"
        self.assertTrue(any("component" in e for e in errors_for(contract)))

    def test_rules_reach_packet_validation_and_acceptance_init(self):
        packet = make_packet(make_contract())
        broken = copy.deepcopy(packet)
        latest = broken["revision_history"][-1]
        latest["contract"]["domain"]["hardware_status"] = "VERIFIED_ON_HARDWARE"
        latest["hash"] = wp.fingerprint(broken["task_id"], PROFILE, latest["version"], latest["contract"])
        for event in broken["events"]:
            event["contract_hash"] = latest["hash"]
        self.assertTrue(any("domain:" in e for e in wp.validate(broken)))
        with self.assertRaisesRegex(ValueError, "domain:"):
            acceptance.initialize(Path(self.enterContext(tempfile.TemporaryDirectory())) / "ledger",
                                  wp.read_json(ROOT / "config/acceptance.example.json"), broken, make_result(broken),
                                  make_artifact(), CONTROLLER, ARCHITECT, IMPLEMENTERS, [])

    def test_example_packets_form_a_dag_with_component_scoped_context(self):
        packets = [wp.create(path.name.split(".")[0], PROFILE, wp.read_json(path), "Architect", "Synthetic", "2026-09-13T00:00:00Z")
                   for path in PACKET_FILES]
        order = wp.graph_order(packets)
        self.assertEqual(order[0], "SHB-01-codec")
        self.assertEqual(order[-1], "SHB-06-workflow")
        components = {wp.current(p)["contract"]["domain"]["component"] for p in packets}
        self.assertEqual(len(components), 6)
        for packet in packets:
            contract = wp.current(packet)["contract"]
            with self.subTest(task=packet["task_id"]):
                self.assertNotIn("sample/synth_bridge/", " ".join(
                    item for item in contract["context_scope"] if "Interface" in item))
                self.assertLessEqual(len([i for i in contract["context_scope"] if i.startswith("sample/synth_bridge/")]), 2)
        levels = {p["task_id"]: wp.current(p)["contract"]["domain"]["validation_levels"] for p in packets}
        self.assertEqual(levels["SHB-04-adapter"]["VAL-HIL"], "hardware_in_loop")
        self.assertEqual(levels["SHB-06-workflow"]["VAL-FIELD"], "field")
        self.assertEqual(wp.current(packets[4])["contract"]["domain"]["hardware_status"], "NOT_HARDWARE_FACING")


class HardwareEvidenceTests(unittest.TestCase):
    def test_example_record_validates_and_its_lines_bind_the_digest(self):
        lines = domain.evidence_lines(EVIDENCE)
        self.assertEqual(lines[0], domain.DIGEST_PREFIX + domain.evidence_digest(EVIDENCE))
        self.assertIn("outcome=pass", lines)
        self.assertIn("operator=" + EVIDENCE["operator"], lines)
        digest, values = domain.parsed_evidence(lines + ["free text", "device=ignored duplicate"])
        self.assertEqual(digest, domain.evidence_digest(EVIDENCE))
        self.assertEqual(values["device"], EVIDENCE["device_identity"])

    def test_record_shape_is_closed(self):
        for field, value in (("outcome", "passed"), ("level", "unit"), ("observed_at", "yesterday"),
                             ("artifacts", [{"reference": "x", "sha256": "short"}]), ("extra", 1)):
            record = copy.deepcopy(EVIDENCE)
            record[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "hardware evidence"):
                domain.validate_hardware_evidence(record)
        record = copy.deepcopy(EVIDENCE)
        del record["observed_behavior"]
        with self.assertRaises(ValueError):
            domain.validate_hardware_evidence(record)

    def test_digest_changes_with_any_field(self):
        record = copy.deepcopy(EVIDENCE)
        record["observed_behavior"] += " and then it did not"
        self.assertNotEqual(domain.evidence_digest(record), domain.evidence_digest(EVIDENCE))


class AttestationRuleTests(AcceptanceBase):
    def hardware_ledger(self):
        ledger, packet = self.start(packet=make_packet(hardware_contract()))
        self.checked(ledger)
        return ledger

    def attest(self, ledger, operator, evidence):
        return acceptance.append(ledger, "ATTESTATION",
                                 {"attestation": {"validation_id": "VAL-FRAMES", "operator": operator, "evidence": evidence}},
                                 previous_state=acceptance.replay(ledger))

    def test_hardware_rung_attestation_must_bind_a_passing_record(self):
        ledger = self.hardware_ledger()
        lines = domain.evidence_lines(EVIDENCE)
        operator = EVIDENCE["operator"]
        with self.assertRaisesRegex(ValueError, "must carry exactly one"):
            self.attest(ledger, operator, ["Watched it work"])
        with self.assertRaisesRegex(ValueError, "must carry exactly one"):
            self.attest(ledger, operator, lines + [lines[0]])
        with self.assertRaisesRegex(ValueError, "must carry the bound record's"):
            self.attest(ledger, operator, [lines[0]])
        with self.assertRaisesRegex(ValueError, "recorded at field"):
            self.attest(ledger, operator, [line.replace("level=hardware_in_loop", "level=field") for line in lines])
        with self.assertRaisesRegex(ValueError, "never attested"):
            self.attest(ledger, operator, [line.replace("outcome=pass", "outcome=fail") for line in lines])
        with self.assertRaisesRegex(ValueError, "operator who recorded"):
            self.attest(ledger, "Someone else", lines)
        with self.assertRaisesRegex(ValueError, "cannot attest its own"):
            self.attest(ledger, "Worker", [line.replace("operator=" + operator, "operator=Worker") for line in lines])
        state = self.attest(ledger, operator, lines)
        self.assertTrue(acceptance.deterministic_satisfied(state))
        self.assertEqual(acceptance.deterministic_status(state)["VAL-FRAMES"], "ATTESTED")

    def test_runnable_check_is_still_executed_never_attested(self):
        ledger, _ = self.start()
        self.checked(ledger)
        with self.assertRaisesRegex(ValueError, "executed, never attested"):
            self.attest(ledger, EVIDENCE["operator"], domain.evidence_lines(EVIDENCE))

    def test_earned_status_requires_acceptance_with_attested_hardware_rungs(self):
        ledger = self.hardware_ledger()
        before = domain.status(ledger)
        self.assertEqual(before["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertEqual(before["validations"][0]["gate"], "NEEDS_ATTESTATION")
        self.attest(ledger, EVIDENCE["operator"], domain.evidence_lines(EVIDENCE))
        self.assertEqual(domain.status(ledger)["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        acceptance.accept(ledger, CONTROLLER)
        earned = domain.status(ledger)
        self.assertEqual(earned["earned_hardware_status"], "VERIFIED_ON_HARDWARE")
        self.assertEqual(earned["highest_level_satisfied"], "hardware_in_loop")
        self.assertEqual(earned["validations"][0]["evidence_digest"], domain.evidence_digest(EVIDENCE))
        # The bound record must be findable and consistent when an evidence directory is supplied.
        records = self.directory / "records"
        records.mkdir()
        self.assertEqual(domain.status(ledger, records)["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        (records / "hil.json").write_text(json.dumps(EVIDENCE), encoding="utf-8")
        self.assertEqual(domain.status(ledger, records)["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE",
                         "The example record is for SHB-04-adapter, not this task")
        mine = dict(EVIDENCE, task_id="ACCEPT-SYN-001")
        (records / "hil.json").write_text(json.dumps(mine), encoding="utf-8")
        self.assertEqual(domain.status(ledger, records)["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE",
                         "A record with a different digest is not the attested one")

    def test_machine_only_acceptance_never_earns_hardware_status(self):
        ledger, _ = self.start()
        self.checked(ledger)
        acceptance.accept(ledger, CONTROLLER)
        earned = domain.status(ledger)
        self.assertEqual(earned["ledger_status"], "ACCEPTED")
        self.assertEqual(earned["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertIn("No validation reaches a hardware rung", earned["reason"])
        self.assertEqual(earned["highest_level_satisfied"], "unit")

    def test_not_hardware_facing_packet_reports_that(self):
        contract = example()
        contract["domain"].update(hardware_assumptions=[], protocol_references=[], hardware_status="NOT_HARDWARE_FACING")
        ledger, _ = self.start(packet=make_packet(contract))
        self.assertEqual(domain.status(ledger)["earned_hardware_status"], "NOT_HARDWARE_FACING")

    def test_status_refuses_another_profile(self):
        contract = wp.read_json(ROOT / "examples/work-packets/family-law.contract.json")
        packet = wp.create("LEGAL-SYN-001", "family-law", contract, "Architect", "Synthetic")
        for target, role, actor in (("ARCHITECTED", "architect", "Architect"), ("READY", "architect", "Architect"),
                                    ("IN_PROGRESS", "worker", "Worker"), ("VALIDATING", "worker", "Worker"),
                                    ("REVIEW", "worker", "Worker")):
            packet = wp.transition(packet, target, role, actor, "Synthetic", ["synthetic-state-evidence"])
        ledger, _ = self.start(packet=packet)
        with self.assertRaisesRegex(ValueError, "not software-hardware"):
            domain.status(ledger)


class ExampleProjectTests(AcceptanceBase):
    def packet_for(self, name, risk=None):
        contract = local_argv(wp.read_json(EXAMPLES / "packets" / f"{name}.contract.json"))
        if risk:
            contract["risk"] = risk
        contract["dependencies"] = []
        return make_packet(contract)

    def test_sample_suites_pass_with_this_interpreter(self):
        completed = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                                   cwd=EXAMPLES / "sample", capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Ran 27 tests", completed.stderr)

    def test_deterministic_gate_reexecutes_the_codec_packet_commands(self):
        ledger, _ = self.start(packet=self.packet_for("SHB-01-codec"))
        outcome = acceptance.run_checks(ledger, EXAMPLES)
        self.assertTrue(outcome["satisfied"], outcome)
        self.assertEqual(outcome["deterministic"], {"VAL-UNIT": "PASSED", "VAL-CONTRACT": "PASSED"})
        acceptance.accept(ledger, CONTROLLER)
        self.assertEqual(domain.status(ledger)["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")

    def test_adapter_packet_splits_the_fake_port_run_from_the_physical_read(self):
        # Risk lowered to exercise the deterministic gate alone; the real packet is high risk.
        ledger, _ = self.start(packet=self.packet_for("SHB-04-adapter", risk="low"))
        outcome = acceptance.run_checks(ledger, EXAMPLES)
        self.assertFalse(outcome["satisfied"])
        self.assertEqual(outcome["deterministic"], {"VAL-UNIT-ADAPTER": "PASSED", "VAL-HIL": "NEEDS_ATTESTATION"})
        with self.assertRaisesRegex(ValueError, "Deterministic gate unsatisfied"):
            acceptance.accept(ledger, CONTROLLER)
        record = dict(EVIDENCE, task_id="ACCEPT-SYN-001")
        acceptance.append(ledger, "ATTESTATION",
                          {"attestation": {"validation_id": "VAL-HIL", "operator": record["operator"],
                                           "evidence": domain.evidence_lines(record)}},
                          previous_state=acceptance.replay(ledger))
        acceptance.accept(ledger, CONTROLLER)
        records = self.directory / "records"
        records.mkdir()
        (records / "run.json").write_text(json.dumps(record), encoding="utf-8")
        earned = domain.status(ledger, records)
        self.assertEqual(earned["earned_hardware_status"], "VERIFIED_ON_HARDWARE")
        self.assertTrue(next(v for v in earned["validations"] if v["validation_id"] == "VAL-HIL")["evidence_verified"])

    def test_high_risk_adapter_packet_needs_cross_family_review_as_well(self):
        ledger, packet = self.start(packet=self.packet_for("SHB-04-adapter"))
        acceptance.run_checks(ledger, EXAMPLES)
        record = dict(EVIDENCE, task_id="ACCEPT-SYN-001")
        acceptance.append(ledger, "ATTESTATION",
                          {"attestation": {"validation_id": "VAL-HIL", "operator": record["operator"],
                                           "evidence": domain.evidence_lines(record)}},
                          previous_state=acceptance.replay(ledger))
        with self.assertRaisesRegex(ValueError, "model_review"):
            acceptance.accept(ledger, "Independent reviewer")
        prepared = self.open_review(ledger)
        packet_text = json.dumps(wp.read_json(prepared["packet"]))
        self.assertIn("hardware_in_loop", packet_text)
        self.assertIn(domain.DIGEST_PREFIX, packet_text)
        self.ingest(ledger, make_report(prepared, wp.current(packet)["contract"]))
        acceptance.accept(ledger, "Independent reviewer")
        self.assertEqual(domain.status(ledger)["earned_hardware_status"], "VERIFIED_ON_HARDWARE")


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args, ok=True):
        completed = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                                   cwd=ROOT, encoding="utf-8")
        if ok:
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(completed.stdout)
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn("Domain rule refused", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        return completed.stderr

    def test_validate_contract_and_hardware_evidence_commands(self):
        result = self.run_cli("validate-contract", ROOT / "examples/work-packets/software-hardware.contract.json")
        self.assertEqual(result["declared_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertIn("no hardware behavior is established", result["note"])
        result = self.run_cli("hardware-evidence", EXAMPLES / "hardware-evidence.example.json", "--validation-id", "VAL-HIL")
        self.assertEqual(result["attest_evidence"][0], domain.DIGEST_PREFIX + result["digest"])
        self.run_cli("hardware-evidence", EXAMPLES / "hardware-evidence.example.json", "--validation-id", "VAL-OTHER", ok=False)
        with tempfile.TemporaryDirectory() as temporary:
            broken = Path(temporary) / "broken.json"
            contract = example()
            contract["domain"]["hardware_status"] = "VERIFIED_ON_HARDWARE"
            broken.write_text(json.dumps(contract), encoding="utf-8")
            self.assertIn("hardware_status", self.run_cli("validate-contract", broken, ok=False))


class BootstrapIntakeTests(unittest.TestCase):
    def test_intake_requires_the_hardware_orientation_fields(self):
        import validate_bootstrap
        fields = validate_bootstrap.DOMAIN_FIELDS[PROFILE]
        for key in ("hardware_identity", "interfaces", "specifications", "environment", "known_paths",
                    "validation_resources", "physical_access", "architecture_boundaries", "baseline"):
            self.assertIn(key, fields)
        data = wp.read_json(ROOT / "config/bootstrap.example.json")
        self.assertEqual(validate_bootstrap.activation_errors(data), [])
        data["domain"]["physical_access"] = "TBD"
        self.assertTrue(any("domain.physical_access" in e for e in validate_bootstrap.activation_errors(data)))


if __name__ == "__main__":
    unittest.main()
