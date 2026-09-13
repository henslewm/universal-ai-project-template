from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from test_model_router import config as router_config
from test_model_router import make_packet, resource


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("feedback_under_test", ROOT / "scripts/feedback.py")
feedback = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(feedback)
wp = feedback.wp
ANCHOR = "a" * 64
BASE_TIME = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)


def timestamp(seconds=0):
    return (BASE_TIME + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def policy(**changes):
    value = wp.read_json(ROOT / "config/feedback.example.json")
    value.update(changes)
    return value


def options():
    return {"task_class": "synthetic-parser", "input_tokens": 1000, "output_tokens": 1000,
            "unavailable_providers": [], "unavailable_resources": []}


def result(dispatch, packet, outcome="FAIL", passed=False, actual="observed wrong value", evidence="RAW-FIRST"):
    return {
        "dispatch_id": dispatch["dispatch_id"], "outcome": outcome,
        "summary": "Synthetic result; no real work or provider invocation claimed.",
        "scope_status": "within", "architecture_conflict": False,
        "validation": [{"check_id": check["id"], "passed": passed,
                        "failure_code": "" if passed else "VALUE_MISMATCH",
                        "expected": "expected value", "actual": actual,
                        "evidence": ["Synthetic objective-check record"]}
                       for check in wp.current(packet)["contract"]["validation"]],
        "evidence": [evidence], "discoveries": [], "api_cost_usd": 0,
        "cost_evidence": "Synthetic zero-cost fixture; no model calls made.",
    }


def diagnosis(classification="REPAIR_CONTRACT", revised=None, anchor=ANCHOR):
    return {"classification": classification, "reason": "Synthetic architect diagnosis",
            "evidence": ["Synthetic architecture review"], "architecture_fingerprint": anchor,
            "revised_contract": revised}


def packet_with_caps(retries=8, caps=None):
    value = make_packet(retries=retries)
    if caps is None:
        return value
    contract = copy.deepcopy(wp.current(value)["contract"])
    contract["retry_budget"]["max_attempts_by_tier"] = caps
    value = wp.create(value["task_id"], value["domain_profile"], contract, "Architect", "Synthetic tier overrides", timestamp())
    for target in ("ARCHITECTED", "READY"):
        value = wp.transition(value, target, "architect", "Architect", "Synthetic readiness", ["Synthetic evidence"], timestamp=timestamp())
    return value


def active_project(directory):
    """Construct disposable, explicitly synthetic approval records and bound files."""
    directory.mkdir()
    (directory / "config").mkdir()
    bootstrap = wp.read_json(ROOT / "config/bootstrap.example.json")
    project = bootstrap["project"]
    configuration = {"domain_profile": bootstrap["domain_profile"], "project_name": project["name"],
                     "objective": project["objective"], "success_criteria": project["definition_of_done"],
                     "out_of_scope": project["non_goals"], "constraints": project["constraints"],
                     "source_locations": bootstrap["sources"]}
    (directory / "config/project.json").write_text(json.dumps(configuration), encoding="utf-8")
    for name in feedback.bootstrap.BOUND_DOCUMENTS:
        (directory / name).write_text(f"# Synthetic fixture: {name}\nNo real project approval or external action.\n", encoding="utf-8")
    bootstrap["configuration"] = configuration
    bootstrap["documents"] = feedback.bootstrap.document_hashes(directory)
    bootstrap["state"] = "ACTIVE"
    anchor = feedback.bootstrap.architecture_fingerprint(bootstrap)
    bootstrap["approval"] = {"approved": True, "approved_by": "Synthetic test user",
                             "approved_at": timestamp(), "architecture_fingerprint": anchor}
    (directory / "config/bootstrap.json").write_text(json.dumps(bootstrap), encoding="utf-8")
    assert feedback.bootstrap.validate(bootstrap, directory) == []
    return anchor


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        anchor_patch = mock.patch.object(feedback, "active_anchor", return_value=ANCHOR)
        self.anchor = anchor_patch.start()
        self.addCleanup(anchor_patch.stop)
        self.counter = 0
        self.time = 0
        self.settings = router_config(*(resource(f"tier-{tier}", tier=tier, latency=tier) for tier in (1, 2, 3, 4)))
        self.settings["policy"]["failures_per_tier"] = 20

    def tick(self):
        self.time += 1
        return timestamp(self.time)

    def start(self, packet=None, limits=None, settings=None):
        self.counter += 1
        directory = self.directory / f"ledger-{self.counter}"
        packet = packet or make_packet()
        feedback.initialize(directory, packet, [packet], limits or policy(), settings or self.settings,
                            self.directory, "Architect", self.tick())
        return directory

    def reserve(self, directory, settings=None):
        return feedback.reserve(directory, settings or self.settings, options(), self.directory, self.tick())

    def complete(self, directory, dispatch, **changes):
        packet = feedback.replay(directory)[0]["packet"]
        reported = result(dispatch, packet, **changes)
        return feedback.complete(directory, reported, self.tick())

    def hold(self, directory, architecture=False):
        dispatch = self.reserve(directory)
        packet = feedback.replay(directory)[0]["packet"]
        reported = result(dispatch, packet)
        reported["architecture_conflict"] = architecture
        if not architecture:
            reported["scope_status"] = "unknown"
        return feedback.complete(directory, reported, self.tick())

    def repair(self, directory, **changes):
        state = feedback.replay(directory)[0]
        revised = copy.deepcopy(wp.current(state["packet"])["contract"])
        revised["goal"] += " Clarified synthetic objective."
        revised.update(changes)
        return feedback.diagnose(directory, diagnosis(revised=revised), "Architect", self.directory, self.tick())

    def test_initialization_freezes_caps_policy_and_caller_inputs(self):
        packet = packet_with_caps(retries=3, caps={"1": 1, "2": 2})
        limits = policy()
        preserved = copy.deepcopy((packet, limits, self.settings))
        directory = self.start(packet, limits)
        packet["state"] = "BLOCKED"
        limits["max_attempts_by_tier"]["1"] = 20
        state, sequence, last_hash = feedback.replay(directory)
        self.assertEqual(sequence, 1)
        self.assertRegex(last_hash, r"^[a-f0-9]{64}$")
        self.assertEqual(state["packet"], preserved[0])
        self.assertEqual(state["policy"], preserved[1])
        self.assertEqual(state["total_cap"], 3)
        self.assertEqual(state["caps"]["1"], 1)
        self.assertEqual(state["caps"]["2"], 2)
        self.assertEqual(state["attempts"], [])

    def test_total_and_per_tier_attempt_caps_end_dispatch(self):
        directory = self.start(packet_with_caps(retries=3, caps={"1": 1, "2": 2}),
                               policy(repeated_failure_per_tier=20, repeated_failure_total=20))
        tiers = []
        for index in range(3):
            dispatch = self.reserve(directory)
            self.assertEqual(dispatch["status"], "DISPATCH")
            tiers.append(dispatch["routing"]["decision"]["selected"]["tier"])
            self.complete(directory, dispatch, actual=f"Distinct observed value {index}")
        self.assertEqual(tiers, [1, 2, 2])
        halted = self.reserve(directory)
        self.assertEqual(halted["status"], "NEEDS_ARCHITECT")
        self.assertEqual(halted["reason"], "TOTAL_ATTEMPT_LIMIT")
        self.assertEqual(len(feedback.replay(directory)[0]["attempts"]), 3)
        with self.assertRaises(ValueError):
            self.reserve(directory)

    def test_repeated_fingerprint_escalates_with_raw_and_focused_evidence(self):
        directory = self.start(limits=policy(max_history_entries=1))
        first = self.reserve(directory)
        self.complete(directory, first, evidence="RAW-FIRST")
        second = self.reserve(directory)
        second_result = result(second, feedback.replay(directory)[0]["packet"],
                               actual="\x1b[31mobserved   wrong\nvalue\x1b[0m", evidence="RAW-SECOND")
        second_result["summary"] = "Different wording does not change the objective failure."
        state = feedback.complete(directory, second_result, self.tick())
        self.assertEqual(state["reason"], "REPEATED_FAILURE_TIER_LIMIT")
        self.assertEqual(state["attempts"][-1]["routing_outcome"], "NEEDS_ESCALATION")
        self.assertEqual(state["attempts"][0]["fingerprint"], state["attempts"][1]["fingerprint"])
        third = self.reserve(directory)
        self.assertEqual(third["routing"]["decision"]["selected"]["tier"], 2)
        state = self.complete(directory, third, evidence="RAW-THIRD")
        self.assertEqual(state["status"], "NEEDS_ARCHITECT")
        self.assertEqual(state["reason"], "REPEATED_FAILURE_TASK_LIMIT")
        focused = feedback.worker_context(state)
        self.assertEqual(len(focused["recent_failures"]), 1)
        self.assertEqual(len(focused["failure_groups"]), 1)
        group = focused["failure_groups"][0]
        self.assertEqual(group["count"], 3)
        self.assertEqual(group["tiers"], {"1": 2, "2": 1})
        self.assertEqual(group["first_evidence"], ["RAW-FIRST"])
        self.assertEqual(group["latest_evidence"], ["RAW-THIRD"])
        self.assertEqual(state["attempts"][1]["result"], second_result)
        self.assertEqual(len(state["attempts"]), 3)

    def test_meaningfully_different_failures_are_not_collapsed(self):
        directory = self.start()
        for index in range(3):
            dispatch = self.reserve(directory)
            reported = result(dispatch, feedback.replay(directory)[0]["packet"])
            if index == 1:
                reported["validation"][0]["failure_code"] = "DIFFERENT_FAILURE"
            elif index == 2:
                reported["validation"][0]["actual"] = "Different actual value"
            state = feedback.complete(directory, reported, self.tick())
            self.assertEqual(state["status"], "IN_PROGRESS")
        self.assertEqual(len({item["fingerprint"] for item in state["attempts"]}), 3)
        self.assertTrue(all(item["count"] == 1 for item in feedback.failure_groups(state)))

    def test_integer_valued_float_tier_uses_the_same_repeated_failure_counter(self):
        settings = copy.deepcopy(self.settings)
        settings["resources"][0]["tier"] = 1.0
        limits = policy(repeated_failure_per_tier=2, repeated_failure_total=20,
                        max_attempts_by_tier={str(tier): 8 for tier in range(5)})
        directory = self.start(limits=limits, settings=settings)
        for _ in range(2):
            dispatch = self.reserve(directory, settings)
            self.assertEqual(dispatch["routing"]["decision"]["selected"]["tier"], 1)
            state = self.complete(directory, dispatch)
        self.assertEqual(state["reason"], "REPEATED_FAILURE_TIER_LIMIT")
        self.assertEqual(feedback.failure_groups(state)[0]["tiers"], {"1": 2})
        dispatched = self.reserve(directory, settings)
        self.assertEqual(dispatched["routing"]["decision"]["selected"]["tier"], 2)

    def test_pending_dispatch_survives_replay_and_prevents_duplicate_work(self):
        directory = self.start()
        reserved = self.reserve(directory)
        before = {path.name: path.read_bytes() for path in directory.iterdir()}
        state, sequence, _ = feedback.replay(directory)
        self.assertEqual(sequence, 2)
        self.assertEqual(state["pending"], reserved["dispatch_id"])
        self.assertEqual(len(state["attempts"]), 1)
        self.assertIsNone(state["attempts"][0]["result"])
        with self.assertRaisesRegex(ValueError, "pending"):
            self.reserve(directory)
        self.assertEqual({path.name: path.read_bytes() for path in directory.iterdir()}, before)

    def test_directory_sync_follows_complete_closed_event_before_dispatch_returns(self):
        directory = self.start()
        order, written_handles = [], []
        original_open = Path.open
        original_fsync = feedback.os.fsync

        def tracked_open(path, *args, **kwargs):
            handle = original_open(path, *args, **kwargs)
            mode = args[0] if args else kwargs.get("mode", "r")
            if path.parent == directory and mode == "x":
                written_handles.append(handle)
            return handle

        def file_sync(descriptor):
            order.append("file_fsync")
            return original_fsync(descriptor)

        def directory_sync(path):
            self.assertEqual(path, directory)
            self.assertEqual(order, ["file_fsync"])
            self.assertEqual(len(written_handles), 1)
            self.assertTrue(written_handles[0].closed)
            event = wp.read_json(directory / "00000002.json")
            self.assertEqual(event["kind"], "DISPATCH")
            state, sequence, last_hash = feedback.replay(directory)
            self.assertEqual(sequence, 2)
            self.assertEqual(last_hash, event["hash"])
            self.assertEqual(state["pending"], state["attempts"][0]["id"])
            order.append("directory_fsync")

        with mock.patch.object(Path, "open", new=tracked_open), \
                mock.patch.object(feedback.os, "fsync", side_effect=file_sync), \
                mock.patch.object(feedback, "sync_directory", side_effect=directory_sync):
            dispatch = self.reserve(directory)
            order.append("intent_returned")
        self.assertEqual(dispatch["status"], "DISPATCH")
        self.assertEqual(order, ["file_fsync", "directory_fsync", "intent_returned"])

    def test_directory_sync_failure_returns_no_intent_but_retains_pending_reservation(self):
        directory = self.start()
        returned = []
        with mock.patch.object(feedback, "sync_directory", side_effect=OSError("Directory sync failed")):
            with self.assertRaisesRegex(OSError, "Directory sync failed"):
                returned.append(self.reserve(directory))
        self.assertEqual(returned, [])
        state, sequence, _ = feedback.replay(directory)
        self.assertEqual(sequence, 2)
        self.assertEqual(len(state["attempts"]), 1)
        self.assertEqual(state["pending"], state["attempts"][0]["id"])
        self.assertIsNone(state["attempts"][0]["result"])
        with self.assertRaisesRegex(ValueError, "pending"):
            self.reserve(directory)
        self.assertEqual(feedback.replay(directory)[1], 2)

    def test_initialization_syncs_existing_parent_before_init_event_and_ledger_after(self):
        directory = self.directory / "durable-init"
        packet = make_packet()
        order = []

        def directory_sync(path):
            if not order:
                self.assertEqual(path, self.directory)
                self.assertTrue(directory.is_dir())
                self.assertEqual(list(directory.iterdir()), [])
                order.append("parent_synced")
            else:
                self.assertEqual(path, directory)
                self.assertEqual(order, ["parent_synced"])
                event = wp.read_json(directory / "00000001.json")
                self.assertEqual(event["kind"], "INIT")
                self.assertEqual(feedback.replay(directory)[1], 1)
                order.append("ledger_synced")

        with mock.patch.object(feedback, "sync_directory", side_effect=directory_sync):
            state = feedback.initialize(directory, packet, [packet], policy(), self.settings,
                                        self.directory, "Architect", self.tick())
            order.append("initialization_returned")
        self.assertEqual(state["status"], "READY")
        self.assertEqual(order, ["parent_synced", "ledger_synced", "initialization_returned"])

    def test_initialization_refuses_missing_parent_without_creating_ancestor_directories(self):
        missing_parent = self.directory / "missing-parent"
        directory = missing_parent / "ledger"
        packet = make_packet()
        with mock.patch.object(feedback, "sync_directory") as synchronized:
            with self.assertRaises(FileNotFoundError):
                feedback.initialize(directory, packet, [packet], policy(), self.settings,
                                    self.directory, "Architect", self.tick())
        self.assertFalse(missing_parent.exists())
        self.assertFalse(directory.exists())
        synchronized.assert_not_called()

    def test_concurrent_reservations_have_exactly_one_exclusive_winner(self):
        directory = self.start()
        original_replay = feedback.replay
        barrier = threading.Barrier(2)

        def synchronized_snapshot(path):
            prior = original_replay(path)
            barrier.wait(timeout=10)
            return prior

        with mock.patch.object(feedback, "replay", side_effect=synchronized_snapshot):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(feedback.reserve, directory, self.settings, options(), self.directory, timestamp(20)) for _ in range(2)]
                outcomes = []
                for future in futures:
                    try:
                        outcomes.append(future.result(timeout=20))
                    except FileExistsError as error:
                        outcomes.append(error)
        self.assertEqual(sum(isinstance(item, dict) and item["status"] == "DISPATCH" for item in outcomes), 1)
        self.assertEqual(sum(isinstance(item, FileExistsError) for item in outcomes), 1)
        state, sequence, _ = feedback.replay(directory)
        self.assertEqual(sequence, 2)
        self.assertEqual(len(state["attempts"]), 1)
        self.assertIsNotNone(state["pending"])

    def test_wrong_duplicate_and_invalid_results_do_not_consume_resolution(self):
        directory = self.start()
        dispatch = self.reserve(directory)
        packet = feedback.replay(directory)[0]["packet"]
        for kind in ("wrong-dispatch", "unknown-check", "duplicate-check", "blank-code"):
            with self.subTest(kind=kind):
                reported = result(dispatch, packet)
                if kind == "wrong-dispatch":
                    reported["dispatch_id"] = "0" * 64
                elif kind == "unknown-check":
                    reported["validation"][0]["check_id"] = "UNKNOWN"
                elif kind == "duplicate-check":
                    reported["validation"].append(copy.deepcopy(reported["validation"][0]))
                else:
                    reported["validation"][0]["failure_code"] = " \t"
                with self.assertRaises(ValueError):
                    feedback.complete(directory, reported, self.tick())
                self.assertEqual(feedback.replay(directory)[1], 2)
                self.assertEqual(feedback.replay(directory)[0]["pending"], dispatch["dispatch_id"])
        reported = result(dispatch, packet)
        feedback.complete(directory, reported, self.tick())
        with self.assertRaisesRegex(ValueError, "pending dispatch"):
            feedback.complete(directory, reported, self.tick())
        self.assertEqual(feedback.replay(directory)[1], 3)

    def test_corrupted_gapped_partial_and_unexpected_log_entries_fail_closed(self):
        for corruption in ("hash", "gap", "partial", "extra"):
            with self.subTest(corruption=corruption):
                directory = self.start()
                self.reserve(directory)
                if corruption == "hash":
                    path = directory / "00000001.json"
                    event = wp.read_json(path)
                    event["data"]["architect"] = "Changed without rehashing"
                    path.write_text(json.dumps(event), encoding="utf-8")
                elif corruption == "gap":
                    (directory / "00000002.json").rename(directory / "00000004.json")
                elif corruption == "partial":
                    (directory / "00000003.json").write_text('{"sequence":3,', encoding="utf-8")
                else:
                    (directory / "unexpected.txt").write_text("Unexpected file", encoding="utf-8")
                before = {path.name: path.read_bytes() for path in directory.iterdir()}
                with self.assertRaises(ValueError):
                    feedback.replay(directory)
                with self.assertRaises(ValueError):
                    self.reserve(directory)
                self.assertEqual({path.name: path.read_bytes() for path in directory.iterdir()}, before)

    def test_passing_result_only_moves_packet_to_independent_review(self):
        directory = self.start()
        dispatch = self.reserve(directory)
        state = self.complete(directory, dispatch, outcome="PASS", passed=True)
        self.assertEqual(state["status"], "REVIEW_PENDING")
        self.assertEqual(state["packet"]["state"], "REVIEW")
        self.assertEqual(state["attempts"][0]["routing_outcome"], "PASS")
        self.assertNotIn("ACCEPTED", [event["to"] for event in state["packet"]["events"]])
        with self.assertRaises(ValueError):
            self.reserve(directory)

    def test_claimed_pass_with_failed_or_missing_validation_is_recorded_as_failure(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                directory = self.start()
                dispatch = self.reserve(directory)
                reported = result(dispatch, feedback.replay(directory)[0]["packet"], outcome="PASS")
                if missing:
                    reported["validation"] = []
                state = feedback.complete(directory, reported, self.tick())
                self.assertEqual(state["status"], "IN_PROGRESS")
                self.assertEqual(state["reason"], "PASS_CONTRADICTED_BY_VALIDATION")
                self.assertEqual(state["attempts"][0]["result"]["outcome"], "PASS")
                self.assertEqual(state["attempts"][0]["routing_outcome"], "FAIL")
                self.assertIsNotNone(state["attempts"][0]["fingerprint"])

    def test_scope_or_architecture_flags_override_claimed_success(self):
        for scope, flag, outcome, expected in (("violated", False, "PASS", "NEEDS_ARCHITECT"),
                                                ("unknown", False, "PASS", "NEEDS_ARCHITECT"),
                                                ("within", True, "PASS", "ARCHITECTURE_HOLD"),
                                                ("within", False, "ARCHITECTURE_CONFLICT", "ARCHITECTURE_HOLD")):
            with self.subTest(scope=scope, flag=flag, outcome=outcome):
                directory = self.start()
                dispatch = self.reserve(directory)
                reported = result(dispatch, feedback.replay(directory)[0]["packet"], outcome=outcome, passed=True)
                reported.update(scope_status=scope, architecture_conflict=flag)
                state = feedback.complete(directory, reported, self.tick())
                self.assertEqual(state["status"], expected)
                with self.assertRaises(ValueError):
                    self.reserve(directory)

    def test_confirmed_architecture_change_is_sticky_needs_decision(self):
        directory = self.start()
        self.hold(directory, architecture=True)
        state = feedback.diagnose(directory, diagnosis("ARCHITECTURE_CHANGE"), "Architect", self.directory, self.tick())
        self.assertEqual(state["status"], "NEEDS_DECISION")
        self.assertEqual(state["packet"]["state"], "NEEDS_DECISION")
        before = feedback.replay(directory)[1]
        with self.assertRaises(ValueError):
            self.reserve(directory)
        for classification in ("BLOCKED", "RESUME_WORK", "REPAIR_CONTRACT"):
            with self.subTest(classification=classification):
                with self.assertRaises(ValueError):
                    feedback.diagnose(directory, diagnosis(classification), "Architect", self.directory, self.tick())
        self.assertEqual(feedback.replay(directory)[1], before)

    def test_blocked_diagnosis_cannot_downgrade_protected_holds_then_resume(self):
        for architecture in (False, True):
            with self.subTest(architecture=architecture):
                directory = self.start()
                held = self.hold(directory, architecture)
                state = feedback.diagnose(directory, diagnosis("BLOCKED"), "Architect", self.directory, self.tick())
                self.assertEqual(state["status"], held["status"])
                with self.assertRaises(ValueError):
                    feedback.diagnose(directory, diagnosis("RESUME_WORK"), "Architect", self.directory, self.tick())

    def test_repeated_blocked_deferrals_consume_a_finite_diagnosis_allowance(self):
        directory = self.start(limits=policy(max_architect_diagnoses=2))
        held = self.hold(directory)
        for count in (1, 2):
            state = feedback.diagnose(directory, diagnosis("BLOCKED"), "Architect", self.directory, self.tick())
            self.assertEqual(state["status"], held["status"])
            self.assertEqual(state["diagnoses"], count)
            self.assertEqual(feedback.summary(state)["remaining_architect_diagnoses"], 2 - count)
        sequence = feedback.replay(directory)[1]
        with self.assertRaisesRegex(ValueError, "diagnosis budget exhausted"):
            feedback.diagnose(directory, diagnosis("BLOCKED"), "Architect", self.directory, self.tick())
        self.assertEqual(feedback.replay(directory)[1], sequence)

    def test_confirmed_architecture_change_still_stops_after_diagnosis_budget_is_exhausted(self):
        directory = self.start(limits=policy(max_architect_diagnoses=1))
        self.hold(directory, architecture=True)
        deferred = feedback.diagnose(directory, diagnosis("BLOCKED"), "Architect", self.directory, self.tick())
        self.assertEqual(deferred["status"], "ARCHITECTURE_HOLD")
        self.assertEqual(deferred["diagnoses"], 1)
        self.assertEqual(feedback.summary(deferred)["remaining_architect_diagnoses"], 0)

        stopped = feedback.diagnose(directory, diagnosis("ARCHITECTURE_CHANGE"), "Architect", self.directory, self.tick())
        self.assertEqual(stopped["status"], "NEEDS_DECISION")
        self.assertEqual(stopped["packet"]["state"], "NEEDS_DECISION")
        self.assertEqual(stopped["reason"], "EXPLICIT_USER_APPROVAL_REQUIRED")
        self.assertEqual(stopped["diagnoses"], 1)
        self.assertEqual(feedback.summary(stopped)["remaining_architect_diagnoses"], 0)
        sequence = feedback.replay(directory)[1]
        for classification in ("ARCHITECTURE_CHANGE", "RESUME_WORK"):
            with self.subTest(classification=classification):
                with self.assertRaises(ValueError):
                    feedback.diagnose(directory, diagnosis(classification), "Architect", self.directory, self.tick())
        with self.assertRaises(ValueError):
            self.reserve(directory)
        self.assertEqual(feedback.replay(directory)[1], sequence)

    def test_repair_requires_current_approval_and_the_original_architect(self):
        directory = self.start()
        self.hold(directory)
        state = feedback.replay(directory)[0]
        revised = copy.deepcopy(wp.current(state["packet"])["contract"])
        revised["goal"] += " Clarified."
        with self.assertRaisesRegex(ValueError, "identity"):
            feedback.diagnose(directory, diagnosis(revised=revised), "Different architect", self.directory, self.tick())
        self.anchor.return_value = "b" * 64
        with self.assertRaisesRegex(ValueError, "unchanged current ACTIVE approval"):
            feedback.diagnose(directory, diagnosis(revised=revised), "Architect", self.directory, self.tick())
        self.anchor.side_effect = ValueError("ACTIVE approval revoked")
        with self.assertRaisesRegex(ValueError, "revoked"):
            feedback.diagnose(directory, diagnosis(revised=revised), "Architect", self.directory, self.tick())
        self.assertEqual(feedback.replay(directory)[1], 3)

    def test_repair_cannot_change_protected_contract_fields_or_retry_limits(self):
        directory = self.start()
        self.hold(directory)
        state = feedback.replay(directory)[0]
        for field in (*feedback.PROTECTED, "retry_budget"):
            with self.subTest(field=field):
                revised = copy.deepcopy(wp.current(state["packet"])["contract"])
                value = revised[field]
                if isinstance(value, list):
                    value.append("NEW-SYNTHETIC-ITEM")
                elif field == "retry_budget":
                    value["max_attempts"] += 1
                elif field == "scope":
                    value["allowed"].append("Expanded scope")
                elif field == "interface":
                    value["version"] = "2.0"
                elif field == "parent":
                    value["objective"] = "Changed objective"
                elif field == "risk":
                    revised["risk"] = "critical" if value != "critical" else "low"
                else:
                    value["unapproved_change"] = True
                with self.assertRaises(ValueError):
                    feedback.diagnose(directory, diagnosis(revised=revised), "Architect", self.directory, self.tick())
                self.assertEqual(feedback.replay(directory)[1], 3)

    def test_repair_preserves_global_tier_budgets_and_has_finite_allowance(self):
        directory = self.start(packet_with_caps(retries=4, caps={"1": 1}), policy(max_contract_repairs=1))
        self.hold(directory)
        before = feedback.replay(directory)[0]
        state = self.repair(directory)
        self.assertEqual(state["status"], "READY")
        self.assertEqual(state["repairs"], 1)
        self.assertEqual(state["caps"], before["caps"])
        self.assertEqual(state["total_cap"], before["total_cap"])
        self.assertEqual(state["attempts"], before["attempts"])
        self.assertEqual(wp.current(state["packet"])["version"], wp.current(before["packet"])["version"] + 1)
        second = self.reserve(directory)
        self.assertEqual(second["routing"]["decision"]["selected"]["tier"], 2)
        reported = result(second, feedback.replay(directory)[0]["packet"])
        reported["scope_status"] = "unknown"
        feedback.complete(directory, reported, self.tick())
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            self.repair(directory)
        self.assertEqual(len(feedback.replay(directory)[0]["attempts"]), 2)

    def test_cumulative_api_budget_survives_contract_repair(self):
        settings = copy.deepcopy(self.settings)
        settings["policy"]["role_api_budget_usd"] = 1
        directory = self.start(settings=settings)
        dispatch = self.reserve(directory, settings)
        reported = result(dispatch, feedback.replay(directory)[0]["packet"])
        reported.update(scope_status="unknown", api_cost_usd=1)
        feedback.complete(directory, reported, self.tick())
        self.repair(directory)
        halted = self.reserve(directory, settings)
        self.assertEqual(halted["status"], "NEEDS_ARCHITECT")
        self.assertEqual(halted["reason"], "CUMULATIVE_API_LIMIT")
        self.assertEqual(len(feedback.replay(directory)[0]["attempts"]), 1)

    def test_repair_cannot_reset_an_exhausted_global_attempt_budget(self):
        directory = self.start(make_packet(retries=1))
        self.hold(directory)
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            self.repair(directory)

    def test_ordinary_blocker_resume_retains_raw_outcome_and_consumed_budget(self):
        directory = self.start()
        dispatch = self.reserve(directory)
        blocked = self.complete(directory, dispatch, outcome="BLOCKED")
        self.assertEqual(blocked["status"], "BLOCKED")
        state = feedback.diagnose(directory, diagnosis("RESUME_WORK"), "Architect", self.directory, self.tick())
        self.assertEqual(state["status"], "READY")
        self.assertEqual(state["resumptions"], 1)
        self.assertEqual(state["attempts"][0]["result"]["outcome"], "BLOCKED")
        self.assertEqual(state["attempts"][0]["routing_outcome"], "FAIL")
        self.assertEqual(feedback.tier_counts(state)["1"], 1)
        self.assertEqual(state["total_cap"], blocked["total_cap"])
        next_dispatch = self.reserve(directory)
        self.assertEqual(next_dispatch["status"], "DISPATCH")
        self.assertEqual(len(feedback.replay(directory)[0]["attempts"]), 2)

    def test_default_disabled_resources_hold_and_blocker_resumptions_are_finite(self):
        disabled = wp.read_json(ROOT / "config/model-router.example.json")
        directory = self.start(limits=policy(max_blocker_resumptions=2), settings=disabled)
        for count in (1, 2):
            halted = self.reserve(directory, disabled)
            self.assertEqual(halted["status"], "BLOCKED")
            state = feedback.diagnose(directory, diagnosis("RESUME_WORK"), "Architect", self.directory, self.tick())
            self.assertEqual(state["resumptions"], count)
            self.assertEqual(state["attempts"], [])
        self.reserve(directory, disabled)
        with self.assertRaisesRegex(ValueError, "resumption budget exhausted"):
            feedback.diagnose(directory, diagnosis("RESUME_WORK"), "Architect", self.directory, self.tick())

    def test_blocker_resume_requires_unchanged_active_approval(self):
        directory = self.start()
        dispatch = self.reserve(directory)
        self.complete(directory, dispatch, outcome="BLOCKED")
        self.anchor.return_value = "b" * 64
        with self.assertRaisesRegex(ValueError, "unchanged ACTIVE approval"):
            feedback.diagnose(directory, diagnosis("RESUME_WORK"), "Architect", self.directory, self.tick())
        self.assertEqual(feedback.replay(directory)[0]["status"], "BLOCKED")

    def test_explicit_provider_recovery_preserves_raw_outage_and_attempt_counts(self):
        directory = self.start()
        dispatch = self.reserve(directory)
        self.complete(directory, dispatch, outcome="PROVIDER_UNAVAILABLE")
        self.assertEqual(self.reserve(directory)["status"], "BLOCKED")
        for classification, providers in (("BLOCKED", ["lmstudio"]), ("RESUME_WORK", ["unknown-provider"])):
            with self.subTest(classification=classification, providers=providers):
                diagnostic = diagnosis(classification)
                diagnostic["resolved_providers"] = providers
                with self.assertRaises(ValueError):
                    feedback.diagnose(directory, diagnostic, "Architect", self.directory, self.tick())
        diagnostic = diagnosis("RESUME_WORK")
        diagnostic["resolved_providers"] = ["lmstudio"]
        state = feedback.diagnose(directory, diagnostic, "Architect", self.directory, self.tick())
        self.assertEqual(state["status"], "READY")
        self.assertEqual(state["attempts"][0]["result"]["outcome"], "PROVIDER_UNAVAILABLE")
        self.assertEqual(state["attempts"][0]["routing_outcome"], "PROVIDER_RECOVERED")
        self.assertEqual(feedback.tier_counts(state)["1"], 1)
        following = self.reserve(directory)
        self.assertEqual(following["status"], "DISPATCH")
        self.assertEqual(len(feedback.replay(directory)[0]["attempts"]), 2)

    def test_initialization_rejects_mixed_profile_or_missing_target_graph(self):
        packet = make_packet()
        contract = wp.read_json(ROOT / "examples/work-packets/family-law.contract.json")
        other = wp.create("FAMILY-SYN-001", "family-law", contract, "Architect", "Synthetic indexing fixture", timestamp())
        for index, graph in enumerate(([packet, other], [])):
            with self.subTest(graph_size=len(graph)):
                directory = self.directory / f"invalid-graph-{index}"
                with self.assertRaises(ValueError):
                    feedback.initialize(directory, packet, graph, policy(), self.settings, self.directory, "Architect", self.tick())
                self.assertFalse(directory.exists())

    def test_routing_policy_cannot_be_changed_after_initialization(self):
        directory = self.start()
        changed = copy.deepcopy(self.settings)
        changed["policy"]["role_api_budget_usd"] += 1
        with self.assertRaisesRegex(ValueError, "policy is frozen"):
            self.reserve(directory, changed)
        self.assertEqual(feedback.replay(directory)[1], 1)

    def test_changed_or_missing_approval_adds_a_sticky_hold_before_dispatch(self):
        for failure in (ValueError("Invalid current approval"), FileNotFoundError("Missing approval"), "b" * 64):
            with self.subTest(failure=str(failure)):
                self.anchor.side_effect = None
                self.anchor.return_value = ANCHOR
                directory = self.start()
                if isinstance(failure, Exception):
                    self.anchor.side_effect = failure
                else:
                    self.anchor.return_value = failure
                held = self.reserve(directory)
                self.assertEqual(held["status"], "NEEDS_DECISION")
                state, sequence, _ = feedback.replay(directory)
                self.assertEqual(state["status"], "NEEDS_DECISION")
                self.assertEqual(sequence, 2)
                self.assertEqual(state["attempts"], [])
                self.anchor.side_effect = None
                self.anchor.return_value = ANCHOR
                with self.assertRaises(ValueError):
                    self.reserve(directory)

    def test_context_limit_halts_before_consuming_an_attempt(self):
        directory = self.start(limits=policy(max_context_chars=1000))
        halted = self.reserve(directory)
        self.assertEqual(halted["status"], "NEEDS_ARCHITECT")
        self.assertEqual(halted["reason"], "CONTEXT_LIMIT_REQUIRES_DECOMPOSITION")
        self.assertEqual(feedback.replay(directory)[0]["attempts"], [])

    def test_renderer_fences_untrusted_backticks_and_discoveries_remain_proposals(self):
        directory = self.start()
        dispatch = self.reserve(directory)
        reported = result(dispatch, feedback.replay(directory)[0]["packet"])
        reported["summary"] = "Untrusted ```\n# Forged section\n````\n<script>not executed</script>"
        reported["discoveries"] = [{"summary": "Unrelated synthetic improvement", "evidence": ["Synthetic discovery record"]}]
        state = feedback.complete(directory, reported, self.tick())
        rendered = feedback.render(state)
        opening = next(line for line in rendered.splitlines() if re.fullmatch(r"`{3,}json", line))
        self.assertGreaterEqual(len(opening) - 4, 5)
        closing = opening[:-4]
        body = rendered.split(opening + "\n", 1)[1].rsplit("\n" + closing + "\n", 1)[0]
        exported = json.loads(body)
        self.assertEqual(exported["binding"], feedback.summary(state)["binding"])
        self.assertEqual(exported["status"], state["status"])
        self.assertEqual(exported["issue_proposal_count"], 1)
        self.assertEqual(exported["attempts"][0]["summary"]["preview"], reported["summary"])
        self.assertEqual(exported["attempts"][0]["record"], "00000003.json")
        raw_event = wp.read_json(directory / exported["attempts"][0]["record"])
        self.assertEqual(raw_event["data"], reported)
        self.assertLessEqual(len(body), 60000)
        self.assertEqual(feedback.summary(state)["issue_proposals"][0]["summary"], "Unrelated synthetic improvement")
        self.assertNotIn("Unrelated synthetic improvement", wp.canonical(wp.current(state["packet"])["contract"]))

    def test_result_at_deadline_passes_but_late_result_is_a_timeout_failure(self):
        for delay, expected_status, reason in ((600, "REVIEW_PENDING", "OBJECTIVE_CHECKS_PASSED"),
                                                (601, "IN_PROGRESS", "ATTEMPT_TIMEOUT")):
            with self.subTest(delay=delay):
                directory = self.start()
                issued = self.time + 1
                dispatch = self.reserve(directory)
                reported = result(dispatch, feedback.replay(directory)[0]["packet"], outcome="PASS", passed=True)
                state = feedback.complete(directory, reported, timestamp(issued + delay))
                self.assertEqual(state["status"], expected_status)
                self.assertEqual(state["reason"], reason)
                self.assertEqual(state["attempts"][0]["result"]["outcome"], "PASS")
                self.assertIsNone(state["pending"])
                if delay > 600:
                    self.assertEqual(state["attempts"][0]["routing_outcome"], "FAIL")

    def test_result_predating_dispatch_is_refused_without_consuming_pending_slot(self):
        directory = self.start()
        dispatch = self.reserve(directory)
        reported = result(dispatch, feedback.replay(directory)[0]["packet"])
        with self.assertRaises(ValueError):
            feedback.complete(directory, reported, timestamp())
        self.assertEqual(feedback.replay(directory)[0]["pending"], dispatch["dispatch_id"])

    def test_oversized_or_malformed_result_preserves_pending_dispatch(self):
        directory = self.start()
        dispatch = self.reserve(directory)
        for field, invalid in (("summary", "x" * 4001), ("evidence", []), ("api_cost_usd", float("nan")), ("discoveries", [{"summary": " ", "evidence": ["Synthetic"]}])):
            with self.subTest(field=field):
                reported = result(dispatch, feedback.replay(directory)[0]["packet"])
                reported[field] = invalid
                with self.assertRaises(ValueError):
                    feedback.complete(directory, reported, self.tick())
                self.assertEqual(feedback.replay(directory)[1], 2)


class DirectorySyncHelperTests(unittest.TestCase):
    def test_posix_helper_opens_syncs_and_closes_directory_in_order(self):
        path = "/synthetic/ledger"
        flags = feedback.os.O_RDONLY | 65536
        calls = mock.Mock()
        with mock.patch.object(feedback.os, "name", "posix"), \
                mock.patch.object(feedback.os, "O_DIRECTORY", 65536, create=True), \
                mock.patch.object(feedback.os, "open", return_value=47) as opened, \
                mock.patch.object(feedback.os, "fsync") as synced, \
                mock.patch.object(feedback.os, "close") as closed:
            calls.attach_mock(opened, "open")
            calls.attach_mock(synced, "fsync")
            calls.attach_mock(closed, "close")
            feedback.sync_directory(path)
        self.assertEqual(calls.mock_calls, [mock.call.open(path, flags), mock.call.fsync(47), mock.call.close(47)])

    def test_posix_helper_closes_descriptor_when_sync_fails_and_propagates_close_failures(self):
        path = "/synthetic/ledger"
        for failure in ("fsync", "close"):
            with self.subTest(failure=failure):
                with mock.patch.object(feedback.os, "name", "posix"), \
                        mock.patch.object(feedback.os, "open", return_value=47), \
                        mock.patch.object(feedback.os, "fsync") as synced, \
                        mock.patch.object(feedback.os, "close") as closed:
                    (synced if failure == "fsync" else closed).side_effect = OSError(f"{failure} failed")
                    with self.assertRaisesRegex(OSError, f"{failure} failed"):
                        feedback.sync_directory(path)
                synced.assert_called_once_with(47)
                closed.assert_called_once_with(47)

    def test_posix_helper_does_not_sync_or_close_when_directory_open_fails(self):
        path = "/synthetic/ledger"
        with mock.patch.object(feedback.os, "name", "posix"), \
                mock.patch.object(feedback.os, "open", side_effect=OSError("open failed")), \
                mock.patch.object(feedback.os, "fsync") as synced, \
                mock.patch.object(feedback.os, "close") as closed:
            with self.assertRaisesRegex(OSError, "open failed"):
                feedback.sync_directory(path)
        synced.assert_not_called()
        closed.assert_not_called()

    def test_non_posix_helper_performs_no_directory_operations(self):
        path = "C:\\synthetic\\ledger"
        with mock.patch.object(feedback.os, "name", "nt"), \
                mock.patch.object(feedback.os, "open") as opened, \
                mock.patch.object(feedback.os, "fsync") as synced, \
                mock.patch.object(feedback.os, "close") as closed:
            feedback.sync_directory(path)
        opened.assert_not_called()
        synced.assert_not_called()
        closed.assert_not_called()


class ActualBootstrapGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.root = self.directory / "synthetic-project"
        self.anchor = active_project(self.root)
        self.packet = make_packet()
        self.settings = router_config()
        self.ledger = self.directory / "ledger"

    def initialize(self):
        return feedback.initialize(self.ledger, self.packet, [self.packet], policy(), self.settings,
                                   self.root, "Architect", timestamp())

    def test_actual_bootstrap_gate_rejects_inactive_or_missing_project_before_creation(self):
        path = self.root / "config/bootstrap.json"
        data = wp.read_json(path)
        data["state"] = "AWAITING_APPROVAL"
        data["approval"] = {"approved": False, "approved_by": None, "approved_at": None, "architecture_fingerprint": None}
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ACTIVE bootstrap required"):
            self.initialize()
        self.assertFalse(self.ledger.exists())
        path.unlink()
        with self.assertRaises(OSError):
            self.initialize()
        self.assertFalse(self.ledger.exists())

    def test_current_bound_document_change_creates_sticky_approval_hold(self):
        state = self.initialize()
        self.assertEqual(state["anchor"], self.anchor)
        (self.root / "PROJECT_CHARTER.md").write_text("Material change after synthetic approval", encoding="utf-8")
        held = feedback.reserve(self.ledger, self.settings, options(), self.root, timestamp(1))
        self.assertEqual(held["status"], "NEEDS_DECISION")
        state, sequence, _ = feedback.replay(self.ledger)
        self.assertEqual(state["reason"], "CURRENT_APPROVAL_REQUIRED")
        self.assertEqual(sequence, 2)
        self.assertEqual(state["attempts"], [])

    def test_packet_profile_must_match_the_actual_approved_project(self):
        contract = wp.read_json(ROOT / "examples/work-packets/family-law.contract.json")
        packet = wp.create("FAMILY-SYN-001", "family-law", contract, "Architect", "Synthetic indexing fixture", timestamp())
        for target in ("ARCHITECTED", "READY"):
            packet = wp.transition(packet, target, "architect", "Architect", "Synthetic readiness", ["Synthetic evidence"], timestamp=timestamp())
        with self.assertRaisesRegex(ValueError, "profile differs"):
            feedback.initialize(self.ledger, packet, [packet], policy(), self.settings, self.root, "Architect", timestamp())
        self.assertFalse(self.ledger.exists())

    def test_completion_still_records_reserved_work_after_real_approval_revocation(self):
        self.initialize()
        dispatch = feedback.reserve(self.ledger, self.settings, options(), self.root, timestamp(1))
        (self.root / "PROJECT_CHARTER.md").write_text("Material change after synthetic approval", encoding="utf-8")
        with self.assertRaises(ValueError):
            feedback.active_anchor(self.root)
        packet = feedback.replay(self.ledger)[0]["packet"]
        state = feedback.complete(self.ledger, result(dispatch, packet, outcome="PASS", passed=True), timestamp(2))
        self.assertEqual(state["status"], "REVIEW_PENDING")
        self.assertIsNone(state["pending"])

    def test_contract_repair_checks_actual_current_bootstrap_files(self):
        self.initialize()
        dispatch = feedback.reserve(self.ledger, self.settings, options(), self.root, timestamp(1))
        packet = feedback.replay(self.ledger)[0]["packet"]
        reported = result(dispatch, packet)
        reported["scope_status"] = "unknown"
        state = feedback.complete(self.ledger, reported, timestamp(2))
        revised = copy.deepcopy(wp.current(state["packet"])["contract"])
        revised["goal"] += " Clarified."
        (self.root / "CONNECTOR_PLAN.md").write_text("Changed bound permissions after approval", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ACTIVE bootstrap required"):
            feedback.diagnose(self.ledger, diagnosis(revised=revised, anchor=self.anchor), "Architect", self.root, timestamp(3))
        self.assertEqual(feedback.replay(self.ledger)[1], 3)


if __name__ == "__main__":
    unittest.main()
