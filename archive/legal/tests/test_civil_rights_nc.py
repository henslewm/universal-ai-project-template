"""Civil-rights-nc domain rules: claim matrices over id-bound assertions, earned from the ledger."""
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
                             make_artifact, make_report, make_result)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("civil_rights_nc_under_test", ROOT / "scripts/civil_rights_nc.py")
domain = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(domain)
wp = acceptance.wp
PROFILE = "civil-rights-nc"
EXAMPLES = ROOT / "examples/civil-rights-nc"
PACKET_FILES = sorted((EXAMPLES / "packets").glob("*.contract.json"))
RECORD = wp.read_json(EXAMPLES / "source-record.example.json")
SCRIPT = ROOT / "scripts/civil_rights_nc.py"
PASS_ARGV = [sys.executable, "-c", "raise SystemExit(0)"]
TASK = "ACCEPT-CRN-001"
# The minimal claim fixture: each primary-source check, the assertion it verifies, and the declared
# source (with its type) whose review can verify that assertion.
TARGETS = {"VAL-ROLE": "AS-ROLE", "VAL-RULE": "AS-RULE", "VAL-FACT": "AS-FACT", "VAL-ADVERSE": "AS-ADVERSE"}
READ_FROM = {"VAL-ROLE": ("SRC-RECORD", "official_record"), "VAL-RULE": ("SRC-CODE", "statute"),
             "VAL-FACT": ("SRC-RECORD", "official_record"), "VAL-ADVERSE": ("SRC-ADVERSE", "case_law")}


def packet_json(name):
    return wp.read_json(EXAMPLES / "packets" / f"{name}.contract.json")


def example():
    return wp.read_json(ROOT / "examples/work-packets/civil-rights-nc.contract.json")


def errors_for(contract):
    return wp.validate_contract(contract, PROFILE)


def local_argv(contract):
    """Run the example packets' declared commands with this interpreter instead of PATH's python."""
    value = copy.deepcopy(contract)
    for check in value["validation"]:
        if "command" in check:
            check["command"]["argv"][0] = sys.executable
    return value


def minimal_contract():
    """One fully verifiable fictional claim: every assertion it rests on has a primary-source check."""
    value = copy.deepcopy(packet_json("CRN-02-federal-individual"))
    value["sources"] = [
        {"id": "SRC-COMPLAINT", "reference": "Fictional complaint (no such filing exists).", "authority": "Fictional allegations."},
        {"id": "SRC-RECORD", "reference": "Fictional official record (no such record exists).", "authority": "Fictional record."},
        {"id": "SRC-CODE", "reference": "Fictional Synthetic Civil Rights Code (no such code exists).", "authority": "Fictional statute."},
        {"id": "SRC-ADVERSE", "reference": "Fictional Roe v. Placeholder (no such case exists).", "authority": "Fictional adverse case."},
    ]
    value["acceptance_criteria"] = [{"id": "AC-MATRIX", "description": "The claim matrix is structured."},
                                    {"id": "AC-READ", "description": "Every assertion the claim rests on is read."}]
    value["validation"] = [{"id": "VAL-STRUCTURE", "description": "Structural check.", "criterion_ids": ["AC-MATRIX"],
                            "evidence_required": ["Structure result."], "command": {"argv": list(PASS_ARGV)}}]
    value["validation"] += [{"id": identifier, "description": f"A non-implementer reads the source for {target}.",
                             "criterion_ids": ["AC-READ"], "evidence_required": ["A source verification record."]}
                            for identifier, target in TARGETS.items()]
    value["domain"] = {
        "workstream": "federal_1983", "forum": "Fictional Synthetic District Court.",
        "procedural_posture": "Fictional pre-filing research.", "claim_basis": "UNVERIFIED_CLAIM",
        "defendants": [{"id": "DEF-A", "identity": "Officer A (fictional)", "role": "Fictional officer.",
                        "kind": "natural_person", "capacities": ["individual"], "assertion_ids": ["AS-ROLE"]}],
        "assertions": [
            {"id": "AS-ROLE", "assertion": "Officer A was on duty on the fictional date.", "fact_status": "ALLEGATION",
             "source_id": "SRC-COMPLAINT", "verified_by": ["SRC-RECORD"]},
            {"id": "AS-RULE", "assertion": "Fictional code section 1 states the elements.", "fact_status": "LEGAL_PROPOSITION",
             "source_id": "SRC-CODE", "verified_by": ["SRC-CODE"]},
            {"id": "AS-FACT", "assertion": "Officer A detained the plaintiff without a warrant.", "fact_status": "DISPUTED_FACT",
             "source_id": "SRC-COMPLAINT", "verified_by": ["SRC-RECORD"]},
            {"id": "AS-ADVERSE", "assertion": "Fictional Roe v. Placeholder grants officers immunity.", "fact_status": "LEGAL_PROPOSITION",
             "source_id": "SRC-ADVERSE", "verified_by": ["SRC-ADVERSE"]},
        ],
        "claims": [{
            "id": "CLM-A", "statement": "Officer A individually detained the plaintiff without a warrant.",
            "legal_question": "Does the fictional detention state a claim against Officer A individually?",
            "defendant_id": "DEF-A", "capacity": "individual", "claim_type": "FEDERAL_1983",
            "right": "Fictional stand-in right against unreasonable seizure.",
            "governing_authority": ["AS-RULE"],
            "elements": [{"id": "EL-1", "requirement": "A deprivation.", "supported_by": ["AS-FACT"]}],
            "missing_evidence": [],
            "threshold_defenses": [{"id": "TD-1", "category": "immunity", "defense": "Fictional immunity.",
                                    "dismissal_risk": "high", "rebuttal": "Fictional rebuttal.", "assertion_ids": ["AS-ADVERSE"]}],
            "adverse_authority": [{"id": "ADV-1", "assertion_id": "AS-ADVERSE", "dismissal_risk": "high"}],
            "remedies": [{"kind": "compensatory_damages", "description": "Fictional damages.", "assertion_ids": ["AS-FACT"]}],
            "limitations": {"accrual": "Fictional date.", "posture": "timely", "prerequisites": "None declared.",
                            "assertion_ids": ["AS-RULE"]},
            "justiciability": {"standing": "Fictional completed injury.", "mootness_and_prospective_relief": "Damages only.",
                               "assertion_ids": ["AS-RULE", "AS-FACT"]},
            "confidence": "medium", "next_action": "None; fixture.",
        }],
        "source_references": ["SRC-COMPLAINT", "SRC-RECORD", "SRC-CODE", "SRC-ADVERSE"],
        "validation_levels": {"VAL-STRUCTURE": "structural", **{identifier: "primary_source_verified" for identifier in TARGETS}},
        "validation_targets": dict(TARGETS),
    }
    return value


