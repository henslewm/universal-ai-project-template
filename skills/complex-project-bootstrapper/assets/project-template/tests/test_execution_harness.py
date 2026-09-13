from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_feedback import ANCHOR, active_project, options, policy, result, timestamp
from test_model_router import config as router_config
from test_model_router import make_packet, resource


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import execution_harness as harness

wp = harness.wp


def configuration():
    value = wp.read_json(ROOT / "config/execution-harness.example.json")
    value["enabled"] = True
    value["bindings"] = [{"resource_id": "local", "harness_id": "cline-cli", "provider": "lmstudio",
                          "model": "synthetic-local-coder", "api_base": "http://127.0.0.1:1234/v1",
                          "credential_env": None}]
    return value


class HarnessConfigTests(unittest.TestCase):
    def test_example_configuration_is_valid_disabled_and_credential_free(self):
        example = wp.read_json(ROOT / "config/execution-harness.example.json")
        harness.config_valid(example)
        self.assertFalse(example["enabled"], "The committed example must not be dispatch-enabled")
        for binding in example["bindings"]:
            self.assertIsNone(binding["credential_env"] or None if binding["credential_env"] is None else None)
        self.assertTrue(any(binding["credential_env"] for binding in example["bindings"]),
                        "A cloud tier should demonstrate environment-named credentials")
        self.assertTrue(any(item["adapter"] == "command" for item in example["harnesses"]),
                        "A replacement harness must be demonstrated so Cline is visibly optional")

    def test_configuration_refuses_credentials_unknown_placeholders_and_bad_bindings(self):
        for mutate, expected in (
            (lambda c: c["bindings"][0].update(credential_env="not-an-env-name"), "environment-variable name"),
            (lambda c: c["bindings"][0].update(harness_id="absent-harness"), "unknown harness"),
            (lambda c: c["bindings"][0].update(api_base="file:///etc/passwd"), "Unsafe API base"),
            (lambda c: c["harnesses"][0]["argv"].append("--key={provider_secret}"), "Unsupported placeholder"),
            (lambda c: c["harnesses"][0].update(command="{brief}"), "command itself cannot be templated"),
            (lambda c: c["harnesses"][0].update(argv=[a.replace("{brief}", "") for a in c["harnesses"][0]["argv"]]),
             "must receive the brief"),
            (lambda c: c["harnesses"][0].update(argv=[a.replace("{report}", "") for a in c["harnesses"][0]["argv"]]),
             "must write a report"),
            (lambda c: c["harnesses"][0]["argv"].append("--api-key=sk-abcdefghijklmnopqrstuvwxyz"), "credential-like"),
            (lambda c: c["harnesses"][0]["argv"].append("authorization: Bearer x"), "credential-like"),
        ):
            with self.subTest(expected=expected):
                value = configuration()
                mutate(value)
                with self.assertRaisesRegex(ValueError, expected):
                    harness.config_valid(value)

    def test_duplicate_harness_and_resource_bindings_are_refused(self):
        value = configuration()
        value["harnesses"].append(copy.deepcopy(value["harnesses"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate harness id"):
            harness.config_valid(value)
        value = configuration()
        value["bindings"].append(copy.deepcopy(value["bindings"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate routed resource"):
            harness.config_valid(value)


class HarnessBase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.project = self.base / "project"
        active_project(self.project)
        self.ledger = self.base / "ledger"
        self.config = configuration()
        self.router = router_config(resource())
        self.packet = make_packet()
        patch = mock.patch.object(harness.feedback, "active_anchor", return_value=ANCHOR)
        patch.start()
        self.addCleanup(patch.stop)
        harness.feedback.initialize(self.ledger, self.packet, [self.packet], policy(), self.router,
                                    self.project, "Synthetic architect", timestamp())

    def fresh_ledger(self, name):
        path = self.base / name
        harness.feedback.initialize(path, self.packet, [self.packet], policy(), self.router,
                                    self.project, "Synthetic architect", timestamp())
        return path

    def prepare(self, destination="run-1"):
        return harness.dispatch(self.ledger, self.config, self.router, options(),
                                self.project, self.base / destination)

class HarnessDispatchTests(HarnessBase):
    def test_dispatch_prepares_a_bounded_brief_and_never_executes_the_harness(self):
        with mock.patch("subprocess.run", side_effect=AssertionError("the adapter must not run a harness")):
            prepared = self.prepare()
        self.assertEqual(prepared["status"], "PREPARED")
        self.assertFalse(prepared["executed"])
        self.assertFalse(prepared["execution_authorized"])
        destination = Path(prepared["destination"])
        brief = wp.read_json(destination / "brief.json")
        self.assertEqual(brief["dispatch_id"], prepared["dispatch_id"])
        self.assertEqual(brief["harness"]["model"], "synthetic-local-coder")
        self.assertTrue((destination / "BOUNDED_WORKER_RULES.md").exists())
        self.assertTrue((destination / "workspace").is_dir())
        self.assertFalse((destination / "report.json").exists(), "the worker writes its own report")
        plan = wp.read_json(destination / "invocation.json")
        self.assertEqual(plan["argv"][0], "cline")
        rendered = "\u0000".join(plan["argv"])
        for path in ("brief.json", "report.json", "BOUNDED_WORKER_RULES.md", "workspace"):
            self.assertIn(str(destination / path), rendered)
        self.assertNotIn("{", rendered, "every placeholder must be substituted")
        self.assertEqual(plan["required_environment"], [])

    def test_brief_is_readable_line_by_line_and_states_the_whole_report_contract(self):
        prepared = self.prepare()
        path = Path(prepared["destination"]) / "brief.json"
        text = path.read_text(encoding="utf-8")
        # A line-based reader must not need a workaround: the brief is indented, not one long line.
        self.assertGreater(len(text.splitlines()), 20)
        self.assertLess(max(len(line) for line in text.splitlines()), 2000)
        contract = wp.read_json(path)["report_contract"]
        self.assertEqual(contract["validation_check_fields"],
                         sorted(harness.feedback.SCHEMA["$defs"]["validation_check"]["required"]))
        self.assertIn("check_id", contract["validation_check_fields"])
        self.assertNotIn("id", contract["validation_check_fields"])
        rules = " ".join(contract["rules"])
        self.assertIn("check_id, not id", rules)
        # Every value the validator enforces is stated, so a compliant worker can actually comply.
        self.assertEqual(sorted(contract["required_fields"]), sorted(harness.REPORT_FIELDS))
        self.assertIn("PROVIDER_UNAVAILABLE", contract["outcomes"])
        self.assertEqual(contract["scope_status_values"], ["within", "violated", "unknown"])
        # A report built strictly from the stated contract is accepted.
        report = {field: None for field in contract["required_fields"]}
        report.update(dispatch_id=prepared["dispatch_id"], outcome="PASS", scope_status="within",
                      summary="Built only from the fields the brief states.", architecture_conflict=False,
                      evidence=["command, stdout and exit code"], discoveries=[], api_cost_usd=0,
                      cost_evidence="Local worker; no metered usage.",
                      validation=[{"check_id": check["id"], "passed": True, "failure_code": "",
                                   "expected": "checker exits 0", "actual": "checker exited 0",
                                   "evidence": ["python workspace/check.py -> ALL CHECKS PASSED"]}
                                  for check in wp.read_json(path)["contract"]["validation"]])
        wp.write_new(Path(prepared["destination"]) / "report.json", json.dumps(report, indent=2))
        ingested = harness.ingest(self.ledger, self.config, Path(prepared["destination"]) / "report.json")
        self.assertEqual(ingested["outcome"], "PASS")

    def test_brief_carries_only_packet_permitted_context_and_stays_bounded(self):
        prepared = self.prepare()
        brief = wp.read_json(Path(prepared["destination"]) / "brief.json")
        harness.feedback.exact(brief, {"schema_version", "dispatch_id", "binding", "harness", "bounds",
                                       "contract", "architect_guidance", "prior_failures",
                                       "failure_groups", "worker_rule", "report_contract"})
        contract = wp.current(self.packet)["contract"]
        self.assertEqual(brief["contract"], contract)
        for required in ("scope", "context_scope", "architecture_boundaries", "non_goals", "validation"):
            self.assertIn(required, brief["contract"])
        self.assertIn("Execute only this contract", brief["worker_rule"])
        self.assertLessEqual(brief["bounds"]["remaining_task_attempts"], contract["retry_budget"]["max_attempts"])


    def test_disabled_configuration_refuses_before_spending_a_reservation(self):
        disabled = configuration()
        disabled["enabled"] = False
        with self.assertRaisesRegex(ValueError, "disabled"):
            harness.dispatch(self.ledger, disabled, self.router, options(), self.project, self.base / "off")
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["attempts"], [])

    def test_unpreparable_dispatch_closes_its_attempt_as_provider_unavailable(self):
        for name, mutate, expected in (
            ("unbound", lambda c: c["bindings"][0].update(resource_id="some-other-resource"),
             "No harness binding for routed resource"),
            ("oversize-brief", lambda c: c["limits"].update(brief_max_chars=1000),
             "Brief exceeds its configured bound"),
        ):
            with self.subTest(case=name):
                value = configuration()
                mutate(value)
                # A spent reservation escalates the controller, so each case needs its own ledger.
                outcome = harness.dispatch(self.fresh_ledger("ledger-" + name), value, self.router,
                                           options(), self.project, self.base / name)
                self.assertEqual(outcome["status"], "HARNESS_UNAVAILABLE")
                self.assertRegex(outcome["reason"], expected)
                self.assertFalse(outcome["prepared"])
                self.assertTrue(outcome["attempt_closed"])
                state = harness.feedback.replay(self.base / ("ledger-" + name))[0]
                self.assertIsNone(state["pending"], "a spent reservation must not be left pending")
                self.assertEqual(state["status"], "NEEDS_ARCHITECT")
                self.assertEqual(state["attempts"][-1]["result"]["outcome"], "PROVIDER_UNAVAILABLE")
                self.assertFalse((self.base / name / "brief.json").exists())

    def test_a_second_dispatch_cannot_reserve_while_one_attempt_is_pending(self):
        prepared = self.prepare()
        self.assertEqual(prepared["status"], "PREPARED")
        with self.assertRaisesRegex(ValueError, "pending dispatch"):
            self.prepare("run-2")

    def test_reused_destination_is_refused_so_evidence_is_never_overwritten(self):
        prepared = self.prepare()
        with self.assertRaises(FileExistsError):
            harness.dispatch(self.ledger, self.config, self.router, options(), self.project,
                             Path(prepared["destination"]))


class HarnessReportTests(HarnessBase):
    def report(self, prepared, **changes):
        value = result({"dispatch_id": prepared["dispatch_id"]}, self.packet, **changes)
        path = Path(prepared["destination"]) / "report.json"
        wp.write_new(path, json.dumps(value, indent=2))
        return value, path

    def test_failed_attempt_is_recorded_with_preserved_evidence_for_the_next_tier(self):
        prepared = self.prepare()
        _, path = self.report(prepared, outcome="FAIL", passed=False)
        ingested = harness.ingest(self.ledger, self.config, path)
        self.assertEqual(ingested["outcome"], "FAIL")
        self.assertTrue(ingested["evidence_preserved"])
        self.assertFalse(ingested["independent_acceptance"])
        self.assertEqual(ingested["attempts_used"], 1)
        state = harness.feedback.replay(self.ledger)[0]
        self.assertIsNone(state["pending"])
        self.assertTrue(state["attempts"][-1]["fingerprint"])
        # The preserved failure reaches the next worker brief rather than being rebuilt.
        following = self.prepare("run-next")
        brief = wp.read_json(Path(following["destination"]) / "brief.json")
        self.assertEqual(len(brief["prior_failures"]), 1)
        self.assertEqual(brief["prior_failures"][0]["fingerprint"], state["attempts"][-1]["fingerprint"])

    def test_report_must_match_its_dispatch_contract_and_carry_no_credentials(self):
        prepared = self.prepare()
        contract = wp.current(self.packet)["contract"]
        for mutate, expected in (
            (lambda r: r.update(dispatch_id="f" * 64), "does not match the reserved dispatch"),
            (lambda r: r["validation"].append({**r["validation"][0], "check_id": "invented-check"}),
             "and no other id"),
            (lambda r: r["validation"].clear(), "Report every contract validation check"),
            (lambda r: r.update(evidence=[]), "requires evidence"),
            (lambda r: r.update(outcome="PASS"), "PASS requires every validation check to pass"),
            (lambda r: r.update(extra_field="widened"), "Expected fields"),
            (lambda r: r.update(cost_evidence="api_key: sk-abcdefghijklmnopqrstuvwxyz"), "credential-like"),
        ):
            with self.subTest(expected=expected):
                value = result({"dispatch_id": prepared["dispatch_id"]}, self.packet)
                mutate(value)
                with self.assertRaisesRegex(ValueError, expected):
                    harness.report_valid(value, contract, prepared["dispatch_id"],
                                         self.config["limits"], len(json.dumps(value)))
        oversize = configuration()
        oversize["limits"]["report_max_bytes"] = 200
        _, path = self.report(prepared)
        with self.assertRaisesRegex(ValueError, "Worker report exceeds"):
            harness.ingest(self.ledger, oversize, path)

    def test_a_worker_cannot_claim_pass_while_reporting_scope_or_architecture_problems(self):
        prepared = self.prepare()
        contract = wp.current(self.packet)["contract"]
        for field, value in (("scope_status", "violated"), ("scope_status", "unknown"),
                             ("architecture_conflict", True)):
            with self.subTest(field=field, value=value):
                report = result({"dispatch_id": prepared["dispatch_id"]}, self.packet,
                                outcome="PASS", passed=True)
                report[field] = value
                with self.assertRaises(ValueError):
                    harness.report_valid(report, contract, prepared["dispatch_id"],
                                         self.config["limits"], len(json.dumps(report)))

    def test_verify_report_checks_a_run_without_recording_or_accepting_it(self):
        prepared = self.prepare()
        brief_path = Path(prepared["destination"]) / "brief.json"
        _, path = self.report(prepared, outcome="PASS", passed=True)
        verified = harness.verify_report(self.config, brief_path, path)
        self.assertTrue(verified["valid"])
        self.assertEqual(verified["outcome"], "PASS")
        self.assertEqual(verified["checks_passed"], verified["checks_total"])
        self.assertFalse(verified["recorded_in_ledger"])
        self.assertFalse(verified["independent_acceptance"])
        # Verification must not touch the ledger, so the attempt is still pending.
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["pending"], prepared["dispatch_id"])
        # It applies the same report contract as ingestion.
        broken = wp.read_json(path)
        broken["validation"][0]["check_id"] = "invented-check"
        wp.write_new(Path(prepared["destination"]) / "broken.json", json.dumps(broken))
        with self.assertRaisesRegex(ValueError, "and no other id"):
            harness.verify_report(self.config, brief_path, Path(prepared["destination"]) / "broken.json")
        # A brief that is not a harness brief is refused rather than trusted.
        wp.write_new(Path(prepared["destination"]) / "not-a-brief.json", json.dumps({"contract": {}}))
        with self.assertRaisesRegex(ValueError, "Expected fields"):
            harness.verify_report(self.config, Path(prepared["destination"]) / "not-a-brief.json", path)

    def test_a_worker_that_writes_nothing_does_not_strand_the_attempt(self):
        prepared = self.prepare()
        missing = Path(prepared["destination"]) / "report.json"
        self.assertFalse(missing.exists())
        # Absence is refused rather than inferred, and the reservation is still pending.
        with self.assertRaisesRegex(ValueError, "record the attempt with abandon"):
            harness.ingest(self.ledger, self.config, missing)
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["pending"], prepared["dispatch_id"])
        for reason, expected in (("too short", "requires a specific recorded reason"),
                                 ("api_key: sk-abcdefghijklmnopqrstuvwxyz0123", "credential-like")):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, expected):
                    harness.abandon(self.ledger, self.config, reason)
        closed = harness.abandon(self.ledger, self.config,
                                 "The local worker narrated tool calls as prose, never read the brief and wrote no report.")
        self.assertEqual(closed["outcome"], "FAIL")
        self.assertTrue(closed["evidence_preserved"])
        self.assertTrue(closed["fingerprint"])
        state = harness.feedback.replay(self.ledger)[0]
        self.assertIsNone(state["pending"], "an abandoned attempt must not stay pending")
        self.assertIn("attempt-abandoned", state["attempts"][-1]["result"]["evidence"][0])
        with self.assertRaisesRegex(ValueError, "No reserved dispatch"):
            harness.abandon(self.ledger, self.config, "Nothing is pending, so there is nothing to abandon here.")
        # Scope is genuinely unknown when nothing was reported, so the architect decides rather than
        # the controller looping a worker that may be structurally unable to complete the packet.
        self.assertEqual(closed["status"], "NEEDS_ARCHITECT")
        self.assertEqual(state["status"], "NEEDS_ARCHITECT")
        with self.assertRaisesRegex(ValueError, "Controller hold"):
            self.prepare("run-after-abandon")
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["attempts"][-1]["result"]["scope_status"], "unknown")

    def test_a_refused_malformed_report_can_also_be_abandoned(self):
        prepared = self.prepare()
        broken = Path(prepared["destination"]) / "report.json"
        wp.write_new(broken, json.dumps({"validation": "not even the right shape"}))
        with self.assertRaises(ValueError):
            harness.ingest(self.ledger, self.config, broken)
        self.assertEqual(harness.feedback.replay(self.ledger)[0]["pending"], prepared["dispatch_id"])
        closed = harness.abandon(self.ledger, self.config,
                                 "The worker wrote a report that does not match the required field set.")
        self.assertEqual(closed["outcome"], "FAIL")
        self.assertIsNone(harness.feedback.replay(self.ledger)[0]["pending"])

    def test_ingest_requires_a_reserved_dispatch(self):
        _, path = self.report({"dispatch_id": "a" * 64, "destination": str(self.base)})
        with self.assertRaisesRegex(ValueError, "No reserved dispatch"):
            harness.ingest(self.ledger, self.config, path)


if __name__ == "__main__":
    unittest.main()
