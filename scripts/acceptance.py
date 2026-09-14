#!/usr/bin/env python3
"""Gate and record independent acceptance of reviewed work; execute only architect-declared checks."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import execution_harness as harness
import feedback
import model_router as router
import work_packet as wp

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = wp.read_json(ROOT / "config/acceptance.schema.json")
wp.Draft202012Validator.check_schema(SCHEMA)
GATES = set(SCHEMA["$defs"]["gate"]["enum"])
if GATES != set(wp.SCHEMA["$defs"]["review_gate"]["enum"]) or any(
        gate not in GATES for floor in wp.REVIEW_FLOORS.values() for gate in floor):
    raise ValueError("Acceptance gate names differ between the schemas and the declared floors")
REVIEW_GATES = ("model_review", "architect_review")
TERMINAL = {"ACCEPTED", "USER_REJECTED", "ESCALATION_REQUIRED", "ARCHITECTURE_CONFLICT"}
# Declared once: the packet renderer, the ledger-free verifier and the tests all read this.
REVIEW_PACKET_FIELDS = {"schema_version", "review_id", "gate", "reviewer", "binding", "gates",
                        "contract", "result_supplied_by_worker", "artifact", "independent_validation",
                        "attestations", "prior_reviews", "open_questions", "paths", "review_contract"}
require = harness.require
secret_free = harness.secret_free


def shape(name, value):
    wp.canonical(value)
    validator = wp.Draft202012Validator({"$defs": SCHEMA["$defs"], "$ref": f"#/$defs/{name}"})
    errors = wp.schema_errors(validator, value)
    if errors:
        raise ValueError("\n".join(errors))


def config_valid(config):
    shape("config", config)
    secret_free(config, "Acceptance configuration")
    for risk, floor in wp.REVIEW_FLOORS.items():
        combined = set(floor) | set(config["policy"]["additional_gates"][risk])
        require("cross_family_review" not in combined or "model_review" in combined,
                f"additional_gates/{risk}: cross_family_review requires model_review")
    return config


def gates_for(contract, policy):
    return sorted(wp.effective_gates(contract) | set(policy["additional_gates"][contract["risk"]]))


def casefolded(values):
    return {value.strip().casefold() for value in values}


def checked_result(result, contract):
    """The worker result under review must be a structurally valid objective PASS claim."""
    feedback.shape("result", result)
    expected = {check["id"] for check in contract["validation"]}
    reported = [check["check_id"] for check in result["validation"]]
    require(len(set(reported)) == len(reported) and set(reported) == expected,
            "The result must report every contract validation check and no other id")
    require(result["outcome"] == "PASS" and all(check["passed"] for check in result["validation"])
            and result["scope_status"] == "within" and not result["architecture_conflict"],
            "Only a claimed objective PASS within scope reaches acceptance review")
    return result


def checked_artifact(artifact, policy):
    shape("artifact", artifact)
    require(len(artifact["content"]) <= policy["artifact_max_chars"],
            "Artifact content exceeds its configured bound; supply a reference with digest instead")
    require(artifact["kind"] == "reference" or artifact["content"].strip(),
            "A diff or files artifact requires its content")
    digest = hashlib.sha256(artifact["content"].encode("utf-8")).hexdigest()
    require(artifact["sha256"] == digest, "Artifact digest does not match its content")
    return artifact


def pending_review(state):
    reviews = state["reviews"]
    if reviews and reviews[-1]["report"] is None and reviews[-1]["abandoned"] is None:
        return reviews[-1]
    return None


def completed(state, gate):
    return [r for r in state["reviews"] if r["gate"] == gate and r["report"] is not None]


def current_completed(state, gate):
    """Completed reviews of the current submission only. A gate approval recorded before a
    resubmission examined a superseded artifact and cannot satisfy the gate for this one;
    the full review history still feeds attempt counting and rejection fingerprints."""
    return [r for r in completed(state, gate) if r["submission"] == state["resubmissions"]]


def deterministic_status(state):
    """Per-validation deterministic gate status from the latest observed check run."""
    checks = state["checks"]
    status = {}
    for check in state["contract"]["validation"]:
        identifier = check["id"]
        if checks is None:
            status[identifier] = "UNRUN"
            continue
        entry = next(r for r in checks["results"] if r["validation_id"] == identifier)
        if entry["passed"]:
            status[identifier] = "PASSED"
        elif entry["machine_runnable"]:
            status[identifier] = "FAILED"
        elif identifier in state["attestations"]:
            status[identifier] = "ATTESTED"
        else:
            status[identifier] = "NEEDS_ATTESTATION"
    return status


def deterministic_satisfied(state):
    return state["checks"] is not None and all(
        value in {"PASSED", "ATTESTED"} for value in deterministic_status(state).values())


def report_valid(report, contract, opened, policy):
    """The complete reviewer report contract; shared by the ledger and the ledger-free verifier."""
    shape("report", report)
    require(len(wp.canonical(report).encode("utf-8")) <= policy["review_report_max_bytes"],
            "Reviewer report exceeds its configured bound")
    secret_free(report, "Reviewer report")
    require(report["review_id"] == opened["review_id"], "Report does not match the opened review")
    require(report["reviewer"] == opened["reviewer"],
            "Report reviewer identity differs from the opened review")
    criteria = {entry["id"] for entry in contract["acceptance_criteria"]}
    found = [finding["criterion_id"] for finding in report["criteria"]]
    require(len(set(found)) == len(found) and set(found) == criteria,
            "Report exactly one finding per contract acceptance criterion and no other id")
    statuses = {finding["criterion_id"]: finding["status"] for finding in report["criteria"]}
    verdict = report["verdict"]
    failures, missing, escalation = report["contract_failures"], report["missing_evidence"], report["escalation_reason"]
    validations = {check["id"]: check for check in contract["validation"]}
    scope_refs = (set(contract["scope"]["allowed"]) | set(contract["scope"]["prohibited"])
                  | set(contract["architecture_boundaries"]))
    for failure in failures:
        refs = scope_refs if failure["kind"] == "scope" else (
            criteria if failure["kind"] == "criterion" else set(validations))
        require(failure["failed_ref"] in refs,
                "A contract failure must name an existing criterion, validation or scope rule")
    if verdict == "APPROVE":
        require(all(status == "met" for status in statuses.values()),
                "APPROVE requires every acceptance criterion to be met")
        require(not failures and not missing and not escalation.strip(),
                "APPROVE carries no failures, missing evidence or escalation")
    elif verdict == "REJECT_BOUNDED":
        require(bool(failures), "A bounded rejection must name specific contract failures")
        require("cannot_determine" not in statuses.values(),
                "Undeterminable criteria are NEEDS_EVIDENCE, not a bounded rejection")
        require("not_met" in statuses.values() or any(f["kind"] == "scope" for f in failures),
                "A bounded rejection requires an unmet criterion or a scope failure")
        require(not missing and not escalation.strip(),
                "A bounded rejection carries no missing evidence or escalation")
    elif verdict == "NEEDS_EVIDENCE":
        require(bool(missing), "NEEDS_EVIDENCE must name the missing evidence")
        require("cannot_determine" in statuses.values(),
                "NEEDS_EVIDENCE requires at least one undeterminable criterion")
        for item in missing:
            check = validations.get(item["validation_id"])
            require(check is not None and item["evidence_required"] in check["evidence_required"],
                    "Missing evidence must reference a contract validation's declared evidence")
        require(not failures and not escalation.strip(),
                "NEEDS_EVIDENCE carries no contract failures or escalation")
    else:
        require(bool(escalation.strip()), f"{verdict} requires a stated escalation reason")
        require(not failures and not missing, f"{verdict} carries no failures or missing evidence")
    return report


def apply(state, event):
    data, timestamp = event["data"], event["timestamp"]
    if state is None:
        if event["kind"] != "INIT":
            raise ValueError("Acceptance ledger must start with INIT")
        feedback.exact(data, {"binding", "contract", "policy", "controller", "architect",
                              "implementers", "result", "artifact", "open_questions"})
        binding, contract = data["binding"], data["contract"]
        feedback.exact(binding, {"task_id", "domain_profile", "revision", "contract_hash"})
        errors = wp.validate_contract(contract)
        if errors:
            raise ValueError("; ".join(errors))
        expected = wp.fingerprint(binding["task_id"], binding["domain_profile"],
                                  binding["revision"], contract)
        require(binding["contract_hash"] == expected, "Binding hash does not match its contract")
        shape("policy", data["policy"])
        shape("implementers", data["implementers"])
        shape("open_questions", data["open_questions"])
        for name in ("controller", "architect"):
            require(isinstance(data[name], str) and data[name].strip(), f"INIT requires a {name} identity")
        checked_result(data["result"], contract)
        checked_artifact(data["artifact"], data["policy"])
        secret_free(data, "Acceptance INIT record")
        return {"binding": copy.deepcopy(binding), "contract": copy.deepcopy(contract),
                "risk": contract["risk"], "policy": copy.deepcopy(data["policy"]),
                "gates": gates_for(contract, data["policy"]),
                "controller": data["controller"], "architect": data["architect"],
                "implementers": copy.deepcopy(data["implementers"]),
                "result": copy.deepcopy(data["result"]), "artifact": copy.deepcopy(data["artifact"]),
                "open_questions": copy.deepcopy(data["open_questions"]),
                "checks": None, "attestations": {}, "reviews": [], "waiver": None,
                "user_decision": None, "accepted": None, "resubmissions": 0,
                "status": "GATES_PENDING", "reason": "INITIALIZED"}
    actors = casefolded(item["actor"] for item in state["implementers"])
    if event["kind"] not in {"REVIEW_RESULT", "REVIEW_ABANDONED"}:
        require(state["status"] not in TERMINAL, f"Acceptance ledger is closed: {state['status']}")
        require(pending_review(state) is None,
                "A review is open; ingest or abandon its report before other gate activity")
    if event["kind"] == "CHECKS":
        feedback.exact(data, {"checks"})
        require(state["status"] == "GATES_PENDING", f"Check run refused at {state['status']}")
        checks = data["checks"]
        shape("checks", checks)
        secret_free(data, "Recorded check run")
        expected = {check["id"]: check for check in state["contract"]["validation"]}
        recorded = [entry["validation_id"] for entry in checks["results"]]
        require(len(set(recorded)) == len(recorded) and set(recorded) == set(expected),
                "Record exactly one check result per contract validation")
        require(checks["workspace_files"] <= state["policy"]["workspace_digest_max_files"],
                "Workspace exceeds the digest bound; decompose the artifact")
        for entry in checks["results"]:
            command = expected[entry["validation_id"]].get("command")
            if command is None:
                require(not entry["machine_runnable"] and not entry["passed"] and entry["argv"] == []
                        and entry["exit_code"] is None and not entry["timed_out"],
                        "A validation without a declared command cannot record an execution")
            else:
                require(entry["machine_runnable"] and entry["argv"] == command["argv"],
                        "A recorded check must execute exactly the contract's declared command")
                require(entry["passed"] == (entry["exit_code"] == 0 and not entry["timed_out"]),
                        "A check passes exactly on a zero exit without timeout")
            bound = state["policy"]["check_output_max_chars"]
            require(len(entry["stdout"]) <= bound and len(entry["stderr"]) <= bound,
                    "Recorded check output exceeds its configured bound")
        state["checks"] = copy.deepcopy(checks)
        state["reason"] = "CHECKS_RECORDED"
    elif event["kind"] == "ATTESTATION":
        feedback.exact(data, {"attestation"})
        attestation = data["attestation"]
        shape("attestation", attestation)
        secret_free(data, "Attestation")
        require(state["status"] == "GATES_PENDING", f"Attestation refused at {state['status']}")
        require(state["checks"] is not None, "Run the deterministic checks before attesting")
        entry = next((r for r in state["checks"]["results"]
                      if r["validation_id"] == attestation["validation_id"]), None)
        require(entry is not None, "Attestation names an unknown validation")
        require(not entry["machine_runnable"],
                "A machine-runnable check is executed, never attested over")
        require(attestation["operator"].strip().casefold() not in actors,
                "An implementation actor cannot attest its own validation")
        state["attestations"][attestation["validation_id"]] = copy.deepcopy(attestation)
        state["reason"] = "ATTESTATION_RECORDED"
    elif event["kind"] == "REVIEW_OPEN":
        feedback.exact(data, {"review"})
        opened = data["review"]
        shape("review_open", opened)
        secret_free(data, "Review opening")
        require(state["status"] == "GATES_PENDING", f"Review refused at {state['status']}")
        require(deterministic_satisfied(state),
                "The deterministic gate must pass before a reviewer is engaged")
        require(len(state["reviews"]) < state["policy"]["max_review_attempts"],
                "Review attempt budget exhausted; escalate to the architect")
        require(opened["gate"] in state["gates"], "This packet does not require that review gate")
        reviewer = opened["reviewer"]
        require(reviewer["actor"].strip().casefold() not in actors,
                "An implementation actor cannot review its own revision")
        required_tier = state["contract"]["routing"]["reviewer_tier"]
        require(reviewer["tier"] >= required_tier,
                f"Reviewer tier {reviewer['tier']} is below the contract's reviewer_tier {required_tier}")
        if opened["gate"] == "architect_review":
            require(reviewer["actor"] == state["architect"],
                    "Architect review must be performed by the recorded architect")
        expected = router.digest({"binding": state["binding"], "review_number": len(state["reviews"]) + 1,
                                  "gate": opened["gate"], "reviewer": reviewer})
        require(opened["review_id"] == expected, "Review id does not reproduce from its opening record")
        state["reviews"].append({"review_id": opened["review_id"], "gate": opened["gate"],
                                 "reviewer": copy.deepcopy(reviewer), "report": None, "abandoned": None,
                                 "submission": state["resubmissions"]})
        state.update(status="REVIEW_OPEN", reason="REVIEW_DISPATCHED")
    elif event["kind"] == "REVIEW_RESULT":
        feedback.exact(data, {"report"})
        opened = pending_review(state)
        require(opened is not None, "No review is awaiting a report")
        report = report_valid(data["report"], state["contract"], opened, state["policy"])
        opened["report"] = copy.deepcopy(report)
        verdict = report["verdict"]
        if verdict == "APPROVE":
            state.update(status="GATES_PENDING", reason="REVIEW_APPROVED")
        elif verdict == "REJECT_BOUNDED":
            fingerprint = feedback.rejection_fingerprint(report["contract_failures"])
            earlier = [feedback.rejection_fingerprint(r["report"]["contract_failures"])
                       for r in state["reviews"][:-1]
                       if r["report"] and r["report"]["verdict"] == "REJECT_BOUNDED"]
            opened["fingerprint"] = fingerprint
            if fingerprint in earlier:
                state.update(status="ESCALATION_REQUIRED", reason="REPEATED_REVIEW_REJECTION")
            else:
                state.update(status="REJECTED", reason="BOUNDED_CORRECTIVE_ACTION_REQUIRED")
        elif verdict == "NEEDS_EVIDENCE":
            state.update(status="GATES_PENDING", reason="REVIEW_NEEDS_EVIDENCE")
        elif verdict == "NEEDS_ESCALATION":
            state.update(status="ESCALATION_REQUIRED", reason="REVIEW_ESCALATED")
        else:
            state.update(status="ARCHITECTURE_CONFLICT", reason="ARCHITECT_DIAGNOSIS_REQUIRED")
    elif event["kind"] == "REVIEW_ABANDONED":
        feedback.exact(data, {"reason"})
        require(pending_review(state) is not None, "No review is awaiting a report")
        text = str(data["reason"]).strip()
        require(20 <= len(text) <= 2000, "Abandoning a review requires a specific recorded reason")
        secret_free(text, "Abandonment reason")
        pending_review(state)["abandoned"] = text
        state.update(status="GATES_PENDING", reason="REVIEW_ABANDONED")
    elif event["kind"] == "WAIVER":
        feedback.exact(data, {"waiver"})
        waiver = data["waiver"]
        shape("waiver", waiver)
        secret_free(data, "Cross-family waiver")
        require(state["status"] == "GATES_PENDING", f"Waiver refused at {state['status']}")
        require("cross_family_review" in state["gates"], "This packet has no cross-family gate to waive")
        require(waiver["operator"].strip().casefold() not in actors,
                "An implementation actor cannot waive review of its own work")
        state["waiver"] = copy.deepcopy(waiver)
        state["reason"] = "CROSS_FAMILY_WAIVED"
    elif event["kind"] == "DECISION":
        feedback.exact(data, {"decision"})
        decision = data["decision"]
        shape("user_decision", decision)
        secret_free(data, "User decision")
        require(state["status"] == "GATES_PENDING", f"User decision refused at {state['status']}")
        require("user_decision" in state["gates"], "This packet has no user-decision gate")
        require(decision["decider"].strip().casefold() not in actors,
                "An implementation actor cannot decide its own acceptance")
        state["user_decision"] = copy.deepcopy(decision)
        if decision["decision"] == "reject":
            state.update(status="USER_REJECTED", reason="USER_DECISION_REJECTED")
        else:
            state["reason"] = "USER_DECISION_RECORDED"
    elif event["kind"] == "RESUBMIT":
        feedback.exact(data, {"result", "artifact", "implementers"})
        require(state["status"] == "REJECTED", "Only a rejected result may be resubmitted")
        shape("implementers", data["implementers"])
        checked_result(data["result"], state["contract"])
        checked_artifact(data["artifact"], state["policy"])
        secret_free(data, "Resubmission")
        state.update(result=copy.deepcopy(data["result"]), artifact=copy.deepcopy(data["artifact"]),
                     implementers=copy.deepcopy(data["implementers"]), checks=None, attestations={},
                     waiver=None, user_decision=None, resubmissions=state["resubmissions"] + 1,
                     status="GATES_PENDING", reason="RESUBMITTED")
    elif event["kind"] == "ACCEPT":
        feedback.exact(data, {"actor"})
        acceptable(state, data["actor"])
        state["accepted"] = {"actor": data["actor"], "gates": gate_summary(state)}
        state.update(status="ACCEPTED", reason="ALL_GATES_PASSED")
    else:
        raise ValueError("Unknown acceptance event kind")
    return state


def approving(state, gate):
    """The review that currently satisfies a review gate, or the stated refusal."""
    finished = current_completed(state, gate)
    require(bool(finished), f"The {gate} gate has no completed review for the current submission")
    latest = finished[-1]
    require(latest["report"]["verdict"] == "APPROVE",
            f"The latest {gate} review did not approve: {latest['report']['verdict']}")
    return latest


def acceptable(state, actor):
    require(state["status"] == "GATES_PENDING", f"Acceptance refused at {state['status']}")
    require(deterministic_satisfied(state),
            "Deterministic gate unsatisfied: " + wp.canonical(deterministic_status(state)))
    approver = None
    if "model_review" in state["gates"]:
        approver = approving(state, "model_review")
    if "cross_family_review" in state["gates"]:
        families = casefolded(item["model_family"] for item in state["implementers"])
        family = approver["reviewer"]["model_family"].strip().casefold()
        require(family not in families or state["waiver"] is not None,
                f"Cross-family gate: reviewer family {approver['reviewer']['model_family']} matches an "
                "implementation actor and no waiver is recorded")
    if "architect_review" in state["gates"]:
        approving(state, "architect_review")
    if "user_decision" in state["gates"]:
        require(state["user_decision"] is not None and state["user_decision"]["decision"] == "approve",
                "User-decision gate: no recorded approval")
    expected = approver["reviewer"]["actor"] if approver else state["controller"]
    require(actor == expected, f"Acceptance must be recorded by {expected}")
    require(actor.strip().casefold() not in casefolded(i["actor"] for i in state["implementers"]),
            "An implementation actor cannot accept its own revision")


def gate_summary(state):
    summary = {"deterministic": deterministic_status(state)}
    for gate in REVIEW_GATES:
        if gate in state["gates"]:
            finished = current_completed(state, gate)
            latest = finished[-1] if finished else None
            summary[gate] = {"review_id": latest["review_id"], "reviewer": latest["reviewer"],
                             "verdict": latest["report"]["verdict"]} if latest else None
    if "cross_family_review" in state["gates"]:
        summary["cross_family_review"] = {"waived": state["waiver"] is not None,
                                          "waiver": state["waiver"]}
    if "user_decision" in state["gates"]:
        summary["user_decision"] = state["user_decision"]
    return summary


def replay(directory):
    paths = sorted(Path(directory).iterdir())
    if not paths:
        raise ValueError("Empty acceptance ledger")
    state, previous, previous_time = None, None, None
    for sequence, path in enumerate(paths, 1):
        if path.name != f"{sequence:08d}.json" or path.is_symlink() or not path.is_file():
            raise ValueError("Acceptance ledger has a gap, unexpected file or unsafe entry")
        event = wp.read_json(path)
        feedback.exact(event, {"sequence", "previous", "kind", "timestamp", "data", "hash"})
        if isinstance(event["sequence"], bool) or event["sequence"] != sequence or event["previous"] != previous:
            raise ValueError("Acceptance ledger sequence/hash chain is broken")
        claimed = event.pop("hash")
        if router.digest(event) != claimed:
            raise ValueError("Acceptance ledger event hash differs")
        current_time = feedback.instant(event["timestamp"])
        if previous_time and current_time < previous_time:
            raise ValueError("Acceptance ledger timestamps descend")
        state = apply(state, event)
        previous, previous_time = claimed, current_time
    return state, sequence, previous


def append(directory, kind, data, timestamp=None, previous_state=None):
    state, sequence, previous = previous_state or (None, 0, None)
    event = {"sequence": sequence + 1, "previous": previous, "kind": kind,
             "timestamp": timestamp or wp.now(), "data": copy.deepcopy(data)}
    feedback.instant(event["timestamp"])
    if sequence:
        prior = wp.read_json(Path(directory) / f"{sequence:08d}.json")
        if feedback.instant(event["timestamp"]) < feedback.instant(prior["timestamp"]):
            raise ValueError("Event timestamp predates current ledger")
    next_state = apply(copy.deepcopy(state), event)
    event["hash"] = router.digest(event)
    serialized = json.dumps(event, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with (Path(directory) / f"{sequence + 1:08d}.json").open("x", encoding="utf-8", newline="\n") as output:
        output.write(serialized)
        output.flush()
        os.fsync(output.fileno())
    feedback.sync_directory(directory)
    return next_state


def initialize(directory, config, packet, result, artifact, controller, architect,
               implementers, open_questions, timestamp=None):
    config_valid(config)
    wp.require_valid(packet)
    require(packet["state"] == "REVIEW", "Acceptance review begins when the packet reaches REVIEW")
    latest = wp.current(packet)
    data = {"binding": {"task_id": packet["task_id"], "domain_profile": packet["domain_profile"],
                        "revision": latest["version"], "contract_hash": latest["hash"]},
            "contract": latest["contract"], "policy": config["policy"], "controller": controller,
            "architect": architect, "implementers": implementers, "result": result,
            "artifact": artifact, "open_questions": open_questions}
    apply(None, {"kind": "INIT", "data": data, "timestamp": timestamp or wp.now()})
    Path(directory).mkdir(exist_ok=False)
    feedback.sync_directory(Path(directory).parent)
    return append(directory, "INIT", data, timestamp)


def stream_digest(stdout_hex, stderr_hex):
    """One digest over both complete streams; each stream is hashed while it is read."""
    return hashlib.sha256(f"stdout:{stdout_hex}\nstderr:{stderr_hex}".encode("ascii")).hexdigest()


# After a check ends or is terminated, its pipes are drained for at most this long; a
# descendant that still holds them after that is killed with the whole tree, not waited on.
DRAIN_GRACE_SECONDS = 5
PROC_ROOT = Path("/proc")


def runnable_group_members(pgid, proc_root=None):
    """Non-zombie processes in a POSIX process group, read from /proc where it exists.

    A killed descendant that nobody reaps — a container whose PID 1 does not reap orphans —
    stays in the group as a zombie, so group existence alone would never report stopped.
    Returns None where /proc is unavailable, and the caller falls back to the group probe.
    """
    root = PROC_ROOT if proc_root is None else Path(proc_root)
    if not root.is_dir():
        return None
    members = 0
    for entry in root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="ascii", errors="replace")
        except FileNotFoundError:
            continue  # The only error that proves the process is gone: it exited after listing.
        except OSError:
            members += 1  # Unreadable is unknown, and unknown fails closed as alive.
            continue
        _, _, rest = stat.rpartition(")")  # The command name may contain spaces or parentheses.
        fields = rest.split()
        if len(fields) < 3:
            members += 1  # An unparseable record is unknown too.
            continue
        state, group = fields[0], fields[2]
        if group == str(pgid) and state not in ("Z", "X", "x"):
            members += 1
    return members


class ProcessTree:
    """The check and every descendant, killable as one unit even after the check itself exits.

    POSIX: the check runs in its own session, so its process group is the tree. Windows: the
    check is assigned to a job object, which descendants inherit and which terminates them all;
    `taskkill /T` is the fallback when a job cannot be created or assigned.
    """

    CREATE_SUSPENDED = 0x4

    def __init__(self, process):
        self.process = process
        self.job = None
        # Saved now: once the leader is reaped, getpgid() on it raises and the group would be lost.
        self.pgid = None if os.name == "nt" else process.pid  # start_new_session makes pid == pgid.
        if os.name == "nt":
            # The check was created suspended, so it is assigned to the job before its first
            # instruction runs. Without a job there is no enforceable tree cleanup on Windows,
            # so the suspended check is killed and the run refuses rather than proceeding unisolated.
            self.job = self._windows_job()
            if self.job is None:
                self._refuse_suspended(process, "Windows job object could not be created or assigned; the check is not run unisolated")
            if self._windows_resume() == 0:
                # Still suspended: refuse now rather than let it sit until the check timeout and
                # be recorded as an ordinary validation failure.
                self._refuse_suspended(process, "Windows check could not be resumed after job assignment; refusing the run")

    @staticmethod
    def _refuse_suspended(process, reason):
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, shell=False)
        try:
            process.kill()
        except OSError:
            pass
        process.wait()
        raise ValueError(reason)

    @classmethod
    def creation_flags(cls):
        return cls.CREATE_SUSPENDED if os.name == "nt" else 0

    def _windows_resume(self):
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # ResumeThread returns a DWORD; without the restype ctypes would read its (DWORD)-1
        # failure as a signed -1 and a failed resume would be counted as resumed.
        kernel32.ResumeThread.restype = wintypes.DWORD

        class ThreadEntry(ctypes.Structure):
            _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ThreadID", wintypes.DWORD),
                        ("th32OwnerProcessID", wintypes.DWORD), ("tpBasePri", wintypes.LONG),
                        ("tpDeltaPri", wintypes.LONG), ("dwFlags", wintypes.DWORD)]

        resumed = 0
        snapshot = kernel32.CreateToolhelp32Snapshot(0x4, 0)  # TH32CS_SNAPTHREAD
        if snapshot == wintypes.HANDLE(-1).value:
            return resumed
        entry = ThreadEntry()
        entry.dwSize = ctypes.sizeof(entry)
        found = kernel32.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.th32OwnerProcessID == self.process.pid:
                thread = kernel32.OpenThread(0x2, False, entry.th32ThreadID)  # THREAD_SUSPEND_RESUME
                if thread:
                    previous = kernel32.ResumeThread(thread)
                    while 1 < previous < 0xFFFFFFFF:
                        previous = kernel32.ResumeThread(thread)
                    if previous != 0xFFFFFFFF:  # (DWORD)-1 signals failure.
                        resumed += 1
                    kernel32.CloseHandle(thread)
            found = kernel32.Thread32Next(snapshot, ctypes.byref(entry))
        kernel32.CloseHandle(snapshot)
        return resumed

    def _windows_job(self):
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            class IoCounters(ctypes.Structure):
                _fields_ = [(name, ctypes.c_ulonglong) for name in
                            ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                             "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

            class BasicLimit(ctypes.Structure):
                _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                            ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                            ("SchedulingClass", wintypes.DWORD)]

            class ExtendedLimit(ctypes.Structure):
                _fields_ = [("BasicLimitInformation", BasicLimit), ("IoInfo", IoCounters),
                            ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

            job = kernel32.CreateJobObjectW(None, None)
            if not job:
                return None
            limits = ExtendedLimit()
            limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                kernel32.CloseHandle(job)
                return None
            if not kernel32.AssignProcessToJobObject(job, wintypes.HANDLE(int(self.process._handle))):
                kernel32.CloseHandle(job)
                return None
            return (kernel32, job)
        except (OSError, AttributeError, ValueError):
            return None

    def kill(self):
        if os.name == "nt":
            if self.job is not None:
                kernel32, job = self.job
                kernel32.TerminateJobObject(job, 1)
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)], capture_output=True, shell=False)
        else:
            self._kill_group()
        try:
            self.process.kill()
        except OSError:
            pass
        self.process.wait()

    def _kill_group(self):
        try:
            os.killpg(self.pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass

    def members_alive(self):
        """Whether any process in the tree still exists; the leader itself is already reaped."""
        if os.name == "nt":
            if self.job is None:
                return False
            import ctypes
            from ctypes import wintypes
            kernel32, job = self.job

            class Accounting(ctypes.Structure):
                _fields_ = [("TotalUserTime", ctypes.c_longlong), ("TotalKernelTime", ctypes.c_longlong),
                            ("ThisPeriodTotalUserTime", ctypes.c_longlong),
                            ("ThisPeriodTotalKernelTime", ctypes.c_longlong), ("TotalPageFaultCount", wintypes.DWORD),
                            ("TotalProcesses", wintypes.DWORD), ("ActiveProcesses", wintypes.DWORD),
                            ("TotalTerminatedProcesses", wintypes.DWORD)]

            info = Accounting()
            if not kernel32.QueryInformationJobObject(job, 1, ctypes.byref(info), ctypes.sizeof(info), None):
                return True  # Unknown counts as alive; the caller then refuses rather than digests.
            return info.ActiveProcesses > 0
        # The kernel is asked first: a group with no member at all, zombie or otherwise, is
        # stopped whatever /proc shows, so an unreadable record of some unrelated process (a
        # hidepid mount) cannot keep a cleanly ended tree looking alive and refuse every run.
        try:
            os.killpg(self.pgid, 0)
        except ProcessLookupError:
            return False
        except (PermissionError, OSError):
            return True
        # The group remains: only /proc can tell a zombie-only group from a runnable member, and
        # a record that cannot be read or parsed still fails closed as alive.
        runnable = runnable_group_members(self.pgid)
        return True if runnable is None else runnable > 0

    def close(self):
        """End anything still alive in the tree once the check is over, and confirm it stopped.

        A descendant that redirected or closed its pipes lets the readers finish normally; it
        must still not outlive the validation it was spawned by, and the digest must not be
        taken while it is still dying. Returns False if the tree cannot be confirmed stopped.
        """
        if os.name == "nt":
            if self.job is not None:
                kernel32, job = self.job
                kernel32.TerminateJobObject(job, 1)
        else:
            self._kill_group()
        deadline = time.monotonic() + DRAIN_GRACE_SECONDS
        while self.members_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        stopped = not self.members_alive()
        if self.job is not None:
            kernel32, job = self.job
            kernel32.CloseHandle(job)  # KILL_ON_JOB_CLOSE ends anything still in the job.
            self.job = None
        return stopped


def bounded_capture(argv, cwd, timeout, bound):
    """Run argv, retaining at most `bound` characters of each stream while hashing all of it.

    The output bound is enforced while the process runs: each reader keeps only a bounded
    prefix in memory and feeds the complete stream to its hasher, so a noisy or runaway
    check cannot exhaust the controller before the bound applies.
    """
    keep = bound * 4 + 4  # A UTF-8 character is at most four bytes; decode, then cut to `bound`.
    lock = threading.Lock()

    def drain(stream, sink):
        # The sink is updated under the lock per chunk, so a reader that never finishes —
        # a descendant still holding the pipe — can be abandoned with an honest partial record.
        # os.read returns what is available; a buffered read(n) would wait for n bytes or EOF.
        for chunk in iter(lambda: os.read(stream.fileno(), 65536), b""):
            with lock:
                sink["hasher"].update(chunk)
                sink["total"] += len(chunk)
                if len(sink["kept"]) < keep:
                    sink["kept"].extend(chunk[:keep - len(sink["kept"])])
        stream.close()

    def finish(sink, abandoned):
        with lock:
            text = bytes(sink["kept"]).decode("utf-8", errors="replace")
            cut = abandoned or sink["total"] > len(sink["kept"]) or len(text) > bound
            return text[:bound], cut, sink["hasher"].hexdigest()

    try:
        process = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                                   start_new_session=os.name != "nt", creationflags=ProcessTree.creation_flags())
    except OSError as exc:
        message = str(exc).encode("utf-8")
        text = message.decode("utf-8")
        return {"exit_code": None, "timed_out": False, "stdout": "", "stderr": text[:bound],
                "output_truncated": len(text) > bound,
                "output_sha256": stream_digest(hashlib.sha256(b"").hexdigest(), hashlib.sha256(message).hexdigest())}
    tree = ProcessTree(process)
    sinks = tuple({"hasher": hashlib.sha256(), "kept": bytearray(), "total": 0} for _ in range(2))
    readers = [threading.Thread(target=drain, args=(process.stdout, sinks[0]), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, sinks[1]), daemon=True)]
    for reader in readers:
        reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        tree.kill()
    # A descendant that inherited the pipes — whether the check timed out or exited normally
    # and left it behind — would hold the readers open forever. The drain is bounded; a reader
    # still alive after the grace period means the tree is killed and the check is recorded
    # as not completing within its bound, with the digest of what was actually observed.
    abandoned = any(not reader.join(timeout=DRAIN_GRACE_SECONDS) and reader.is_alive() for reader in readers)
    if abandoned:
        tree.kill()
        for reader in readers:
            reader.join(timeout=DRAIN_GRACE_SECONDS)
    # Nothing from the tree may still be running when the workspace is scanned and digested.
    require(tree.close(), "The check's process tree could not be confirmed stopped; refuse to digest a moving workspace")
    out, out_cut, out_hex = finish(sinks[0], abandoned)
    err, err_cut, err_hex = finish(sinks[1], abandoned)
    return {"exit_code": None if timed_out or abandoned else process.returncode,
            "timed_out": timed_out or abandoned,
            "stdout": out, "stderr": err, "output_truncated": out_cut or err_cut,
            "output_sha256": stream_digest(out_hex, err_hex)}


# Directories and other non-file entries count against this multiple of the file bound.
ENTRY_MULTIPLIER = 4


FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def is_link(entry):
    """Whether a path or directory entry is a symlink or, on Windows, any reparse point.

    An NTFS junction is not a symlink to `is_symlink()`, yet `resolve()` follows it and a scan
    descends into it as an ordinary directory; the reparse-point attribute identifies junctions,
    mount points and every other redirection alike, so all of them are refused as links.
    """
    if entry.is_symlink():
        return True
    if os.name != "nt":
        return False
    stat = entry.stat(follow_symlinks=False) if isinstance(entry, os.DirEntry) else os.lstat(entry)
    return bool(getattr(stat, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)


def scan_workspace(workspace, policy):
    """Every entry under the workspace, refused on any symlink and bounded; returns the files.

    Every entry is inspected before filtering to files: a symlinked directory is not a file,
    and rglob does not descend into it, so it would otherwise never be seen at all.
    """
    require(not is_link(workspace), "Workspace contains a symlink; refuse to digest it")
    # Walked with os.scandir, one entry at a time, with both bounds checked as entries arrive:
    # Path.rglob and Path.walk build each directory's full listing first, so a wide directory
    # would be buffered before any bound applied.
    limit = policy["workspace_digest_max_files"]
    files, entries, pending = [], 0, [workspace]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as listing:
            for entry in listing:
                entries += 1
                require(entries <= ENTRY_MULTIPLIER * limit,
                        "Workspace exceeds the entry bound; decompose the artifact")
                require(not is_link(entry), "Workspace contains a symlink; refuse to digest it")
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    files.append(Path(entry.path))
                    require(len(files) <= limit, "Workspace exceeds the digest bound; decompose the artifact")
    return sorted(files)


def run_checks(directory, workspace, timestamp=None):
    """Execute the contract's declared validation commands and record what was observed.

    This is the one deliberate exception to the metadata-only pattern: independence requires
    observing the checks run, not transcribing a worker's claim that they ran. It executes
    only commands the architect declared in the contract; it never invokes a model, never
    runs a harness, and recording an observation is still not accepting work.
    """
    prior = replay(directory)
    state = prior[0]
    require(state["status"] == "GATES_PENDING", f"Check run refused at {state['status']}")
    # Inspect every existing component of the supplied path before resolving it: resolve()
    # would replace a symlinked (or, on Windows, junctioned) root or ancestor with its target
    # and the later check would see an ordinary directory. abspath normalizes lexically only.
    supplied = Path(os.path.abspath(workspace))
    require(not is_link(supplied), "Workspace root is a symlink; refuse to digest it")
    for ancestor in supplied.parents:
        require(not (ancestor.exists() and is_link(ancestor)),
                f"Workspace path has a linked ancestor at {ancestor}; refuse to digest it")
    workspace = supplied.resolve()
    require(workspace.is_dir(), f"No workspace directory at {workspace}")
    policy = state["policy"]
    results = []
    for check in state["contract"]["validation"]:
        command = check.get("command")
        if command is None:
            empty = hashlib.sha256(b"").hexdigest()
            results.append({"validation_id": check["id"], "machine_runnable": False, "passed": False,
                            "argv": [], "exit_code": None, "duration_seconds": None, "timed_out": False,
                            "stdout": "", "stderr": "", "output_truncated": False,
                            "output_sha256": stream_digest(empty, empty)})
            continue
        cwd = (workspace / command.get("cwd", ".")).resolve()
        require(cwd == workspace or workspace in cwd.parents, "Check cwd escapes the workspace")
        require(cwd.is_dir(), f"Check cwd does not exist: {cwd}")
        # Scanned before every command: an earlier check could create a link, a later one read
        # through it and remove it, and a single pre-loop or final scan would see a clean tree.
        scan_workspace(workspace, policy)
        timeout = command.get("timeout_seconds", policy["check_timeout_seconds"])
        started = time.monotonic()
        observed = bounded_capture(command["argv"], cwd, timeout, policy["check_output_max_chars"])
        duration = time.monotonic() - started
        results.append({"validation_id": check["id"], "machine_runnable": True,
                        "passed": observed["exit_code"] == 0 and not observed["timed_out"],
                        "argv": list(command["argv"]), "duration_seconds": round(duration, 3), **observed})
    # Scanned again after the commands, so a link created during execution is caught too.
    files = scan_workspace(workspace, policy)
    listing = [{"path": path.relative_to(workspace).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in files]
    checks = {"workspace": str(workspace), "workspace_digest": router.digest(listing),
              "workspace_files": len(files), "results": results}
    recorded = append(directory, "CHECKS", {"checks": checks}, timestamp, prior)
    return {"status": recorded["status"], "workspace_digest": checks["workspace_digest"],
            "deterministic": deterministic_status(recorded),
            "satisfied": deterministic_satisfied(recorded)}


def review_contract(paths, policy, reviews_used):
    report_def = SCHEMA["$defs"]["report"]
    return {
        "write_to": str(paths["report"]),
        "required_fields": sorted(report_def["required"]),
        "verdicts": list(report_def["properties"]["verdict"]["enum"]),
        "criterion_fields": sorted(SCHEMA["$defs"]["criterion_finding"]["required"]),
        "criterion_statuses": list(SCHEMA["$defs"]["criterion_finding"]["properties"]["status"]["enum"]),
        "contract_failure_fields": sorted(SCHEMA["$defs"]["contract_failure"]["required"]),
        "failure_kinds": list(SCHEMA["$defs"]["contract_failure"]["properties"]["kind"]["enum"]),
        "missing_evidence_fields": sorted(SCHEMA["$defs"]["missing_evidence"]["required"]),
        "report_max_bytes": policy["review_report_max_bytes"],
        "rules": [
            "Write the report at exactly the write_to path; another location is not found and not accepted.",
            "Report exactly these fields as one JSON object; any other field is refused.",
            "review_id and reviewer must be the values above; a report that does not match is refused.",
            "Report one finding per contract acceptance criterion under criterion_id, and no other ids.",
            "A criterion is met only with evidence cited from this packet; unverifiable means cannot_determine.",
            "result_supplied_by_worker is the worker's assertion; independent_validation is what was observed."
            " Where they disagree, the observation wins and the disagreement is a finding.",
            "APPROVE only when every criterion is met.",
            "REJECT_BOUNDED must fill contract_failures: each names an existing criterion, validation or"
            " scope rule and a corrective action performable inside this contract.",
            "A change to scope or the contract is NEEDS_ESCALATION or ARCHITECTURE_CONFLICT, never an edit.",
            "Never include credentials, tokens or private keys in any field.",
        ],
    }


def review_packet(state, paths):
    """Render the minimal reviewer context from the ledger's own records; nothing is curated in."""
    opened = pending_review(state)
    require(opened is not None, "No review is awaiting a packet")
    document = {
        "schema_version": "1.0",
        "review_id": opened["review_id"],
        "gate": opened["gate"],
        "reviewer": opened["reviewer"],
        "binding": state["binding"],
        "gates": {"risk": state["risk"], "required": state["gates"],
                  "reviews_used": len(state["reviews"]),
                  "max_review_attempts": state["policy"]["max_review_attempts"]},
        "contract": state["contract"],
        "result_supplied_by_worker": state["result"],
        "artifact": state["artifact"],
        "independent_validation": state["checks"],
        "attestations": sorted(state["attestations"].values(), key=lambda a: a["validation_id"]),
        "prior_reviews": [{"review_id": r["review_id"], "gate": r["gate"], "reviewer": r["reviewer"],
                           "verdict": r["report"]["verdict"] if r["report"] else None,
                           "contract_failures": r["report"]["contract_failures"] if r["report"] else [],
                           "abandoned": r["abandoned"]}
                          for r in state["reviews"][:-1]],
        "open_questions": state["open_questions"],
        "paths": {"packet": str(paths["packet"]), "report": str(paths["report"]),
                  "rules": str(paths["rules"])},
        "review_contract": review_contract(paths, state["policy"], len(state["reviews"])),
    }
    rendered = wp.canonical(document)
    readable = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    require(max(len(rendered), len(readable)) <= state["policy"]["review_packet_max_chars"],
            "Review packet exceeds its configured bound; shrink the artifact or reference it")
    secret_free(rendered, "Review packet")
    secret_free(readable, "Review packet")
    return document, readable