def claim_of(contract):
    return contract["domain"]["claims"][0]


def assertion_of(contract, identifier):
    return next(item for item in contract["domain"]["assertions"] if item["id"] == identifier)


def make_packet(contract, task_id=TASK, state="REVIEW"):
    value = wp.create(task_id, PROFILE, contract, "Architect", "Synthetic acceptance fixture")
    for target, role, actor in (
        ("ARCHITECTED", "architect", "Architect"), ("READY", "architect", "Architect"),
        ("IN_PROGRESS", "worker", "Worker"), ("VALIDATING", "worker", "Worker"),
        ("REVIEW", "worker", "Worker"),
    ):
        value = wp.transition(value, target, role, actor, "Synthetic state assertion", ["synthetic-state-evidence"])
        if target == state:
            return value
    return value


def record_for(packet, validation_id, **changes):
    """A live source verification record for `validation_id`, bound to `packet`'s current submission."""
    source_id, source_type = READ_FROM.get(validation_id, (RECORD["source_id"], RECORD["source_type"]))
    targets = wp.current(packet)["contract"]["domain"]["validation_targets"]
    value = dict(RECORD, task_id=packet["task_id"], revision=wp.current(packet)["version"],
                 contract_hash=wp.current(packet)["hash"], validation_id=validation_id,
                 assertion_id=targets.get(validation_id, RECORD["assertion_id"]), source_id=source_id,
                 source_type=source_type, outcome="supports", observed_at=wp.now())
    value.update(changes)
    return value


def has(errors, text):
    return any(text in error for error in errors)


