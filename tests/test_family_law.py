"""Family-law domain rules: allegations and inferences never become verified fact by repetition."""
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
                             make_artifact, make_result)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("family_law_under_test", ROOT / "scripts/family_law.py")
domain = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(domain)
wp = acceptance.wp
PROFILE = "family-law"
EXAMPLES = ROOT / "examples/family-law"
PACKET_FILES = sorted((EXAMPLES / "packets").glob("*.contract.json"))
RECORD = wp.read_json(EXAMPLES / "source-record.example.json")
SCRIPT = ROOT / "scripts/family_law.py"
PASS_ARGV = [sys.executable, "-c", "raise SystemExit(0)"]


def live(record=None, **changes):
    """`record` (default RECORD) with `observed_at` refreshed to now: an attested observation must
    fall between the ledger's current submission and the attestation itself, and RECORD's fixed
    illustrative date always predates any ledger this suite builds moments later."""
    return dict(RECORD if record is None else record, observed_at=wp.now(), **changes)


def live_lines(record=None, **changes):
    """The attestation lines for `live(record, **changes)`, always declaring outcome=supports
    unless overridden -- the happy path for earning VERIFIED_FACT."""
    merged = live(record, **changes)
    if "outcome" not in changes:
        merged["outcome"] = "supports"
    return domain.evidence_lines(merged)


def example():
    return wp.read_json(ROOT / "examples/work-packets/family-law.contract.json")


def errors_for(contract):
    return wp.validate_contract(contract, PROFILE)


def local_argv(contract):
    """Run the example packets' declared commands with this interpreter instead of PATH's python."""
    value = copy.deepcopy(contract)
    for check in value["validation"]:
        if "command" in check:
            check["command"]["argv"][0] = sys.executable
    return value


def custody_contract():
    """FAM-03-custody, ready to run: this interpreter on its structural rung, no dependencies, and
    `low` risk so these unit tests exercise the domain module's own logic without also having to
    satisfy the full multi-gate review flow the packet's real `high` risk would require."""
    value = local_argv(wp.read_json(EXAMPLES / "packets/FAM-03-custody.contract.json"))
    value["dependencies"] = []
    value["risk"] = "low"
    return value


def two_source_rung_contract():
    """`custody_contract()` with a second, independent primary_source_verified check added -- a
    record explicitly bound to one check must not verify a different one at the same rung, even
    though both share the submission, artifact and operator."""
    value = custody_contract()
    value["acceptance_criteria"].append(
        {"id": "AC-SECOND", "description": "A second, independent allegation was checked against its own source."})
    value["validation"].append({"id": "VAL-SECOND-REVIEW", "description": "Review a second, unrelated allegation.",
                                "criterion_ids": ["AC-SECOND"],
                                "evidence_required": ["A second source verification record."]})
    value["domain"]["validation_levels"]["VAL-SECOND-REVIEW"] = "primary_source_verified"
    return value


def make_packet(contract=None, state="REVIEW"):
    contract = contract or custody_contract()
    value = wp.create("ACCEPT-FAM-001", "family-law", contract, "Architect", "Synthetic acceptance fixture")
    for target, role, actor in (
        ("ARCHITECTED", "architect", "Architect"), ("READY", "architect", "Architect"),
        ("IN_PROGRESS", "worker", "Worker"), ("VALIDATING", "worker", "Worker"),
        ("REVIEW", "worker", "Worker"),
    ):
        value = wp.transition(value, target, role, actor, "Synthetic state assertion", ["synthetic-state-evidence"])
        if target == state:
            return value
    return value


