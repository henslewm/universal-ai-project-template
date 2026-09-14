from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from test_model_router import config as router_config
from test_model_router import resource


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("acceptance_under_test", ROOT / "scripts/acceptance.py")
acceptance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acceptance)
wp = acceptance.wp
feedback = acceptance.feedback
ANCHOR = "a" * 64
PASS_ARGV = [sys.executable, "-c", "raise SystemExit(0)"]
FAIL_ARGV = [sys.executable, "-c", "print('observed failure'); raise SystemExit(3)"]
SLEEP_ARGV = [sys.executable, "-c", "import time; time.sleep(15)"]
# Built by concatenation so the credential-like shape exists only in the produced output,
# never in the recorded contract itself.
SECRET_ARGV = [sys.executable, "-c", "print('api_' + 'key= topsecretvalue')"]


def make_contract(risk="low", argv=PASS_ARGV, review=None, cwd=None, timeout=None):
    value = wp.read_json(ROOT / "examples/work-packets/software-hardware.contract.json")
    value["risk"] = risk
    if argv is not None:
        command = {"argv": list(argv)}
        if cwd is not None:
            command["cwd"] = cwd
        if timeout is not None:
            command["timeout_seconds"] = timeout
        value["validation"][0]["command"] = command
    if review is not None:
        value["review"] = review
    return value


def make_packet(contract=None, state="REVIEW"):
    contract = contract or make_contract()
    value = wp.create("ACCEPT-SYN-001", "software-hardware", contract, "Architect", "Synthetic acceptance fixture")
    for target, role, actor in (
        ("ARCHITECTED", "architect", "Architect"), ("READY", "architect", "Architect"),
        ("IN_PROGRESS", "worker", "Worker"), ("VALIDATING", "worker", "Worker"),
        ("REVIEW", "worker", "Worker"),
    ):
        value = wp.transition(value, target, role, actor, "Synthetic state assertion", ["synthetic-state-evidence"])
        if target == state:
            return value
    return value


def make_result(packet, **changes):
    contract = wp.current(packet)["contract"]
    value = {
        "dispatch_id": "e" * 64, "outcome": "PASS",
        "summary": "Synthetic worker claim; assertions only, no real work implied.",
        "scope_status": "within", "architecture_conflict": False,
        "validation": [{"check_id": check["id"], "passed": True, "failure_code": "",
                        "expected": "expected value", "actual": "expected value",
                        "evidence": ["Synthetic worker-supplied record"]}
                       for check in contract["validation"]],
        "evidence": ["Synthetic worker evidence"], "discoveries": [], "api_cost_usd": 0,
        "cost_evidence": "Synthetic zero-cost fixture; no model calls made.",
    }
    value.update(changes)
    return value


def make_artifact(content="diff --git a/parser.py b/parser.py\n+synthetic change\n"):
    return {"kind": "diff", "reference": "branch synthetic-change at commit ffff",
            "content": content, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}


IMPLEMENTERS = [{"actor": "Worker", "model_family": "qwen"}]
CONTROLLER, ARCHITECT = "Acceptance controller", "Architect"
REVIEWER = {"actor": "Independent reviewer", "model_family": "sonnet", "tier": 3}


def make_report(prepared, contract, verdict="APPROVE", **changes):
    value = {
        "schema_version": "1.0", "review_id": prepared["review_id"], "reviewer": prepared["reviewer"],
        "verdict": verdict, "summary": "Synthetic review outcome over the packet only.",
        "criteria": [{"criterion_id": item["id"], "status": "met",
                      "evidence": ["Cited from the review packet"]}
                     for item in contract["acceptance_criteria"]],
        "contract_failures": [], "missing_evidence": [], "escalation_reason": "",
    }
    value.update(changes)
    return value


def bound_to(fb_state, result):
    """The binding fields decision_for carries; hand-built decisions must carry them too."""
    packet_binding = feedback.binding(fb_state["packet"])
    return {"binding": {key: packet_binding[key] for key in ("task_id", "revision", "contract_hash")},
            "result_dispatch_id": result["dispatch_id"]}


def process_alive(pid):
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        alive = bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        kernel32.CloseHandle(handle)
        return alive
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        # A killed child reparented to init is reaped by init; a zombie under us needs a wait.
        return os.waitpid(pid, os.WNOHANG) == (0, 0)
    except ChildProcessError:
        return True


def make_failure(ref="AC-VALID", kind="criterion", what="Observed value differs from the packet evidence"):
    return {"failed_ref": ref, "kind": kind, "what_failed": what,
            "evidence": ["Synthetic reviewer observation"],
            "corrective_action": "Correct the parser output for the failing sample within this contract"}


class AcceptanceBase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.counter = 0

    def config(self, **policy):
        value = wp.read_json(ROOT / "config/acceptance.example.json")
        value["policy"].update(policy)
        return value

    def workspace(self, files=("artifact.txt",)):
        self.counter += 1
        space = self.directory / f"workspace-{self.counter}"
        space.mkdir()
        for name in files:
            (space / name).write_text("synthetic artifact content\n", encoding="utf-8")
        return space

    def start(self, risk="low", argv=PASS_ARGV, review=None, packet=None, config=None, **contract_kw):
        self.counter += 1
        ledger = self.directory / f"ledger-{self.counter}"
        packet = packet or make_packet(make_contract(risk=risk, argv=argv, review=review, **contract_kw))
        acceptance.initialize(ledger, config or self.config(), packet, make_result(packet),
                              make_artifact(), CONTROLLER, ARCHITECT, IMPLEMENTERS, [])
        return ledger, packet

    def checked(self, ledger):
        return acceptance.run_checks(ledger, self.workspace())

    def open_review(self, ledger, gate="model_review", reviewer=None):
        self.counter += 1
        return acceptance.prepare_review(ledger, self.directory / f"review-{self.counter}",
                                         gate, reviewer or dict(REVIEWER))

    def ingest(self, ledger, report):
        self.counter += 1
        path = self.directory / f"report-{self.counter}.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        return acceptance.ingest_review(ledger, path)

    def state(self, ledger):
        return acceptance.replay(ledger)[0]


class ConfigAndFloorTests(AcceptanceBase):
    def test_example_configuration_is_valid_and_gate_names_agree_across_declarations(self):
        config = acceptance.config_valid(wp.read_json(ROOT / "config/acceptance.example.json"))
        self.assertEqual(config["schema_version"], "1.0")
        self.assertEqual(acceptance.GATES, set(wp.SCHEMA["$defs"]["review_gate"]["enum"]))
        for floor in wp.REVIEW_FLOORS.values():
            self.assertTrue(floor <= acceptance.GATES)

    def test_configuration_refusals(self):
        broken = self.config()
        broken["policy"]["additional_gates"]["low"] = ["cross_family_review"]
        with self.assertRaisesRegex(ValueError, "cross_family_review requires model_review"):
            acceptance.config_valid(broken)
        secret = self.config()
        secret["policy"]["additional_gates"]["low"] = []
        secret["leak"] = "api_key: sk-ABCDEFGHIJKLMNOPQRSTUV"
        with self.assertRaises(ValueError):
            acceptance.config_valid(secret)

    def test_review_block_cannot_loosen_below_the_risk_floor(self):
        below = make_contract(risk="high", review={"required_gates": ["deterministic", "model_review"]})
        errors = wp.validate_contract(below)
        self.assertTrue(any("loosens below" in error for error in errors), errors)
        exact = make_contract(risk="high", review={"required_gates":
                              ["deterministic", "model_review", "cross_family_review"]})
        self.assertEqual(wp.validate_contract(exact), [])
        tightened = make_contract(risk="low", review={"required_gates": ["deterministic", "model_review"]})
        self.assertEqual(wp.validate_contract(tightened), [])
        self.assertEqual(wp.effective_gates(tightened), {"deterministic", "model_review"})

    def test_review_block_gate_dependencies_and_unknown_gates_are_refused(self):
        orphan = make_contract(risk="low", review={"required_gates": ["deterministic", "cross_family_review"]})
        self.assertTrue(any("cross_family_review requires model_review" in e
                            for e in wp.validate_contract(orphan)))
        unknown = make_contract(risk="low", review={"required_gates": ["deterministic", "vibes"]})
        self.assertTrue(wp.validate_contract(unknown))

    def test_command_cwd_escapes_are_refused_statically(self):
        for cwd in ("../outside", "/absolute", "C:/absolute", "a/../../b"):
            with self.subTest(cwd=cwd):
                contract = make_contract(cwd=cwd)
                self.assertTrue(any("cwd must stay inside" in e for e in wp.validate_contract(contract)))
        self.assertEqual(wp.validate_contract(make_contract(cwd="subdir")), [])

    def test_policy_additional_gates_extend_the_contract_floor(self):
        config = self.config()
        config["policy"]["additional_gates"]["low"] = ["model_review"]
        ledger, _ = self.start(risk="low", config=config)
        self.assertIn("model_review", self.state(ledger)["gates"])