class ContractRuleTests(unittest.TestCase):
    def mutated(self, change, contract=None):
        value = copy.deepcopy(contract or minimal_contract())
        change(value)
        return errors_for(value)

    def test_example_contracts_and_the_minimal_fixture_satisfy_the_domain_rules(self):
        self.assertEqual(len(PACKET_FILES), 4)
        for path in PACKET_FILES:
            with self.subTest(packet=path.name):
                self.assertEqual(errors_for(wp.read_json(path)), [])
                self.assertTrue(wp.read_json(path)["domain"]["synthetic"])
        self.assertEqual(errors_for(example()), [])
        self.assertEqual(errors_for(minimal_contract()), [])

    def test_domain_block_is_closed_at_every_level(self):
        for where in (lambda c: c["domain"], lambda c: claim_of(c), lambda c: c["domain"]["defendants"][0],
                      lambda c: c["domain"]["assertions"][0], lambda c: claim_of(c)["elements"][0],
                      lambda c: claim_of(c)["limitations"]):
            with self.subTest(where=where):
                self.assertTrue(has(self.mutated(lambda c: where(c).update(notes="Not declared")), "Additional properties"))

    def test_a_packet_carries_at_most_one_claim(self):
        def second(c):
            other = copy.deepcopy(claim_of(c))
            other.update(id="CLM-B", statement="A second fictional claim.")
            c["domain"]["claims"].append(other)
        self.assertTrue(has(self.mutated(second), "is too long"))

    def test_an_earned_status_is_never_authored_anywhere_in_the_block(self):
        self.assertTrue(has(self.mutated(lambda c: c["domain"].update(claim_basis="SOURCE_VERIFIED_CLAIM")),
                            "SOURCE_VERIFIED_CLAIM is earned in the acceptance ledger"))
        self.assertTrue(has(self.mutated(lambda c: claim_of(c).update(next_action="Mark it SOURCE_VERIFIED now.")),
                            "SOURCE_VERIFIED is earned in the acceptance ledger"))

    def test_machine_rung_requires_a_command_and_source_rung_forbids_one(self):
        self.assertTrue(has(self.mutated(lambda c: c["validation"][0].pop("command")), "must declare a command"))
        self.assertTrue(has(self.mutated(lambda c: c["validation"][1].update(command={"argv": list(PASS_ARGV)})),
                            "must not declare a command"))

    def test_every_validation_is_mapped_to_exactly_one_rung(self):
        self.assertTrue(has(self.mutated(lambda c: c["domain"]["validation_levels"].pop("VAL-STRUCTURE")), "unmapped: VAL-STRUCTURE"))
        self.assertTrue(has(self.mutated(lambda c: c["domain"]["validation_levels"].update({"VAL-GHOST": "structural"})),
                            "does not declare: VAL-GHOST"))

    def test_every_primary_source_check_names_one_declared_verifiable_assertion(self):
        self.assertTrue(has(self.mutated(lambda c: c["domain"]["validation_targets"].pop("VAL-FACT")), "missing: VAL-FACT"))
        self.assertTrue(has(self.mutated(lambda c: c["domain"]["validation_targets"].update({"VAL-STRUCTURE": "AS-FACT"})),
                            "not primary_source_verified: VAL-STRUCTURE"))
        self.assertTrue(has(self.mutated(lambda c: c["domain"]["validation_targets"].update({"VAL-FACT": "AS-GHOST"})),
                            "validation_targets/VAL-FACT: unknown assertion AS-GHOST"))

        def unknown_target(c):
            assertion_of(c, "AS-FACT").update(fact_status="UNKNOWN", verified_by=[])
        self.assertTrue(has(self.mutated(unknown_target), "is declared UNKNOWN; no record can verify"))

    def test_ids_and_assertion_text_are_declared_once(self):
        def duplicate_assertion_id(c):
            c["domain"]["assertions"].append(dict(assertion_of(c, "AS-FACT"), assertion="Different fictional text."))
        self.assertTrue(has(self.mutated(duplicate_assertion_id), "duplicates the id of assertions/2 (AS-FACT)"))

        def duplicate_text(c):
            c["domain"]["assertions"].append(dict(assertion_of(c, "AS-FACT"), id="AS-FACT-2"))
            claim_of(c)["elements"][0]["supported_by"].append("AS-FACT-2")
        self.assertTrue(has(self.mutated(duplicate_text), "duplicates the assertion text of assertions/2"))

        def duplicate_defendant(c):
            c["domain"]["defendants"].append(copy.deepcopy(c["domain"]["defendants"][0]))
        self.assertTrue(has(self.mutated(duplicate_defendant), "duplicates the id of defendants/0"))

        def duplicate_element(c):
            claim_of(c)["elements"].append(copy.deepcopy(claim_of(c)["elements"][0]))
        self.assertTrue(has(self.mutated(duplicate_element), "elements/1: duplicates the id"))

    def test_every_reference_resolves(self):
        self.assertTrue(has(self.mutated(lambda c: claim_of(c).update(defendant_id="DEF-GHOST")), "unknown defendant DEF-GHOST"))
        self.assertTrue(has(self.mutated(lambda c: claim_of(c)["elements"][0]["supported_by"].append("AS-GHOST")),
                            "unknown assertion AS-GHOST"))
        self.assertTrue(has(self.mutated(lambda c: c["domain"]["defendants"][0]["assertion_ids"].append("AS-GHOST")),
                            "defendants/0/assertion_ids: unknown assertion AS-GHOST"))
        self.assertTrue(has(self.mutated(lambda c: claim_of(c)["missing_evidence"].append(
            {"element_id": "EL-GHOST", "description": "Fictional gap."})), "EL-GHOST is not an element of this claim"))
        self.assertTrue(has(self.mutated(lambda c: assertion_of(c, "AS-FACT").update(source_id="SRC-GHOST")),
                            "unknown source SRC-GHOST"))
        self.assertTrue(has(self.mutated(lambda c: assertion_of(c, "AS-FACT")["verified_by"].append("SRC-GHOST")),
                            "verified_by: unknown source SRC-GHOST"))
        self.assertTrue(has(self.mutated(lambda c: c["domain"]["source_references"].append("SRC-GHOST")),
                            "source_references/4: unknown source SRC-GHOST"))

    def test_a_claim_names_one_of_its_defendants_capacities_and_capacity_follows_kind(self):
        self.assertTrue(has(self.mutated(lambda c: claim_of(c).update(capacity="official")),
                            "DEF-A is not analyzed in official capacity"))
        self.assertTrue(has(self.mutated(lambda c: c["domain"]["defendants"][0].update(capacities=["individual", "entity"])),
                            "a natural person has no entity capacity"))
        self.assertTrue(has(self.mutated(lambda c: c["domain"]["defendants"][0].update(kind="entity")),
                            "an entity is analyzed only in entity capacity"))

    def test_a_legal_proposition_is_verified_only_by_its_own_authority(self):
        self.assertTrue(has(self.mutated(lambda c: assertion_of(c, "AS-RULE")["verified_by"].append("SRC-RECORD")),
                            "verified_by must be exactly [SRC-CODE]"))
        self.assertTrue(has(self.mutated(lambda c: assertion_of(c, "AS-RULE").update(verified_by=["SRC-RECORD"])),
                            "verified_by must be exactly [SRC-CODE]"))

    def test_an_allegation_cannot_be_verified_by_the_filing_that_alleges_it(self):
        self.assertTrue(has(self.mutated(lambda c: assertion_of(c, "AS-ROLE")["verified_by"].append("SRC-COMPLAINT")),
                            "an allegation cannot be verified by the filing that alleges it"))
        # A different declared source verifying an allegation stays allowed.
        self.assertEqual(self.mutated(lambda c: assertion_of(c, "AS-ROLE")["verified_by"].append("SRC-CODE")), [])

    def test_governing_and_adverse_authority_are_distinct_legal_propositions(self):
        self.assertTrue(has(self.mutated(lambda c: claim_of(c).update(governing_authority=["AS-FACT"])),
                            "governing_authority: AS-FACT is not a LEGAL_PROPOSITION"))
        self.assertTrue(has(self.mutated(lambda c: claim_of(c)["adverse_authority"][0].update(assertion_id="AS-FACT")),
                            "adverse_authority/0: AS-FACT is not a LEGAL_PROPOSITION"))
        self.assertTrue(has(self.mutated(lambda c: claim_of(c).update(governing_authority=["AS-RULE", "AS-ADVERSE"])),
                            "both governing and adverse authority: AS-ADVERSE"))

    def test_elements_rest_on_evidence_and_legal_conclusions_on_law(self):
        self.assertTrue(has(self.mutated(lambda c: claim_of(c)["elements"][0].update(supported_by=["AS-RULE"])),
                            "elements/0: an element is tied to evidence"))
        self.assertTrue(has(self.mutated(lambda c: claim_of(c)["threshold_defenses"][0].update(assertion_ids=["AS-FACT"])),
                            "threshold_defenses/0: a legal conclusion needs its legal basis"))
        self.assertTrue(has(self.mutated(lambda c: claim_of(c)["limitations"].update(assertion_ids=["AS-FACT"])),
                            "limitations: a legal conclusion needs its legal basis"))

    def test_governing_and_adverse_authority_are_each_read_by_a_primary_source_check(self):
        def untarget(c):
            c["domain"]["validation_targets"].pop("VAL-ADVERSE")
            c["domain"]["validation_levels"].pop("VAL-ADVERSE")
            c["validation"] = [v for v in c["validation"] if v["id"] != "VAL-ADVERSE"]
        self.assertTrue(has(self.mutated(untarget), "authority AS-ADVERSE must be the target of a primary_source_verified"))

    def test_claim_basis_and_sources_follow_from_the_declared_claim_and_assertions(self):
        self.assertTrue(has(self.mutated(lambda c: c["domain"].update(claim_basis="NOT_CLAIM_ASSERTING")),
                            "a packet with a claim is UNVERIFIED_CLAIM"))
        broken = example()
        broken["domain"]["claim_basis"] = "UNVERIFIED_CLAIM"
        self.assertTrue(has(errors_for(broken), "a packet with no claim is NOT_CLAIM_ASSERTING"))
        self.assertTrue(has(self.mutated(lambda c: c["domain"].update(source_references=[])),
                            "a packet with assertions must cite the sources"))
        broken = example()
        broken["validation"].append({"id": "VAL-READ", "description": "Read a fictional source.", "criterion_ids": ["AC-LINKS"],
                                     "evidence_required": ["A record."]})
        broken["domain"]["validation_levels"]["VAL-READ"] = "primary_source_verified"
        self.assertTrue(has(errors_for(broken), "a packet with no assertions cannot carry a primary-source check"))

    def test_claim_type_and_capacity_trigger_their_required_analyses(self):
        self.assertTrue(has(self.mutated(lambda c: claim_of(c).update(claim_type="NC_CORUM")),
                            "an NC_CORUM claim must analyze adequate_state_remedy"))
        corum = copy.deepcopy(minimal_contract())
        claim_of(corum).update(claim_type="NC_CORUM", adequate_state_remedy={
            "posture": "contested", "summary": "Fictional remedy question.", "assertion_ids": ["AS-ADVERSE"]})
        self.assertEqual(errors_for(corum), [])
        # Optional, never forbidden, where the trigger does not hold.
        federal = copy.deepcopy(corum)
        claim_of(federal)["claim_type"] = "FEDERAL_1983"
        self.assertEqual(errors_for(federal), [])

        def entity(c):
            c["domain"]["defendants"][0].update(kind="entity", capacities=["entity"])
            claim_of(c)["capacity"] = "entity"
        self.assertTrue(has(self.mutated(entity), "must state its entity_liability"))

    def test_an_undetermined_posture_declares_what_is_unknown(self):
        self.assertTrue(has(self.mutated(lambda c: claim_of(c)["limitations"].update(posture="undetermined")),
                            "limitations: an undetermined posture must declare what is unknown"))

        def declared(c):
            c["domain"]["assertions"].append({"id": "AS-TOLLING", "assertion": "Tolling is not yet researched.",
                                              "fact_status": "UNKNOWN", "source_id": "SRC-COMPLAINT", "verified_by": []})
            claim_of(c)["limitations"].update(posture="undetermined", assertion_ids=["AS-RULE", "AS-TOLLING"])
        self.assertEqual(self.mutated(declared), [])

    def test_legal_propositions_require_model_review_and_a_strong_reviewer(self):
        self.assertTrue(has(self.mutated(lambda c: c.update(risk="low")), "must carry at least medium risk"))
        self.assertFalse(has(self.mutated(lambda c: c.update(risk="low", review={"required_gates": ["deterministic", "model_review"]})),
                             "must carry at least medium risk"))
        self.assertTrue(has(self.mutated(lambda c: c["routing"].update(reviewer_tier=2)), "requires reviewer tier 3"))

    def test_rules_reach_packet_validation_and_acceptance_init(self):
        packet = make_packet(minimal_contract())
        broken = copy.deepcopy(packet)
        latest = broken["revision_history"][-1]
        latest["contract"]["domain"]["claim_basis"] = "NOT_CLAIM_ASSERTING"
        latest["hash"] = wp.fingerprint(broken["task_id"], PROFILE, latest["version"], latest["contract"])
        for event in broken["events"]:
            event["contract_hash"] = latest["hash"]
        # A stored revision replays and is reported (ADR-037); authoring it is refused.
        self.assertEqual(wp.validate(broken), [])
        self.assertTrue(any("domain:" in e for e in wp.domain_shortfall(broken)[1]))
        with self.assertRaisesRegex(ValueError, "domain:"):
            wp.create("WP-NEW", PROFILE, latest["contract"], "Architect", "Synthetic")
        with self.assertRaisesRegex(ValueError, "domain:"):
            wp.revise(make_packet(minimal_contract()), latest["contract"], "Architect", "Synthetic")
        with self.assertRaisesRegex(ValueError, "domain:"):
            acceptance.initialize(Path(tempfile.mkdtemp()) / "ledger", wp.read_json(ROOT / "config/acceptance.example.json"),
                                  broken, make_result(broken), make_artifact(), CONTROLLER, ARCHITECT, IMPLEMENTERS, [])

    def test_a_packet_authored_with_the_pre_module_free_form_block_replays_and_can_be_repaired(self):
        # The exact free-form block the civil-rights example carried before this profile had rules:
        # any generated project's stored packets look like this, and they must not be stranded.
        legacy = example()
        legacy["domain"] = {"synthetic": True, "record_set": "CR-NC-SYN-DEMO",
                            "jurisdiction_label": "North Carolina context label only; no jurisdiction determination.",
                            "legal_authority_status": "No legal authority asserted."}
        packet = make_packet(example())
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
        self.assertEqual(wp.validate(repaired), [])
        self.assertIn("DOMAIN SHORTFALL", wp.render(stored))