def packet_paths(destination):
    destination = Path(destination)
    return {"rundir": destination, "packet": destination / "review-packet.json",
            "report": destination / "review-report.json", "rules": destination / "REVIEWER_RULES.md"}


def write_review_files(state, destination):
    paths = packet_paths(destination)
    document, readable = review_packet(state, paths)
    paths["rundir"].mkdir(parents=True, exist_ok=False)
    wp.write_new(paths["packet"], readable)
    wp.write_new(paths["rules"], (ROOT / "templates/acceptance/REVIEWER_RULES.md").read_text(encoding="utf-8"))
    return {"status": state["status"], "review_id": document["review_id"], "gate": document["gate"],
            "reviewer": document["reviewer"], "destination": str(paths["rundir"]),
            "packet": str(paths["packet"]), "expect_report_at": str(paths["report"]),
            "packet_chars": len(readable), "reviews_used": len(state["reviews"]),
            "max_review_attempts": state["policy"]["max_review_attempts"]}


def prepare_review(directory, destination, gate, reviewer, timestamp=None):
    require(not Path(destination).exists(), f"Review directory already exists: {destination}")
    prior = replay(directory)
    state = prior[0]
    review_id = router.digest({"binding": state["binding"], "review_number": len(state["reviews"]) + 1,
                               "gate": gate, "reviewer": reviewer})
    data = {"review": {"review_id": review_id, "gate": gate, "reviewer": reviewer}}
    # Validate and render against the candidate state before anything is recorded, so a packet
    # that cannot be rendered refuses cleanly instead of stranding an opened review.
    stamp = timestamp or wp.now()
    candidate = apply(copy.deepcopy(state), {"kind": "REVIEW_OPEN", "data": data, "timestamp": stamp})
    review_packet(candidate, packet_paths(destination))
    recorded = append(directory, "REVIEW_OPEN", data, stamp, prior)
    return write_review_files(recorded, destination)