class ContractRuleTests(unittest.TestCase):
    def test_example_contracts_satisfy_the_domain_rules(self):
        for path in PACKET_FILES:
            with self.subTest(packet=path.name):
                self.assertEqual(errors_for(wp.read_json(path)), [])

    def test_work_packet_fixture_satisfies_the_domain_rules(self):
        self.assertEqual(errors_for(example()), [])

    def test_domain_rules_apply_only_to_the_registered_profile(self):
        broken = example()
        broken["domain"] = {"synthetic": True}
        self.assertEqual(wp.validate_contract(broken, "civil-rights-nc"), [])
        self.assertTrue(any(e.startswith("domain:") for e in errors_for(broken)))
        self.assertIsNone(wp.domain_module("civil-rights-nc"))

    def test_domain_block_is_closed_and_extension_properties_are_refused(self):
        contract = example()
        contract["domain"]["notes"] = "Not part of the closed block"
        self.assertTrue(any("Additional properties" in e for e in errors_for(contract)))

    def test_verified_fact_is_refused_wherever_it_appears(self):
        contract = custody_contract()
        contract["domain"]["fact_basis"] = "VERIFIED_FACT"
        self.assertTrue(any("earned in the acceptance ledger" in e for e in errors_for(contract)))
        contract = custody_contract()
        contract["domain"]["fact_assertions"][0]["assertion"] += " (already VERIFIED_FACT per the author)"
        self.assertTrue(any("earned in the acceptance ledger" in e for e in errors_for(contract)))

    def test_machine_rung_requires_a_command_and_source_rung_forbids_one(self):
        contract = custody_contract()
        del contract["validation"][0]["command"]
        self.assertTrue(any("must declare a command" in e for e in errors_for(contract)))
        contract = custody_contract()
        contract["validation"][1]["command"] = {"argv": list(PASS_ARGV)}
        self.assertTrue(any("must not declare a command" in e for e in errors_for(contract)))

    def test_every_validation_is_mapped_to_exactly_one_rung(self):
        contract = custody_contract()
        del contract["domain"]["validation_levels"]["VAL-TRANSCRIPT-REVIEW"]
        self.assertTrue(any("unmapped" in e for e in errors_for(contract)))
        contract = custody_contract()
        contract["domain"]["validation_levels"]["VAL-EXTRA"] = "structural"
        self.assertTrue(any("does not declare" in e for e in errors_for(contract)))

    def test_fact_assertions_and_source_references_cite_contract_sources(self):
        contract = custody_contract()
        contract["domain"]["fact_assertions"][0]["source_id"] = "SRC-UNKNOWN"
        self.assertTrue(any("unknown source" in e for e in errors_for(contract)))
        contract = custody_contract()
        contract["domain"]["source_references"].append("SRC-UNKNOWN")
        self.assertTrue(any("unknown source" in e for e in errors_for(contract)))

    def test_fact_basis_status_follows_from_declared_fact_assertions(self):
        contract = custody_contract()
        contract["domain"]["fact_basis"] = "NOT_FACT_ASSERTING"
        self.assertTrue(any(f"is {domain.UNVERIFIED}" in e for e in errors_for(contract)))
        contract = wp.read_json(EXAMPLES / "packets/FAM-01-docket.contract.json")
        contract["domain"]["fact_basis"] = "UNVERIFIED_FACT"
        self.assertTrue(any(f"is {domain.NOT_ASSERTING}" in e for e in errors_for(contract)))

    def test_a_packet_with_no_fact_assertions_cannot_carry_a_primary_source_check(self):
        contract = wp.read_json(EXAMPLES / "packets/FAM-01-docket.contract.json")
        contract["domain"]["validation_levels"]["VAL-STRUCTURE"] = "primary_source_verified"
        del contract["validation"][0]["command"]
        self.assertTrue(any("cannot carry a primary-source check" in e for e in errors_for(contract)))

    def test_legal_proposition_requires_adverse_authority(self):
        contract = wp.read_json(EXAMPLES / "packets/FAM-04-issue-brief.contract.json")
        del contract["domain"]["adverse_authority"]
        self.assertTrue(any("adverse_authority" in e for e in errors_for(contract)))

    def test_rules_reach_packet_validation_and_acceptance_init(self):
        packet = make_packet(custody_contract())
        broken = copy.deepcopy(packet)
        latest = broken["revision_history"][-1]
        latest["contract"]["domain"]["fact_basis"] = "VERIFIED_FACT"
        latest["hash"] = wp.fingerprint(broken["task_id"], PROFILE, latest["version"], latest["contract"])
        for event in broken["events"]:
            event["contract_hash"] = latest["hash"]
        # A stored revision replays and is reported (ADR-037); authoring it is refused.
        self.assertEqual(wp.validate(broken), [])
        self.assertTrue(any("domain:" in e for e in wp.domain_shortfall(broken)[1]))
        with self.assertRaisesRegex(ValueError, "domain:"):
            wp.create("WP-NEW", PROFILE, latest["contract"], "Architect", "Synthetic")
        with self.assertRaisesRegex(ValueError, "domain:"):
            wp.revise(make_packet(custody_contract()), latest["contract"], "Architect", "Synthetic")
        with self.assertRaisesRegex(ValueError, "domain:"):
            acceptance.initialize(Path(tempfile.mkdtemp()) / "ledger", wp.read_json(ROOT / "config/acceptance.example.json"),
                                  broken, make_result(broken), make_artifact(), CONTROLLER, ARCHITECT, IMPLEMENTERS, [])

    def test_packet_authored_before_the_domain_rules_can_still_be_transitioned_and_revised(self):
        # A packet whose stored revision carries the formerly valid free-form domain block must
        # not be stranded; it replays, its shortfall is named, it can be transitioned, and it can
        # be revised into compliance -- but not into another non-compliant revision.
        legacy = example()
        legacy["domain"] = {"synthetic": True, "note": "Pre-#10 free-form extension data"}
        packet = make_packet(custody_contract())
        stored = copy.deepcopy(packet)
        stored["revision_history"][0]["contract"] = legacy
        stored["revision_history"][0]["hash"] = wp.fingerprint(stored["task_id"], PROFILE, 1, legacy)
        for event in stored["events"]:
            event["contract_hash"] = stored["revision_history"][0]["hash"]
        self.assertEqual(wp.validate(stored), [])
        self.assertIn(1, wp.domain_shortfall(stored))
        self.assertTrue(any("'workstream' is a required property" in e for e in wp.domain_shortfall(stored)[1]))
        moved = wp.transition(stored, "ACCEPTED", "reviewer", "Reviewer", "Synthetic", ["synthetic-state-evidence"])
        self.assertEqual(moved["state"], "ACCEPTED")
        with self.assertRaisesRegex(ValueError, "domain:"):
            wp.revise(stored, dict(legacy, title="Still non-compliant"), "Architect", "Synthetic")
        repaired = wp.revise(stored, example(), "Architect", "Brought under the domain rules")
        self.assertEqual(wp.domain_shortfall(repaired), {1: wp.domain_shortfall(stored)[1]})
        self.assertEqual(wp.validate(repaired), [])
        self.assertIn("DOMAIN SHORTFALL", wp.render(stored))
        self.assertIn("'workstream' is a required property", wp.render(stored))