class SourceRecordTests(unittest.TestCase):
    def test_example_record_is_bound_to_its_packet(self):
        contract = packet_json("CRN-02-federal-individual")
        packet = wp.create("CRN-02-federal-individual", PROFILE, contract, "Architect", "Synthetic")
        self.assertEqual(RECORD["contract_hash"], wp.current(packet)["hash"])
        self.assertEqual(RECORD["assertion_id"], contract["domain"]["validation_targets"][RECORD["validation_id"]])
        self.assertIn(RECORD["source_id"], assertion_of(contract, RECORD["assertion_id"])["verified_by"])

    def test_evidence_lines_are_the_digest_and_every_bound_field(self):
        lines = domain.evidence_lines(RECORD)
        self.assertEqual(len(lines), 1 + len(domain.EVIDENCE_KEYS))
        self.assertEqual(len(domain.EVIDENCE_KEYS), 10)
        self.assertEqual(lines[0], domain.DIGEST_PREFIX + domain.evidence_digest(RECORD))
        self.assertIn(f"assertion_id={RECORD['assertion_id']}", lines)

    def test_duplicate_keys_impossible_timestamps_and_extra_fields_are_refused(self):
        text = json.dumps(RECORD)
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            domain.load_record(text[:-1] + ', "outcome": "contradicts"}')
        with self.assertRaisesRegex(ValueError, "observed_at"):
            domain.validate_source_record(dict(RECORD, observed_at="2026-99-99T99:99:99Z"))
        with self.assertRaisesRegex(ValueError, "Additional properties"):
            domain.validate_source_record(dict(RECORD, claim_verified="Free text binds nothing."))

    def test_digest_changes_when_any_field_changes(self):
        base = domain.evidence_digest(RECORD)
        for key in ("assertion_id", "source_id", "outcome", "contract_hash"):
            with self.subTest(key=key):
                changed = dict(RECORD, **{key: "AS-OTHER" if key == "assertion_id" else
                                          "SRC-OTHER" if key == "source_id" else
                                          "contradicts" if key == "outcome" else "0" * 64})
                self.assertNotEqual(domain.evidence_digest(changed), base)


