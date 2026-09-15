"""Software + hardware domain rules: simulated success never becomes hardware verification."""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import re
import shutil
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


def declared_scope(contract):
    """What a packet's context_scope says it owns (sample modules and tests) and consumes (interfaces)."""
    owned = {Path(item).stem for item in contract["context_scope"] if item.startswith("sample/synth_bridge/")}
    consumed = {name for item in contract["context_scope"] if item.startswith("Interface")
                for name in re.findall(r"synth_bridge\.(\w+)", item)}
    files = [item for item in contract["context_scope"] if item.startswith("sample/") and item.endswith(".py")]
    return owned, consumed, files


def synth_bridge_imports(path):
    """The synth_bridge modules a sample file imports, parsed rather than pattern-matched."""
    names = set()
    inside_package = path.parent.name == "synth_bridge"
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            if node.level and inside_package:  # `from . import codec` / `from .transport import X`
                if node.module is None:
                    names.update(alias.name for alias in node.names)
                else:
                    names.add(node.module.split(".")[0])
            elif node.module == "synth_bridge":
                names.update(alias.name for alias in node.names)
            elif node.module and node.module.startswith("synth_bridge."):
                names.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            names.update(alias.name.split(".")[1] for alias in node.names if alias.name.startswith("synth_bridge."))
    return names