def render_review(directory, destination):
    """Re-render the pending review's packet, recovering a crash between record and write."""
    require(not Path(destination).exists(), f"Review directory already exists: {destination}")
    return write_review_files(replay(directory)[0], destination)


def ingest_review(directory, report_path, timestamp=None):
    prior = replay(directory)
    path = Path(report_path)
    require(path.is_file(), f"No reviewer report at {path}; record the review with abandon-review instead")
    require(path.stat().st_size <= prior[0]["policy"]["review_report_max_bytes"],
            "Reviewer report exceeds its configured bound")
    report = wp.read_json(path)
    recorded = append(directory, "REVIEW_RESULT", {"report": report}, timestamp, prior)
    latest = recorded["reviews"][-1]
    return {"status": recorded["status"], "reason": recorded["reason"], "verdict": report["verdict"],
            "review_id": latest["review_id"], "gate": latest["gate"],
            "contract_failures": len(report["contract_failures"]),
            "reviews_used": len(recorded["reviews"]),
            "max_review_attempts": recorded["policy"]["max_review_attempts"],
            "acceptance_granted": False}


def decision_for(state, head):
    """The condensed cross-ledger decision this ledger currently supports."""
    reference = f"acceptance-ledger:{head}"
    bound = {"binding": {key: state["binding"][key] for key in ("task_id", "revision", "contract_hash")},
             "result_dispatch_id": state["result"]["dispatch_id"]}
    if state["accepted"] is not None:
        finished = current_completed(state, "model_review")
        if finished:
            latest = finished[-1]
            review_id, reviewer = latest["review_id"], latest["reviewer"]
        else:
            review_id = router.digest({"binding": state["binding"], "deterministic_acceptance": True})
            reviewer = {"actor": state["controller"], "model_family": "deterministic-gate", "tier": 0}
        evidence = [reference, f"workspace:{state['checks']['workspace_digest']}"]
        evidence += [f"review:{r['review_id']}" for r in state["reviews"] if r["report"]][:17]
        return {"review_id": review_id, "verdict": "APPROVE", "reviewer": reviewer,
                "summary": "All required acceptance gates passed; recorded in the acceptance ledger.",
                "evidence": evidence, "contract_failures": [], "acceptance_reference": reference, **bound}
    if state["user_decision"] is not None and state["user_decision"]["decision"] == "reject":
        return {"review_id": router.digest({"binding": state["binding"], "user_rejection": True}),
                "verdict": "NEEDS_ESCALATION",
                "reviewer": {"actor": state["user_decision"]["decider"], "model_family": "human", "tier": 4},
                "summary": "User decision rejected acceptance: " + state["user_decision"]["reason"],
                "evidence": [reference], "contract_failures": [], "acceptance_reference": reference, **bound}
    finished = [r for r in state["reviews"] if r["report"] is not None]
    require(bool(finished), "No acceptance decision has been recorded yet")
    latest = finished[-1]
    report = latest["report"]
    require(report["verdict"] != "APPROVE",
            "An approval alone is not acceptance; every required gate must pass through accept")
    failures = [{"failed_ref": f["failed_ref"], "kind": f["kind"], "what_failed": f["what_failed"],
                 "corrective_action": f["corrective_action"]} for f in report["contract_failures"]]
    return {"review_id": latest["review_id"], "verdict": report["verdict"],
            "reviewer": latest["reviewer"], "summary": report["summary"],
            "evidence": [reference, f"review:{latest['review_id']}"],
            "contract_failures": failures, "acceptance_reference": reference, **bound}