class AttestationRuleTests(AcceptanceBase):
    def attest(self, ledger, record, validation_id=None, operator=None, evidence=None):
        return acceptance.append(ledger, "ATTESTATION", {"attestation": {
            "validation_id": validation_id or record["validation_id"], "operator": operator or record["operator"],
            "evidence": domain.evidence_lines(record) if evidence is None else evidence}},
            previous_state=acceptance.replay(ledger))

    def ready(self, contract=None):
        contract = contract or minimal_contract()
        packet = make_packet(contract)
        ledger, _ = self.start(packet=packet)
        self.checked(ledger)
        return ledger, packet

    def accepted(self, contract=None, changes=None):
        """Attest every primary-source check with a live record (overridden per check by `changes`),
        pass independent model review, accept, and return the ledger with its record directory."""
        contract = contract or minimal_contract()
        ledger, packet = self.ready(contract)
        self.counter += 1
        records = self.directory / f"records-{self.counter}"
        records.mkdir()
        for validation_id in contract["domain"]["validation_targets"]:
            record = record_for(packet, validation_id, **(changes or {}).get(validation_id, {}))
            self.attest(ledger, record)
            (records / f"{validation_id}.json").write_text(json.dumps(record), encoding="utf-8")
        if "model_review" in wp.effective_gates(contract):
            prepared = self.open_review(ledger)
            self.ingest(ledger, make_report(prepared, contract))
            acceptance.accept(ledger, prepared["reviewer"]["actor"])
        else:
            acceptance.accept(ledger, CONTROLLER)
        return ledger, records

    def claim_result(self, ledger, records=None):
        result = domain.status(ledger, records)
        self.assertEqual(len(result["claims"]), 1)
        return result, result["claims"][0]

    def test_every_example_packets_declared_commands_execute_through_the_gate(self):
        self.assertEqual(len(PACKET_FILES), 4)
        for path in PACKET_FILES + [ROOT / "examples/work-packets/civil-rights-nc.contract.json"]:
            with self.subTest(packet=path.name):
                contract = local_argv(wp.read_json(path))
                declared = [check["id"] for check in contract["validation"] if "command" in check]
                self.assertTrue(declared)
                ledger, _ = self.start(packet=make_packet(contract))
                self.checked(ledger)
                observed = acceptance.deterministic_status(self.state(ledger))
                for identifier in declared:
                    self.assertEqual(observed[identifier], "PASSED", identifier)

    def test_a_fully_read_non_synthetic_claim_earns_source_verified_claim(self):
        ledger, records = self.accepted()
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(result["earned_claim_basis"], "SOURCE_VERIFIED_CLAIM")
        self.assertEqual(claim["claim_status"], "SOURCE_VERIFIED_CLAIM")
        self.assertIn("not a merits prediction", claim["reason"])
        self.assertEqual({a["status"] for a in result["assertions"]}, {"SOURCE_VERIFIED"})
        self.assertEqual(result["highest_level_satisfied"], "primary_source_verified")
        self.assertEqual(result["evidence_basis"], "record")

    def test_an_attestation_alone_earns_nothing(self):
        ledger, _ = self.accepted()
        result, claim = self.claim_result(ledger)
        self.assertEqual(result["evidence_basis"], "attestation")
        self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
        self.assertIn("supply --evidence-dir", claim["reason"])
        self.assertEqual(result["highest_level_satisfied"], "structural")

    def test_attestation_is_refused_when_it_names_another_assertion_than_its_check_verifies(self):
        ledger, packet = self.ready()
        record = record_for(packet, "VAL-FACT", assertion_id="AS-ROLE")
        with self.assertRaisesRegex(ValueError, "contract declares VAL-FACT verifies AS-FACT"):
            self.attest(ledger, record)

    def test_attestation_is_refused_for_another_submission_check_or_time(self):
        ledger, packet = self.ready()
        refusals = (
            (record_for(packet, "VAL-FACT", dispatch_id="f" * 64), None, "ledger's current result"),
            (record_for(packet, "VAL-FACT", artifact_sha256="0" * 64), None, "ledger's current artifact"),
            (record_for(packet, "VAL-RULE"), "VAL-FACT", "recorded for VAL-RULE but this attestation is for VAL-FACT"),
            (record_for(packet, "VAL-FACT", observed_at="2099-01-01T00:00:00Z"), None, "is after the attestation"),
            (record_for(packet, "VAL-FACT", observed_at="2020-01-01T00:00:00Z"), None, "before the current result"),
        )
        for record, validation_id, message in refusals:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.attest(ledger, record, validation_id=validation_id)

    def test_attestation_lines_are_exactly_the_bound_records_lines(self):
        ledger, packet = self.ready()
        lines = domain.evidence_lines(record_for(packet, "VAL-FACT"))
        operator = RECORD["operator"]
        for evidence, message in ((lines + ["note=unverified"], "these are refused"),
                                  (lines + ["outcome=contradicts"], "more than one outcome"),
                                  ([lines[0], lines[1] + "\noutcome=contradicts"] + lines[2:], "carry a line break"),
                                  (lines[:-1], "must carry the bound record's assertion_id")):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.attest(ledger, None, validation_id="VAL-FACT", operator=operator, evidence=evidence)

    def test_a_runnable_check_can_never_be_attested(self):
        ledger, packet = self.ready()
        with self.assertRaisesRegex(ValueError, "machine-runnable"):
            self.attest(ledger, record_for(packet, "VAL-FACT"), validation_id="VAL-STRUCTURE")

    def test_a_record_for_another_task_revision_or_contract_never_verifies(self):
        for field, value, message in (("task_id", "OTHER-TASK", "record task_id OTHER-TASK"),
                                      ("revision", 2, "record revision 2"),
                                      ("contract_hash", "0" * 64, "record contract_hash")):
            with self.subTest(field=field):
                ledger, records = self.accepted(changes={"VAL-FACT": {field: value}})
                result, claim = self.claim_result(ledger, records)
                self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
                self.assertIn(message, claim["reason"])

    def test_an_undeclared_source_verifies_nothing(self):
        ledger, records = self.accepted(changes={"VAL-FACT": {"source_id": "SRC-GHOST"}})
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
        self.assertIn("record source_id SRC-GHOST is not a source the contract declares", claim["reason"])

    def test_a_declared_source_that_cannot_verify_the_assertion_covers_nothing(self):
        # The complaint is declared, but it is not among AS-FACT's verifying sources.
        ledger, records = self.accepted(changes={"VAL-FACT": {"source_id": "SRC-COMPLAINT", "source_type": "docket_filing"}})
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
        self.assertIn("No re-verified supporting record covers: AS-FACT", claim["reason"])
        check = next(c for c in result["validations"] if c["validation_id"] == "VAL-FACT")
        self.assertIs(check["evidence_verified"], True)
        self.assertIs(check["covers_assertion"], False)
        self.assertNotEqual(result["highest_level_satisfied"], None)

    def test_a_contradiction_from_a_declared_non_verifying_source_still_surfaces(self):
        ledger, records = self.accepted(changes={"VAL-FACT": {"source_id": "SRC-COMPLAINT", "source_type": "docket_filing",
                                                              "outcome": "contradicts"}})
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(claim["claim_status"], "CONTRADICTED_BY_SOURCE")

    def test_a_legal_proposition_is_verified_only_from_a_primary_law_source_type(self):
        ledger, records = self.accepted(changes={"VAL-RULE": {"source_type": "exhibit"}})
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
        self.assertIn("record source_type exhibit is not primary law", claim["reason"])

    def test_record_problems_check_the_assertion_by_id_on_the_record_basis_too(self):
        contract = minimal_contract()
        packet = make_packet(contract)
        record = record_for(packet, "VAL-FACT")
        attestation = {"validation_id": "VAL-FACT", "operator": record["operator"], "evidence": domain.evidence_lines(record)}
        binding = {"task_id": TASK, "revision": 1, "contract_hash": wp.current(packet)["hash"],
                   "dispatch_id": record["dispatch_id"], "artifact_sha256": record["artifact_sha256"]}
        assertions = {a["id"]: a for a in contract["domain"]["assertions"]}
        sources = {s["id"] for s in contract["sources"]}
        targets = contract["domain"]["validation_targets"]
        self.assertEqual(domain.record_problems(record, binding, "VAL-FACT", "primary_source_verified", attestation,
                                                targets, assertions, sources), [])
        other = dict(record, assertion_id="AS-ROLE")
        problems = domain.record_problems(other, binding, "VAL-FACT", "primary_source_verified",
                                          dict(attestation, evidence=domain.evidence_lines(other)), targets, assertions, sources)
        self.assertTrue(has(problems, "record assertion_id AS-ROLE is not AS-FACT"))

    def test_the_defendants_identity_is_part_of_what_the_claim_rests_on(self):
        ledger, records = self.accepted(changes={"VAL-ROLE": {"source_id": "SRC-COMPLAINT", "source_type": "docket_filing"}})
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
        self.assertIn("AS-ROLE (defendant DEF-A)", claim["reason"])

    def test_an_assertion_no_check_reads_keeps_the_claim_unverified(self):
        contract = minimal_contract()
        contract["validation"] = [v for v in contract["validation"] if v["id"] != "VAL-ROLE"]
        contract["domain"]["validation_levels"].pop("VAL-ROLE")
        contract["domain"]["validation_targets"].pop("VAL-ROLE")
        self.assertEqual(errors_for(contract), [])
        ledger, records = self.accepted(contract)
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
        role = next(a for a in result["assertions"] if a["assertion_id"] == "AS-ROLE")
        self.assertEqual(role["reason"], "no primary_source_verified validation targets it")

    def test_a_contradiction_names_its_role_and_outranks_an_unrelated_record_problem(self):
        ledger, records = self.accepted(changes={"VAL-ADVERSE": {"outcome": "contradicts"},
                                                 "VAL-FACT": {"revision": 2}})
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(result["earned_claim_basis"], "CONTRADICTED_BY_SOURCE")
        self.assertIn("AS-ADVERSE (threshold_defense TD-1, adverse_authority ADV-1)", claim["reason"])
        self.assertIn("misstates a source", claim["reason"])
        self.assertIn("also: VAL-FACT: record revision 2", claim["reason"])

    def test_a_contradiction_the_claim_does_not_rest_on_is_reported_for_that_assertion_only(self):
        contract = minimal_contract()
        contract["domain"]["assertions"].append({"id": "AS-ASIDE", "assertion": "A fictional side fact.",
                                                 "fact_status": "INFERENCE", "source_id": "SRC-COMPLAINT",
                                                 "verified_by": ["SRC-RECORD"]})
        contract["validation"].append({"id": "VAL-ASIDE", "description": "Read the side fact.", "criterion_ids": ["AC-READ"],
                                       "evidence_required": ["A record."]})
        contract["domain"]["validation_levels"]["VAL-ASIDE"] = "primary_source_verified"
        contract["domain"]["validation_targets"]["VAL-ASIDE"] = "AS-ASIDE"
        READ_FROM["VAL-ASIDE"] = ("SRC-RECORD", "official_record")
        self.addCleanup(READ_FROM.pop, "VAL-ASIDE")
        ledger, records = self.accepted(contract, changes={"VAL-ASIDE": {"outcome": "contradicts"}})
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(claim["claim_status"], "SOURCE_VERIFIED_CLAIM")
        aside = next(a for a in result["assertions"] if a["assertion_id"] == "AS-ASIDE")
        self.assertEqual(aside["status"], "CONTRADICTED_BY_SOURCE")

    def test_inconclusive_unknown_and_missing_evidence_each_keep_the_claim_unverified(self):
        ledger, records = self.accepted(changes={"VAL-FACT": {"outcome": "inconclusive"}})
        self.assertIn("inconclusive", self.claim_result(ledger, records)[1]["reason"])

        unknown = minimal_contract()
        unknown["domain"]["assertions"].append({"id": "AS-OPEN", "assertion": "Not yet researched.",
                                                "fact_status": "UNKNOWN", "source_id": "SRC-COMPLAINT", "verified_by": []})
        claim_of(unknown)["elements"][0]["supported_by"].append("AS-OPEN")
        ledger, records = self.accepted(unknown)
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
        self.assertIn("UNKNOWN assertion(s)", claim["reason"])
        self.assertEqual(next(a for a in result["assertions"] if a["assertion_id"] == "AS-OPEN")["status"], "UNKNOWN")

        gap = minimal_contract()
        claim_of(gap)["missing_evidence"].append({"element_id": "EL-1", "description": "Fictional recording not obtained."})
        ledger, records = self.accepted(gap)
        claim = self.claim_result(ledger, records)[1]
        self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
        self.assertIn("declares missing evidence", claim["reason"])

    def test_a_synthetic_contract_never_earns_a_verified_status(self):
        contract = minimal_contract()
        contract["domain"]["synthetic"] = True
        ledger, records = self.accepted(contract)
        result, claim = self.claim_result(ledger, records)
        self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
        self.assertIn("synthetic: true", claim["reason"])
        self.assertEqual(result["highest_level_satisfied"], "structural")

    def test_a_claimless_packet_reports_each_assertions_earned_status(self):
        contract = local_argv(packet_json("CRN-01-defendant-map"))
        contract["domain"].pop("synthetic")
        READ_FROM["VAL-ROSTER-REVIEW"] = ("SRC-CRN-ROSTER", "official_record")
        self.addCleanup(READ_FROM.pop, "VAL-ROSTER-REVIEW")
        ledger, records = self.accepted(contract)
        result = domain.status(ledger, records)
        self.assertEqual(result["earned_claim_basis"], "NOT_CLAIM_ASSERTING")
        self.assertEqual(result["claims"], [])
        earned = {a["assertion_id"]: a["status"] for a in result["assertions"]}
        self.assertEqual(earned, {"AS-ALPHA-ROLE": "SOURCE_VERIFIED", "AS-BETA-ROLE": "UNVERIFIED",
                                  "AS-GAMMA-EMPLOYER": "UNVERIFIED"})

    def test_a_ledger_not_yet_accepted_earns_nothing(self):
        ledger, packet = self.ready()
        result, claim = self.claim_result(ledger)
        self.assertEqual(claim["claim_status"], "UNVERIFIED_CLAIM")
        self.assertIn("not ACCEPTED", claim["reason"])

    def test_status_refuses_another_profile(self):
        contract = wp.read_json(ROOT / "examples/work-packets/software-hardware.contract.json")
        packet = wp.create("HW-SYN-001", "software-hardware", contract, "Architect", "Synthetic")
        for target, role, actor in (("ARCHITECTED", "architect", "Architect"), ("READY", "architect", "Architect"),
                                    ("IN_PROGRESS", "worker", "Worker"), ("VALIDATING", "worker", "Worker"),
                                    ("REVIEW", "worker", "Worker")):
            packet = wp.transition(packet, target, role, actor, "Synthetic", ["synthetic-state-evidence"])
        ledger, _ = self.start(packet=packet)
        with self.assertRaisesRegex(ValueError, "not civil-rights-nc"):
            domain.status(ledger)


