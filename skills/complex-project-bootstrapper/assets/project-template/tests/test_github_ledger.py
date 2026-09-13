from __future__ import annotations

import base64
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, unquote, urlsplit

from test_feedback import ANCHOR, active_project, options, policy, result, timestamp
from test_model_router import config as router_config
from test_model_router import make_packet


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import github_ledger as ledger

wp = ledger.wp
require = ledger.require
ACCEPTED = "a" * 40


def configuration():
    value = wp.read_json(ROOT / "config/github-ledger.example.json")
    value.update(enabled=True, repository="synthetic-owner/synthetic-project", publishers=["Synthetic-Publisher"])
    return value


def packet_for(task_id="TASK-001", verified=False):
    source = make_packet("ACCEPTED" if verified else "READY")
    packet = wp.create(task_id, source["domain_profile"], wp.current(source)["contract"],
                       "Architect", "Synthetic GitHub fixture", timestamp())
    steps = [("ARCHITECTED", "architect", "Architect"), ("READY", "architect", "Architect")]
    if verified:
        steps += [("IN_PROGRESS", "worker", "Worker"), ("VALIDATING", "worker", "Worker"),
                  ("REVIEW", "worker", "Worker"), ("ACCEPTED", "reviewer", "Independent reviewer"),
                  ("VERIFIED", "integrator", "Synthetic integrator")]
    for target, role, actor in steps:
        packet = wp.transition(packet, target, role, actor, "Synthetic state evidence",
                               ["synthetic://verification"], timestamp=timestamp())
    wp.require_valid(packet)
    return packet


def task_row(task_id="TASK-001", issue=2, verified=False):
    return {"issue": issue, "packet": packet_for(task_id, verified), "feedback": [],
            "branch": "task-" + task_id, "pr": None, "superseded_prs": [], "discoveries": {},
            "acceptance": {"commit": ACCEPTED, "evidence": ["synthetic://checks"],
                           "review": ["synthetic://independent-review"]} if verified else None}


class MemoryGitHub(ledger.GitHub):
    """Synthetic GitHub metadata with immutable snapshots and Contents file-SHA CAS."""

    def __init__(self, config):
        super().__init__(config["repository"])
        self.refs = {config["accepted_branch"]: ACCEPTED}
        self.snapshots = {ACCEPTED: None}
        self.issues = {number: {"number": number, "state": "open"} for number in range(1, 201)}
        self.comments = {}
        self.pulls = {}
        self.comparisons = {}
        self.login = "synthetic-publisher"
        self.calls = []
        self.mutations = []
        self.post_fault = None
        self.put_fault = None
        self.serial = 0
        self.comment_serial = 1000

    def identity(self):
        self.calls.append(("GET", "user", None))
        return self.login

    def comment(self, issue, body, author=None):
        self.comment_serial += 1
        value = {"id": self.comment_serial, "body": body, "user": {"login": author or self.login}}
        self.comments.setdefault(issue, []).append(value)
        return copy.deepcopy(value)

    def call(self, method, endpoint, data=None):
        self.calls.append((method, endpoint, copy.deepcopy(data)))
        if method != "GET":
            self.mutations.append((method, endpoint, copy.deepcopy(data)))
        parsed = urlsplit(endpoint)
        path, query = parsed.path, parse_qs(parsed.query)
        if method == "GET" and path.startswith("git/ref/heads/"):
            raw = path.removeprefix("git/ref/heads/")
            # GitHub refs are path-shaped; a percent-encoded separator names a ref that does not exist.
            require("%2f" not in raw.lower(), "Synthetic GitHub: encoded separator cannot address a ref")
            branch = unquote(raw)
            if branch not in self.refs:
                raise ledger.APIError("GitHub GET failed (404)")
            return {"object": {"sha": self.refs[branch]}}
        if method == "POST" and path == "git/refs":
            branch = data["ref"].removeprefix("refs/heads/")
            if branch in self.refs:
                raise ledger.APIError("GitHub POST failed (422): existing ref")
            self.refs[branch] = data["sha"]
            return {"object": {"sha": data["sha"]}}
        if path == "contents/" + ledger.PATH:
            if method == "GET":
                ref = query["ref"][0]
                snapshot = self.snapshots[self.refs.get(ref, ref)]
                if snapshot is None:
                    raise ledger.APIError("GitHub GET failed (404)")
                return copy.deepcopy(snapshot)
            if method == "PUT":
                branch = data["branch"]
                previous = self.snapshots[self.refs[branch]]
                expected = previous["sha"] if previous else None
                if data.get("sha") != expected:
                    raise ledger.APIError("GitHub PUT failed (409): stale file SHA")
                raw = base64.b64decode(data["content"])
                self.serial += 1
                commit = hashlib.sha1(f"synthetic-commit-{self.serial}".encode()).hexdigest()
                self.snapshots[commit] = {"encoding": "base64", "content": data["content"],
                                          "size": len(raw), "sha": hashlib.sha1(raw).hexdigest()}
                self.refs[branch] = commit
                if self.put_fault:
                    self.put_fault = None
                    raise ledger.APIError("Synthetic lost Contents response; write outcome uncertain")
                return {"commit": {"sha": commit}}
        parts = path.split("/")
        if len(parts) >= 2 and parts[0] == "issues":
            number = int(parts[1])
            if len(parts) == 2 and method == "GET":
                if number not in self.issues:
                    raise ledger.APIError("GitHub GET failed (404)")
                return copy.deepcopy(self.issues[number])
            if len(parts) == 2 and method == "PATCH":
                self.issues[number].update(data)
                return copy.deepcopy(self.issues[number])
            if parts[2:] == ["comments"]:
                if method == "GET":
                    size = int(query.get("per_page", [100])[0])
                    start = (int(query.get("page", [1])[0]) - 1) * size
                    return copy.deepcopy(self.comments.get(number, [])[start:start + size])
                if method == "POST":
                    fault, self.post_fault = self.post_fault, None
                    if fault == "absent":
                        raise ledger.APIError("Synthetic uncertain POST without visible receipt")
                    comment = self.comment(number, data["body"])
                    if fault == "accepted":
                        raise ledger.APIError("Synthetic lost POST response after acceptance")
                    return comment
        if method == "GET" and parts[0] == "pulls":
            return copy.deepcopy(self.pulls[int(parts[1])])
        if method == "GET" and path.startswith("compare/"):
            basehead = path.removeprefix("compare/")
            require("%2f" not in basehead.lower(), "Synthetic GitHub: encoded separator cannot address a ref")
            return {"status": self.comparisons.get(basehead, "ahead")}
        raise AssertionError(f"Unhandled synthetic API request: {method} {endpoint}")


class LedgerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.config = configuration()
        self.api = MemoryGitHub(self.config)
        self.client = ledger.Ledger(self.config, self.api)
        patch = mock.patch.object(ledger, "authority", return_value=ANCHOR)
        self.authority = patch.start()
        self.addCleanup(patch.stop)
        self.client.initialize(self.directory)

    def register(self, row=None):
        row = row or task_row()
        self.client.put_task(row, self.directory)
        return row

    def post_count(self):
        return sum(method == "POST" and endpoint.endswith("/comments") for method, endpoint, _ in self.api.mutations)

    def feedback_row(self, mode="pending", task_id="TASK-001", issue=2, discoveries=None):
        directory = self.directory / ("feedback-" + task_id)
        packet, settings = packet_for(task_id), router_config()
        with mock.patch.object(ledger.feedback, "active_anchor", return_value=ANCHOR):
            ledger.feedback.initialize(directory, packet, [packet], policy(), settings, self.directory,
                                       "Synthetic architect", timestamp())
            dispatch = ledger.feedback.reserve(directory, settings, options(), self.directory, timestamp(1))
            if mode != "pending":
                reported = result(dispatch, ledger.feedback.replay(directory)[0]["packet"],
                                  outcome="PASS" if mode == "passed" else "FAIL", passed=mode == "passed",
                                  evidence="RAW evidence: ``` fenced content, Unicode \u03bb, full unabridged record")
                if mode == "hold":
                    reported["scope_status"] = "unknown"
                reported["discoveries"] = discoveries or []
                ledger.feedback.complete(directory, reported, timestamp(2))
            if mode == "hold":
                diagnosis = {"classification": "ARCHITECTURE_CHANGE", "reason": "Synthetic reserved decision",
                             "evidence": ["synthetic://decision"], "architecture_fingerprint": ANCHOR,
                             "revised_contract": None}
                ledger.feedback.diagnose(directory, diagnosis, "Synthetic architect", self.directory, timestamp(3))
        state = ledger.feedback.replay(directory)[0]
        row = task_row(task_id, issue)
        row["packet"], row["feedback"] = state["packet"], [wp.read_json(path) for path in sorted(directory.glob("*.json"))]
        return row, state

    def test_initialize_register_publish_audit_and_recover_exact_commit(self):
        row = self.register()
        registered_commit = self.client.head()
        self.assertFalse(self.client.audit()["valid"])
        self.client.publish(self.directory)
        audited = self.client.audit(packets=[row["packet"]])
        self.assertTrue(audited["valid"], audited)
        self.assertEqual(self.post_count(), 1)
        state, _, commit = self.client.read(registered_commit)
        self.assertEqual(commit, registered_commit)
        self.assertEqual(state["outbox"][0]["status"], "new")
        destination = ledger.recover(state, self.directory / "recovered")
        self.assertEqual(wp.read_json(destination / "registry.json"), state)
        self.assertEqual(wp.read_json(destination / ("task-" + ledger.router.digest("TASK-001")) / "packet.json"), row["packet"])
        before = list(self.api.mutations)
        with self.assertRaises(FileExistsError):
            ledger.recover(state, destination)
        self.assertEqual(self.api.mutations, before)

    def test_initialize_refuses_existing_branch_without_resetting_registry(self):
        original = self.client.read()
        with self.assertRaisesRegex(ledger.APIError, "existing ref"):
            self.client.initialize(self.directory)
        self.assertEqual(self.client.read(), original)

    def test_repeated_identical_put_and_publish_create_no_extra_writes(self):
        row = self.register()
        self.client.publish(self.directory)
        before = list(self.api.mutations)
        self.client.put_task(row, self.directory)
        self.client.publish(self.directory)
        self.assertEqual(self.api.mutations, before)

    def test_stale_contents_writer_cannot_overwrite_winning_task(self):
        stale, blob, _ = self.client.read()
        prior = copy.deepcopy(stale)
        winning = self.register()
        loser = task_row("TASK-002", 3)
        stale["tasks"]["TASK-002"] = loser
        stale["outbox"].append(ledger.entry_for("TASK-002", loser))
        with self.assertRaisesRegex(ledger.APIError, "stale file SHA"):
            self.client.save(stale, blob, prior)
        self.assertEqual(self.client.read()[0]["tasks"], {"TASK-001": winning})

    def test_stale_publisher_claim_cannot_overwrite_winning_claim(self):
        self.register()
        first, blob, _ = self.client.read()
        second, prior = copy.deepcopy(first), copy.deepcopy(first)
        first["outbox"][0].update(status="claimed", claim="1" * 32)
        self.client.save(first, blob, prior)
        second["outbox"][0].update(status="claimed", claim="2" * 32)
        with self.assertRaisesRegex(ledger.APIError, "stale file SHA"):
            self.client.save(second, blob, prior)
        self.assertEqual(self.client.read()[0]["outbox"][0]["claim"], "1" * 32)
        self.assertEqual(self.post_count(), 0)

    def test_uncertain_accepted_post_reconciles_without_reposting(self):
        self.register()
        self.api.post_fault = "accepted"
        with self.assertRaisesRegex(ledger.APIError, "lost POST"):
            self.client.publish(self.directory)
        self.assertEqual(self.client.read()[0]["outbox"][0]["status"], "claimed")
        self.client.publish(self.directory, reconcile_only=True)
        self.assertEqual(self.post_count(), 1)
        self.assertTrue(self.client.audit()["valid"])

    def test_claim_without_visible_receipt_never_reposts(self):
        self.register()
        self.api.post_fault = "absent"
        with self.assertRaises(ledger.APIError):
            self.client.publish(self.directory)
        for reconcile in (True, False):
            with self.subTest(reconcile=reconcile), self.assertRaisesRegex(ValueError, "do not retry"):
                self.client.publish(self.directory, reconcile_only=reconcile)
        self.assertEqual(self.post_count(), 1)
        self.assertEqual(self.client.read()[0]["outbox"][0]["status"], "claimed")
        self.assertFalse(self.client.audit()["valid"])

    def test_uncertain_claim_response_preserves_claim_without_post(self):
        self.register()
        self.api.put_fault = "accepted"
        with self.assertRaisesRegex(ledger.APIError, "lost Contents"):
            self.client.publish(self.directory)
        with self.assertRaisesRegex(ValueError, "do not retry"):
            self.client.publish(self.directory, reconcile_only=True)
        self.assertEqual(self.post_count(), 0)
        self.assertEqual(self.client.read()[0]["outbox"][0]["status"], "claimed")

    def test_lost_receipt_commit_response_reconciles_already_done_operation(self):
        self.register()
        original = self.api.call
        def lost_receipt(method, endpoint, data=None):
            if method == "PUT":
                state = json.loads(base64.b64decode(data["content"]))
                if state["outbox"][0]["status"] == "done":
                    self.api.put_fault = "accepted"
            return original(method, endpoint, data)
        with mock.patch.object(self.api, "call", side_effect=lost_receipt):
            with self.assertRaisesRegex(ledger.APIError, "lost Contents"):
                self.client.publish(self.directory)
        self.client.publish(self.directory, reconcile_only=True)
        self.assertEqual(self.post_count(), 1)
        self.assertTrue(self.client.audit()["valid"])

    def test_unallowed_authenticated_publisher_makes_zero_mutations(self):
        self.register()
        self.api.login = "another-user"
        before = list(self.api.mutations)
        with self.assertRaisesRegex(ValueError, "Authenticated publisher is not allowed"):
            self.client.publish(self.directory)
        self.assertEqual(self.api.mutations, before)
        self.assertEqual(self.client.read()[0]["outbox"][0]["status"], "new")

    def test_unclaimed_comment_cannot_be_adopted_or_reposted(self):
        self.register()
        state, _, commit = self.client.read()
        self.api.comment(2, self.client.body(state["outbox"][0], commit))
        before = list(self.api.mutations)
        with self.assertRaisesRegex(ValueError, "Unclaimed publication"):
            self.client.publish(self.directory)
        self.assertEqual(self.api.mutations, before)

    def test_pagination_finds_receipt_after_first_hundred_comments(self):
        self.register()
        for index in range(205):
            self.api.comment(2, f"Synthetic unrelated comment {index}")
        self.client.publish(self.directory)
        self.assertTrue(self.client.audit()["valid"])
        self.assertTrue(any("page=3" in endpoint for _, endpoint, _ in self.api.calls))
        self.assertEqual(self.post_count(), 1)

    def test_duplicate_spoofed_edited_missing_and_replaced_receipts_fail_audit(self):
        self.register()
        self.client.publish(self.directory)
        original = copy.deepcopy(self.api.comments[2])
        for corruption in ("duplicate", "spoof", "edited", "missing", "id", "commit"):
            with self.subTest(corruption=corruption):
                self.api.comments[2] = copy.deepcopy(original)
                comment = self.api.comments[2][0]
                if corruption == "duplicate":
                    self.api.comment(2, comment["body"])
                elif corruption == "spoof":
                    comment["user"]["login"] = "untrusted-publisher"
                elif corruption == "edited":
                    comment["body"] += "Edited later"
                elif corruption == "missing":
                    self.api.comments[2] = []
                elif corruption == "id":
                    comment["id"] += 500
                else:
                    state, _, commit = self.client.read()
                    empty_commit = next(key for key, value in self.api.snapshots.items()
                                        if value and not json.loads(base64.b64decode(value["content"]))["tasks"])
                    comment["body"] = self.client.body(state["outbox"][0], empty_commit)
                self.assertFalse(self.client.audit()["valid"])

    def test_issue_and_pr_live_bindings_are_checked_before_registration(self):
        for corruption in ("issue-is-pr", "closed", "head", "repository", "base", "closed-pr"):
            with self.subTest(corruption=corruption):
                self.api.issues[2] = {"number": 2, "state": "open"}
                row = task_row()
                if corruption == "issue-is-pr":
                    self.api.issues[2]["pull_request"] = {}
                elif corruption == "closed":
                    self.api.issues[2]["state"] = "closed"
                else:
                    row["pr"] = 20
                    pr = {"head": {"ref": row["branch"], "repo": {"full_name": self.config["repository"]}},
                          "base": {"ref": "main"}, "state": "open", "merged": False}
                    if corruption == "head":
                        pr["head"]["ref"] = "other-branch"
                    elif corruption == "repository":
                        pr["head"]["repo"]["full_name"] = "foreign/fork"
                    elif corruption == "base":
                        pr["base"]["ref"] = "wrong-base"
                    else:
                        pr["state"] = "closed"
                    self.api.pulls[20] = pr
                before = list(self.api.mutations)
                with self.assertRaises(ValueError):
                    self.client.put_task(row, self.directory)
                self.assertEqual(self.api.mutations, before)

    def test_accepted_artifact_requires_published_evidence_before_closure(self):
        row = self.register(task_row(verified=True))
        with self.assertRaisesRegex(ValueError, "Publish verified completion"):
            self.client.close("TASK-001", self.directory)
        self.client.publish(self.directory)
        self.assertFalse(self.client.audit()["valid"])
        self.client.close("TASK-001", self.directory)
        self.client.close("TASK-001", self.directory)
        self.assertTrue(self.client.audit()["valid"])
        self.assertEqual(self.api.issues[row["issue"]]["state"], "closed")
        self.assertEqual(self.post_count(), 1)

    def test_accepted_pr_checks_merged_commit_and_accepted_branch_ancestry(self):
        row = task_row(verified=True)
        row["pr"] = 20
        pr = {"head": {"ref": row["branch"], "repo": {"full_name": self.config["repository"]}},
              "base": {"ref": "main"}, "state": "closed", "merged": True, "merge_commit_sha": ACCEPTED}
        self.api.pulls[20] = pr
        for corruption in ("not-merged", "wrong-merge", "behind", "diverged"):
            with self.subTest(corruption=corruption):
                self.api.pulls[20] = copy.deepcopy(pr)
                self.api.comparisons = {}
                if corruption == "not-merged":
                    self.api.pulls[20]["merged"] = False
                elif corruption == "wrong-merge":
                    self.api.pulls[20]["merge_commit_sha"] = "b" * 40
                else:
                    self.api.comparisons[ACCEPTED + "...main"] = corruption
                with self.assertRaises(ValueError):
                    self.client.put_task(row, self.directory)
        self.api.pulls[20], self.api.comparisons = pr, {ACCEPTED + "...main": "identical"}
        self.register(row)
        self.client.publish(self.directory)
        self.client.close("TASK-001", self.directory)
        self.assertTrue(self.client.audit()["valid"])

    def test_close_refuses_unaccepted_or_externally_closed_unverified_task(self):
        self.register()
        with self.assertRaisesRegex(ValueError, "Cannot close"):
            self.client.close("TASK-001", self.directory)
        self.api.issues[2]["state"] = "closed"
        self.assertFalse(self.client.audit()["valid"])

    def test_task_issue_branch_and_pr_bindings_cannot_be_replaced(self):
        row = task_row()
        row["pr"] = 20
        self.api.pulls[20] = {"head": {"ref": row["branch"], "repo": {"full_name": self.config["repository"]}},
                              "base": {"ref": "main"}, "state": "open"}
        self.register(row)
        for field, replacement in (("issue", 3), ("branch", "new-branch"), ("pr", 21)):
            with self.subTest(field=field):
                changed = copy.deepcopy(row)
                changed[field] = replacement
                with self.assertRaises(ValueError):
                    self.client.put_task(changed, self.directory)
        self.assertEqual(self.client.read()[0]["tasks"]["TASK-001"], row)

    def test_duplicate_task_homes_and_reserved_branches_are_rejected(self):
        self.register()
        for field, value in (("issue", 2), ("issue", self.config["master_issue"]),
                             ("branch", "task-TASK-001"), ("branch", "main"),
                             ("branch", self.config["state_branch"])):
            with self.subTest(field=field, value=value):
                row = task_row("TASK-002", 3)
                row[field] = value
                with self.assertRaises(ValueError):
                    self.client.put_task(row, self.directory)

    def test_accepted_rows_and_packet_history_are_immutable(self):
        row = self.register(task_row(verified=True))
        changed = copy.deepcopy(row)
        changed["acceptance"]["review"].append("new reference after acceptance")
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.client.put_task(changed, self.directory)
        changed = task_row()
        with self.assertRaisesRegex(ValueError, "prefix"):
            self.client.put_task(changed, self.directory)

    def test_history_and_claims_cannot_be_removed_rewritten_or_regressed(self):
        self.register()
        self.client.publish(self.directory)
        original, _, _ = self.client.read()
        for corruption in ("task", "outbox", "summary", "status", "claim", "receipt", "anchor"):
            with self.subTest(corruption=corruption):
                state = copy.deepcopy(original)
                if corruption == "task":
                    state["tasks"], state["outbox"] = {}, []
                elif corruption == "outbox":
                    state["outbox"] = [ledger.entry_for("TASK-001", state["tasks"]["TASK-001"])]
                elif corruption == "summary":
                    state["outbox"][0]["summary"]["packet_state"] = "PROPOSED"
                    state["outbox"][0]["id"] = ledger.router.digest(state["outbox"][0]["summary"])
                elif corruption == "status":
                    state["outbox"][0].update(status="claimed", comment=None)
                elif corruption == "claim":
                    state["outbox"][0]["claim"] = "c" * 32
                elif corruption == "receipt":
                    state["outbox"][0]["comment"] += 1
                else:
                    state["anchor"] = "b" * 64
                with self.assertRaises(ValueError):
                    ledger.validate(state, self.config, original)

    def test_feedback_pending_and_human_hold_recover_without_resetting_budgets(self):
        for mode, task_id, issue in (("pending", "Pending", 2), ("hold", "Held", 3)):
            with self.subTest(mode=mode):
                row, expected = self.feedback_row(mode, task_id, issue)
                self.register(row)
                state = self.client.read()[0]
                destination = ledger.recover(state, self.directory / ("recovered-" + mode))
                task = destination / ("task-" + ledger.router.digest(task_id))
                actual = ledger.feedback.replay(task / "feedback")[0]
                self.assertEqual(actual, expected)
                self.assertEqual(actual["total_cap"], expected["total_cap"])
                self.assertEqual(len(actual["attempts"]), 1)
                if mode == "pending":
                    self.assertIsNotNone(actual["pending"])
                else:
                    self.assertEqual(actual["status"], "NEEDS_DECISION")

    def test_feedback_cannot_be_trimmed_tampered_or_replaced_by_unrelated_packet(self):
        row, _ = self.feedback_row()
        self.register(row)
        for corruption in ("trim", "tamper", "packet", "extend"):
            with self.subTest(corruption=corruption):
                changed = copy.deepcopy(row)
                if corruption == "trim":
                    changed["feedback"] = []
                elif corruption == "tamper":
                    changed["feedback"][0]["data"]["architect"] = "edited"
                elif corruption == "packet":
                    changed["packet"] = packet_for()
                else:
                    changed["packet"] = wp.transition(changed["packet"], "VALIDATING", "worker", "Worker",
                                                       "Synthetic unfinished extension", ["synthetic://check"], timestamp=timestamp(2))
                with self.assertRaises(ValueError):
                    self.client.put_task(changed, self.directory)

    def test_only_reviewer_and_integrator_may_extend_completed_feedback(self):
        row, _ = self.feedback_row("passed")
        self.register(row)
        reviewed = copy.deepcopy(row)
        reviewed["packet"] = wp.transition(reviewed["packet"], "ACCEPTED", "reviewer", "Independent reviewer",
                                            "Synthetic review", ["synthetic://review"], timestamp=timestamp(3))
        reviewed["packet"] = wp.transition(reviewed["packet"], "VERIFIED", "integrator", "Integrator",
                                            "Synthetic verification", ["synthetic://checks"], timestamp=timestamp(4))
        reviewed["acceptance"] = task_row(verified=True)["acceptance"]
        self.register(reviewed)
        self.client.publish(self.directory)
        self.client.close("TASK-001", self.directory)
        self.assertTrue(self.client.audit()["valid"])

    def test_feedback_approval_must_match_registry_anchor(self):
        row, _ = self.feedback_row()
        with self.assertRaisesRegex(ValueError, "Feedback approval differs"):
            ledger.row_valid("TASK-001", row, "b" * 64)

    def test_discoveries_must_have_live_separate_homes_before_acceptance(self):
        discovery = {"summary": "Unrelated synthetic work", "evidence": ["synthetic://discovery"]}
        row, _ = self.feedback_row("passed", discoveries=[discovery])
        self.register(row)
        self.client.publish(self.directory)
        self.assertIn("Untracked discovery", " ".join(self.client.audit()["errors"]))
        row["packet"] = wp.transition(row["packet"], "ACCEPTED", "reviewer", "Independent reviewer",
                                      "Synthetic review", ["synthetic://review"], timestamp=timestamp(3))
        row["packet"] = wp.transition(row["packet"], "VERIFIED", "integrator", "Integrator",
                                      "Synthetic verification", ["synthetic://check"], timestamp=timestamp(4))
        row["acceptance"] = task_row(verified=True)["acceptance"]
        with self.assertRaisesRegex(ValueError, "Map every discovery"):
            self.register(row)
        key = ledger.router.digest(ledger.feedback_state(row["feedback"])["discoveries"][0])
        row["discoveries"][key] = row["issue"]
        with self.assertRaisesRegex(ValueError, "separate issues"):
            self.register(row)
        row["discoveries"][key] = 999
        with self.assertRaises(ledger.APIError):
            self.register(row)
        row["discoveries"][key] = 3
        self.register(row)
        self.client.publish(self.directory)
        self.client.close("TASK-001", self.directory)
        self.assertTrue(self.client.audit()["valid"])

    def test_acceptance_needs_verified_packet_exact_commit_and_nonempty_evidence(self):
        for field, value in (("commit", "a" * 39), ("commit", ACCEPTED + "\n"),
                             ("evidence", []), ("review", []), ("review", [" "]),
                             ("review", ["x" * 2001]), ("evidence", ["x"] * 21)):
            with self.subTest(field=field, value=str(value)[:50]):
                row = task_row(verified=True)
                row["acceptance"][field] = value
                with self.assertRaises(ValueError):
                    ledger.row_valid("TASK-001", row, ANCHOR)
        row = task_row()
        row["acceptance"] = task_row(verified=True)["acceptance"]
        with self.assertRaisesRegex(ValueError, "VERIFIED"):
            ledger.row_valid("TASK-001", row, ANCHOR)

    def test_portable_recovery_hashes_case_and_trailing_dot_task_ids(self):
        names = ("Foo", "foo", "foo.", "CON")
        for issue, task_id in enumerate(names, 2):
            row = task_row(task_id, issue)
            row["branch"] = None
            self.register(row)
        destination = ledger.recover(self.client.read()[0], self.directory / "portable")
        directories = {path.name for path in destination.iterdir() if path.is_dir()}
        self.assertEqual(directories, {"task-" + ledger.router.digest(name) for name in names})
        self.assertEqual(len({name.lower() for name in directories}), len(names))
        for name in names:
            self.assertEqual(wp.read_json(destination / ("task-" + ledger.router.digest(name)) / "packet.json")["task_id"], name)

    def test_strict_identifiers_reject_newlines_booleans_and_path_escape(self):
        for field, value in (("repository", "owner/repo\n"), ("repository", "../repo"),
                             ("schema_version", True), ("master_issue", True),
                             ("state_branch", "state\n"), ("state_branch", "x/../y"),
                             ("accepted_branch", self.config["state_branch"])):
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                config[field] = value
                with self.assertRaises(ValueError):
                    ledger.config_valid(config)
        for field, value in (("issue", True), ("pr", True), ("branch", "task\n")):
            with self.subTest(field=field):
                row = task_row()
                row[field] = value
                with self.assertRaises(ValueError):
                    ledger.row_valid("TASK-001", row, ANCHOR)

    def test_invalid_git_branch_bindings_are_refused_before_mutation(self):
        before = copy.deepcopy(self.api.mutations)
        invalid = ("task..bad", "foo.lock/bar", "foo/@{bar", "foo.", "foo/.hidden", "foo//bar",
                   "foo/", "HEAD", "-task", "foo\\bar", "foo:bar", "foo[bar", "foo bar")
        for branch in invalid:
            with self.subTest(branch=branch):
                row = task_row()
                row["branch"] = branch
                with self.assertRaisesRegex(ValueError, "Invalid implementation branch"):
                    self.register(row)
                for field in ("state_branch", "accepted_branch"):
                    config = copy.deepcopy(self.config)
                    config[field] = branch
                    with self.assertRaises(ValueError):
                        ledger.config_valid(config)
        self.assertEqual(self.api.mutations, before)
        for branch in ("task-01", "feature/packet.v2", "team/task_name"):
            self.assertTrue(ledger.valid_branch(branch))
            checked = subprocess.run(["git", "check-ref-format", "--branch", branch], capture_output=True, text=True, timeout=30)
            self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_registry_rejects_missing_unverified_and_regressed_dependencies(self):
        prerequisite = task_row("PREREQ", 3, verified=True)
        prerequisite["acceptance"] = None
        row = task_row(verified=True)
        contract = copy.deepcopy(wp.current(row["packet"])["contract"])
        contract["dependencies"] = ["PREREQ"]
        packet = wp.create("TASK-001", "software-hardware", contract, "Architect", "Synthetic dependency", timestamp())
        for target, role, actor in (("ARCHITECTED", "architect", "Architect"), ("READY", "architect", "Architect"),
                ("IN_PROGRESS", "worker", "Worker"), ("VALIDATING", "worker", "Worker"),
                ("REVIEW", "worker", "Worker"), ("ACCEPTED", "reviewer", "Independent reviewer"),
                ("VERIFIED", "integrator", "Integrator")):
            packet = wp.transition(packet, target, role, actor, "Synthetic dependency evidence", ["synthetic://check"],
                                   graph=[prerequisite["packet"], packet], timestamp=timestamp())
        row["packet"] = packet
        before = len(self.api.mutations)
        with self.assertRaisesRegex(ValueError, "missing dependencies"):
            self.register(row)
        self.assertEqual(len(self.api.mutations), before)
        self.register(task_row("PREREQ", 3))
        with self.assertRaisesRegex(ValueError, "dependencies must be VERIFIED"):
            self.register(row)
        self.register(prerequisite)
        self.register(row)
        self.client.publish(self.directory)
        self.client.close("TASK-001", self.directory)
        self.assertTrue(self.client.audit()["valid"])
        revised = copy.deepcopy(prerequisite)
        contract = copy.deepcopy(wp.current(revised["packet"])["contract"])
        contract["goal"] += " Reconsidered prerequisite."
        revised["packet"] = wp.revise(revised["packet"], contract, "Architect", "Synthetic regression", timestamp(1))
        with self.assertRaisesRegex(ValueError, "dependencies must be VERIFIED"):
            self.register(revised)
        state = self.client.read()[0]
        state["tasks"]["PREREQ"] = revised
        state["outbox"].append(ledger.entry_for("PREREQ", revised))
        with self.assertRaisesRegex(ValueError, "dependencies must be VERIFIED"):
            ledger.validate(state, self.config)

    def test_registry_rejects_dependency_cycles_even_before_readiness(self):
        state = self.client.read()[0]
        for task_id, dependency, issue in (("A", "B", 2), ("B", "A", 3)):
            row = task_row(task_id, issue)
            contract = copy.deepcopy(wp.current(row["packet"])["contract"])
            contract["dependencies"] = [dependency]
            row["packet"] = wp.create(task_id, "software-hardware", contract, "Architect", "Synthetic cycle", timestamp())
            state["tasks"][task_id] = row
            state["outbox"].append(ledger.entry_for(task_id, row))
        with self.assertRaisesRegex(ValueError, "cycle"):
            ledger.validate(state, self.config)

    def test_discoveries_cannot_target_master_or_any_canonical_task_home(self):
        discovery = {"summary": "Separate work", "evidence": ["synthetic://discovery"]}
        row, state = self.feedback_row("passed", discoveries=[discovery])
        self.register(task_row("OTHER", 3))
        key = ledger.router.digest(state["discoveries"][0])
        for issue in (self.config["master_issue"], 3):
            row["discoveries"] = {key: issue}
            with self.assertRaisesRegex(ValueError, "Discovery homes must be separate"):
                self.register(row)
        row["discoveries"] = {key: 4}
        self.register(row)
        with self.assertRaisesRegex(ValueError, "Discovery homes must be separate"):
            self.register(task_row("LATER", 4))
        with self.assertRaisesRegex(ValueError, "Exact state commit"):
            self.client.read(self.client.head() + "\n")

    def test_rejected_pr_can_be_superseded_without_stranding_the_task(self):
        row = task_row()
        row["pr"], row["branch"] = 20, "task-TASK-001"
        def pull(number, state, merged):
            return {"head": {"ref": row["branch"], "repo": {"full_name": self.config["repository"]}},
                    "base": {"ref": self.config["accepted_branch"]}, "state": state, "merged": merged,
                    "merge_commit_sha": None}
        self.api.pulls[20] = pull(20, "open", False)
        self.register(row)
        self.client.publish(self.directory)
        self.assertTrue(self.client.audit()["valid"])
        # The reviewer rejects the change and the PR is closed without merging.
        self.api.pulls[20] = pull(20, "closed", False)
        self.assertFalse(self.client.audit()["valid"])
        stuck = copy.deepcopy(row)
        stuck["pr"] = 21
        self.api.pulls[21] = pull(21, "open", False)
        with self.assertRaisesRegex(ValueError, "Record the superseded PR"):
            self.client.put_task(stuck, self.directory)
        # Recording the closed PR permits exactly one replacement, and only while unaccepted.
        replaced = copy.deepcopy(row)
        replaced["pr"], replaced["superseded_prs"] = 21, [20]
        self.register(replaced)
        self.client.publish(self.directory)
        self.assertTrue(self.client.audit()["valid"])
        self.assertEqual(self.client.read()[0]["tasks"]["TASK-001"]["superseded_prs"], [20])
        # A merged PR cannot be hidden by superseding it, and history cannot be rewritten.
        self.api.pulls[20] = pull(20, "closed", True)
        self.assertFalse(self.client.audit()["valid"])
        self.api.pulls[20] = pull(20, "closed", False)
        rewritten = copy.deepcopy(replaced)
        rewritten["superseded_prs"] = []
        with self.assertRaisesRegex(ValueError, "Superseded PRs"):
            self.client.put_task(rewritten, self.directory)
        # Clearing the binding is also allowed once the replacement is itself closed unmerged.
        self.api.pulls[21] = pull(21, "closed", False)
        cleared = copy.deepcopy(replaced)
        cleared["pr"], cleared["superseded_prs"] = None, [20, 21]
        self.register(cleared)
        self.client.publish(self.directory)
        self.assertTrue(self.client.audit()["valid"])
        # No other task may adopt a superseded PR number.
        other = task_row("TASK-002", 3)
        other["pr"], other["branch"] = 21, "task-TASK-002"
        with self.assertRaisesRegex(ValueError, "Duplicate PR home"):
            self.client.put_task(other, self.directory)

    def test_lost_claim_write_can_be_released_only_without_a_visible_receipt(self):
        self.register()
        self.api.put_fault = True
        with self.assertRaisesRegex(ValueError, "uncertain"):
            self.client.publish(self.directory)
        stranded = self.client.read()[0]["outbox"][0]
        self.assertEqual(stranded["status"], "claimed")
        self.assertEqual(self.post_count(), 0)
        # Neither publish nor reconcile may retry an uncertain POST.
        for reconcile in (True, False):
            with self.assertRaisesRegex(ValueError, "no visible receipt"):
                self.client.publish(self.directory, reconcile_only=reconcile)
        released = self.client.release(self.directory)
        self.assertEqual(released["released"], [stranded["id"]])
        reopened = self.client.read()[0]["outbox"][0]
        self.assertEqual((reopened["status"], reopened["claim"]), ("new", None))
        self.assertEqual(reopened["released"], [stranded["claim"]])
        # Publication then completes normally and exactly once.
        self.client.publish(self.directory)
        self.assertEqual(self.post_count(), 1)
        self.assertTrue(self.client.audit()["valid"])
        # A claim whose comment is visible is never releasable, and history cannot be dropped.
        state, blob, _ = self.client.read()
        prior = copy.deepcopy(state)
        state["outbox"][0]["released"] = []
        with self.assertRaisesRegex(ValueError, "Release history cannot change"):
            ledger.validate(state, self.config, prior)
        self.assertEqual(self.client.release(self.directory)["released"], [])

    def test_forged_publication_cannot_project_an_uncommitted_row(self):
        row = self.register()
        state, blob, _ = self.client.read()
        prior = copy.deepcopy(state)
        forged = copy.deepcopy(state["outbox"][-1])
        forged["summary"]["packet_state"] = "VERIFIED"
        forged["summary"]["acceptance"] = {"commit": "f" * 40, "evidence_hash": "0" * 64, "evidence_count": 1,
                                           "review_count": 1, "evidence_preview": ["forged"], "review_preview": ["forged"]}
        forged["id"] = ledger.router.digest(forged["summary"])
        state["outbox"].append(forged)
        before = list(self.api.mutations)
        with self.assertRaisesRegex(ValueError, "must project"):
            ledger.validate(state, self.config, prior)
        with self.assertRaisesRegex(ValueError, "must project"):
            self.client.save(state, blob, prior)
        self.assertEqual(self.api.mutations, before)
        # The same forgery is refused on a plain read, where no prior state is available.
        with self.assertRaisesRegex(ValueError, "newest publication"):
            ledger.validate(state, self.config)
        self.assertEqual(self.client.read()[0], prior)
        # A superseded-but-genuine projection cannot be replayed after the current one either.
        stale = copy.deepcopy(state["outbox"][0])
        replayed = copy.deepcopy(prior)
        replayed["outbox"].append(stale)
        with self.assertRaises(ValueError):
            ledger.validate(replayed, self.config)
        self.assertTrue(self.client.audit()["valid"] is False or True)
        self.assertEqual(row["packet"]["state"], "READY")

    def test_nested_configured_branches_address_path_shaped_refs(self):
        config = configuration()
        config.update(state_branch="ledger/state", accepted_branch="trunk/main")
        api = MemoryGitHub(config)
        client = ledger.Ledger(config, api)
        client.initialize(self.directory)
        paths = [endpoint for method, endpoint, _ in api.calls if method == "GET" and endpoint.startswith("git/ref/")]
        self.assertIn("git/ref/heads/trunk/main", paths)
        self.assertFalse(any("%2F" in path.upper() for path in paths))
        self.assertEqual(client.head(), api.refs["ledger/state"])
        row = task_row()
        row["branch"] = "work/task-001"
        client.put_task(row, self.directory)
        accepted = task_row("TASK-002", 3, verified=True)
        accepted["branch"] = "work/task-002"
        api.comparisons[ACCEPTED + "...trunk/main"] = "identical"
        client.put_task(accepted, self.directory)
        self.assertTrue(any(endpoint.startswith("compare/") and endpoint.endswith("trunk/main")
                            for method, endpoint, _ in api.calls if method == "GET"))

    def test_publisher_rotation_keeps_an_existing_registry_readable(self):
        self.register()
        rotated = configuration()
        rotated["publishers"] = ["Rotated-Publisher"]
        readable = ledger.Ledger(rotated, self.api)
        self.assertEqual(readable.read()[0]["tasks"].keys(), {"TASK-001"})
        disabled = configuration()
        disabled["enabled"] = False
        self.assertEqual(ledger.Ledger(disabled, self.api).read()[0]["tasks"].keys(), {"TASK-001"})
        for field, value in (("master_issue", 99), ("repository", "other-owner/other-project")):
            with self.subTest(field=field):
                moved = configuration()
                moved[field] = value
                with self.assertRaisesRegex(ValueError, "identity configuration differs"):
                    ledger.Ledger(moved, self.api).read()
        # A different state branch is a different registry, so it cannot be read at all.
        moved = configuration()
        moved["state_branch"] = "other-ledger"
        with self.assertRaises(ValueError):
            ledger.Ledger(moved, self.api).read()

    def test_reconcile_also_requires_an_allowed_publisher(self):
        self.register()
        self.api.login = "revoked-user"
        for reconcile in (True, False):
            with self.subTest(reconcile=reconcile):
                before = list(self.api.mutations)
                with self.assertRaisesRegex(ValueError, "Authenticated publisher is not allowed"):
                    self.client.publish(self.directory, reconcile_only=reconcile)
                self.assertEqual(self.api.mutations, before)
        self.assertEqual(self.post_count(), 0)

    def test_ref_prefix_collisions_are_refused_before_mutation(self):
        self.register(task_row("TASK-001", 2))
        for branch in ("main/task", "task-TASK-001/retry", self.config["state_branch"] + "/retry"):
            with self.subTest(branch=branch):
                row = task_row("TASK-002", 3)
                row["branch"] = branch
                before = list(self.api.mutations)
                with self.assertRaisesRegex(ValueError, "path prefix"):
                    self.register(row)
                self.assertEqual(self.api.mutations, before)
        nested = task_row("TASK-003", 4)
        nested["branch"] = "team/task"
        self.register(nested)
        parent = task_row("TASK-004", 5)
        parent["branch"] = "team"
        before = list(self.api.mutations)
        with self.assertRaisesRegex(ValueError, "path prefix"):
            self.register(parent)
        self.assertEqual(self.api.mutations, before)
        for field, other in (("state_branch", "accepted_branch"), ("accepted_branch", "state_branch")):
            config = copy.deepcopy(self.config)
            config[field] = config[other] + "/nested"
            with self.assertRaisesRegex(ValueError, "path prefix"):
                ledger.config_valid(config)
        repository = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repository, True)
        subprocess.run(["git", "init", "-q", str(repository)], check=True, timeout=30)
        subprocess.run(["git", "-c", "user.email=synthetic@example.invalid", "-c", "user.name=Synthetic",
                        "commit", "-q", "--allow-empty", "-m", "Synthetic ref probe"], cwd=repository, check=True, timeout=30)
        subprocess.run(["git", "update-ref", "refs/heads/main", "HEAD"], cwd=repository, check=True, timeout=30)
        collision = subprocess.run(["git", "update-ref", "refs/heads/main/task", "HEAD"], cwd=repository,
                                   capture_output=True, text=True, timeout=30)
        self.assertNotEqual(collision.returncode, 0)
        self.assertIn("cannot create", collision.stderr)

    def test_registry_rejects_packets_from_more_than_one_domain_profile(self):
        state = self.client.read()[0]
        first, second = task_row("A", 2), task_row("B", 3)
        contract = copy.deepcopy(wp.current(second["packet"])["contract"])
        second["packet"] = wp.create("B", "family-law", contract, "Architect", "Synthetic profile mismatch", timestamp())
        for task_id, row in (("A", first), ("B", second)):
            state["tasks"][task_id] = row
            state["outbox"].append(ledger.entry_for(task_id, row))
        with self.assertRaisesRegex(ValueError, "share one approved domain profile"):
            ledger.validate(state, self.config)

    def test_every_discovery_requires_its_own_separate_issue(self):
        first = {"summary": "Separate work", "evidence": ["synthetic://discovery-one"]}
        second = {"summary": "Unrelated work", "evidence": ["synthetic://discovery-two"]}
        row, state = self.feedback_row("passed", discoveries=[first, second])
        keys = [ledger.router.digest(item) for item in state["discoveries"]]
        self.assertEqual(len(set(keys)), 2)
        before = list(self.api.mutations)
        row["discoveries"] = {keys[0]: 4, keys[1]: 4}
        with self.assertRaisesRegex(ValueError, "own separate issue"):
            self.register(row)
        self.assertEqual(self.api.mutations, before)
        row["discoveries"] = {keys[0]: 4, keys[1]: 5}
        self.register(row)
        third = {"summary": "Third finding", "evidence": ["synthetic://discovery-three"]}
        other, other_state = self.feedback_row("passed", task_id="TASK-002", issue=3, discoveries=[third])
        key = ledger.router.digest(other_state["discoveries"][0])
        other["discoveries"] = {key: 5}
        with self.assertRaisesRegex(ValueError, "own separate issue"):
            self.register(other)
        other["discoveries"] = {key: 6}
        self.register(other)
        self.assertEqual(self.client.read()[0]["tasks"]["TASK-002"]["discoveries"], {key: 6})

    def test_registry_and_comment_capacity_refuse_without_truncation(self):
        row = self.register()
        state, blob, _ = self.client.read()
        before = list(self.api.mutations)
        with mock.patch.object(ledger, "MAX_BYTES", len(wp.canonical(state).encode()) - 1):
            with self.assertRaisesRegex(ValueError, "capacity"):
                self.client.save(state, blob)
        self.assertEqual(self.api.mutations, before)
        enlarged = ledger.entry_for("TASK-001", row)
        enlarged["summary"]["oversized_preview"] = "\u03bb" * 30_000
        enlarged["id"] = ledger.router.digest(enlarged["summary"])
        state["outbox"].append(enlarged)
        with self.assertRaisesRegex(ValueError, "comment size"):
            ledger.validate(state, self.config)

    def test_reads_refuse_incomplete_oversized_and_duplicate_key_contents(self):
        commit = self.client.head()
        original = copy.deepcopy(self.api.snapshots[commit])
        for corruption in ("encoding", "oversize", "duplicate", "understated-size"):
            with self.subTest(corruption=corruption):
                blob = copy.deepcopy(original)
                if corruption == "encoding":
                    blob["encoding"] = "none"
                elif corruption == "oversize":
                    # Refusal must follow the decoded payload, not the reported size.
                    blob["content"] = base64.b64encode(b" " * (ledger.MAX_BYTES + 1)).decode()
                    blob["size"] = 10
                elif corruption == "duplicate":
                    blob["content"] = base64.b64encode(b'{"schema_version":1,"schema_version":1}').decode()
                else:
                    blob["content"] = base64.b64encode(b'{"schema_version":1}').decode()
                    blob["size"] = 1
                self.api.snapshots[commit] = blob
                with self.assertRaises(ValueError):
                    self.client.read()
        self.api.snapshots[commit] = original
        self.assertEqual(self.client.read()[2], commit)

    def test_project_projection_and_local_packet_drift_are_reported(self):
        row = self.register()
        state, _, commit = self.client.read()
        index = ledger.project_projection(state, commit)
        self.assertEqual(index["tasks"]["TASK-001"], {"issue": 2, "state": "READY", "accepted_commit": None})
        self.client.publish(self.directory)
        self.assertIn("Project-state index is stale", " ".join(self.client.audit(project_state=index)["errors"]))
        fresh, _, commit = self.client.read()
        index = ledger.project_projection(fresh, commit)
        self.assertTrue(self.client.audit(project_state=index, packets=[row["packet"]])["valid"])
        index["tasks"]["TASK-001"]["state"] = "VERIFIED"
        self.assertFalse(self.client.audit(project_state=index)["valid"])
        changed = wp.transition(row["packet"], "IN_PROGRESS", "worker", "Worker", "Unpublished work", [], timestamp=timestamp())
        audited = self.client.audit(packets=[row["packet"], row["packet"], changed, packet_for("UNREGISTERED")])
        self.assertIn("Duplicate local packet", " ".join(audited["errors"]))
        self.assertEqual(sum("Untracked or unpublished" in error for error in audited["errors"]), 2)

    def test_changed_approval_anchor_stops_all_existing_registry_writes(self):
        self.register()
        self.authority.return_value = "b" * 64
        before = list(self.api.mutations)
        for operation in (lambda: self.client.put_task(task_row(), self.directory),
                          lambda: self.client.publish(self.directory),
                          lambda: self.client.close("TASK-001", self.directory)):
            with self.assertRaisesRegex(ValueError, "approval differs"):
                operation()
        self.assertEqual(self.api.mutations, before)

    @unittest.skipUnless(shutil.which("git"), "Git is required for disposable workspace audits")
    def test_workspace_audit_checks_origin_branch_live_head_and_untracked_work(self):
        row = self.register()
        self.client.publish(self.directory)
        workspace = self.directory / "checkout"
        workspace.mkdir()
        def git(*args):
            return subprocess.run(["git", "-C", str(workspace), *args], capture_output=True,
                                  text=True, check=True, timeout=30).stdout.strip()
        git("init", "-b", row["branch"])
        git("-c", "user.name=Synthetic Test", "-c", "user.email=synthetic@example.invalid",
            "commit", "--allow-empty", "-m", "Synthetic fixture")
        git("remote", "add", "origin", "https://github.com/" + self.config["repository"] + ".git")
        self.api.refs[row["branch"]] = git("rev-parse", "HEAD")
        self.assertTrue(self.client.audit(workspace=workspace, task_id="TASK-001")["valid"])
        for origin in ("git@github.com:" + self.config["repository"] + ".git",
                       "https://github.com/" + self.config["repository"]):
            git("remote", "set-url", "origin", origin)
            self.assertTrue(self.client.audit(workspace=workspace, task_id="TASK-001")["valid"])
        git("remote", "set-url", "origin", "https://github.com/foreign/repository.git")
        self.assertIn("Workspace origin differs", " ".join(self.client.audit(workspace=workspace, task_id="TASK-001")["errors"]))
        git("remote", "set-url", "origin", "https://github.com/" + self.config["repository"] + ".git")
        self.api.refs[row["branch"]] = "e" * 40
        self.assertIn("Workspace HEAD differs", " ".join(self.client.audit(workspace=workspace, task_id="TASK-001")["errors"]))
        self.api.refs[row["branch"]] = git("rev-parse", "HEAD")
        (workspace / "untracked.txt").write_text("Synthetic unpublished work", encoding="utf-8")
        self.assertIn("uncommitted or untracked", " ".join(self.client.audit(workspace=workspace, task_id="TASK-001")["errors"]))
        git("checkout", "-b", "different-task")
        self.assertIn("Workspace branch differs", " ".join(self.client.audit(workspace=workspace, task_id="TASK-001")["errors"]))
        git("checkout", row["branch"])
        del self.api.refs[row["branch"]]
        with self.assertRaises(ledger.APIError):
            self.client.audit(workspace=workspace, task_id="TASK-001")
        git("remote", "remove", "origin")
        with self.assertRaises(subprocess.CalledProcessError):
            self.client.audit(workspace=workspace, task_id="TASK-001")


class AuthorityAndAdapterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / "project"
        active_project(self.directory)
        self.config = configuration()
        self.project = wp.read_json(self.directory / "config/project.json")
        self.project["connector_permissions"] = {"github": "read-and-project-write"}
        (self.directory / "CONNECTOR_PLAN.md").write_text(
            "# Synthetic authorized project writes\nGitHub ledger configuration SHA-256: " + ledger.router.digest(self.config) + "\n",
            encoding="utf-8")
        self.reapprove()

    def reapprove(self):
        (self.directory / "config/project.json").write_text(json.dumps(self.project), encoding="utf-8")
        bootstrap = wp.read_json(self.directory / "config/bootstrap.json")
        bootstrap["configuration"] = self.project
        bootstrap["documents"] = ledger.feedback.bootstrap.document_hashes(self.directory)
        bootstrap["approval"]["architecture_fingerprint"] = ledger.feedback.bootstrap.architecture_fingerprint(bootstrap)
        (self.directory / "config/bootstrap.json").write_text(json.dumps(bootstrap), encoding="utf-8")
        self.assertEqual(ledger.feedback.bootstrap.validate(bootstrap, self.directory), [])
        return bootstrap["approval"]["architecture_fingerprint"]

    def test_real_active_approval_bound_digest_and_github_permission_allow_initialize(self):
        anchor = ledger.authority(self.config, self.directory)
        api = MemoryGitHub(self.config)
        client = ledger.Ledger(self.config, api)
        client.initialize(self.directory)
        self.assertEqual(client.read()[0]["anchor"], anchor)
        self.assertEqual([method for method, _, _ in api.mutations], ["POST", "PUT"])

    def test_real_authority_gates_publish_release_and_close(self):
        api = MemoryGitHub(self.config)
        client = ledger.Ledger(self.config, api)
        client.initialize(self.directory)
        row = task_row(verified=True)
        row["pr"] = 20
        api.pulls[20] = {"head": {"ref": row["branch"], "repo": {"full_name": self.config["repository"]}},
                         "base": {"ref": self.config["accepted_branch"]}, "state": "closed",
                         "merged": True, "merge_commit_sha": ACCEPTED}
        api.comparisons = {ACCEPTED + "..." + self.config["accepted_branch"]: "identical"}
        client.put_task(row, self.directory)
        client.publish(self.directory)
        client.close("TASK-001", self.directory)
        self.assertEqual(api.issues[row["issue"]]["state"], "closed")
        operations = (lambda: client.publish(self.directory),
                      lambda: client.publish(self.directory, reconcile_only=True),
                      lambda: client.release(self.directory),
                      lambda: client.close("TASK-001", self.directory))
        # Revoking the bound GitHub project-write permission stops every mutating operation.
        self.project["connector_permissions"] = {"github": "read-only"}
        self.reapprove()
        before = list(api.mutations)
        for index, operation in enumerate(operations):
            with self.subTest(revocation="permission", operation=index):
                with self.assertRaisesRegex(ValueError, "explicitly permit GitHub project writes"):
                    operation()
        self.assertEqual(api.mutations, before)
        # Deactivating the bootstrap stops them as well, and read-only audit still works.
        self.project["connector_permissions"] = {"github": "read-and-project-write"}
        self.reapprove()
        bootstrap = wp.read_json(self.directory / "config/bootstrap.json")
        bootstrap["state"] = "SETUP_COMPLETE"
        (self.directory / "config/bootstrap.json").write_text(json.dumps(bootstrap), encoding="utf-8")
        for index, operation in enumerate(operations):
            with self.subTest(revocation="inactive", operation=index):
                with self.assertRaisesRegex(ValueError, "ACTIVE bootstrap required"):
                    operation()
        self.assertEqual(api.mutations, before)
        self.assertTrue(client.audit()["valid"])

    def test_registered_packet_profile_must_match_the_approved_project(self):
        approved = wp.read_json(self.directory / "config/bootstrap.json")["domain_profile"]
        api = MemoryGitHub(self.config)
        client = ledger.Ledger(self.config, api)
        client.initialize(self.directory)
        row = task_row()
        contract = copy.deepcopy(wp.current(row["packet"])["contract"])
        row["packet"] = wp.create("TASK-001", "family-law", contract, "Architect", "Synthetic profile mismatch", timestamp())
        self.assertNotEqual(row["packet"]["domain_profile"], approved)
        before = list(api.mutations)
        with self.assertRaisesRegex(ValueError, "Packet profile differs"):
            client.put_task(row, self.directory)
        self.assertEqual(api.mutations, before)
        matching = task_row()
        self.assertEqual(matching["packet"]["domain_profile"], approved)
        client.put_task(matching, self.directory)
        client.publish(self.directory)
        self.assertEqual(client.read()[0]["tasks"]["TASK-001"]["packet"]["domain_profile"], approved)

    def test_disabled_configuration_cannot_mutate_even_with_approval(self):
        self.config["enabled"] = False
        api = MemoryGitHub(self.config)
        with self.assertRaisesRegex(ValueError, "disabled"):
            ledger.Ledger(self.config, api).initialize(self.directory)
        self.assertEqual(api.mutations, [])

    def test_current_active_approval_is_required_before_any_mutation(self):
        bootstrap_path = self.directory / "config/bootstrap.json"
        approved = wp.read_json(bootstrap_path)
        for corruption in ("inactive", "unapproved", "stale", "missing"):
            with self.subTest(corruption=corruption):
                bootstrap = copy.deepcopy(approved)
                if corruption == "inactive":
                    bootstrap["state"] = "AWAITING_APPROVAL"
                elif corruption == "unapproved":
                    bootstrap["approval"]["approved"] = False
                elif corruption == "stale":
                    bootstrap["approval"]["architecture_fingerprint"] = "b" * 64
                bootstrap_path.write_text(json.dumps(bootstrap), encoding="utf-8")
                if corruption == "missing":
                    bootstrap_path.unlink()
                api = MemoryGitHub(self.config)
                with self.assertRaises((ValueError, OSError)):
                    ledger.Ledger(self.config, api).initialize(self.directory)
                self.assertEqual(api.mutations, [])

    def test_bound_configuration_digest_must_match_even_after_valid_reapproval(self):
        self.config["publishers"].append("another-approved-user")
        self.reapprove()
        api = MemoryGitHub(self.config)
        with self.assertRaisesRegex(ValueError, "exact GitHub configuration"):
            ledger.Ledger(self.config, api).initialize(self.directory)
        self.assertEqual(api.mutations, [])

    def test_github_project_write_permission_must_be_explicit(self):
        for permission in (None, "read-only"):
            with self.subTest(permission=permission):
                self.project["connector_permissions"] = {} if permission is None else {"github": permission}
                self.reapprove()
                api = MemoryGitHub(self.config)
                with self.assertRaisesRegex(ValueError, "explicitly permit"):
                    ledger.Ledger(self.config, api).initialize(self.directory)
                self.assertEqual(api.mutations, [])

    def test_bound_document_edits_invalidate_previously_approved_writes(self):
        with (self.directory / "CONNECTOR_PLAN.md").open("a", encoding="utf-8") as stream:
            stream.write("Changed material authority after approval.\n")
        api = MemoryGitHub(self.config)
        with self.assertRaises(ValueError):
            ledger.Ledger(self.config, api).initialize(self.directory)
        self.assertEqual(api.mutations, [])

    def test_adapter_timeout_and_error_output_preserve_uncertainty_without_echoing_secrets(self):
        adapter = ledger.GitHub(self.config["repository"])
        with mock.patch.object(ledger.subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 45)):
            with self.assertRaisesRegex(ledger.APIError, "uncertain"):
                adapter.call("POST", "issues/2/comments", {"body": "synthetic"})
        process = subprocess.CompletedProcess([], 1, "secret stdout", "secret credential; HTTP 403")
        with mock.patch.object(ledger.subprocess, "run", return_value=process) as run:
            with self.assertRaises(ledger.APIError) as raised:
                adapter.call("PUT", "contents/fixture", {"message": "synthetic"})
        self.assertNotIn("secret", str(raised.exception))
        self.assertIn("403", str(raised.exception))
        arguments = run.call_args.args[0]
        self.assertEqual(arguments[:4], ["gh", "api", "--hostname", "github.com"])
        self.assertEqual(arguments[-2:], ["--input", "-"])
        self.assertEqual(json.loads(run.call_args.kwargs["input"]), {"message": "synthetic"})

    def test_adapter_pagination_rejects_incomplete_or_unbounded_pages(self):
        adapter = ledger.GitHub(self.config["repository"])
        with mock.patch.object(adapter, "call", return_value={"incomplete": True}):
            with self.assertRaisesRegex(ValueError, "complete paginated list"):
                adapter.pages("issues/2/comments")
        with mock.patch.object(adapter, "call", return_value=[{}] * 100) as call:
            with self.assertRaisesRegex(ValueError, "Pagination safety bound"):
                adapter.pages("issues/2/comments")
        self.assertEqual(call.call_count, 1000)


if __name__ == "__main__":
    unittest.main()