def accept(directory, actor, timestamp=None):
    prior = replay(directory)
    recorded = append(directory, "ACCEPT", {"actor": actor}, timestamp, prior)
    head = replay(directory)[2]
    return {"status": recorded["status"], "reason": recorded["reason"], "actor": actor,
            "gates": recorded["accepted"]["gates"], "decision": decision_for(recorded, head)}


def sync_feedback(directory, feedback_ledger, timestamp=None):
    state, _, head = replay(directory)
    decision = decision_for(state, head)
    task = feedback.replay(feedback_ledger)[0]
    expected = feedback.binding(task["packet"])
    require(all(decision["binding"][key] == expected[key] for key in ("task_id", "revision", "contract_hash")),
            "Acceptance ledger and feedback ledger are bound to different task revisions")
    recorded = feedback.review(feedback_ledger, decision, timestamp)
    return {"feedback_status": recorded["status"], "feedback_reason": recorded["reason"],
            "verdict": decision["verdict"], "packet_state": recorded["packet"]["state"]}


def apply_decision(directory, packet, graph=None, timestamp=None):
    state, _, head = replay(directory)
    decision = decision_for(state, head)
    wp.require_valid(packet)
    latest = wp.current(packet)
    binding = state["binding"]
    require(packet["task_id"] == binding["task_id"] and latest["version"] == binding["revision"]
            and latest["hash"] == binding["contract_hash"],
            "Packet does not match the revision this acceptance ledger reviewed")
    targets = {"APPROVE": "ACCEPTED", "REJECT_BOUNDED": "IN_PROGRESS",
               "NEEDS_ESCALATION": "ESCALATED", "ARCHITECTURE_CONFLICT": "ARCHITECTURE_CONFLICT"}
    require(decision["verdict"] in targets,
            f"No packet transition follows {decision['verdict']}; gather the evidence instead")
    return wp.transition(packet, targets[decision["verdict"]], "reviewer",
                         decision["reviewer"]["actor"], decision["summary"], decision["evidence"],
                         graph, timestamp), decision