class CommandLineTests(AcceptanceBase):
    def run_cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=ROOT, capture_output=True,
                                encoding="utf-8", timeout=120)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("Domain rule refused", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result.stderr

    def test_validate_contract_and_source_record_commands(self):
        for path in PACKET_FILES:
            with self.subTest(packet=path.name):
                self.assertTrue(self.run_cli("validate-contract", path)["valid"])
        broken = self.directory / "broken.json"
        contract = minimal_contract()
        contract["domain"]["claim_basis"] = "NOT_CLAIM_ASSERTING"
        broken.write_text(json.dumps(contract), encoding="utf-8")
        self.assertIn("a packet with a claim is UNVERIFIED_CLAIM", self.run_cli("validate-contract", broken, ok=False))
        printed = self.run_cli("source-record", EXAMPLES / "source-record.example.json", "--validation-id", RECORD["validation_id"])
        self.assertEqual(printed["attest_evidence"], domain.evidence_lines(RECORD))
        self.run_cli("source-record", EXAMPLES / "source-record.example.json", "--validation-id", "VAL-OTHER", ok=False)

    def test_status_command_names_its_evidence_basis(self):
        contract = minimal_contract()
        packet = make_packet(contract)
        ledger = self.directory / "ledger"
        acceptance.initialize(ledger, wp.read_json(ROOT / "config/acceptance.example.json"), packet, make_result(packet),
                              make_artifact(), CONTROLLER, ARCHITECT, IMPLEMENTERS, [])
        acceptance.run_checks(ledger, self.workspace())
        records = self.directory / "records"
        records.mkdir()
        for validation_id in TARGETS:
            record = record_for(packet, validation_id)
            acceptance.append(ledger, "ATTESTATION", {"attestation": {"validation_id": validation_id, "operator": record["operator"],
                                                                      "evidence": domain.evidence_lines(record)}},
                              previous_state=acceptance.replay(ledger))
            (records / f"{validation_id}.json").write_text(json.dumps(record), encoding="utf-8")
        prepared = self.open_review(ledger)
        self.ingest(ledger, make_report(prepared, contract))
        acceptance.accept(ledger, prepared["reviewer"]["actor"])
        attested = self.run_cli("status", ledger)
        self.assertEqual((attested["evidence_basis"], attested["earned_claim_basis"]), ("attestation", "UNVERIFIED_CLAIM"))
        verified = self.run_cli("status", ledger, "--evidence-dir", records)
        self.assertEqual((verified["evidence_basis"], verified["earned_claim_basis"]), ("record", "SOURCE_VERIFIED_CLAIM"))


class BootstrapIntakeTests(unittest.TestCase):
    FIELDS = ("forum_jurisdiction", "defendants_roles", "capacities", "alleged_rights", "procedural_history",
              "evidence_sources", "limitations_accrual", "objectives_remedies", "prior_proceedings", "reserved_actions")

    def test_intake_requires_the_civil_rights_orientation_fields(self):
        import validate_bootstrap
        self.assertEqual(tuple(validate_bootstrap.DOMAIN_FIELDS[PROFILE]), self.FIELDS)
        data = wp.read_json(ROOT / "tests/fixtures/bootstrap-civil-rights-awaiting.json")
        self.assertEqual(validate_bootstrap.activation_errors(data), [])
        data["domain"]["prior_proceedings"] = "TBD"
        self.assertTrue(any("domain.prior_proceedings" in e for e in validate_bootstrap.activation_errors(data)))

    def test_every_published_listing_names_exactly_the_validator_fields(self):
        # ADR-040: validate_bootstrap.DOMAIN_FIELDS is the single source; the schema clause, the
        # intake reference and the fixture are tested against it so none can drift.
        import validate_bootstrap
        fields = set(validate_bootstrap.DOMAIN_FIELDS[PROFILE])
        schema = wp.read_json(ROOT / "config/bootstrap.schema.json")
        clause = next(c for c in schema["allOf"]
                      if c.get("if", {}).get("properties", {}).get("domain_profile", {}).get("const") == PROFILE)
        domain_schema = clause["then"]["properties"]["domain"]
        self.assertEqual(set(domain_schema["required"]), fields)
        self.assertEqual(set(domain_schema["properties"]), fields)
        for key, question in validate_bootstrap.DOMAIN_FIELDS[PROFILE].items():
            self.assertEqual(domain_schema["properties"][key]["description"], question)
        reference = (ROOT / "skills/complex-project-bootstrapper/references/intake-schema.md").read_text(encoding="utf-8")
        row = next(line for line in reference.splitlines() if line.startswith(f"| `{PROFILE}` |"))
        named = set(row.split("|")[2].replace("`", "").replace(" ", "").split(","))
        self.assertEqual(named, fields)
        fixture = wp.read_json(ROOT / "tests/fixtures/bootstrap-civil-rights-awaiting.json")
        self.assertEqual(set(fixture["domain"]), fields)


if __name__ == "__main__":
    unittest.main()