class SourceRecordTests(unittest.TestCase):
    def test_example_record_is_bound_to_the_packet_file_it_documents(self):
        contract = wp.read_json(EXAMPLES / "packets/FAM-03-custody.contract.json")
        packet = wp.create(RECORD["task_id"], "family-law", contract, "Architect", "Synthetic")
        self.assertEqual(RECORD["contract_hash"], wp.current(packet)["hash"])

    def test_example_record_validates_and_its_lines_bind_the_digest(self):
        digest = domain.evidence_digest(RECORD)
        lines = domain.evidence_lines(RECORD)
        self.assertEqual(lines[0], domain.DIGEST_PREFIX + digest)
        self.assertEqual(len(lines), 1 + len(domain.EVIDENCE_KEYS))

    def test_record_loader_refuses_duplicate_keys_and_impossible_timestamps(self):
        text = json.dumps(RECORD).replace('"outcome": "contradicts"', '"outcome": "contradicts", "outcome": "supports"')
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            domain.load_record(text)
        broken = dict(RECORD, observed_at="2026-99-99T00:00:00Z")
        with self.assertRaises(ValueError):
            domain.validate_source_record(broken)

    def test_record_shape_is_closed(self):
        broken = dict(RECORD, extra_field="Not in the schema")
        with self.assertRaisesRegex(ValueError, "Additional properties"):
            domain.validate_source_record(broken)

    def test_digest_changes_with_any_field(self):
        base = domain.evidence_digest(RECORD)
        for field in ("citation", "outcome", "observed_at", "operator"):
            with self.subTest(field=field):
                changed = dict(RECORD, **{field: RECORD[field] + " (changed)"})
                self.assertNotEqual(domain.evidence_digest(changed), base)


