"""Software + hardware domain rules: simulated success never becomes hardware verification."""
from __future__ import annotations

import ast
import contextlib
import copy
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_acceptance import (ARCHITECT, CONTROLLER, IMPLEMENTERS, AcceptanceBase, acceptance,
                             make_artifact, make_contract, make_failure, make_packet, make_report, make_result)

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


def live(record=None, **changes):
    """`record` (default EVIDENCE) with `observed_at` refreshed to now. Codex round 20 on PR #34
    (ADR-052): an attested observation must fall between the ledger's current submission and the
    attestation itself, and EVIDENCE's fixed illustrative date always predates any ledger this
    suite builds moments later."""
    return dict(EVIDENCE if record is None else record, observed_at=wp.now(), **changes)


def live_lines(record=None, **changes):
    """The attestation lines for `live(record, **changes)`."""
    return domain.evidence_lines(live(record, **changes))


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


def two_hardware_rung_contract():
    """`hardware_contract()` with a second, independent hardware-rung check added -- the
    post-merge independent review's repro: a record explicitly for one check (room-temperature
    VAL-FRAMES) must not verify a different one (maximum-temperature VAL-HOT) in the same
    submission, even though both share the submission, artifact, operator and permitted
    observation time."""
    value = hardware_contract()
    value["acceptance_criteria"].append(
        {"id": "AC-HOT", "description": "Maximum-temperature testing was performed and observed to pass."})
    value["validation"].append({"id": "VAL-HOT", "description": "Observe behavior at maximum rated temperature.",
                                "criterion_ids": ["AC-HOT"],
                                "evidence_required": ["Maximum-temperature observation record."]})
    value["domain"]["validation_levels"]["VAL-HOT"] = "hardware_in_loop"
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
        # Every reporting path qualifies its verdict with the shortfall; none calls it clean.
        self.assertIn("DOMAIN SHORTFALL", wp.render(stored))
        self.assertIn("'component' is a required property", wp.render(stored))
        self.assertEqual(wp.shortfall_note(make_packet(make_contract())), "")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "legacy.json"
            path.write_text(json.dumps(stored), encoding="utf-8")
            for command in (["validate", str(path)], ["graph", str(path)]):
                with self.subTest(command=command[0]):
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        code = wp.main(command)
                    self.assertEqual(code, 0)
                    self.assertIn("VALID", out.getvalue())
                    self.assertIn("DOMAIN SHORTFALL", out.getvalue())
                    self.assertIn("revision 1", out.getvalue())

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
    def test_example_record_is_bound_to_the_packet_file_it_documents(self):
        # Codex round 14 on PR #34: the example illustrates SHB-04-adapter revision 1's VAL-HIL
        # walkthrough (README's operator procedure); its revision and contract_hash must actually
        # match that packet file so `status --evidence-dir` accepts it as the doc describes,
        # not merely pass the standalone `hardware-evidence` command in isolation.
        contract = wp.read_json(EXAMPLES / "packets/SHB-04-adapter.contract.json")
        self.assertEqual(EVIDENCE["revision"], 1)
        self.assertEqual(EVIDENCE["contract_hash"], wp.fingerprint("SHB-04-adapter", PROFILE, 1, contract))

    def test_example_record_validates_and_its_lines_bind_the_digest(self):
        lines = domain.evidence_lines(EVIDENCE)
        self.assertEqual(lines[0], domain.DIGEST_PREFIX + domain.evidence_digest(EVIDENCE))
        self.assertIn("outcome=pass", lines)
        self.assertIn("operator=" + EVIDENCE["operator"], lines)
        digest, values, unrecognized = domain.parsed_evidence_strict(lines + ["free text", "unknown=ignored", " outcome=fail"])
        self.assertEqual(digest, domain.evidence_digest(EVIDENCE))
        self.assertEqual(values["device"], EVIDENCE["device_identity"])
        self.assertEqual(unrecognized, ["free text", "unknown=ignored", " outcome=fail"])
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

    def test_record_fields_that_become_lines_are_single_line(self):
        # Codex round 8 on PR #34 (ADR-039): a record value with an embedded line break used to
        # become one attestation element that read as two lines. The schema refuses it in the
        # record, and the attestation rule refuses any element carrying a line break.
        for field in ("device_identity", "firmware_version", "operator"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field):
                    domain.validate_hardware_evidence(dict(EVIDENCE, **{field: "SN-1\noutcome=fail"}))
                with self.assertRaisesRegex(ValueError, field):
                    domain.validate_hardware_evidence(dict(EVIDENCE, **{field: "SN-1\r\noutcome=fail"}))
                # Codex round 9: an end anchor matches before a trailing newline, so the prohibition is explicit.
                for trailing in ("SN-1\n", "SN-1\r", "SN-1\r\n", "\nSN-1"):
                    with self.assertRaisesRegex(ValueError, field):
                        domain.validate_hardware_evidence(dict(EVIDENCE, **{field: trailing}))
        domain.validate_hardware_evidence(dict(EVIDENCE, test_setup="Multi-line narrative\nis fine here"))

    def test_single_line_fields_are_bounded_so_their_attestation_line_fits(self):
        # Codex round 17 on PR #34: device_identity, firmware_version and operator were unbounded,
        # so a schema-valid record could still be refused at attestation once evidence_lines()
        # adds a key prefix and the value exceeds acceptance's own 2000-character bounded_text
        # element limit. The bound leaves room for the longest key ("firmware=" / "operator=").
        for field, key in (("device_identity", "device"), ("firmware_version", "firmware"), ("operator", "operator")):
            with self.subTest(field=field):
                record = dict(EVIDENCE, **{field: "a" * 1991})
                domain.validate_hardware_evidence(record)
                emitted = next(line for line in domain.evidence_lines(record) if line.startswith(key + "="))
                self.assertLessEqual(len(emitted), 2000)
                with self.assertRaisesRegex(ValueError, "hardware evidence"):
                    domain.validate_hardware_evidence(dict(EVIDENCE, **{field: "a" * 1992}))

    def test_record_shape_is_closed(self):
        for field, value in (("outcome", "passed"), ("level", "unit"), ("observed_at", "yesterday"),
                             ("artifacts", [{"reference": "x", "sha256": "short"}]), ("extra", 1),
                             ("revision", 0), ("revision", "1"), ("contract_hash", "short"),
                             ("contract_hash", "g" * 64), ("dispatch_id", "short"),
                             ("artifact_sha256", "g" * 64),
                             # Codex round 17: an end anchor matches before a trailing newline, so
                             # identifier and sha256 use a strict end assertion instead (as
                             # acceptance.schema.json does), matching ADR-039's class for single_line.
                             ("task_id", EVIDENCE["task_id"] + "\n"),
                             ("validation_id", EVIDENCE["validation_id"] + "\n"),
                             ("contract_hash", EVIDENCE["contract_hash"] + "\n"),
                             ("dispatch_id", EVIDENCE["dispatch_id"] + "\n"),
                             ("artifact_sha256", EVIDENCE["artifact_sha256"] + "\n")):
            record = copy.deepcopy(EVIDENCE)
            record[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "hardware evidence"):
                domain.validate_hardware_evidence(record)
        for field in ("observed_behavior", "revision", "contract_hash", "dispatch_id", "artifact_sha256"):
            record = copy.deepcopy(EVIDENCE)
            del record[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
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

    def test_attestation_is_refused_for_a_result_or_artifact_it_was_not_observed_against(self):
        # Codex round 18 on PR #34 (ADR-049): the attestation basis alone (no --evidence-dir) must
        # also refuse a record bound to a different submission, not only the record basis
        # (ADR-047). Neither field needs a resubmission to demonstrate: any mismatch is refused
        # the moment it is attested.
        ledger = self.hardware_ledger()
        for field, other in (("dispatch_id", "f" * 64), ("artifact_sha256", "0" * 64)):
            with self.subTest(field=field):
                record = live(validation_id="VAL-FRAMES", **{field: other})
                with self.assertRaisesRegex(ValueError, "ledger's current"):
                    self.attest(ledger, record["operator"], domain.evidence_lines(record))

    def test_non_synthetic_contract_can_earn_verified_on_hardware(self):
        # Codex round 18 on PR #34 (ADR-050): synthetic contracts are capped at
        # UNVERIFIED_ON_HARDWARE, but that cap must be specific to synthetic:true, not a blanket
        # regression -- a contract that omits it can still earn VERIFIED_ON_HARDWARE.
        contract = hardware_contract()
        del contract["domain"]["synthetic"]
        ledger, packet = self.start(packet=make_packet(contract))
        self.checked(ledger)
        record = live(task_id="ACCEPT-SYN-001", validation_id="VAL-FRAMES",
                     contract_hash=wp.current(packet)["hash"])
        self.attest(ledger, record["operator"], domain.evidence_lines(record))
        acceptance.accept(ledger, CONTROLLER)
        self.assertEqual(domain.status(ledger)["earned_hardware_status"], "VERIFIED_ON_HARDWARE")
        records = self.directory / "records"
        records.mkdir()
        (records / "run.json").write_text(json.dumps(record), encoding="utf-8")
        checked = domain.status(ledger, records)
        self.assertEqual((checked["earned_hardware_status"], checked["evidence_basis"]), ("VERIFIED_ON_HARDWARE", "record"))
        self.assertEqual(checked["highest_level_satisfied"], "hardware_in_loop")

    def test_attestation_is_refused_for_a_different_validation_at_the_same_rung(self):
        # Post-merge independent review (ADR-056): the printed evidence lines omitted the
        # record's validation_id, so a schema-valid record explicitly for one hardware-rung check
        # could be appended unchanged for a different check at the same rung -- level, device,
        # firmware, observed_at, outcome, operator, dispatch_id and artifact_sha256 can all
        # legitimately match across two checks in the same submission. Reproduced with a
        # room-temperature VAL-FRAMES record attested against maximum-temperature VAL-HOT.
        ledger, _ = self.start(packet=make_packet(two_hardware_rung_contract()))
        self.checked(ledger)
        record = live(validation_id="VAL-FRAMES")
        with self.assertRaisesRegex(ValueError, "recorded for VAL-FRAMES but this attestation is for VAL-HOT"):
            acceptance.append(ledger, "ATTESTATION",
                              {"attestation": {"validation_id": "VAL-HOT", "operator": record["operator"],
                                               "evidence": domain.evidence_lines(record)}},
                              previous_state=acceptance.replay(ledger))
        # The record still verifies the check it actually names.
        state = acceptance.append(ledger, "ATTESTATION",
                                  {"attestation": {"validation_id": "VAL-FRAMES", "operator": record["operator"],
                                                   "evidence": domain.evidence_lines(record)}},
                                  previous_state=acceptance.replay(ledger))
        self.assertEqual(acceptance.deterministic_status(state)["VAL-FRAMES"], "ATTESTED")
        self.assertEqual(acceptance.deterministic_status(state)["VAL-HOT"], "NEEDS_ATTESTATION")

    def test_hardware_rung_attestation_must_bind_a_passing_record(self):
        ledger = self.hardware_ledger()
        lines = live_lines(validation_id="VAL-FRAMES")
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
        # Codex round 15 on PR #34: an observation dated after the attestation event that records
        # it cannot have happened yet, whether or not a hardware evidence record is ever supplied.
        with self.assertRaisesRegex(ValueError, "is after the attestation recording it"):
            self.attest(ledger, operator,
                       ["observed_at=2099-01-01T00:00:00Z" if line.startswith("observed_at=") else line
                        for line in lines])
        state = self.attest(ledger, operator, lines)
        self.assertTrue(acceptance.deterministic_satisfied(state))
        self.assertEqual(acceptance.deterministic_status(state)["VAL-FRAMES"], "ATTESTED")

    def test_hardware_attestation_carries_nothing_but_the_record_lines(self):
        # Codex round 7 on PR #34 (ADR-038): a line the parser did not recognize used to ride
        # along unverified — ` outcome=fail` beside `outcome=pass`. Every line is now either the
        # digest, one of the six recognized keys, or refused.
        ledger = self.hardware_ledger()
        for extra in (" outcome=fail", "outcome =fail", "OUTCOME=fail", "note: observed by hand", "unknown=value"):
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(ValueError, "every line is verified, so these are refused"):
                    self.attest(ledger, EVIDENCE["operator"], domain.evidence_lines(EVIDENCE) + [extra])
        with self.assertRaisesRegex(ValueError, "non-empty"):  # a blank line is refused by the controller's shape first
            self.attest(ledger, EVIDENCE["operator"], domain.evidence_lines(EVIDENCE) + [""])
        self.assertEqual(domain.status(ledger)["validations"][0]["gate"], "NEEDS_ATTESTATION")
        self.attest(ledger, EVIDENCE["operator"], live_lines(validation_id="VAL-FRAMES"))
        self.assertEqual(domain.status(ledger)["validations"][0]["gate"], "ATTESTED")

    def test_attestation_element_with_a_line_break_is_refused(self):
        ledger = self.hardware_ledger()
        lines = [line.replace("device=", "device=SN-1\noutcome=fail; was ") if line.startswith("device=") else line
                 for line in domain.evidence_lines(EVIDENCE)]
        with self.assertRaisesRegex(ValueError, "element is one line"):
            self.attest(ledger, EVIDENCE["operator"], lines)

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
        # A new acceptance must not rest on the shortfall (Codex round 21 on PR #34, ADR-053):
        # replaying a shortfall-marked attestation as ATTESTED only preserves an already-recorded
        # acceptance's history, never justifies a fresh one.
        with self.assertRaisesRegex(ValueError, "cannot rest on a stored attestation"):
            acceptance.accept(ledger, CONTROLLER)
        report = domain.status(ledger)
        self.assertEqual(report["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertIn("not ACCEPTED", report["reason"])

    def test_a_ledger_already_accepted_on_a_now_invalid_attestation_still_replays_accepted(self):
        # The other half of ADR-053: an ACCEPT event itself stored before the rule existed is
        # history, not a new decision, and must keep replaying as ACCEPTED even though the
        # attestation it rested on now fails the current rule.
        ledger = self.hardware_ledger()
        lines = domain.evidence_lines(EVIDENCE) + ["outcome=fail"]
        _, sequence, previous = acceptance.replay(ledger)
        event = {"sequence": sequence + 1, "previous": previous, "kind": "ATTESTATION", "timestamp": wp.now(),
                 "data": {"attestation": {"validation_id": "VAL-FRAMES", "operator": EVIDENCE["operator"], "evidence": lines}}}
        event["hash"] = acceptance.router.digest(event)
        (ledger / f"{sequence + 1:08d}.json").write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8")
        _, sequence, previous = acceptance.replay(ledger)
        accepted = {"sequence": sequence + 1, "previous": previous, "kind": "ACCEPT", "timestamp": wp.now(),
                   "data": {"actor": CONTROLLER}}
        accepted["hash"] = acceptance.router.digest(accepted)
        (ledger / f"{sequence + 1:08d}.json").write_text(json.dumps(accepted, indent=2) + "\n", encoding="utf-8")
        state = acceptance.replay(ledger)[0]
        self.assertEqual(state["status"], "ACCEPTED")
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
        record = live(validation_id="VAL-FRAMES")
        self.attest(ledger, record["operator"], domain.evidence_lines(record))
        self.assertEqual(domain.status(ledger)["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        acceptance.accept(ledger, CONTROLLER)
        earned = domain.status(ledger)
        # This contract declares synthetic: true (ADR-050), so it never earns VERIFIED_ON_HARDWARE
        # or credits the attested hardware rung toward highest_level_satisfied, no matter how
        # completely it is attested; the attestation itself is still recorded and reported.
        self.assertIn("synthetic: true", earned["reason"])
        self.assertEqual(earned["evidence_basis"], "attestation")
        self.assertIsNone(earned["highest_level_satisfied"])
        self.assertEqual(earned["validations"][0]["gate"], "ATTESTED")
        self.assertEqual(earned["validations"][0]["evidence_digest"], domain.evidence_digest(record))
        self.assertIsNone(earned["validations"][0]["evidence_path"])
        # The bound record must be findable and consistent when an evidence directory is supplied.
        records = self.directory / "records"
        records.mkdir()
        checked = domain.status(ledger, records)
        self.assertEqual((checked["earned_hardware_status"], checked["evidence_basis"]), ("UNVERIFIED_ON_HARDWARE", "record"))
        (records / "hil.json").write_text(json.dumps(EVIDENCE), encoding="utf-8")
        self.assertEqual(domain.status(ledger, records)["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE",
                         "not found by digest: the example record's task_id and observed_at differ")
        mine = dict(record, task_id="ACCEPT-SYN-001")
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
        self.assertIn("Ran 41 tests", completed.stderr)

    def test_deterministic_gate_reexecutes_the_codec_packet_commands(self):
        ledger, _ = self.start(packet=self.packet_for("SHB-01-codec"))
        outcome = acceptance.run_checks(ledger, EXAMPLES)
        self.assertTrue(outcome["satisfied"], outcome)
        self.assertEqual(outcome["deterministic"], {"VAL-UNIT": "PASSED", "VAL-CONTRACT": "PASSED"})
        acceptance.accept(ledger, CONTROLLER)
        self.assertEqual(domain.status(ledger)["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")

    def test_adapter_packet_splits_the_fake_port_run_from_the_physical_read(self):
        # Risk lowered to exercise the deterministic gate alone; the real packet is high risk.
        ledger, packet = self.start(packet=self.packet_for("SHB-04-adapter", risk="low"))
        outcome = acceptance.run_checks(ledger, EXAMPLES)
        self.assertFalse(outcome["satisfied"])
        self.assertEqual(outcome["deterministic"], {"VAL-UNIT-ADAPTER": "PASSED", "VAL-HIL": "NEEDS_ATTESTATION"})
        with self.assertRaisesRegex(ValueError, "Deterministic gate unsatisfied"):
            acceptance.accept(ledger, CONTROLLER)
        record = live(task_id="ACCEPT-SYN-001", contract_hash=wp.current(packet)["hash"])
        acceptance.append(ledger, "ATTESTATION",
                          {"attestation": {"validation_id": "VAL-HIL", "operator": record["operator"],
                                           "evidence": domain.evidence_lines(record)}},
                          previous_state=acceptance.replay(ledger))
        acceptance.accept(ledger, CONTROLLER)
        records = self.directory / "records"
        records.mkdir()
        (records / "run.json").write_text(json.dumps(record), encoding="utf-8")
        earned = domain.status(ledger, records)
        # UNVERIFIED_ON_HARDWARE only because this packet declares synthetic: true (ADR-050); the
        # record itself verified, which is what this test exercises.
        self.assertIn("synthetic: true", earned["reason"])
        self.assertEqual(earned["evidence_basis"], "record")
        entry = next(v for v in earned["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertTrue(entry["evidence_verified"])
        self.assertEqual(Path(entry["evidence_path"]), records / "run.json")

    def revised_adapter_packet(self, note="Revised once for the ADR-043 regression."):
        """The SHB-04-adapter packet revised once (revision 2), back at REVIEW. Two calls with
        different `note` text are two independently revised, same-revision-number variants."""
        packet = self.packet_for("SHB-04-adapter", risk="low")
        contract = copy.deepcopy(wp.current(packet)["contract"])
        contract["goal"] += " " + note
        packet = wp.revise(packet, contract, "Architect", "Synthetic revision for the ADR-043 regression")
        for target, role, actor in (
            ("ARCHITECTED", "architect", "Architect"), ("READY", "architect", "Architect"),
            ("IN_PROGRESS", "worker", "Worker"), ("VALIDATING", "worker", "Worker"),
            ("REVIEW", "worker", "Worker"),
        ):
            packet = wp.transition(packet, target, role, actor, "Synthetic state assertion", ["synthetic-state-evidence"])
        return packet

    def adapter_evidence(self, **changes):
        """EVIDENCE bound to a fresh, revision-1 SHB-04-adapter packet's task and contract hash --
        the packet `attested_adapter_ledger` builds by default when its own `packet` is None --
        with `observed_at` refreshed to now (ADR-052)."""
        packet = self.packet_for("SHB-04-adapter", risk="low")
        return live(task_id="ACCEPT-SYN-001", contract_hash=wp.current(packet)["hash"], **changes)

    def attested_adapter_ledger(self, record, lines=None, operator=None, packet=None):
        """An accepted low-risk adapter ledger whose VAL-HIL attestation binds `record`'s digest.

        `record`'s `observed_at` is refreshed to now (ADR-052) only after this ledger's own INIT
        exists, so the attestation is never stale relative to it. `lines`, if given, is a callable
        receiving the refreshed record and returning the attestation lines (default:
        `domain.evidence_lines`), so any forging built from the record sees the fresh timestamp too.
        """
        ledger, _ = self.start(packet=packet or self.packet_for("SHB-04-adapter", risk="low"))
        acceptance.run_checks(ledger, EXAMPLES)
        record = live(record)
        evidence = lines(record) if lines else domain.evidence_lines(record)
        acceptance.append(ledger, "ATTESTATION",
                          {"attestation": {"validation_id": "VAL-HIL", "operator": operator or record["operator"],
                                           "evidence": evidence}},
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
        full = self.adapter_evidence()
        dispatch_id, artifact_sha256 = full["dispatch_id"], full["artifact_sha256"]

        def hand_typed(record):
            # `record` is the refreshed stub (task_id/validation_id/level/outcome/operator plus
            # a live observed_at, ADR-052); its digest is exactly what's written to records/run.json.
            return [domain.DIGEST_PREFIX + domain.evidence_digest(record), "level=hardware_in_loop",
                    "device=Typed by hand", "firmware=9.9.9", f"observed_at={record['observed_at']}",
                    "outcome=pass", f"operator={record['operator']}",
                    f"dispatch_id={dispatch_id}", f"artifact_sha256={artifact_sha256}",
                    f"validation_id={record['validation_id']}"]

        stub = {key: full[key] for key in ("task_id", "validation_id", "level", "outcome", "operator")}
        ledger, records = self.attested_adapter_ledger(stub, lines=hand_typed)
        checked = domain.status(ledger, records)
        self.assertEqual(checked["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertIn("not a valid hardware evidence record", checked["reason"])
        self.assertEqual(checked["highest_level_satisfied"], "unit",
                         "a hardware rung whose record failed verification is not a satisfied rung")
        entry = next(v for v in checked["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertFalse(entry["evidence_verified"])
        self.assertEqual(Path(entry["evidence_path"]), records / "run.json", "found by digest, refused on content")
        # A complete record whose attested lines disagree with it does not verify either, field by
        # field. observed_at is exercised directly against record_problems below (a live, appended
        # attestation has nowhere to put a "different but still valid" observed_at: the ADR-052
        # window between submission and attestation is a live ledger's own elapsed time, too
        # narrow to reliably land a distinct value inside it).
        for key, field in (("device", "device_identity"), ("firmware", "firmware_version")):
            with self.subTest(field=field):
                def forge(record, key=key):
                    return [f"{key}=Something else" if line.startswith(key + "=") else line
                            for line in domain.evidence_lines(record)]
                ledger, records = self.attested_adapter_ledger(full, lines=forge)
                checked = domain.status(ledger, records)
                self.assertEqual(checked["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
                self.assertIn(f"attested {key} differs from the record's {field}", checked["reason"])
        binding = {"task_id": full["task_id"], "revision": full["revision"], "contract_hash": full["contract_hash"],
                  "dispatch_id": full["dispatch_id"], "artifact_sha256": full["artifact_sha256"]}
        attestation = {"operator": full["operator"], "evidence": domain.evidence_lines(full)}
        self.assertEqual(domain.record_problems(full, binding, full["validation_id"], full["level"], attestation), [])
        forged_at = dict(full, observed_at="2001-01-01T00:00:00Z")
        problems = domain.record_problems(forged_at, binding, full["validation_id"], full["level"], attestation)
        self.assertIn("attested observed_at differs from the record's observed_at", problems)
        # The consistent record still verifies on the record basis (UNVERIFIED_ON_HARDWARE only
        # because this packet declares synthetic: true, ADR-050).
        ledger, records = self.attested_adapter_ledger(full)
        checked = domain.status(ledger, records)
        self.assertEqual(checked["evidence_basis"], "record")
        entry = next(v for v in checked["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertTrue(entry["evidence_verified"])

    def test_a_record_bound_to_an_earlier_revision_does_not_verify_a_later_one(self):
        # Codex round 12 on PR #34 (ADR-043): task_id and validation_id identity were checked, but
        # nothing tied a record to which contract revision it was produced under. A revision that
        # keeps the same task, validation ID and rung (as this one does) must still refuse
        # hardware evidence recorded against the earlier, changed revision.
        stale = live(task_id="ACCEPT-SYN-001", revision=1)
        ledger, records = self.attested_adapter_ledger(stale, packet=self.revised_adapter_packet())
        checked = domain.status(ledger, records)
        self.assertEqual(checked["ledger_status"], "ACCEPTED")
        self.assertEqual(checked["revision"], 2)
        self.assertEqual(checked["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertIn("record revision 1 is not the ledger's 2", checked["reason"])
        entry = next(v for v in checked["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertFalse(entry["evidence_verified"])
        # A record made against the actual revision and contract record-verifies (remains
        # UNVERIFIED_ON_HARDWARE only because this packet declares synthetic: true, ADR-050).
        matching = self.revised_adapter_packet()
        current = live(task_id="ACCEPT-SYN-001", revision=2, contract_hash=wp.current(matching)["hash"])
        ledger, records = self.attested_adapter_ledger(current, packet=matching)
        checked = domain.status(ledger, records)
        self.assertEqual(checked["evidence_basis"], "record")
        entry = next(v for v in checked["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertTrue(entry["evidence_verified"])

    def test_a_record_bound_to_a_different_same_numbered_revision_does_not_verify(self):
        # Codex round 13 on PR #34 (ADR-043 extended): revision numbers are lineage-local -- two
        # independently revised variants of the same task can both be "revision 2" with different
        # content. A record observed against one variant must not verify a ledger bound to the
        # other, even though the revision number matches.
        variant_a = self.revised_adapter_packet("Revision 2, variant A.")
        variant_b = self.revised_adapter_packet("Revision 2, variant B.")
        self.assertEqual(wp.current(variant_a)["version"], wp.current(variant_b)["version"])
        self.assertNotEqual(wp.current(variant_a)["hash"], wp.current(variant_b)["hash"])
        record_for_a = live(task_id="ACCEPT-SYN-001", revision=2, contract_hash=wp.current(variant_a)["hash"])
        ledger, records = self.attested_adapter_ledger(record_for_a, packet=variant_b)
        checked = domain.status(ledger, records)
        self.assertEqual(checked["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
        self.assertIn(f"record contract_hash {wp.current(variant_a)['hash']} is not the ledger's "
                      f"{wp.current(variant_b)['hash']}", checked["reason"])
        entry = next(v for v in checked["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertFalse(entry["evidence_verified"])

    def rejected_and_resubmitted_adapter(self, attest_with):
        """A medium-risk SHB-04-adapter ledger accepted after a rejection and a resubmission that
        replaced the result and artifact. `attest_with(original, result, artifact)` chooses the
        record VAL-HIL's post-resubmission attestation binds; returns the ledger and that record."""
        ledger, packet = self.start(packet=self.packet_for("SHB-04-adapter", risk="medium"))
        acceptance.run_checks(ledger, EXAMPLES)
        # Bound to this packet's own contract hash, at its own ("medium") risk -- not
        # adapter_evidence()'s risk="low" packet, which hashes differently.
        original = live(task_id="ACCEPT-SYN-001", contract_hash=wp.current(packet)["hash"])
        acceptance.append(ledger, "ATTESTATION",
                          {"attestation": {"validation_id": "VAL-HIL", "operator": original["operator"],
                                           "evidence": domain.evidence_lines(original)}},
                          previous_state=acceptance.replay(ledger))
        contract = wp.current(packet)["contract"]
        rejection = make_report(self.open_review(ledger), contract, verdict="REJECT_BOUNDED",
                                criteria=[{"criterion_id": "AC-HOST-RULES", "status": "not_met",
                                           "evidence": ["Packet evidence contradicts the claim"]},
                                          {"criterion_id": "AC-HIL-READ", "status": "met",
                                           "evidence": ["Cited from the review packet"]}],
                                contract_failures=[make_failure(ref="AC-HOST-RULES")])
        self.ingest(ledger, rejection)
        self.assertEqual(self.state(ledger)["status"], "REJECTED")
        result = make_result(packet, dispatch_id="f" * 64)
        artifact = make_artifact("a materially different resubmission\n")
        acceptance.append(ledger, "RESUBMIT", {"result": result, "artifact": artifact, "implementers": IMPLEMENTERS},
                          previous_state=acceptance.replay(ledger))
        acceptance.run_checks(ledger, EXAMPLES)
        record = attest_with(original, result, artifact)
        acceptance.append(ledger, "ATTESTATION",
                          {"attestation": {"validation_id": "VAL-HIL", "operator": record["operator"],
                                           "evidence": domain.evidence_lines(record)}},
                          previous_state=acceptance.replay(ledger))
        self.ingest(ledger, make_report(self.open_review(ledger), contract))
        acceptance.accept(ledger, "Independent reviewer")
        return ledger, record

    def test_re_attesting_a_rejected_submissions_record_after_resubmit_is_refused(self):
        # Codex round 16 on PR #34 (ADR-047), closed at append time by round 18's ADR-049: contract
        # identity alone does not identify which implementation was tested. RESUBMIT clears the
        # prior attestation, and re-attesting the same unchanged evidence file -- describing the
        # rejected implementation's observation, never repeated against the resubmission -- is now
        # refused as soon as it is attested, not only when a record is later re-verified. Here the
        # observation's own timestamp predates the resubmission too (ADR-052 on round 20), so that
        # is the bound that fires first; either bound alone would refuse this attestation.
        with self.assertRaisesRegex(ValueError, "before the current result and artifact were submitted"):
            self.rejected_and_resubmitted_adapter(lambda original, result, artifact: original)

    def test_a_record_bound_to_the_resubmission_verifies(self):
        # The other half of the round-16 regression: a record actually made against the
        # resubmission's result and artifact is attested and record-verifies (both remain
        # UNVERIFIED_ON_HARDWARE only because this packet declares synthetic: true, per ADR-050).
        ledger, record = self.rejected_and_resubmitted_adapter(
            lambda original, result, artifact: live(original, dispatch_id=result["dispatch_id"],
                                                     artifact_sha256=acceptance.artifact_identity(artifact)))
        records = self.directory / f"records-{self.counter}"
        records.mkdir()
        (records / "run.json").write_text(json.dumps(record), encoding="utf-8")
        checked = domain.status(ledger, records)
        self.assertEqual(checked["evidence_basis"], "record")
        entry = next(v for v in checked["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertTrue(entry["evidence_verified"])

    def test_evidence_fields_are_compared_exactly_and_only_the_operator_is_case_folded(self):
        # Codex round 2 on PR #34: `device=SN-ABC` must not verify against `device_identity: SN-abc`;
        # a different case is a different unit. The operator keeps the controller's actor normalization.
        full = self.adapter_evidence(device_identity="SN-ABC", operator="Bench Operator")
        transforms = {"device": lambda r: "SN-abc", "firmware": lambda r: r["firmware_version"].upper(),
                     "observed_at": lambda r: r["observed_at"].lower()}
        for key, transform in transforms.items():
            with self.subTest(field=key):
                def forge(record, key=key, transform=transform):
                    other = transform(record)
                    return [f"{key}={other}" if line.startswith(key + "=") else line
                            for line in domain.evidence_lines(record)]
                ledger, records = self.attested_adapter_ledger(full, lines=forge)
                checked = domain.status(ledger, records)
                self.assertEqual(checked["earned_hardware_status"], "UNVERIFIED_ON_HARDWARE")
                self.assertIn(f"attested {key} differs", checked["reason"])

        def forge_operator(record):
            return ["operator=bench operator" if line.startswith("operator=") else line
                    for line in domain.evidence_lines(record)]

        ledger, records = self.attested_adapter_ledger(full, lines=forge_operator, operator="BENCH OPERATOR")
        checked = domain.status(ledger, records)
        self.assertIn("synthetic: true", checked["reason"])  # ADR-050; the case-folded match itself verified
        entry = next(v for v in checked["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertTrue(entry["evidence_verified"])

    def test_record_file_with_a_duplicate_key_is_named_as_refused_not_missing(self):
        # ADR-034: the file the attestation would bind carries outcome fail then pass. It is
        # refused by the loader and status says so, rather than reporting no record at all.
        full = self.adapter_evidence()
        ledger, records = self.attested_adapter_ledger(full)
        full = wp.read_json(records / "run.json")  # the refreshed record attested_adapter_ledger actually attested
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
        self.assertEqual(checked["evidence_basis"], "record")
        entry = next(v for v in checked["validations"] if v["validation_id"] == "VAL-HIL")
        self.assertTrue(entry["evidence_verified"])
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
        record = live(task_id="ACCEPT-SYN-001", operator="Someone else at the bench")
        lines = [line if not line.startswith("operator=") else "operator=Attesting operator"
                 for line in domain.evidence_lines(record)]
        acceptance.append(ledger, "ATTESTATION",
                          {"attestation": {"validation_id": "VAL-HIL", "operator": "Attesting operator", "evidence": lines}},
                          previous_state=acceptance.replay(ledger))
        acceptance.accept(ledger, CONTROLLER)
        before = domain.status(ledger)
        # Attestation-basis status reports what was attested (no operator mismatch here, since
        # nothing re-checks the record without --evidence-dir); UNVERIFIED_ON_HARDWARE only
        # because this packet declares synthetic: true (ADR-050).
        self.assertIn("synthetic: true", before["reason"])
        self.assertEqual(next(v for v in before["validations"] if v["validation_id"] == "VAL-HIL")["gate"], "ATTESTED")
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
        record = live(task_id="ACCEPT-SYN-001")
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
        checked = domain.status(ledger)
        # Acceptance succeeded with the cross-family gate satisfied; UNVERIFIED_ON_HARDWARE only
        # because this packet declares synthetic: true (ADR-050), not for lack of acceptance.
        self.assertEqual(checked["ledger_status"], "ACCEPTED")
        self.assertIn("synthetic: true", checked["reason"])


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
            record = live(task_id="ACCEPT-SYN-001", contract_hash=wp.current(packet)["hash"])
            acceptance.append(ledger, "ATTESTATION",
                              {"attestation": {"validation_id": "VAL-HIL", "operator": record["operator"],
                                               "evidence": domain.evidence_lines(record)}},
                              previous_state=acceptance.replay(ledger))
            acceptance.accept(ledger, CONTROLLER)
            # This packet declares synthetic: true (ADR-050), so earned_hardware_status is capped
            # at UNVERIFIED_ON_HARDWARE throughout; evidence_basis is what this test names.
            attested = self.run_cli("status", ledger)
            self.assertEqual(attested["evidence_basis"], "attestation")
            self.assertIn("synthetic: true", attested["reason"])
            self.assertEqual(next(v for v in attested["validations"] if v["validation_id"] == "VAL-HIL")["gate"],
                             "ATTESTED")
            records = base / "records"
            records.mkdir()
            empty = self.run_cli("status", ledger, "--evidence-dir", records)
            self.assertIn("no hardware evidence record with the attested digest", empty["reason"],
                         "an empty record directory verifies nothing")
            (records / "run.json").write_text(json.dumps(record), encoding="utf-8")
            verified = self.run_cli("status", ledger, "--evidence-dir", records)
            self.assertEqual(verified["evidence_basis"], "record")
            self.assertTrue(next(v for v in verified["validations"] if v["validation_id"] == "VAL-HIL")["evidence_verified"])


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

    def test_published_intake_reference_names_every_validator_field(self):
        # Codex round 8 on PR #34 (ADR-040): the bootstrapper's intake reference still listed the
        # three legacy fields. Every profile's fields must appear in it, in every copy.
        import validate_bootstrap
        copies = [ROOT / "skills/complex-project-bootstrapper/references/intake-schema.md",
                  ROOT / ".agents/skills/complex-project-bootstrapper/references/intake-schema.md",
                  ROOT / ".claude/skills/complex-project-bootstrapper/references/intake-schema.md"]
        texts = [path.read_text(encoding="utf-8") for path in copies]
        self.assertEqual(len(set(texts)), 1, "the intake reference copies differ; run scripts/sync_skills.py")
        for profile, fields in validate_bootstrap.DOMAIN_FIELDS.items():
            row = next(line for line in texts[0].splitlines() if line.startswith(f"| `{profile}` |"))
            for key in fields:
                with self.subTest(profile=profile, key=key):
                    self.assertIn(f"`{key}`", row)

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