class InitTests(AcceptanceBase):
    def test_init_requires_a_packet_at_review(self):
        packet = make_packet(state="READY")
        with self.assertRaisesRegex(ValueError, "reaches REVIEW"):
            acceptance.initialize(self.directory / "early", self.config(), packet, make_result(packet),
                                  make_artifact(), CONTROLLER, ARCHITECT, IMPLEMENTERS, [])

    def test_init_refuses_a_result_that_is_not_a_clean_objective_pass(self):
        packet = make_packet()
        bad = [make_result(packet, outcome="FAIL"), make_result(packet, scope_status="unknown"),
               make_result(packet, architecture_conflict=True), make_result(packet, validation=[])]
        failed = make_result(packet)
        failed["validation"][0]["passed"] = False
        failed["validation"][0]["failure_code"] = "VALUE_MISMATCH"
        bad.append(failed)
        for result in bad:
            with self.subTest(result=result["outcome"]), self.assertRaises(ValueError):
                acceptance.initialize(self.directory / f"bad-{bad.index(result)}", self.config(), packet,
                                      result, make_artifact(), CONTROLLER, ARCHITECT, IMPLEMENTERS, [])

    def test_init_refuses_artifact_digest_mismatch_and_oversize(self):
        packet = make_packet()
        wrong = make_artifact()
        wrong["sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "digest does not match"):
            acceptance.initialize(self.directory / "wrong", self.config(), packet, make_result(packet),
                                  wrong, CONTROLLER, ARCHITECT, IMPLEMENTERS, [])
        with self.assertRaisesRegex(ValueError, "exceeds its configured bound"):
            acceptance.initialize(self.directory / "big", self.config(artifact_max_chars=200), packet,
                                  make_result(packet), make_artifact("x" * 300 + "\n"),
                                  CONTROLLER, ARCHITECT, IMPLEMENTERS, [])

    def test_ledger_tampering_is_detected_on_replay(self):
        ledger, _ = self.start()
        self.checked(ledger)
        path = ledger / "00000002.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["data"]["checks"]["results"][0]["passed"] = False
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash differs"):
            acceptance.replay(ledger)
        (ledger / "00000001.json").unlink()
        with self.assertRaisesRegex(ValueError, "gap|chain"):
            acceptance.replay(ledger)


class DeterministicGateTests(AcceptanceBase):
    def test_passing_command_is_observed_and_satisfies_the_gate(self):
        ledger, _ = self.start()
        outcome = self.checked(ledger)
        self.assertTrue(outcome["satisfied"])
        state = self.state(ledger)
        entry = state["checks"]["results"][0]
        self.assertEqual(entry["exit_code"], 0)
        self.assertEqual(entry["argv"], PASS_ARGV)
        self.assertEqual(state["checks"]["workspace_files"], 1)

    def test_failing_command_fails_the_gate_and_blocks_acceptance(self):
        ledger, _ = self.start(argv=FAIL_ARGV)
        outcome = self.checked(ledger)
        self.assertFalse(outcome["satisfied"])
        entry = self.state(ledger)["checks"]["results"][0]
        self.assertEqual(entry["exit_code"], 3)
        self.assertIn("observed failure", entry["stdout"])
        with self.assertRaisesRegex(ValueError, "Deterministic gate unsatisfied"):
            acceptance.accept(ledger, CONTROLLER)

    def test_timeout_is_recorded_and_fails_the_check(self):
        ledger, _ = self.start(argv=SLEEP_ARGV, timeout=1)
        outcome = self.checked(ledger)
        self.assertFalse(outcome["satisfied"])
        entry = self.state(ledger)["checks"]["results"][0]
        self.assertTrue(entry["timed_out"])
        self.assertIsNone(entry["exit_code"])
        self.assertFalse(entry["passed"])

    def test_credential_bearing_output_is_refused_and_nothing_is_recorded(self):
        ledger, _ = self.start(argv=SECRET_ARGV)
        before = sorted(path.name for path in ledger.iterdir())
        with self.assertRaisesRegex(ValueError, "credential-like"):
            self.checked(ledger)
        self.assertEqual(sorted(path.name for path in ledger.iterdir()), before)

    def test_unrunnable_validation_requires_attestation_and_not_from_an_implementer(self):
        ledger, _ = self.start(argv=None)
        outcome = self.checked(ledger)
        self.assertFalse(outcome["satisfied"])
        self.assertEqual(outcome["deterministic"]["VAL-FRAMES"], "NEEDS_ATTESTATION")
        with self.assertRaisesRegex(ValueError, "cannot attest"):
            acceptance.append(ledger, "ATTESTATION",
                              {"attestation": {"validation_id": "VAL-FRAMES", "operator": "Worker",
                                               "evidence": ["Self-attested"]}},
                              previous_state=acceptance.replay(ledger))
        state = acceptance.append(ledger, "ATTESTATION",
                                  {"attestation": {"validation_id": "VAL-FRAMES", "operator": "Operator",
                                                   "evidence": ["Observed the manual check pass"]}},
                                  previous_state=acceptance.replay(ledger))
        self.assertTrue(acceptance.deterministic_satisfied(state))

    def test_reviewer_below_the_contract_reviewer_tier_is_refused(self):
        # Codex P1 on PR #21: a declared tier-0 reviewer could satisfy a tier-4 task's gate.
        contract = make_contract(risk="medium")
        contract["routing"]["reviewer_tier"] = 3
        ledger, _ = self.start(packet=make_packet(contract))
        self.checked(ledger)
        with self.assertRaisesRegex(ValueError, "below the contract's reviewer_tier 3"):
            self.open_review(ledger, reviewer={"actor": "Weak reviewer", "model_family": "sonnet", "tier": 2})
        self.assertEqual(self.state(ledger)["reviews"], [])
        prepared = self.open_review(ledger, reviewer={"actor": "Strong reviewer", "model_family": "sonnet", "tier": 4})
        self.assertEqual(prepared["reviewer"]["tier"], 4)

    def test_symlinked_directory_in_the_workspace_is_refused(self):
        # Codex P2 on PR #21: a directory symlink is neither a file nor descended into, so the
        # digest silently omitted everything a check could read through it.
        ledger, _ = self.start()
        space = self.workspace()
        outside = self.directory / "outside"
        outside.mkdir()
        (outside / "input.txt").write_text("changes without changing the digest\n", encoding="utf-8")
        try:
            os.symlink(outside, space / "linked", target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlinks unavailable here: {exc}")
        with self.assertRaisesRegex(ValueError, "symlink"):
            acceptance.run_checks(ledger, space)
        self.assertIsNone(self.state(ledger)["checks"])

    def test_symlinked_workspace_root_is_refused_before_resolution(self):
        # Codex P2 on PR #22: resolve() replaced a symlinked root with its target first.
        ledger, _ = self.start()
        real = self.workspace()
        link = self.directory / "workspace-link"
        try:
            os.symlink(real, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlinks unavailable here: {exc}")
        with self.assertRaisesRegex(ValueError, "Workspace root is a symlink"):
            acceptance.run_checks(ledger, link)
        self.assertIsNone(self.state(ledger)["checks"])
        self.assertTrue(acceptance.run_checks(ledger, real)["satisfied"])

    def test_timeout_is_enforced_when_a_descendant_holds_the_output_pipes(self):
        # Codex P1 on PR #22: killing only the immediate process left a grandchild holding
        # the pipes, and the unconditional reader joins waited on it indefinitely.
        script = ("import subprocess, sys, time\n"
                  "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
                  "sys.stdout.write('parent started'); sys.stdout.flush(); time.sleep(120)")
        ledger, _ = self.start(argv=[sys.executable, "-c", script], timeout=2)
        started = time.monotonic()
        self.checked(ledger)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 2 + acceptance.DRAIN_GRACE_SECONDS + 10, "reader joins were not bounded")
        entry = self.state(ledger)["checks"]["results"][0]
        self.assertTrue(entry["timed_out"])
        self.assertFalse(entry["passed"])
        self.assertIn("parent started", entry["stdout"])

    def test_symlink_removed_by_a_check_is_caught_before_execution(self):
        # Codex P1 on PR #22 round 2: a check could read through a link, remove it, and pass
        # a post-run scan with a digest that never saw the linked inputs.
        removal = [sys.executable, "-c", "import os; os.rmdir('linked') if os.path.isdir('linked') else os.remove('linked')"]
        ledger, _ = self.start(argv=removal)
        space = self.workspace()
        outside = self.directory / "outside-inputs"
        outside.mkdir()
        try:
            os.symlink(outside, space / "linked", target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlinks unavailable here: {exc}")
        with self.assertRaisesRegex(ValueError, "symlink"):
            acceptance.run_checks(ledger, space)
        self.assertTrue((space / "linked").is_symlink(), "the check must not have run")
        self.assertIsNone(self.state(ledger)["checks"])

    def test_descendant_left_behind_by_a_normal_exit_is_killed(self):
        # Codex P1 on PR #22 round 2: the parent exits normally, a grandchild keeps the pipes,
        # and abandoning the readers left it running indefinitely.
        script = ("import subprocess, sys\n"
                  "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
                  "open('grandchild.pid', 'w').write(str(child.pid)); sys.stdout.write('parent done')")
        ledger, _ = self.start(argv=[sys.executable, "-c", script])
        space = self.workspace()
        started = time.monotonic()
        acceptance.run_checks(ledger, space)
        self.assertLess(time.monotonic() - started, 2 * acceptance.DRAIN_GRACE_SECONDS + 10)
        entry = self.state(ledger)["checks"]["results"][0]
        self.assertFalse(entry["passed"])
        self.assertTrue(entry["timed_out"])
        self.assertIn("parent done", entry["stdout"])
        pid = int((space / "grandchild.pid").read_text())
        self.assertFalse(process_alive(pid), "the grandchild was alive when the digest was taken")

    def test_symlink_created_by_one_check_and_consumed_by_the_next_is_caught(self):
        # Codex P1 on PR #22 round 3: with several commands, a scan only before the loop and
        # after it never sees a link that the first check creates and the second removes.
        outside = self.directory / "outside-inputs"
        outside.mkdir()
        try:
            probe = self.directory / "probe-link"
            os.symlink(outside, probe, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlinks unavailable here: {exc}")
        contract = make_contract()
        contract["validation"][0]["criterion_ids"] = ["AC-VALID"]
        contract["validation"][0]["command"] = {"argv": [
            sys.executable, "-c", f"import os; os.symlink({str(outside)!r}, 'linked', target_is_directory=True)"]}
        contract["validation"].append({"id": "VAL-SECOND", "description": "Consumes and removes the link.",
                                       "criterion_ids": ["AC-INVALID"], "evidence_required": ["Recorded outcome."],
                                       "command": {"argv": [sys.executable, "-c",
                                                            "import os; os.rmdir('linked'); open('second-ran', 'w').close()"]}})
        ledger, _ = self.start(packet=make_packet(contract))
        space = self.workspace()
        with self.assertRaisesRegex(ValueError, "symlink"):
            acceptance.run_checks(ledger, space)
        self.assertTrue((space / "linked").is_symlink(), "the first check ran and left its link")
        self.assertFalse((space / "second-ran").exists(), "the second check must not have run")
        self.assertIsNone(self.state(ledger)["checks"])

    def test_descendant_that_closed_its_pipes_does_not_outlive_the_check(self):
        # Codex P1 on PR #22 round 3: a descendant that closes stdout and stderr lets the readers
        # finish, so nothing was abandoned and nothing was killed; it must still be ended.
        script = ("import os, subprocess, sys\n"
                  "child = subprocess.Popen([sys.executable, '-c', "
                  "'import os, time; os.close(1); os.close(2); time.sleep(120)'])\n"
                  "open('quiet-grandchild.pid', 'w').write(str(child.pid)); print('parent done')")
        ledger, _ = self.start(argv=[sys.executable, "-c", script])
        space = self.workspace()
        started = time.monotonic()
        acceptance.run_checks(ledger, space)
        # On POSIX the readers finish and the check passes; on Windows the grandchild still holds
        # a duplicated handle and is ended through the abandoned-drain path. Either way it is
        # already dead when run_checks returns: the digest was taken only after the tree stopped.
        self.assertLess(time.monotonic() - started, 3 * acceptance.DRAIN_GRACE_SECONDS + 10)
        pid = int((space / "quiet-grandchild.pid").read_text())
        self.assertFalse(process_alive(pid), "the quiet grandchild was alive when the digest was taken")

    def test_run_refuses_when_the_tree_cannot_be_confirmed_stopped(self):
        # Codex P1 on PR #22 round 7: the digest must not be taken while a member is still dying.
        ledger, _ = self.start()
        with mock.patch.object(acceptance.ProcessTree, "members_alive", return_value=True):
            with self.assertRaisesRegex(ValueError, "could not be confirmed stopped"):
                acceptance.run_checks(ledger, self.workspace())
        self.assertIsNone(self.state(ledger)["checks"])

    @unittest.skipUnless(os.name == "nt", "Windows job objects only")
    def test_windows_check_belongs_to_its_job_before_it_runs(self):
        # Codex P1 on PR #22 round 4: assignment after launch left a window for a fast check
        # to spawn and exit unisolated. The check is created suspended, assigned, then resumed.
        process = subprocess.Popen([sys.executable, "-c", "print('ran after resume')"], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, creationflags=acceptance.ProcessTree.creation_flags())
        tree = acceptance.ProcessTree(process)
        self.assertIsNotNone(tree.job, "the suspended check must be in a job before it resumes")
        out, _ = process.communicate(timeout=30)
        self.assertEqual(process.returncode, 0)
        self.assertIn(b"ran after resume", out)
        tree.close()

    def test_workspace_entry_bound_is_enforced_while_scanning(self):
        # Codex P2 on PR #22 round 5: the tree was materialized before the file bound applied,
        # so a workspace of many directories and few files could exhaust the controller.
        ledger, _ = self.start(config=self.config(workspace_digest_max_files=2))
        space = self.workspace(files=("one.txt",))
        for index in range(acceptance.ENTRY_MULTIPLIER * 2 + 1):
            (space / f"dir-{index}").mkdir()
        with self.assertRaisesRegex(ValueError, "entry bound"):
            acceptance.run_checks(ledger, space)
        self.assertIsNone(self.state(ledger)["checks"])
        ledger, _ = self.start(config=self.config(workspace_digest_max_files=2))
        small = self.workspace(files=("one.txt", "two.txt", "three.txt"))
        with self.assertRaisesRegex(ValueError, "digest bound"):
            acceptance.run_checks(ledger, small)

    @unittest.skipUnless(os.name == "nt", "Windows job objects only")
    def test_windows_run_refuses_when_the_job_cannot_be_set_up(self):
        # Codex P1 on PR #22 round 6: resuming without a job left no enforceable cleanup.
        ledger, _ = self.start()
        with mock.patch.object(acceptance.ProcessTree, "_windows_job", return_value=None):
            with self.assertRaisesRegex(ValueError, "not run unisolated"):
                acceptance.run_checks(ledger, self.workspace())
        self.assertIsNone(self.state(ledger)["checks"])
        process = subprocess.Popen([sys.executable, "-c", "print('never')"], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, creationflags=acceptance.ProcessTree.creation_flags())
        with mock.patch.object(acceptance.ProcessTree, "_windows_job", return_value=None):
            with self.assertRaises(ValueError):
                acceptance.ProcessTree(process)
        self.assertIsNotNone(process.poll(), "the suspended check must have been killed, not resumed")

    def test_workspace_scan_does_not_use_a_buffering_traversal(self):
        # Codex P2 on PR #22 round 6: Path.rglob/walk list a whole directory before yielding.
        ledger, _ = self.start()
        space = self.workspace(files=("a.txt", "b.txt"))
        (space / "nested").mkdir()
        (space / "nested" / "c.txt").write_text("x", encoding="utf-8")
        with mock.patch.object(Path, "rglob", side_effect=AssertionError("rglob must not be used")):
            with mock.patch.object(Path, "walk", side_effect=AssertionError("walk must not be used"), create=True):
                files = acceptance.scan_workspace(space, self.config()["policy"])
        self.assertEqual([f.name for f in files], ["a.txt", "b.txt", "c.txt"])

    def test_check_output_is_bounded_while_running_and_hashed_in_full(self):
        # Codex P2 on PR #21: capture_output buffered everything before the bound applied.
        payload = 300000
        argv = [sys.executable, "-c", f"import sys; sys.stdout.write('x' * {payload}); sys.stderr.write('e' * 10)"]
        ledger, _ = self.start(argv=argv, config=self.config(check_output_max_chars=200))
        self.checked(ledger)
        entry = self.state(ledger)["checks"]["results"][0]
        self.assertTrue(entry["passed"])
        self.assertEqual(len(entry["stdout"]), 200)
        self.assertEqual(entry["stderr"], "e" * 10)
        self.assertTrue(entry["output_truncated"])
        expected = acceptance.stream_digest(hashlib.sha256(b"x" * payload).hexdigest(),
                                            hashlib.sha256(b"e" * 10).hexdigest())
        self.assertEqual(entry["output_sha256"], expected)

    def test_runaway_output_is_stopped_at_the_timeout_with_a_bounded_record(self):
        argv = [sys.executable, "-c", "import sys\nwhile True: sys.stdout.write('y' * 65536)"]
        ledger, _ = self.start(argv=argv, timeout=2, config=self.config(check_output_max_chars=200))
        self.checked(ledger)
        entry = self.state(ledger)["checks"]["results"][0]
        self.assertTrue(entry["timed_out"])
        self.assertFalse(entry["passed"])
        self.assertIsNone(entry["exit_code"])
        self.assertEqual(entry["stdout"], "y" * 200)
        self.assertTrue(entry["output_truncated"])

    def test_attestation_over_a_runnable_check_is_refused(self):
        ledger, _ = self.start(argv=FAIL_ARGV)
        self.checked(ledger)
        with self.assertRaisesRegex(ValueError, "executed, never attested"):
            acceptance.append(ledger, "ATTESTATION",
                              {"attestation": {"validation_id": "VAL-FRAMES", "operator": "Operator",
                                               "evidence": ["Trust me"]}},
                              previous_state=acceptance.replay(ledger))

    def test_recorded_checks_must_execute_exactly_the_contract_command(self):
        ledger, _ = self.start()
        state = self.state(ledger)
        forged = {"workspace": "synthetic", "workspace_digest": "c" * 64, "workspace_files": 1,
                  "results": [{"validation_id": "VAL-FRAMES", "machine_runnable": True, "passed": True,
                               "argv": [sys.executable, "-c", "raise SystemExit(1)"], "exit_code": 0,
                               "duration_seconds": 0.1, "timed_out": False, "stdout": "", "stderr": "",
                               "output_truncated": False,
                               "output_sha256": acceptance.router.digest({"stdout": "", "stderr": ""})}]}
        with self.assertRaisesRegex(ValueError, "exactly the contract's declared command"):
            acceptance.append(ledger, "CHECKS", {"checks": forged},
                              previous_state=acceptance.replay(ledger))
        forged["results"][0]["argv"] = PASS_ARGV
        forged["results"][0]["exit_code"] = 1
        with self.assertRaisesRegex(ValueError, "zero exit without timeout"):
            acceptance.append(ledger, "CHECKS", {"checks": forged},
                              previous_state=acceptance.replay(ledger))

    def test_workspace_digest_bound_is_enforced(self):
        ledger, _ = self.start(config=self.config(workspace_digest_max_files=1))
        with self.assertRaisesRegex(ValueError, "digest bound"):
            acceptance.run_checks(ledger, self.workspace(files=("one.txt", "two.txt")))


class ReviewFlowTests(AcceptanceBase):
    def test_reviewer_is_not_engaged_before_the_deterministic_gate_passes(self):
        ledger, _ = self.start(risk="medium")
        with self.assertRaisesRegex(ValueError, "deterministic gate must pass"):
            self.open_review(ledger)
        ledger2, _ = self.start(risk="medium", argv=FAIL_ARGV)
        self.checked(ledger2)
        with self.assertRaisesRegex(ValueError, "deterministic gate must pass"):
            self.open_review(ledger2)

    def test_review_packet_is_rendered_from_the_ledger_with_declared_fields_only(self):
        ledger, _ = self.start(risk="medium")
        self.checked(ledger)
        prepared = self.open_review(ledger)
        packet = wp.read_json(prepared["packet"])
        self.assertEqual(set(packet), acceptance.REVIEW_PACKET_FIELDS)
        self.assertEqual(packet["review_id"], prepared["review_id"])
        self.assertIn("result_supplied_by_worker", packet)
        self.assertIsNotNone(packet["independent_validation"])
        self.assertTrue((Path(prepared["destination"]) / "REVIEWER_RULES.md").is_file())
        with self.assertRaisesRegex((ValueError, FileExistsError), "exists"):
            acceptance.prepare_review(ledger, Path(prepared["destination"]), "model_review", dict(REVIEWER))

    def test_reviewer_independence_and_gate_assignment_are_enforced_at_opening(self):
        ledger, _ = self.start(risk="medium")
        self.checked(ledger)
        with self.assertRaisesRegex(ValueError, "cannot review its own revision"):
            self.open_review(ledger, reviewer={"actor": "Worker", "model_family": "sonnet", "tier": 3})
        with self.assertRaisesRegex(ValueError, "does not require that review gate"):
            self.open_review(ledger, gate="architect_review")
        ledger2, _ = self.start(risk="critical")
        self.checked(ledger2)
        with self.assertRaisesRegex(ValueError, "recorded architect"):
            self.open_review(ledger2, gate="architect_review", reviewer=dict(REVIEWER))

    def test_review_attempt_budget_is_finite(self):
        ledger, _ = self.start(risk="medium", config=self.config(max_review_attempts=1))
        self.checked(ledger)
        self.open_review(ledger)
        acceptance.append(ledger, "REVIEW_ABANDONED",
                          {"reason": "Synthetic reviewer produced no usable report"},
                          previous_state=acceptance.replay(ledger))
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            self.open_review(ledger)

    def test_report_refusals(self):
        ledger, packet = self.start(risk="medium")
        contract = wp.current(packet)["contract"]
        self.checked(ledger)
        prepared = self.open_review(ledger)
        good = make_report(prepared, contract)
        cases = {
            "unexpected field": {**good, "confidence": "high"},
            "wrong review id": {**good, "review_id": "d" * 64},
            "identity mismatch": {**good, "reviewer": {**prepared["reviewer"], "model_family": "other"}},
            "unknown criterion": {**good, "criteria": good["criteria"][:1] + [
                {"criterion_id": "AC-INVENTED", "status": "met", "evidence": ["x"]}]},
            "missing criterion": {**good, "criteria": good["criteria"][:1]},
            "approve with unmet": {**good, "criteria": [
                {**good["criteria"][0], "status": "not_met"}, good["criteria"][1]]},
            "approve with failures": {**good, "contract_failures": [make_failure()]},
            "credential": {**good, "summary": "api_key: sk-ABCDEFGHIJKLMNOPQRSTUV noted"},
            "reject without failures": {**good, "verdict": "REJECT_BOUNDED"},
            "reject all met": {**good, "verdict": "REJECT_BOUNDED", "contract_failures": [make_failure()]},
            "reject unknown ref": {**good, "verdict": "REJECT_BOUNDED",
                                   "criteria": [{**good["criteria"][0], "status": "not_met"}, good["criteria"][1]],
                                   "contract_failures": [make_failure(ref="AC-INVENTED")]},
            "needs evidence empty": {**good, "verdict": "NEEDS_EVIDENCE"},
            "escalation without reason": {**good, "verdict": "NEEDS_ESCALATION"},
        }
        for name, report in cases.items():
            with self.subTest(case=name), self.assertRaises(ValueError):
                self.ingest(ledger, report)
        self.assertEqual(self.state(ledger)["status"], "REVIEW_OPEN")

    def test_bounded_rejection_names_corrective_action_and_returns_for_correction(self):
        ledger, packet = self.start(risk="medium")
        contract = wp.current(packet)["contract"]
        self.checked(ledger)
        prepared = self.open_review(ledger)
        rejection = make_report(prepared, contract, verdict="REJECT_BOUNDED",
                                criteria=[{"criterion_id": "AC-VALID", "status": "not_met",
                                           "evidence": ["Packet evidence contradicts the claim"]},
                                          {"criterion_id": "AC-INVALID", "status": "met",
                                           "evidence": ["Cited from the review packet"]}],
                                contract_failures=[make_failure()])
        outcome = self.ingest(ledger, rejection)
        self.assertEqual(outcome["verdict"], "REJECT_BOUNDED")
        state = self.state(ledger)
        self.assertEqual(state["status"], "REJECTED")
        with self.assertRaisesRegex(ValueError, "Acceptance refused at REJECTED|refused at REJECTED"):
            acceptance.accept(ledger, prepared["reviewer"]["actor"])

    def test_repeated_identical_rejection_escalates_instead_of_looping(self):
        ledger, packet = self.start(risk="medium")
        contract = wp.current(packet)["contract"]
        for round_number in (1, 2):
            self.checked(ledger) if round_number == 1 else None
            prepared = self.open_review(ledger)
            rejection = make_report(prepared, contract, verdict="REJECT_BOUNDED",
                                    criteria=[{"criterion_id": "AC-VALID", "status": "not_met",
                                               "evidence": ["Same defect observed"]},
                                              {"criterion_id": "AC-INVALID", "status": "met",
                                               "evidence": ["Cited from the review packet"]}],
                                    contract_failures=[make_failure()])
            self.ingest(ledger, rejection)
            if round_number == 1:
                self.assertEqual(self.state(ledger)["status"], "REJECTED")
                acceptance.append(ledger, "RESUBMIT",
                                  {"result": make_result(packet), "artifact": make_artifact(),
                                   "implementers": IMPLEMENTERS},
                                  previous_state=acceptance.replay(ledger))
                self.checked(ledger)
        self.assertEqual(self.state(ledger)["status"], "ESCALATION_REQUIRED")
        self.assertEqual(self.state(ledger)["reason"], "REPEATED_REVIEW_REJECTION")

    def test_needs_evidence_names_declared_evidence_and_reopens_the_gates(self):
        ledger, packet = self.start(risk="medium")
        contract = wp.current(packet)["contract"]
        self.checked(ledger)
        prepared = self.open_review(ledger)
        needs = make_report(prepared, contract, verdict="NEEDS_EVIDENCE",
                            criteria=[{"criterion_id": "AC-VALID", "status": "cannot_determine",
                                       "evidence": ["No sample-by-sample record in the packet"]},
                                      {"criterion_id": "AC-INVALID", "status": "met",
                                       "evidence": ["Cited from the review packet"]}],
                            missing_evidence=[{"validation_id": "VAL-FRAMES",
                                               "evidence_required": "Sample-by-sample expected and observed results.",
                                               "reason": "The packet carries only a summary claim"}])
        self.ingest(ledger, needs)
        state = self.state(ledger)
        self.assertEqual((state["status"], state["reason"]), ("GATES_PENDING", "REVIEW_NEEDS_EVIDENCE"))
        undeclared = copy.deepcopy(needs)
        undeclared["missing_evidence"][0]["evidence_required"] = "Something never declared"
        prepared2 = self.open_review(ledger)
        undeclared["review_id"], undeclared["reviewer"] = prepared2["review_id"], prepared2["reviewer"]
        with self.assertRaisesRegex(ValueError, "declared evidence"):
            self.ingest(ledger, undeclared)

    def test_resubmission_clears_checks_attestations_waiver_and_decision(self):
        review = {"required_gates": ["deterministic", "model_review", "cross_family_review",
                                     "architect_review", "user_decision"]}
        ledger, packet = self.start(risk="low", review=review)
        contract = wp.current(packet)["contract"]
        self.checked(ledger)
        acceptance.append(ledger, "WAIVER", {"waiver": {"operator": "Operator",
                                                        "reason": "Synthetic waiver for the fixture"}},
                          previous_state=acceptance.replay(ledger))
        acceptance.append(ledger, "DECISION", {"decision": {"decider": "Winston", "decision": "approve",
                                                            "reason": "Synthetic user approval"}},
                          previous_state=acceptance.replay(ledger))
        prepared = self.open_review(ledger)
        rejection = make_report(prepared, contract, verdict="REJECT_BOUNDED",
                                criteria=[{"criterion_id": "AC-VALID", "status": "not_met",
                                           "evidence": ["Observed defect"]},
                                          {"criterion_id": "AC-INVALID", "status": "met",
                                           "evidence": ["Cited from the review packet"]}],
                                contract_failures=[make_failure()])
        self.ingest(ledger, rejection)
        state = acceptance.append(ledger, "RESUBMIT",
                                  {"result": make_result(packet), "artifact": make_artifact("new content\n"),
                                   "implementers": IMPLEMENTERS},
                                  previous_state=acceptance.replay(ledger))
        self.assertIsNone(state["checks"])
        self.assertEqual(state["attestations"], {})
        self.assertIsNone(state["waiver"])
        self.assertIsNone(state["user_decision"])
        self.assertEqual(state["resubmissions"], 1)


class AcceptTests(AcceptanceBase):
    def test_low_risk_deterministic_only_acceptance_by_the_controller(self):
        ledger, _ = self.start(risk="low")
        self.checked(ledger)
        with self.assertRaisesRegex(ValueError, "must be recorded by"):
            acceptance.accept(ledger, "Somebody else")
        outcome = acceptance.accept(ledger, CONTROLLER)
        self.assertEqual(outcome["status"], "ACCEPTED")
        self.assertEqual(outcome["decision"]["verdict"], "APPROVE")
        self.assertEqual(outcome["decision"]["reviewer"]["model_family"], "deterministic-gate")
        with self.assertRaisesRegex(ValueError, "closed"):
            acceptance.accept(ledger, CONTROLLER)

    def test_an_implementation_actor_cannot_grant_acceptance(self):
        ledger, _ = self.start(risk="low")
        self.checked(ledger)
        record = acceptance.replay(ledger)
        state = copy.deepcopy(record[0])
        state["controller"] = "Worker"
        with self.assertRaisesRegex(ValueError, "cannot accept its own revision"):
            acceptance.acceptable(state, "Worker")

    def test_medium_risk_requires_an_approving_model_review(self):
        ledger, packet = self.start(risk="medium")
        contract = wp.current(packet)["contract"]
        self.checked(ledger)
        with self.assertRaisesRegex(ValueError, "no completed review"):
            acceptance.accept(ledger, REVIEWER["actor"])
        prepared = self.open_review(ledger)
        self.ingest(ledger, make_report(prepared, contract))
        with self.assertRaisesRegex(ValueError, "must be recorded by"):
            acceptance.accept(ledger, CONTROLLER)
        outcome = acceptance.accept(ledger, REVIEWER["actor"])
        self.assertEqual(outcome["status"], "ACCEPTED")
        self.assertEqual(outcome["gates"]["model_review"]["verdict"], "APPROVE")

    def test_high_risk_same_family_review_is_refused_without_a_recorded_waiver(self):
        ledger, packet = self.start(risk="high")
        contract = wp.current(packet)["contract"]
        self.checked(ledger)
        same_family = {"actor": "Same-family reviewer", "model_family": "qwen", "tier": 3}
        prepared = self.open_review(ledger, reviewer=same_family)
        self.ingest(ledger, make_report(prepared, contract, reviewer=same_family))
        with self.assertRaisesRegex(ValueError, "no waiver is recorded"):
            acceptance.accept(ledger, same_family["actor"])
        with self.assertRaisesRegex(ValueError, "cannot waive review of its own work"):
            acceptance.append(ledger, "WAIVER", {"waiver": {"operator": "Worker", "reason": "Self-waiver"}},
                              previous_state=acceptance.replay(ledger))
        acceptance.append(ledger, "WAIVER",
                          {"waiver": {"operator": "Winston",
                                      "reason": "No cross-family reviewer reachable this session"}},
                          previous_state=acceptance.replay(ledger))
        outcome = acceptance.accept(ledger, same_family["actor"])
        self.assertEqual(outcome["status"], "ACCEPTED")
        self.assertTrue(outcome["gates"]["cross_family_review"]["waived"])

    def test_high_risk_cross_family_review_needs_no_waiver(self):
        ledger, packet = self.start(risk="high")
        contract = wp.current(packet)["contract"]
        self.checked(ledger)
        prepared = self.open_review(ledger)
        self.ingest(ledger, make_report(prepared, contract))
        outcome = acceptance.accept(ledger, REVIEWER["actor"])
        self.assertEqual(outcome["status"], "ACCEPTED")
        self.assertFalse(outcome["gates"]["cross_family_review"]["waived"])

    def test_critical_risk_requires_architect_review_and_user_decision(self):
        ledger, packet = self.start(risk="critical")
        contract = wp.current(packet)["contract"]
        self.checked(ledger)
        prepared = self.open_review(ledger)
        self.ingest(ledger, make_report(prepared, contract))
        with self.assertRaisesRegex(ValueError, "architect_review gate has no completed review"):
            acceptance.accept(ledger, REVIEWER["actor"])
        architect_identity = {"actor": ARCHITECT, "model_family": "opus", "tier": 4}
        second = self.open_review(ledger, gate="architect_review", reviewer=architect_identity)
        self.ingest(ledger, make_report(second, contract, reviewer=architect_identity))
        with self.assertRaisesRegex(ValueError, "no recorded approval"):
            acceptance.accept(ledger, REVIEWER["actor"])
        acceptance.append(ledger, "DECISION",
                          {"decision": {"decider": "Winston", "decision": "approve",
                                        "reason": "Synthetic explicit user approval"}},
                          previous_state=acceptance.replay(ledger))
        outcome = acceptance.accept(ledger, REVIEWER["actor"])
        self.assertEqual(outcome["status"], "ACCEPTED")

    def test_a_gate_approval_recorded_before_a_resubmission_does_not_satisfy_the_gate(self):
        # Independent-review finding on Issue #8 itself: without submission binding, a
        # model_review APPROVE of the superseded artifact plus a post-resubmission
        # architect_review APPROVE let accept close a submission model_review never examined.
        ledger, packet = self.start(risk="critical", config=self.config(max_review_attempts=5))
        contract = wp.current(packet)["contract"]
        self.checked(ledger)
        first = self.open_review(ledger)
        self.ingest(ledger, make_report(first, contract))
        architect_identity = {"actor": ARCHITECT, "model_family": "opus", "tier": 4}
        second = self.open_review(ledger, gate="architect_review", reviewer=architect_identity)
        rejection = make_report(second, contract, reviewer=architect_identity, verdict="REJECT_BOUNDED",
                                criteria=[{"criterion_id": "AC-VALID", "status": "not_met",
                                           "evidence": ["Observed defect"]},
                                          {"criterion_id": "AC-INVALID", "status": "met",
                                           "evidence": ["Cited from the review packet"]}],
                                contract_failures=[make_failure()])
        self.ingest(ledger, rejection)
        acceptance.append(ledger, "RESUBMIT",
                          {"result": make_result(packet), "artifact": make_artifact("corrected content\n"),
                           "implementers": IMPLEMENTERS},
                          previous_state=acceptance.replay(ledger))
        self.checked(ledger)
        third = self.open_review(ledger, gate="architect_review", reviewer=architect_identity)
        self.ingest(ledger, make_report(third, contract, reviewer=architect_identity))
        acceptance.append(ledger, "DECISION",
                          {"decision": {"decider": "Winston", "decision": "approve",
                                        "reason": "Synthetic explicit user approval"}},
                          previous_state=acceptance.replay(ledger))
        acceptance.append(ledger, "WAIVER",
                          {"waiver": {"operator": "Winston",
                                      "reason": "Synthetic waiver so only the stale approval blocks"}},
                          previous_state=acceptance.replay(ledger))
        with self.assertRaisesRegex(ValueError, "model_review gate has no completed review for the current submission"):
            acceptance.accept(ledger, REVIEWER["actor"])
        fourth = self.open_review(ledger)
        self.ingest(ledger, make_report(fourth, contract))
        outcome = acceptance.accept(ledger, REVIEWER["actor"])
        self.assertEqual(outcome["status"], "ACCEPTED")
        self.assertEqual(outcome["gates"]["model_review"]["review_id"], fourth["review_id"])

    def test_user_rejection_is_terminal(self):
        ledger, _ = self.start(risk="critical")
        self.checked(ledger)
        state = acceptance.append(ledger, "DECISION",
                                  {"decision": {"decider": "Winston", "decision": "reject",
                                                "reason": "Synthetic user rejection"}},
                                  previous_state=acceptance.replay(ledger))
        self.assertEqual(state["status"], "USER_REJECTED")
        with self.assertRaisesRegex(ValueError, "USER_REJECTED"):
            self.checked(ledger)


class VerifyAndCliTests(AcceptanceBase):
    def test_verify_review_validates_a_packet_report_pair_without_a_ledger(self):
        ledger, packet = self.start(risk="medium")
        contract = wp.current(packet)["contract"]
        self.checked(ledger)
        prepared = self.open_review(ledger)
        report = make_report(prepared, contract)
        report_path = self.directory / "loose-report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        outcome = acceptance.verify_review(self.config(), prepared["packet"], report_path)
        self.assertTrue(outcome["valid"])
        self.assertFalse(outcome["acceptance_granted"])
        tampered = dict(report, review_id="d" * 64)
        report_path.write_text(json.dumps(tampered), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not match the opened review"):
            acceptance.verify_review(self.config(), prepared["packet"], report_path)

    def test_cli_round_trip(self):
        ledger, packet = self.start(risk="medium")
        self.checked(ledger)
        prepared = self.open_review(ledger)
        report = make_report(prepared, wp.current(packet)["contract"])
        report_path = Path(prepared["destination"]) / "review-report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        run = subprocess.run([sys.executable, str(ROOT / "scripts/acceptance.py"),
                              "--config", str(ROOT / "config/acceptance.example.json"),
                              "verify-review", prepared["packet"], str(report_path)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(json.loads(run.stdout)["valid"])


class FeedbackIntegrationTests(AcceptanceBase):
    def setUp(self):
        super().setUp()
        anchor_patch = mock.patch.object(feedback, "active_anchor", return_value=ANCHOR)
        anchor_patch.start()
        self.addCleanup(anchor_patch.stop)
        self.settings = router_config(*(resource(f"tier-{tier}", tier=tier, latency=tier) for tier in (1, 2, 3, 4)))
        self.settings["policy"]["failures_per_tier"] = 20

    def options(self):
        return {"task_class": "synthetic-parser", "input_tokens": 1000, "output_tokens": 1000,
                "unavailable_providers": [], "unavailable_resources": []}

    def feedback_to_review(self, contract):
        packet = make_packet(contract, state="READY")
        self.counter += 1
        fb = self.directory / f"feedback-{self.counter}"
        feedback.initialize(fb, packet, [packet], wp.read_json(ROOT / "config/feedback.example.json"),
                            self.settings, self.directory, ARCHITECT)
        dispatch = feedback.reserve(fb, self.settings, self.options(), self.directory)
        state = feedback.replay(fb)[0]
        result = make_result(state["packet"], dispatch_id=dispatch["dispatch_id"])
        feedback.complete(fb, result)
        state = feedback.replay(fb)[0]
        self.assertEqual(state["status"], "REVIEW_PENDING")
        self.assertEqual(state["packet"]["state"], "REVIEW")
        return fb, state, result

    def acceptance_for(self, fb_state, result, risk_config=None):
        self.counter += 1
        ledger = self.directory / f"ledger-{self.counter}"
        acceptance.initialize(ledger, risk_config or self.config(), fb_state["packet"], result,
                              make_artifact(), CONTROLLER, ARCHITECT,
                              [{"actor": "worker:tier-1", "model_family": "qwen"}], [])
        return ledger

    def test_full_acceptance_closes_the_feedback_task(self):
        contract = make_contract(risk="medium")
        contract["retry_budget"]["max_attempts"] = 8
        fb, state, result = self.feedback_to_review(contract)
        ledger = self.acceptance_for(state, result)
        self.checked(ledger)
        prepared = self.open_review(ledger)
        self.ingest(ledger, make_report(prepared, wp.current(state["packet"])["contract"]))
        acceptance.accept(ledger, REVIEWER["actor"])
        outcome = acceptance.sync_feedback(ledger, fb)
        self.assertEqual(outcome["feedback_status"], "ACCEPTED")
        self.assertEqual(outcome["packet_state"], "ACCEPTED")
        with self.assertRaisesRegex(ValueError, "Controller hold"):
            feedback.reserve(fb, self.settings, self.options(), self.directory)

    def test_acceptance_decision_is_bound_to_its_own_task_and_result(self):
        # Codex P1 on PR #21: task A's accepted ledger forwarded to task B's feedback ledger
        # recorded A's APPROVE against B. Now the decision carries its binding and the
        # reviewed result, and both the forwarding step and the task ledger refuse a mismatch.
        contract_a = make_contract(risk="medium")
        contract_a["retry_budget"]["max_attempts"] = 8
        contract_b = copy.deepcopy(contract_a)
        contract_b["goal"] = "A different task under review at the same time"
        fb_a, state_a, result_a = self.feedback_to_review(contract_a)
        fb_b, state_b, result_b = self.feedback_to_review(contract_b)
        ledger = self.acceptance_for(state_a, result_a)
        self.checked(ledger)
        prepared = self.open_review(ledger)
        self.ingest(ledger, make_report(prepared, wp.current(state_a["packet"])["contract"]))
        acceptance.accept(ledger, REVIEWER["actor"])
        with self.assertRaisesRegex(ValueError, "bound to different task revisions"):
            acceptance.sync_feedback(ledger, fb_b)
        self.assertEqual(feedback.replay(fb_b)[0]["status"], "REVIEW_PENDING")
        decision = acceptance.decision_for(*[acceptance.replay(ledger)[i] for i in (0, 2)])
        self.assertEqual(decision["binding"]["task_id"], state_a["packet"]["task_id"])
        self.assertEqual(decision["result_dispatch_id"], result_a["dispatch_id"])
        for field, value in (("binding", {**decision["binding"], "contract_hash": "a" * 64}),
                             ("binding", {**decision["binding"], "revision": 2}),
                             ("binding", {**decision["binding"], "task_id": "OTHER-TASK"}),
                             ("result_dispatch_id", "d" * 64)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "different"):
                feedback.review(fb_a, {**decision, field: value})
        with self.assertRaisesRegex(ValueError, "different task, revision or contract"):
            feedback.review(fb_b, decision)
        self.assertEqual(feedback.replay(fb_b)[0]["status"], "REVIEW_PENDING")
        outcome = acceptance.sync_feedback(ledger, fb_a)
        self.assertEqual(outcome["feedback_status"], "ACCEPTED")

    def test_pre_binding_review_events_replay_but_new_decisions_require_the_binding(self):
        # Codex P1 on PR #22 round 2: a ledger written before the binding was required must still
        # replay; only a new REVIEW event must carry the binding.
        contract = make_contract(risk="medium")
        contract["retry_budget"]["max_attempts"] = 8
        fb, state, result = self.feedback_to_review(contract)
        legacy = {"review_id": "f" * 64, "verdict": "NEEDS_ESCALATION", "reviewer": dict(REVIEWER),
                  "summary": "Recorded by the previous schema", "evidence": ["legacy evidence"],
                  "contract_failures": [], "acceptance_reference": "acceptance-ledger:legacy"}
        with self.assertRaisesRegex(ValueError, "binding.*required|required property"):
            feedback.review(fb, legacy)
        # Write the legacy event exactly as the previous version stored it, on the hash chain.
        _, sequence, previous = feedback.replay(fb)
        event = {"sequence": sequence + 1, "previous": previous, "kind": "REVIEW",
                 "timestamp": wp.now(), "data": {"decision": legacy}}
        event["hash"] = acceptance.router.digest(event)
        (fb / f"{sequence + 1:08d}.json").write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8")
        replayed = feedback.replay(fb)[0]
        self.assertEqual((replayed["status"], replayed["reason"]), ("NEEDS_ARCHITECT", "REVIEW_ESCALATED"))
        self.assertEqual(replayed["packet"]["state"], "ESCALATED")

    def test_approval_alone_does_not_close_the_feedback_task(self):
        contract = make_contract(risk="medium")
        contract["retry_budget"]["max_attempts"] = 8
        fb, state, result = self.feedback_to_review(contract)
        ledger = self.acceptance_for(state, result)
        self.checked(ledger)
        prepared = self.open_review(ledger)
        self.ingest(ledger, make_report(prepared, wp.current(state["packet"])["contract"]))
        with self.assertRaisesRegex(ValueError, "approval alone is not acceptance"):
            acceptance.sync_feedback(ledger, fb)

    def test_bounded_rejection_returns_the_task_to_the_worker_with_the_failures(self):
        contract = make_contract(risk="medium")
        contract["retry_budget"]["max_attempts"] = 8
        fb, state, result = self.feedback_to_review(contract)
        ledger = self.acceptance_for(state, result)
        self.checked(ledger)
        prepared = self.open_review(ledger)
        rejection = make_report(prepared, wp.current(state["packet"])["contract"],
                                verdict="REJECT_BOUNDED",
                                criteria=[{"criterion_id": "AC-VALID", "status": "not_met",
                                           "evidence": ["Observed defect"]},
                                          {"criterion_id": "AC-INVALID", "status": "met",
                                           "evidence": ["Cited from the review packet"]}],
                                contract_failures=[make_failure()])
        self.ingest(ledger, rejection)
        outcome = acceptance.sync_feedback(ledger, fb)
        self.assertEqual(outcome["feedback_status"], "IN_PROGRESS")
        self.assertEqual(outcome["packet_state"], "IN_PROGRESS")
        fb_state = feedback.replay(fb)[0]
        context = feedback.worker_context(fb_state)
        self.assertEqual(len(context["review_rejections"]), 1)
        self.assertEqual(context["review_rejections"][0]["contract_failures"][0]["failed_ref"], "AC-VALID")
        dispatch = feedback.reserve(fb, self.settings, self.options(), self.directory)
        self.assertEqual(dispatch["status"], "DISPATCH")
        self.assertEqual(len(dispatch["context"]["review_rejections"]), 1)

    def test_repeated_identical_rejection_in_the_task_ledger_escalates(self):
        contract = make_contract(risk="medium")
        contract["retry_budget"]["max_attempts"] = 8
        fb, state, result = self.feedback_to_review(contract)
        decision = {"review_id": "f" * 64, "verdict": "REJECT_BOUNDED",
                    "reviewer": dict(REVIEWER), "summary": "Synthetic rejection",
                    "evidence": ["Synthetic review evidence"],
                    "contract_failures": [{"failed_ref": "AC-VALID", "kind": "criterion",
                                           "what_failed": "Observed defect",
                                           "corrective_action": "Fix within contract"}],
                    "acceptance_reference": "acceptance-ledger:synthetic", **bound_to(state, result)}
        feedback.review(fb, decision)
        self.assertEqual(feedback.replay(fb)[0]["status"], "IN_PROGRESS")
        dispatch = feedback.reserve(fb, self.settings, self.options(), self.directory)
        second = make_result(feedback.replay(fb)[0]["packet"], dispatch_id=dispatch["dispatch_id"])
        feedback.complete(fb, second)
        self.assertEqual(feedback.replay(fb)[0]["status"], "REVIEW_PENDING")
        with self.assertRaisesRegex(ValueError, "different worker result"):
            feedback.review(fb, decision)  # The first decision reviewed the first result, not this one.
        decision.update(bound_to(feedback.replay(fb)[0], second))
        feedback.review(fb, decision)
        final = feedback.replay(fb)[0]
        self.assertEqual((final["status"], final["reason"]),
                         ("NEEDS_ARCHITECT", "REPEATED_REVIEW_REJECTION"))
        self.assertEqual(final["packet"]["state"], "ESCALATED")

    def test_review_decision_requires_review_pending(self):
        contract = make_contract(risk="medium")
        contract["retry_budget"]["max_attempts"] = 8
        packet = make_packet(contract, state="READY")
        self.counter += 1
        fb = self.directory / f"feedback-{self.counter}"
        feedback.initialize(fb, packet, [packet], wp.read_json(ROOT / "config/feedback.example.json"),
                            self.settings, self.directory, ARCHITECT)
        decision = {"review_id": "f" * 64, "verdict": "APPROVE", "reviewer": dict(REVIEWER),
                    "summary": "Premature", "evidence": ["x"], "contract_failures": [],
                    "acceptance_reference": "acceptance-ledger:synthetic",
                    **bound_to(feedback.replay(fb)[0], {"dispatch_id": "e" * 64})}
        with self.assertRaisesRegex(ValueError, "awaiting review"):
            feedback.review(fb, decision)

    def test_contract_repair_cannot_change_risk_or_review_gates(self):
        contract = make_contract(risk="medium", review={"required_gates": ["deterministic", "model_review"]})
        contract["retry_budget"]["max_attempts"] = 8
        fb, state, result = self.feedback_to_review(contract)
        decision = {"review_id": "f" * 64, "verdict": "NEEDS_ESCALATION", "reviewer": dict(REVIEWER),
                    **bound_to(state, result),
                    "summary": "Synthetic escalation to reach an architect hold",
                    "evidence": ["Synthetic review evidence"], "contract_failures": [],
                    "acceptance_reference": "acceptance-ledger:synthetic"}
        feedback.review(fb, decision)
        self.assertEqual(feedback.replay(fb)[0]["status"], "NEEDS_ARCHITECT")
        for change in ({"review": {"required_gates": ["deterministic"]}}, {"risk": "low"}):
            revised = copy.deepcopy(wp.current(feedback.replay(fb)[0]["packet"])["contract"])
            revised["goal"] += " Clarified."
            revised.update(change)
            diagnosis = {"classification": "REPAIR_CONTRACT", "reason": "Synthetic repair",
                         "evidence": ["Synthetic"], "architecture_fingerprint": ANCHOR,
                         "revised_contract": revised}
            with self.subTest(change=tuple(change)), self.assertRaises(ValueError):
                feedback.diagnose(fb, diagnosis, ARCHITECT, self.directory)

    def test_apply_records_the_decision_on_a_standalone_packet(self):
        ledger, packet = self.start(risk="low")
        self.checked(ledger)
        acceptance.accept(ledger, CONTROLLER)
        updated, decision = acceptance.apply_decision(ledger, packet)
        self.assertEqual(updated["state"], "ACCEPTED")
        self.assertEqual(decision["verdict"], "APPROVE")
        self.assertEqual(updated["events"][-1]["role"], "reviewer")


if __name__ == "__main__":
    unittest.main()