class AttestationRuleTests(AcceptanceBase):
    def custody_ledger(self):
        ledger, packet = self.start(packet=make_packet(custody_contract()))
        self.checked(ledger)
        return ledger

    def attest(self, ledger, operator, evidence, validation_id="VAL-TRANSCRIPT-REVIEW"):
        return acceptance.append(ledger, "ATTESTATION",
                                 {"attestation": {"validation_id": validation_id, "operator": operator, "evidence": evidence}},
                                 previous_state=acceptance.replay(ledger))

    def test_attestation_is_refused_for_a_result_or_artifact_it_was_not_observed_against(self):
        ledger = self.custody_ledger()
        for field, other in (("dispatch_id", "f" * 64), ("artifact_sha256", "0" * 64)):
            with self.subTest(field=field):
                record = live(**{field: other})
                with self.assertRaisesRegex(ValueError, "ledger's current"):
                    self.attest(ledger, record["operator"], domain.evidence_lines(record))

    def test_supporting_review_earns_verified_fact_when_not_synthetic(self):
        contract = custody_contract()
        del contract["domain"]["synthetic"]
        ledger, packet = self.start(packet=make_packet(contract))
        self.checked(ledger)
        record = live(task_id="ACCEPT-FAM-001", contract_hash=wp.current(packet)["hash"], outcome="supports")
        self.attest(ledger, record["operator"], domain.evidence_lines(record))
        acceptance.accept(ledger, CONTROLLER)
        self.assertEqual(domain.status(ledger)["earned_fact_basis"], "VERIFIED_FACT")
        records = self.directory / "records"
        records.mkdir()
        (records / "run.json").write_text(json.dumps(record), encoding="utf-8")
        checked = domain.status(ledger, records)
        self.assertEqual((checked["earned_fact_basis"], checked["evidence_basis"]), ("VERIFIED_FACT", "record"))
        self.assertEqual(checked["highest_level_satisfied"], "primary_source_verified")

    def test_attestation_is_refused_for_a_different_validation_at_the_same_rung(self):
        ledger, _ = self.start(packet=make_packet(two_source_rung_contract()))
        self.checked(ledger)
        record = live()
        with self.assertRaisesRegex(ValueError, "recorded for VAL-TRANSCRIPT-REVIEW but this attestation is for VAL-SECOND-REVIEW"):
            self.attest(ledger, record["operator"], live_lines(record), validation_id="VAL-SECOND-REVIEW")
        state = self.attest(ledger, record["operator"], live_lines(record))
        self.assertEqual(acceptance.deterministic_status(state)["VAL-TRANSCRIPT-REVIEW"], "ATTESTED")
        self.assertEqual(acceptance.deterministic_status(state)["VAL-SECOND-REVIEW"], "NEEDS_ATTESTATION")

    def test_primary_source_attestation_must_bind_a_well_formed_record(self):
        ledger = self.custody_ledger()
        lines = live_lines()
        operator = RECORD["operator"]
        with self.assertRaisesRegex(ValueError, "must carry exactly one"):
            self.attest(ledger, operator, ["Read the transcript"])
        with self.assertRaisesRegex(ValueError, "must carry exactly one"):
            self.attest(ledger, operator, lines + [lines[0]])
        with self.assertRaisesRegex(ValueError, "must carry the bound record's"):
            self.attest(ledger, operator, [lines[0]])
        with self.assertRaisesRegex(ValueError, "recorded at "):
            self.attest(ledger, operator, [line.replace("level=primary_source_verified", "level=structural") for line in lines])
        with self.assertRaisesRegex(ValueError, "operator who reviewed"):
            self.attest(ledger, "Someone else", lines)
        with self.assertRaisesRegex(ValueError, "cannot attest its own"):
            self.attest(ledger, "Worker", [line.replace("operator=" + operator, "operator=Worker") for line in lines])
        with self.assertRaisesRegex(ValueError, "is after the attestation recording it"):
            self.attest(ledger, operator,
                       ["observed_at=2099-01-01T00:00:00Z" if line.startswith("observed_at=") else line
                        for line in lines])
        state = self.attest(ledger, operator, lines)
        self.assertTrue(acceptance.deterministic_satisfied(state))
        self.assertEqual(acceptance.deterministic_status(state)["VAL-TRANSCRIPT-REVIEW"], "ATTESTED")

    def test_attestation_carries_nothing_but_the_record_lines(self):
        ledger = self.custody_ledger()
        for extra in (" outcome=supports", "outcome =supports", "OUTCOME=supports", "note: read by hand", "unknown=value"):
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(ValueError, "every line is verified, so these are refused"):
                    self.attest(ledger, RECORD["operator"], live_lines() + [extra])

    def test_contradictory_duplicate_line_is_refused_at_attestation(self):
        ledger = self.custody_ledger()
        lines = live_lines() + ["outcome=contradicts"]
        with self.assertRaisesRegex(ValueError, "more than one outcome= line"):
            self.attest(ledger, RECORD["operator"], lines)

    def test_runnable_check_is_still_executed_never_attested(self):
        ledger, _ = self.start(packet=make_packet(custody_contract()))
        self.checked(ledger)
        with self.assertRaisesRegex(ValueError, "executed, never attested"):
            self.attest(ledger, RECORD["operator"], live_lines(), validation_id="VAL-DECLARED-STATUS")

    def test_contradicting_review_reports_contradicted_by_source_not_verified(self):
        contract = custody_contract()
        del contract["domain"]["synthetic"]
        ledger, packet = self.start(packet=make_packet(contract))
        self.checked(ledger)
        record = live(task_id="ACCEPT-FAM-001", contract_hash=wp.current(packet)["hash"], outcome="contradicts")
        self.attest(ledger, record["operator"], domain.evidence_lines(record))
        acceptance.accept(ledger, CONTROLLER)
        report = domain.status(ledger)
        self.assertEqual(report["earned_fact_basis"], "CONTRADICTED_BY_SOURCE")
        # The packet's structural rung genuinely passed; only the contradicted source rung is
        # excluded from what counts as satisfied.
        self.assertEqual(report["highest_level_satisfied"], "structural")

    def test_inconclusive_review_does_not_earn_verified_fact(self):
        contract = custody_contract()
        del contract["domain"]["synthetic"]
        ledger, packet = self.start(packet=make_packet(contract))
        self.checked(ledger)
        record = live(task_id="ACCEPT-FAM-001", contract_hash=wp.current(packet)["hash"], outcome="inconclusive")
        self.attest(ledger, record["operator"], domain.evidence_lines(record))
        acceptance.accept(ledger, CONTROLLER)
        report = domain.status(ledger)
        self.assertEqual(report["earned_fact_basis"], "UNVERIFIED_FACT")
        self.assertIn("inconclusive", report["reason"])

    def test_synthetic_contract_never_earns_verified_fact_even_fully_attested(self):
        ledger = self.custody_ledger()
        record = live(task_id="ACCEPT-FAM-001")
        self.attest(ledger, record["operator"], live_lines(record))
        acceptance.accept(ledger, CONTROLLER)
        earned = domain.status(ledger)
        self.assertIn("synthetic: true", earned["reason"])
        # The structural rung still counts; only the synthetic source rung is excluded.
        self.assertEqual(earned["highest_level_satisfied"], "structural")
        self.assertEqual(earned["validations"][0]["gate"], "PASSED")

    def test_machine_only_acceptance_never_earns_fact_status(self):
        contract = custody_contract()
        del contract["validation"][1]  # remove the primary-source rung entirely
        contract["acceptance_criteria"] = [c for c in contract["acceptance_criteria"] if c["id"] != "AC-REVIEWED"]
        del contract["domain"]["fact_assertions"][0]
        contract["domain"]["fact_basis"] = "NOT_FACT_ASSERTING"
        del contract["domain"]["validation_levels"]["VAL-TRANSCRIPT-REVIEW"]
        # A NOT_FACT_ASSERTING contract with only a machine rung reports that declared status.
        ledger, _ = self.start(packet=make_packet(contract))
        self.checked(ledger)
        acceptance.accept(ledger, CONTROLLER)
        earned = domain.status(ledger)
        self.assertEqual(earned["earned_fact_basis"], "NOT_FACT_ASSERTING")

    def test_status_refuses_another_profile(self):
        contract = wp.read_json(ROOT / "examples/work-packets/software-hardware.contract.json")
        packet = wp.create("HW-SYN-001", "software-hardware", contract, "Architect", "Synthetic")
        for target, role, actor in (("ARCHITECTED", "architect", "Architect"), ("READY", "architect", "Architect"),
                                    ("IN_PROGRESS", "worker", "Worker"), ("VALIDATING", "worker", "Worker"),
                                    ("REVIEW", "worker", "Worker")):
            packet = wp.transition(packet, target, role, actor, "Synthetic", ["synthetic-state-evidence"])
        ledger, _ = self.start(packet=packet)
        with self.assertRaisesRegex(ValueError, "not family-law"):
            domain.status(ledger)


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

    def test_validate_contract_and_source_record_commands(self):
        result = self.run_cli("validate-contract", ROOT / "examples/work-packets/family-law.contract.json")
        self.assertEqual(result["declared_fact_basis"], "NOT_FACT_ASSERTING")
        self.assertIn("no fact is established", result["note"])
        result = self.run_cli("source-record", EXAMPLES / "source-record.example.json",
                              "--validation-id", "VAL-TRANSCRIPT-REVIEW")
        self.assertEqual(result["attest_evidence"][0], domain.DIGEST_PREFIX + result["digest"])
        self.run_cli("source-record", EXAMPLES / "source-record.example.json", "--validation-id", "VAL-OTHER", ok=False)
        with tempfile.TemporaryDirectory() as temporary:
            broken = Path(temporary) / "broken.json"
            contract = example()
            contract["domain"]["fact_basis"] = "VERIFIED_FACT"
            broken.write_text(json.dumps(contract), encoding="utf-8")
            self.assertIn("fact_basis", self.run_cli("validate-contract", broken, ok=False))

    def test_status_command_names_its_evidence_basis(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            contract = custody_contract()
            del contract["domain"]["synthetic"]
            packet = make_packet(contract)
            ledger = base / "ledger"
            acceptance.initialize(ledger, wp.read_json(ROOT / "config/acceptance.example.json"), packet,
                                  make_result(packet), make_artifact(), CONTROLLER, ARCHITECT, IMPLEMENTERS, [])
            acceptance.run_checks(ledger, base)
            record = live(task_id="ACCEPT-FAM-001", contract_hash=wp.current(packet)["hash"], outcome="supports")
            acceptance.append(ledger, "ATTESTATION",
                              {"attestation": {"validation_id": "VAL-TRANSCRIPT-REVIEW", "operator": record["operator"],
                                               "evidence": domain.evidence_lines(record)}},
                              previous_state=acceptance.replay(ledger))
            acceptance.accept(ledger, CONTROLLER)
            attested = self.run_cli("status", ledger)
            self.assertEqual(attested["evidence_basis"], "attestation")
            self.assertEqual(attested["earned_fact_basis"], "VERIFIED_FACT")
            records = base / "records"
            records.mkdir()
            empty = self.run_cli("status", ledger, "--evidence-dir", records)
            self.assertIn("no source verification record with the attested digest", empty["reason"])
            (records / "run.json").write_text(json.dumps(record), encoding="utf-8")
            verified = self.run_cli("status", ledger, "--evidence-dir", records)
            self.assertEqual(verified["evidence_basis"], "record")
            self.assertEqual(verified["earned_fact_basis"], "VERIFIED_FACT")


class BootstrapIntakeTests(unittest.TestCase):
    def test_intake_requires_the_family_law_orientation_fields(self):
        import validate_bootstrap
        fields = validate_bootstrap.DOMAIN_FIELDS[PROFILE]
        for key in ("case_identity", "controlling_orders", "objectives_and_deadlines", "discovery", "evidence",
                    "financial_support", "parenting_custody", "adverse_facts", "appellate_preservation",
                    "reserved_actions"):
            self.assertIn(key, fields)
        data = wp.read_json(ROOT / "tests/fixtures/bootstrap-family-law-awaiting.json")
        self.assertEqual(validate_bootstrap.activation_errors(data), [])
        data["domain"]["adverse_facts"] = "TBD"
        self.assertTrue(any("domain.adverse_facts" in e for e in validate_bootstrap.activation_errors(data)))


if __name__ == "__main__":
    unittest.main()