def summary(state):
    opened = pending_review(state)
    return {"binding": state["binding"], "risk": state["risk"], "gates": state["gates"],
            "status": state["status"], "reason": state["reason"],
            "deterministic": deterministic_status(state),
            "deterministic_satisfied": deterministic_satisfied(state),
            "pending_review": opened["review_id"] if opened else None,
            "reviews": [{"review_id": r["review_id"], "gate": r["gate"], "reviewer": r["reviewer"],
                         "verdict": r["report"]["verdict"] if r["report"] else None,
                         "abandoned": r["abandoned"]} for r in state["reviews"]],
            "reviews_used": len(state["reviews"]),
            "max_review_attempts": state["policy"]["max_review_attempts"],
            "attested": sorted(state["attestations"]), "waiver": state["waiver"],
            "user_decision": state["user_decision"], "resubmissions": state["resubmissions"],
            "accepted": state["accepted"]}


def verify_review(config, packet_path, report_path):
    """Validate a reviewer report against its own review packet, without a ledger.

    Records nothing and accepts nothing; it exists so an operator-run review can be
    checked by the real validator rather than by eye.
    """
    config_valid(config)
    document = wp.read_json(Path(packet_path))
    feedback.exact(document, REVIEW_PACKET_FIELDS)
    path = Path(report_path)
    require(path.stat().st_size <= config["policy"]["review_report_max_bytes"],
            "Reviewer report exceeds its configured bound")
    report = wp.read_json(path)
    opened = {"review_id": document["review_id"], "gate": document["gate"],
              "reviewer": document["reviewer"]}
    report_valid(report, document["contract"], opened, config["policy"])
    return {"valid": True, "review_id": report["review_id"], "verdict": report["verdict"],
            "criteria_met": sum(1 for f in report["criteria"] if f["status"] == "met"),
            "criteria_total": len(report["criteria"]),
            "contract_failures": len(report["contract_failures"]),
            "recorded_in_ledger": False, "acceptance_granted": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate-config")
    begin = commands.add_parser("init")
    begin.add_argument("ledger", type=Path)
    for key in ("packet", "result", "artifact", "implementers"):
        begin.add_argument("--" + key, required=True, type=Path)
    begin.add_argument("--questions", type=Path)
    begin.add_argument("--controller", required=True)
    begin.add_argument("--architect", required=True)
    checks = commands.add_parser("run-checks")
    checks.add_argument("ledger", type=Path)
    checks.add_argument("--workspace", required=True, type=Path)
    attest = commands.add_parser("attest")
    attest.add_argument("ledger", type=Path)
    attest.add_argument("--validation-id", required=True)
    attest.add_argument("--operator", required=True)
    attest.add_argument("--evidence", action="append", required=True)
    prepare = commands.add_parser("prepare-review")
    prepare.add_argument("ledger", type=Path)
    prepare.add_argument("destination", type=Path)
    prepare.add_argument("--gate", required=True, choices=list(REVIEW_GATES))
    prepare.add_argument("--reviewer-actor", required=True)
    prepare.add_argument("--model-family", required=True)
    prepare.add_argument("--tier", required=True, type=int)
    rerender = commands.add_parser("render-review")
    rerender.add_argument("ledger", type=Path)
    rerender.add_argument("destination", type=Path)
    take = commands.add_parser("ingest-review")
    take.add_argument("ledger", type=Path)
    take.add_argument("report", type=Path)
    give_up = commands.add_parser("abandon-review")
    give_up.add_argument("ledger", type=Path)
    give_up.add_argument("--reason", required=True)
    waive = commands.add_parser("waive-cross-family")
    waive.add_argument("ledger", type=Path)
    waive.add_argument("--operator", required=True)
    waive.add_argument("--reason", required=True)
    decide = commands.add_parser("decide")
    decide.add_argument("ledger", type=Path)
    decide.add_argument("--decider", required=True)
    decide.add_argument("--decision", required=True, choices=["approve", "reject"])
    decide.add_argument("--reason", required=True)
    redo = commands.add_parser("resubmit")
    redo.add_argument("ledger", type=Path)
    for key in ("result", "artifact", "implementers"):
        redo.add_argument("--" + key, required=True, type=Path)
    close = commands.add_parser("accept")
    close.add_argument("ledger", type=Path)
    close.add_argument("--actor", required=True)
    stat = commands.add_parser("status")
    stat.add_argument("ledger", type=Path)
    check = commands.add_parser("verify-review")
    check.add_argument("packet", type=Path)
    check.add_argument("report", type=Path)
    forward = commands.add_parser("sync-feedback")
    forward.add_argument("ledger", type=Path)
    forward.add_argument("feedback_ledger", type=Path)
    update = commands.add_parser("apply")
    update.add_argument("ledger", type=Path)
    update.add_argument("--packet", required=True, type=Path)
    update.add_argument("--output", required=True, type=Path)
    update.add_argument("--graph", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        config = config_valid(wp.read_json(args.config))
        if args.command == "validate-config":
            result = {"valid": True, "max_review_attempts": config["policy"]["max_review_attempts"],
                      "floors": {risk: sorted(gates) for risk, gates in wp.REVIEW_FLOORS.items()},
                      "additional_gates": config["policy"]["additional_gates"]}
        elif args.command == "init":
            state = initialize(args.ledger, config, wp.read_json(args.packet), wp.read_json(args.result),
                               wp.read_json(args.artifact), args.controller, args.architect,
                               wp.read_json(args.implementers),
                               wp.read_json(args.questions) if args.questions else [])
            result = summary(state)
        elif args.command == "run-checks":
            result = run_checks(args.ledger, args.workspace)
        elif args.command == "attest":
            state = append(args.ledger, "ATTESTATION",
                           {"attestation": {"validation_id": args.validation_id, "operator": args.operator,
                                            "evidence": args.evidence}}, previous_state=replay(args.ledger))
            result = summary(state)
        elif args.command == "prepare-review":
            reviewer = {"actor": args.reviewer_actor, "model_family": args.model_family, "tier": args.tier}
            result = prepare_review(args.ledger, args.destination, args.gate, reviewer)
        elif args.command == "render-review":
            result = render_review(args.ledger, args.destination)
        elif args.command == "ingest-review":
            result = ingest_review(args.ledger, args.report)
        elif args.command == "abandon-review":
            state = append(args.ledger, "REVIEW_ABANDONED", {"reason": args.reason},
                           previous_state=replay(args.ledger))
            result = summary(state)
        elif args.command == "waive-cross-family":
            state = append(args.ledger, "WAIVER",
                           {"waiver": {"operator": args.operator, "reason": args.reason}},
                           previous_state=replay(args.ledger))
            result = summary(state)
        elif args.command == "decide":
            state = append(args.ledger, "DECISION",
                           {"decision": {"decider": args.decider, "decision": args.decision,
                                         "reason": args.reason}}, previous_state=replay(args.ledger))
            result = summary(state)
        elif args.command == "resubmit":
            state = append(args.ledger, "RESUBMIT",
                           {"result": wp.read_json(args.result), "artifact": wp.read_json(args.artifact),
                            "implementers": wp.read_json(args.implementers)},
                           previous_state=replay(args.ledger))
            result = summary(state)
        elif args.command == "accept":
            result = accept(args.ledger, args.actor)
        elif args.command == "status":
            result = summary(replay(args.ledger)[0])
        elif args.command == "verify-review":
            result = verify_review(config, args.packet, args.report)
        elif args.command == "sync-feedback":
            result = sync_feedback(args.ledger, args.feedback_ledger)
        else:
            updated, decision = apply_decision(args.ledger, wp.read_json(args.packet),
                                               [wp.read_json(p) for p in args.graph] if args.graph else None)
            wp.write_new(args.output, json.dumps(updated, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
            result = {"packet_state": updated["state"], "verdict": decision["verdict"],
                      "output": str(args.output)}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("valid", True) and result.get("status") not in {"ESCALATION_REQUIRED", "ARCHITECTURE_CONFLICT", "USER_REJECTED"} else 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Acceptance refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