def scope_violations(contracts, sample_root):
    """Imports a packet's files make that its declared scope does not admit, plus consumed
    interfaces whose owning packet is not a declared dependency. Empty means the scopes are true."""
    owner = {module: task for task, contract in contracts.items() for module in declared_scope(contract)[0]}
    problems = []
    for task, contract in contracts.items():
        owned, consumed, files = declared_scope(contract)
        for item in files:
            extra = synth_bridge_imports(sample_root / Path(item).relative_to("sample")) - owned - consumed
            if extra:
                problems.append(f"{task}: {item} imports undeclared {sorted(extra)}")
        for module in sorted(consumed):
            if owner.get(module) not in contract["dependencies"]:
                problems.append(f"{task}: consumes {module} owned by {owner.get(module)} without declaring the dependency")
    return problems


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
        self.assertEqual(wp.validate_contract(broken, "family-law"), [])
        self.assertTrue(any(e.startswith("domain:") for e in errors_for(broken)))
        self.assertIsNone(wp.domain_module("family-law"))
        # There is no default profile: a caller cannot skip the domain rules by omitting it.
        with self.assertRaises(TypeError):
            wp.validate_contract(broken)
        with self.assertRaisesRegex(ValueError, "registered domain profile"):
            wp.validate_contract(broken, None)

    def test_domain_block_is_closed_and_the_earned_status_is_refused_in_any_text(self):
        contract = example()
        contract["domain"]["notes"] = "Reviewed and VERIFIED_ON_HARDWARE by the author"
        self.assertTrue(any("Additional properties" in e and "notes" in e for e in errors_for(contract)))
        for path, mutate in (("assumption", lambda c: c["domain"]["hardware_assumptions"][0].__setitem__(
                                  "assumption", "Bench VERIFIED_ON_HARDWARE already")),
                             ("component", lambda c: c["domain"].__setitem__("component", "VERIFIED_ON_HARDWARE"))):
            with self.subTest(path=path):
                contract = example()
                mutate(contract)
                self.assertTrue(any("earned in the acceptance ledger, never authored" in e for e in errors_for(contract)))
        # The declared status UNVERIFIED_ON_HARDWARE contains the literal as a substring and is not a claim.
        self.assertEqual(errors_for(example()), [])

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
        # A stored revision replays and is reported (ADR-037); authoring it is refused.
        self.assertEqual(wp.validate(broken), [])
        self.assertTrue(any("domain:" in e for e in wp.domain_shortfall(broken)[1]))
        with self.assertRaisesRegex(ValueError, "domain:"):
            wp.create("WP-NEW", PROFILE, latest["contract"], "Architect", "Synthetic")
        with self.assertRaisesRegex(ValueError, "domain:"):
            wp.revise(make_packet(make_contract()), latest["contract"], "Architect", "Synthetic")
        with self.assertRaisesRegex(ValueError, "domain:"):
            acceptance.initialize(Path(self.enterContext(tempfile.TemporaryDirectory())) / "ledger",
                                  wp.read_json(ROOT / "config/acceptance.example.json"), broken, make_result(broken),
                                  make_artifact(), CONTROLLER, ARCHITECT, IMPLEMENTERS, [])

    def test_packet_authored_before_the_domain_rules_can_still_be_transitioned_and_revised(self):
        # Codex round 5 on PR #34 (ADR-037): a packet whose stored revision carries the formerly
        # valid free-form domain block must not be stranded; it replays, its shortfall is named,
        # it can be transitioned, and it can be revised into compliance — but not into another
        # non-compliant revision.
        legacy = example()
        legacy["domain"] = {"synthetic": True, "note": "Pre-#9 free-form extension data"}
        packet = make_packet(make_contract())
        stored = copy.deepcopy(packet)
        stored["revision_history"][0]["contract"] = legacy
        stored["revision_history"][0]["hash"] = wp.fingerprint(stored["task_id"], PROFILE, 1, legacy)
        for event in stored["events"]:
            event["contract_hash"] = stored["revision_history"][0]["hash"]
        self.assertEqual(wp.validate(stored), [])
        self.assertIn(1, wp.domain_shortfall(stored))
        self.assertTrue(any("'component' is a required property" in e for e in wp.domain_shortfall(stored)[1]))
        moved = wp.transition(stored, "ACCEPTED", "reviewer", "Reviewer", "Synthetic", ["synthetic-state-evidence"])
        self.assertEqual(moved["state"], "ACCEPTED")
        with self.assertRaisesRegex(ValueError, "domain:"):
            wp.revise(stored, dict(legacy, title="Still non-compliant"), "Architect", "Synthetic")
        repaired = wp.revise(stored, example(), "Architect", "Brought under the domain rules")
        self.assertEqual(wp.domain_shortfall(repaired), {1: wp.domain_shortfall(stored)[1]})
        self.assertEqual(wp.validate(repaired), [])

    def test_example_packets_form_a_dag_with_component_scoped_context(self):
        packets = [wp.create(path.name.split(".")[0], PROFILE, wp.read_json(path), "Architect", "Synthetic", "2026-09-13T00:00:00Z")
                   for path in PACKET_FILES]
        order = wp.graph_order(packets)
        self.assertEqual(order[0], "SHB-01-codec")
        self.assertEqual(order[-1], "SHB-06-workflow")
        components = {wp.current(p)["contract"]["domain"]["component"] for p in packets}
        self.assertEqual(len(components), 6)
        contracts = {p["task_id"]: wp.current(p)["contract"] for p in packets}
        # Declared scope is checked against actual imports, not against the shape of the paths:
        # every module a packet's files import is owned by the packet or named as a consumed
        # interface, and every consumed interface's owner is a declared dependency.
        self.assertEqual(scope_violations(contracts, EXAMPLES / "sample"), [])
        owned, consumed, _ = declared_scope(contracts["SHB-04-adapter"])
        self.assertEqual((owned, consumed), ({"adapter"}, {"transport"}))
        self.assertEqual(synth_bridge_imports(EXAMPLES / "sample/tests/test_adapter.py"), {"adapter", "transport"})
        # Negative control: the comparison sees an undeclared import and an undeclared dependency.
        copied = Path(self.enterContext(tempfile.TemporaryDirectory())) / "sample"
        shutil.copytree(EXAMPLES / "sample", copied)
        adapter_test = copied / "tests/test_adapter.py"
        adapter_test.write_text("from synth_bridge import codec\n" + adapter_test.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertEqual(scope_violations(contracts, copied), ["SHB-04-adapter: sample/tests/test_adapter.py imports undeclared ['codec']"])
        narrowed = copy.deepcopy(contracts)
        narrowed["SHB-06-workflow"]["dependencies"].remove("SHB-01-codec")
        self.assertIn("SHB-06-workflow: consumes codec owned by SHB-01-codec without declaring the dependency",
                      scope_violations(narrowed, EXAMPLES / "sample"))
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
        digest, values = domain.parsed_evidence(lines + ["free text", "unknown=ignored"])
        self.assertEqual(digest, domain.evidence_digest(EVIDENCE))
        self.assertEqual(values["device"], EVIDENCE["device_identity"])
        # A recognized key twice is refused rather than resolved by position (Codex P1 on PR #34).
        for extra in ("device=another unit", "outcome=fail", "operator=" + EVIDENCE["operator"]):
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(ValueError, "more than one"):
                    domain.parsed_evidence(lines + [extra])

    def test_record_loader_refuses_duplicate_keys_and_impossible_timestamps(self):
        # Codex round 3 on PR #34 (ADR-034): json.loads keeps the last of duplicate keys, so a
        # file saying outcome fail then pass hashed as passing; and the timestamp pattern admitted
        # 2026-99-99. One loader refuses the former; a format checker refuses the latter.
        text = json.dumps(EVIDENCE)[:-1] + ', "outcome": "pass"}'
        with self.assertRaisesRegex(ValueError, "duplicate key 'outcome'"):
            domain.load_record(text)
        nested = json.dumps(dict(EVIDENCE, artifacts=[{"reference": "b"}]))
        with self.assertRaisesRegex(ValueError, "duplicate key 'reference'"):
            domain.load_record(nested.replace('{"reference": "b"}', '{"reference": "a", "reference": "b"}'))
        with self.assertRaisesRegex(ValueError, "JSON object"):
            domain.load_record("[]")
        for text in (json.dumps(dict(EVIDENCE, extra=1)).replace('"extra": 1', '"extra": NaN'),
                     json.dumps(dict(EVIDENCE, extra=1)).replace('"extra": 1', '"extra": Infinity'),
                     json.dumps(dict(EVIDENCE, extra=1)).replace('"extra": 1', '"extra": 1e999')):
            with self.subTest(text=text[-40:]):
                with self.assertRaises(ValueError):
                    domain.load_record(text)
        for stamp in ("2026-99-99T99:99:99Z", "2026-02-30T00:00:00Z", "2026-09-13T24:00:00Z"):
            with self.subTest(stamp=stamp):
                with self.assertRaises(ValueError):
                    domain.validate_hardware_evidence(dict(EVIDENCE, observed_at=stamp))
        domain.validate_hardware_evidence(dict(EVIDENCE, observed_at="2026-09-13T23:59:59+00:00"))

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

    def test_contradictory_duplicate_line_is_refused_at_attestation(self):
        # Codex P1 on PR #34: `outcome=pass` followed by `outcome=fail` used to keep the first and
        # attest a failed observation as passing. Append refuses it; a stored attestation that
        # slipped through before the rule is reported unverified by status, not replayed as good.
        ledger = self.hardware_ledger()
        lines = domain.evidence_lines(EVIDENCE) + ["outcome=fail"]
        with self.assertRaisesRegex(ValueError, "more than one outcome= line"):
            self.attest(ledger, EVIDENCE["operator"], lines)
        self.assertEqual(domain.status(ledger)["validations"][0]["gate"], "NEEDS_ATTESTATION")

    def test_stored_attestation_the_rule_would_now_refuse_replays_marked_and_unverified(self):
        # ADR-032: a duplicate-key attestation accepted before the round-1 refusal is on the
        # hash chain; replay marks it instead of raising, status reports it unverified, and a new
        # attestation with the same defect is still refused.
        ledger = self.hardware_ledger()
        lines = domain.evidence_lines(EVIDENCE) + ["outcome=fail"]
        _, sequence, previous = acceptance.replay(ledger)
        event = {"sequence": sequence + 1, "previous": previous, "kind": "ATTESTATION", "timestamp": wp.now(),
                 "data": {"attestation": {"validation_id": "VAL-FRAMES", "operator": EVIDENCE["operator"], "evidence": lines}}}
        event["hash"] = acceptance.router.digest(event)
        (ledger / f"{sequence + 1:08d}.json").write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8")
        state = acceptance.replay(ledger)[0]
        self.assertIn("more than one outcome= line", state["attestations"]["VAL-FRAMES"]["domain_shortfall"])
        self.assertEqual(acceptance.summary(state)["attestation_shortfall"].keys(), {"VAL-FRAMES"})
        self.assertFalse(domain.status(ledger)["validations"][0]["evidence_verified"])
        with self.assertRaisesRegex(ValueError, "more than one outcome= line"):
            self.attest(ledger, EVIDENCE["operator"], lines)
        # The marked attestation satisfies the controller's gate as recorded, so the ledger can
        # still be accepted; the hardware status it earns is UNVERIFIED with the shortfall stated.
        acceptance.accept(ledger, CONTROLLER)
        report = domain.status(ledger)
        self.assertEqual(report["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertIn("stored attestation fails the current rule", report["reason"])

    def test_ledger_stored_before_the_domain_rules_replays_marked(self):
        # ADR-032: the #8 dogfood ledger's contract predates the structural domain block. It must
        # keep replaying for audit and acceptance status, marked with the shortfall; a new INIT with
        # that contract is refused; the hardware status is the one derivation that refuses.
        legacy = example()
        legacy["domain"] = {"synthetic": True, "note": "Pre-#9 free-form extension data"}
        ledger, _ = self.start()
        init = wp.read_json(ledger / "00000001.json")
        init["data"]["contract"] = legacy
        init["data"]["binding"]["contract_hash"] = wp.fingerprint(init["data"]["binding"]["task_id"], PROFILE,
                                                                  init["data"]["binding"]["revision"], legacy)
        old = Path(self.enterContext(tempfile.TemporaryDirectory())) / "legacy-ledger"
        old.mkdir()
        init["hash"] = acceptance.router.digest({k: v for k, v in init.items() if k != "hash"})
        (old / "00000001.json").write_text(json.dumps(init, indent=2) + "\n", encoding="utf-8")
        state = acceptance.replay(old)[0]
        self.assertEqual(state["status"], "GATES_PENDING")
        self.assertTrue(any("'component' is a required property" in e for e in state["domain_shortfall"]))
        self.assertEqual(acceptance.summary(state)["domain_shortfall"], state["domain_shortfall"])
        with self.assertRaisesRegex(ValueError, "predates the software-hardware domain rules"):
            domain.status(old)
        with self.assertRaisesRegex(ValueError, "domain: .*'component' is a required property"):
            acceptance.apply(None, init, stored=False)  # the same event as a new INIT is refused

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
        # Without an evidence directory the verdict rests on the attestations and says so.
        self.assertEqual(earned["evidence_basis"], "attestation")
        self.assertIn("not record-verified", earned["reason"])
        self.assertEqual(earned["highest_level_satisfied"], "hardware_in_loop")
        self.assertEqual(earned["validations"][0]["evidence_digest"], domain.evidence_digest(EVIDENCE))
        self.assertIsNone(earned["validations"][0]["evidence_path"])
        # The bound record must be findable and consistent when an evidence directory is supplied.
        records = self.directory / "records"
        records.mkdir()
        checked = domain.status(ledger, records)
        self.assertEqual((checked["earned_hardware_status"], checked["evidence_basis"]), ("UNVERIFIED_ON_HARDWARE", "record"))
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
        self.assertIn("Ran 34 tests", completed.stderr)

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
        self.assertEqual(earned["evidence_basis"], "record")
        self.assertIn("re-verified", earned["reason"])
        entry = next(v for v in earned["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertTrue(entry["evidence_verified"])
        self.assertEqual(Path(entry["evidence_path"]), records / "run.json")

    def attested_adapter_ledger(self, record, lines=None, operator=None):
        """An accepted low-risk adapter ledger whose VAL-HIL attestation binds `record`'s digest."""
        ledger, _ = self.start(packet=self.packet_for("SHB-04-adapter", risk="low"))
        acceptance.run_checks(ledger, EXAMPLES)
        acceptance.append(ledger, "ATTESTATION",
                          {"attestation": {"validation_id": "VAL-HIL", "operator": operator or record["operator"],
                                           "evidence": lines or domain.evidence_lines(record)}},
                          previous_state=acceptance.replay(ledger))
        acceptance.accept(ledger, CONTROLLER)
        records = self.directory / f"records-{self.counter}"
        records.mkdir()
        (records / "run.json").write_text(json.dumps(record), encoding="utf-8")
        return ledger, records

    def test_digest_matched_object_must_be_a_valid_record_that_says_what_was_attested(self):
        # Cross-family review of the #9 dogfood: a digest proves which bytes were bound, not that
        # they are a hardware evidence record. A five-field object carrying only the binding
        # fields, with the attestation's device/firmware/time lines typed by hand, satisfied the
        # old comparison. Verification now validates the found record against the schema and
        # compares every attested line with it.
        full = dict(EVIDENCE, task_id="ACCEPT-SYN-001")
        stub = {key: full[key] for key in ("task_id", "validation_id", "level", "outcome", "operator")}
        lines = [domain.DIGEST_PREFIX + domain.evidence_digest(stub), "level=hardware_in_loop", "device=Typed by hand",
                 "firmware=9.9.9", "observed_at=2026-09-14T00:00:00Z", "outcome=pass", f"operator={stub['operator']}"]
        ledger, records = self.attested_adapter_ledger(stub, lines=lines)
        checked = domain.status(ledger, records)
        self.assertEqual(checked["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertIn("not a valid hardware evidence record", checked["reason"])
        self.assertEqual(checked["highest_level_satisfied"], "unit",
                         "a hardware rung whose record failed verification is not a satisfied rung")
        entry = next(v for v in checked["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertFalse(entry["evidence_verified"])
        self.assertEqual(Path(entry["evidence_path"]), records / "run.json", "found by digest, refused on content")
        # A complete record whose attested lines disagree with it does not verify either, field by field.
        for key, field in (("device", "device_identity"), ("firmware", "firmware_version"), ("observed_at", "observed_at")):
            with self.subTest(field=field):
                other = "2001-01-01T00:00:00Z" if key == "observed_at" else "Something else"
                forged = [f"{key}={other}" if line.startswith(key + "=") else line
                          for line in domain.evidence_lines(full)]
                ledger, records = self.attested_adapter_ledger(full, lines=forged)
                checked = domain.status(ledger, records)
                self.assertEqual(checked["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
                self.assertIn(f"attested {key} differs from the record's {field}", checked["reason"])
        # The consistent record still verifies on the record basis.
        ledger, records = self.attested_adapter_ledger(full)
        checked = domain.status(ledger, records)
        self.assertEqual((checked["earned_hardware_status"], checked["evidence_basis"]), ("VERIFIED_ON_HARDWARE", "record"))

    def test_evidence_fields_are_compared_exactly_and_only_the_operator_is_case_folded(self):
        # Codex round 2 on PR #34: `device=SN-ABC` must not verify against `device_identity: SN-abc`;
        # a different case is a different unit. The operator keeps the controller's actor normalization.
        full = dict(EVIDENCE, task_id="ACCEPT-SYN-001", device_identity="SN-ABC", operator="Bench Operator")
        for key, other in (("device", "SN-abc"), ("firmware", full["firmware_version"].upper()),
                           ("observed_at", full["observed_at"].lower())):
            with self.subTest(field=key):
                lines = [f"{key}={other}" if line.startswith(key + "=") else line for line in domain.evidence_lines(full)]
                ledger, records = self.attested_adapter_ledger(full, lines=lines)
                checked = domain.status(ledger, records)
                self.assertEqual(checked["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
                self.assertIn(f"attested {key} differs", checked["reason"])
        lines = ["operator=bench operator" if line.startswith("operator=") else line for line in domain.evidence_lines(full)]
        ledger, records = self.attested_adapter_ledger(full, lines=lines, operator="BENCH OPERATOR")
        self.assertEqual(domain.status(ledger, records)["earned_hardware_status"], "VERIFIED_ON_HARDWARE")

    def test_record_file_with_a_duplicate_key_is_named_as_refused_not_missing(self):
        # ADR-034: the file the attestation would bind carries outcome fail then pass. It is
        # refused by the loader and status says so, rather than reporting no record at all.
        full = dict(EVIDENCE, task_id="ACCEPT-SYN-001")
        ledger, records = self.attested_adapter_ledger(full)
        (records / "run.json").write_text(json.dumps(dict(full, outcome="fail"))[:-1] + ', "outcome": "pass"}',
                                          encoding="utf-8")
        checked = domain.status(ledger, records)
        self.assertEqual(checked["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertIn("refused: run.json: duplicate key 'outcome'", checked["reason"])
        # A file the loader refuses earlier in the scan is named and the scan continues to the record.
        (records / "run.json").write_text(json.dumps(full), encoding="utf-8")
        (records / "a-bad.json").write_text(json.dumps(dict(full, extra=1)).replace('"extra": 1', '"extra": NaN'), encoding="utf-8")
        (records / "b-bad.json").write_text(json.dumps(dict(full, extra=1)).replace('"extra": 1', '"extra": 1e999'), encoding="utf-8")
        checked = domain.status(ledger, records)
        self.assertEqual((checked["earned_hardware_status"], checked["evidence_basis"]), ("VERIFIED_ON_HARDWARE", "record"))
        with tempfile.TemporaryDirectory() as temporary:
            broken = Path(temporary) / "dup.json"
            broken.write_text(json.dumps(EVIDENCE)[:-1] + ', "outcome": "pass"}', encoding="utf-8")
            completed = subprocess.run([sys.executable, str(SCRIPT), "hardware-evidence", str(broken)],
                                       capture_output=True, text=True, cwd=ROOT, encoding="utf-8")
            self.assertEqual(completed.returncode, 1)
            self.assertIn("duplicate key 'outcome'", completed.stderr)

    def test_record_recorded_by_another_operator_does_not_verify_the_attestation(self):
        # The attestation's operator= line is checked at append time against the attesting operator,
        # but the digest line is only a string then: an attester can bind a record someone else
        # recorded and copy their own name into the line. status --evidence-dir compares the
        # record's operator to the attesting operator, so that record does not verify.
        ledger, _ = self.start(packet=self.packet_for("SHB-04-adapter", risk="low"))
        acceptance.run_checks(ledger, EXAMPLES)
        record = dict(EVIDENCE, task_id="ACCEPT-SYN-001", operator="Someone else at the bench")
        lines = [line if not line.startswith("operator=") else "operator=Attesting operator"
                 for line in domain.evidence_lines(record)]
        acceptance.append(ledger, "ATTESTATION",
                          {"attestation": {"validation_id": "VAL-HIL", "operator": "Attesting operator", "evidence": lines}},
                          previous_state=acceptance.replay(ledger))
        acceptance.accept(ledger, CONTROLLER)
        self.assertEqual(domain.status(ledger)["earned_hardware_status"], "VERIFIED_ON_HARDWARE",
                         "attestation-basis status reports what was attested")
        records = self.directory / "records"
        records.mkdir()
        (records / "run.json").write_text(json.dumps(record), encoding="utf-8")
        checked = domain.status(ledger, records)
        self.assertEqual(checked["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertIn("record operator is not the attesting operator", checked["reason"])
        entry = next(v for v in checked["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertFalse(entry["evidence_verified"])
        self.assertEqual(Path(entry["evidence_path"]), records / "run.json", "the record was found; it did not verify")

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

    def test_status_command_names_its_evidence_basis(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            contract = local_argv(wp.read_json(EXAMPLES / "packets/SHB-04-adapter.contract.json"))
            contract["risk"] = "low"
            contract["dependencies"] = []
            packet = make_packet(contract)
            ledger = base / "ledger"
            acceptance.initialize(ledger, wp.read_json(ROOT / "config/acceptance.example.json"), packet,
                                  make_result(packet), make_artifact(), CONTROLLER, ARCHITECT, IMPLEMENTERS, [])
            acceptance.run_checks(ledger, EXAMPLES)
            record = dict(EVIDENCE, task_id="ACCEPT-SYN-001")
            acceptance.append(ledger, "ATTESTATION",
                              {"attestation": {"validation_id": "VAL-HIL", "operator": record["operator"],
                                               "evidence": domain.evidence_lines(record)}},
                              previous_state=acceptance.replay(ledger))
            acceptance.accept(ledger, CONTROLLER)
            attested = self.run_cli("status", ledger)
            self.assertEqual((attested["earned_hardware_status"], attested["evidence_basis"]),
                             ("VERIFIED_ON_HARDWARE", "attestation"))
            self.assertIn("not record-verified", attested["reason"])
            records = base / "records"
            records.mkdir()
            self.assertEqual(self.run_cli("status", ledger, "--evidence-dir", records)["earned_hardware_status"],
                             "UNVERIFIED_ON_HARDWARE", "an empty record directory verifies nothing")
            (records / "run.json").write_text(json.dumps(record), encoding="utf-8")
            verified = self.run_cli("status", ledger, "--evidence-dir", records)
            self.assertEqual((verified["earned_hardware_status"], verified["evidence_basis"]),
                             ("VERIFIED_ON_HARDWARE", "record"))


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

    def test_published_bootstrap_schema_requires_the_same_fields_as_the_validator(self):
        # Codex P2 on PR #34: the schema editors read still named the three legacy fields, so an
        # approval package the validator refuses looked complete to schema-based tooling.
        schema = wp.read_json(ROOT / "config/bootstrap.schema.json")
        clause = next(c for c in schema["allOf"]
                      if c.get("if", {}).get("properties", {}).get("domain_profile", {}).get("const") == PROFILE)
        domain_schema = clause["then"]["properties"]["domain"]
        import validate_bootstrap
        self.assertEqual(set(domain_schema["required"]), set(validate_bootstrap.DOMAIN_FIELDS[PROFILE]))
        self.assertEqual(set(domain_schema["properties"]), set(validate_bootstrap.DOMAIN_FIELDS[PROFILE]))
        for key in ("hardware_identity", "physical_access"):
            self.assertEqual(domain_schema["properties"][key]["pattern"], "\\S")


if __name__ == "__main__":
    unittest.main()
