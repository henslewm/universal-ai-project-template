#!/usr/bin/env python3
"""Reserve bounded worker attempts and replay their local evidence; no model calls."""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import model_router as router
import validate_bootstrap as bootstrap
import work_packet as wp

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = wp.read_json(ROOT / "config/feedback.schema.json")
wp.Draft202012Validator.check_schema(SCHEMA)
ACTIVE = {"READY", "IN_PROGRESS"}
PROTECTED = ("parent", "scope", "non_goals", "interface", "dependencies", "architecture_boundaries", "domain", "risk")


def shape(name, value):
    wp.canonical(value)
    validator = wp.Draft202012Validator({"$defs": SCHEMA["$defs"], "$ref": f"#/$defs/{name}"})
    errors = wp.schema_errors(validator, value)
    if errors:
        raise ValueError("\n".join(errors))


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"Expected fields: {', '.join(sorted(keys))}")


def instant(value):
    if not isinstance(value, str) or not wp.valid_timestamp(value):
        raise ValueError("Invalid event timestamp")
    return datetime.fromisoformat(value.upper().replace("Z", "+00:00"))


def active_anchor(root, expected_profile=None):
    root = Path(root).resolve()
    data = wp.read_json(root / "config/bootstrap.json")
    errors = bootstrap.validate(data, root)
    if errors or data.get("state") != "ACTIVE":
        raise ValueError("ACTIVE bootstrap required: " + "; ".join(errors or ["autonomy is off"]))
    if expected_profile is not None and data["domain_profile"] != expected_profile:
        raise ValueError("Packet profile differs from the approved project's profile")
    return bootstrap.architecture_fingerprint(data)


def binding(packet):
    revision = wp.current(packet)
    return {"task_id": packet["task_id"], "revision": revision["version"],
            "contract_hash": revision["hash"], "role": "worker"}


def graph_check(packet, graph):
    if not isinstance(graph, list):
        raise ValueError("A complete packet graph is required")
    for item in graph:
        wp.require_valid(item)
        if item["domain_profile"] != packet["domain_profile"]:
            raise ValueError("Graph contains a different domain profile")
    matches = [item for item in graph if item["task_id"] == packet["task_id"]]
    if len(matches) != 1 or wp.canonical(matches[0]) != wp.canonical(packet):
        raise ValueError("Graph must contain the exact current packet once")
    wp.graph_order(graph)


def current_graph(state, packet=None):
    packet = packet or state["packet"]
    return [packet if item["task_id"] == packet["task_id"] else item for item in state["graph"]]


def tier_counts(state):
    return {str(t): sum(a["tier"] == t for a in state["attempts"]) for t in range(5)}


def failure_groups(state):
    groups = {}
    for attempt in state["attempts"]:
        if not attempt.get("fingerprint"):
            continue
        key = attempt["fingerprint"]
        group = groups.setdefault(key, {"fingerprint": key, "count": 0, "tiers": {},
                                       "first_evidence": attempt["result"]["evidence"], "latest_evidence": []})
        group["count"] += 1
        tier = str(int(attempt["tier"]))
        group["tiers"][tier] = group["tiers"].get(tier, 0) + 1
        group["latest_evidence"] = attempt["result"]["evidence"]
    return [groups[key] for key in sorted(groups)]


def worker_context(state):
    failures = [a for a in state["attempts"] if a.get("fingerprint")]
    context = {"binding": binding(state["packet"]), "contract": wp.current(state["packet"])["contract"],
               "controller_status": state["status"], "architect_guidance": state["latest_diagnosis"],
               "remaining_task_attempts": state["total_cap"] - len(state["attempts"]),
               "tier_counts": tier_counts(state), "tier_caps": state["caps"],
               "failure_groups": failure_groups(state),
               "recent_failures": [{"attempt_id": a["id"], "fingerprint": a["fingerprint"],
                                    "summary": a["result"]["summary"], "validation": a["result"]["validation"]}
                                   for a in failures[-int(state["policy"]["max_history_entries"]):]],
               # Present only once a rejection exists, so ledgers recorded before this key reproduce.
               **({"review_rejections": [{"review_id": r["review_id"], "fingerprint": r["fingerprint"],
                                          "summary": r["summary"], "contract_failures": r["contract_failures"]}
                                         for r in state["review_rejections"][-int(state["policy"]["max_history_entries"]):]]}
                  if state["review_rejections"] else {}),
               "worker_rule": "Execution requires a matching reserved dispatch. Execute only this contract. Report unrelated discoveries as issue proposals. Do not revise scope or accept your own result."}
    if len(wp.canonical(context)) > state["policy"]["max_context_chars"]:
        raise ValueError("CONTEXT_LIMIT_REQUIRES_DECOMPOSITION")
    return context


def history(state):
    revision = wp.current(state["packet"])["version"]
    relevant = [a for a in state["attempts"] if a["revision"] == revision]
    return [{"sequence": index, "resource_id": a["resource_id"], "provider_id": a["provider_id"],
             "tier": a["tier"], "outcome": a["routing_outcome"], "api_cost_usd": a["result"]["api_cost_usd"],
             "elapsed_seconds": a["elapsed_seconds"], "decision_id": a["id"],
             "config_hash": a["config_hash"], "evidence": a["result"]["evidence"]}
            for index, a in enumerate(relevant, 1)]


def plan(state, config, options):
    if state["pending"]:
        raise ValueError("A reserved dispatch is pending; reconcile it before another attempt")
    if state["status"] not in ACTIVE:
        raise ValueError(f"Controller hold: {state['status']}")
    router.validate_config(config)
    if config["policy"] != state["router_policy"]:
        raise ValueError("Routing policy is frozen for this task; resource mappings may change")
    exact(options, {"task_class", "input_tokens", "output_tokens", "unavailable_providers", "unavailable_resources"})
    graph_check(state["packet"], current_graph(state))
    result = {"status": "NEEDS_ARCHITECT", "reason": "TOTAL_ATTEMPT_LIMIT", "routing": None, "context": None}
    if len(state["attempts"]) >= state["total_cap"]:
        return result
    try:
        result["context"] = worker_context(state)
    except ValueError:
        result["reason"] = "CONTEXT_LIMIT_REQUIRES_DECOMPOSITION"
        return result
    request = {"schema_version": "1.0", "binding": binding(state["packet"]), **copy.deepcopy(options),
               "attempts": history(state), "observations": []}
    # Validate caller filters before combining them with immutable controller limits.
    router.check_shape("request", request)
    config = copy.deepcopy(config)
    old_spend = sum((router.dec(a["result"]["api_cost_usd"]) for a in state["attempts"]
                     if a["revision"] != request["binding"]["revision"]), router.dec(0))
    remaining = router.dec(config["policy"]["role_api_budget_usd"]) - old_spend
    if remaining < 0 or (remaining == 0 and old_spend > 0):
        result["reason"] = "CUMULATIVE_API_LIMIT"
        return result
    config["policy"]["role_api_budget_usd"] = float(remaining)
    counts = tier_counts(state)
    exhausted = [r["id"] for r in config["resources"] if counts[str(int(r["tier"]))] >= state["caps"][str(int(r["tier"]))]]
    request["unavailable_resources"] = sorted(set(request["unavailable_resources"] + exhausted))
    routed = router.record(state["packet"], config, request)
    result["routing"] = routed
    if routed["decision"]["status"] == "ROUTED":
        result.update(status="DISPATCH", reason="BOUNDED_DISPATCH")
    else:
        result["reason"] = routed["decision"]["reason_codes"][0]
        if result["reason"] == "NO_ELIGIBLE_RESOURCE":
            # Exhausted tiers need architect resolution; temporary filters may be reconciled.
            result["status"] = "NEEDS_ARCHITECT" if exhausted else "BLOCKED"
    return result


def normalize(text):
    return " ".join(re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text).split())


def failure_fingerprint(contract, result, timed_out=False):
    actual = {item["check_id"]: item for item in result["validation"]}
    failures = []
    for check in sorted(contract["validation"], key=lambda item: item["id"]):
        item = actual.get(check["id"])
        if item is None:
            failures.append({"check_id": check["id"], "code": "MISSING_VALIDATION"})
        elif not item["passed"]:
            failures.append({"check_id": check["id"], "code": normalize(item["failure_code"]),
                             "expected": normalize(item["expected"]), "actual": normalize(item["actual"])})
    return router.digest({"failures": failures, "scope": result["scope_status"],
                          "architecture_conflict": result["architecture_conflict"], "timed_out": timed_out,
                          "outcome": result["outcome"] if not failures else "OBJECTIVE_FAILURE"})


def move(state, target, actor, reason, evidence, timestamp):
    packet = state["packet"]
    state["packet"] = wp.transition(packet, target, "worker", actor, reason, evidence,
                                    current_graph(state), timestamp)


def apply_result(state, result, timestamp):
    shape("result", result)
    if not state["pending"] or result["dispatch_id"] != state["pending"]:
        raise ValueError("Result does not match the pending dispatch")
    attempt = state["attempts"][-1]
    contract = wp.current(state["packet"])["contract"]
    checks = {check["id"] for check in contract["validation"]}
    ids = [check["check_id"] for check in result["validation"]]
    if len(ids) != len(set(ids)) or set(ids) - checks:
        raise ValueError("Validation IDs must be unique and belong to the current contract")
    if any(not item["passed"] and not normalize(item["failure_code"]) for item in result["validation"]):
        raise ValueError("Failed validations require a stable failure code")
    elapsed = (instant(timestamp) - instant(attempt["issued_at"])).total_seconds()
    if elapsed < 0:
        raise ValueError("Result predates dispatch")
    timed_out = instant(timestamp) > instant(attempt["deadline"])
    passed = set(ids) == checks and all(item["passed"] for item in result["validation"])
    outcome = result["outcome"]
    status, reason = "IN_PROGRESS", "BOUNDED_RETRY"
    if result["architecture_conflict"] or outcome == "ARCHITECTURE_CONFLICT":
        status, reason, outcome = "ARCHITECTURE_HOLD", "ARCHITECT_DIAGNOSIS_REQUIRED", "ARCHITECTURE_CONFLICT"
    elif result["scope_status"] != "within":
        status, reason, outcome = "NEEDS_ARCHITECT", "SCOPE_REVIEW_REQUIRED", "BLOCKED"
    elif timed_out:
        outcome, reason = "FAIL", "ATTEMPT_TIMEOUT"
    elif outcome == "BLOCKED":
        status, reason = "BLOCKED", "WORKER_BLOCKED"
    elif outcome == "PASS" and passed:
        status, reason = "REVIEW_PENDING", "OBJECTIVE_CHECKS_PASSED"
    elif outcome == "PASS":
        outcome, reason = "FAIL", "PASS_CONTRADICTED_BY_VALIDATION"
    attempt.update(result=copy.deepcopy(result), elapsed_seconds=elapsed, resolved_at=timestamp,
                   routing_outcome=outcome, fingerprint=None)
    if outcome in {"FAIL", "NEEDS_ESCALATION", "ARCHITECTURE_CONFLICT"} or result["scope_status"] != "within":
        attempt["fingerprint"] = failure_fingerprint(contract, result, timed_out)
    groups = failure_groups(state)
    group = next((g for g in groups if g["fingerprint"] == attempt["fingerprint"]), None)
    if group and status == "IN_PROGRESS":
        if group["count"] >= state["policy"]["repeated_failure_total"]:
            status, reason, outcome = "NEEDS_ARCHITECT", "REPEATED_FAILURE_TASK_LIMIT", "NEEDS_ESCALATION"
        elif group["tiers"].get(str(int(attempt["tier"])), 0) >= state["policy"]["repeated_failure_per_tier"]:
            reason, outcome = "REPEATED_FAILURE_TIER_LIMIT", "NEEDS_ESCALATION"
    attempt["routing_outcome"] = outcome
    actor = "worker:" + attempt["resource_id"]
    if status == "ARCHITECTURE_HOLD":
        move(state, "ARCHITECTURE_CONFLICT", actor, reason, result["evidence"], timestamp)
    elif status == "NEEDS_ARCHITECT":
        move(state, "ESCALATED", actor, reason, result["evidence"], timestamp)
    elif status == "BLOCKED":
        move(state, "BLOCKED", actor, reason, result["evidence"], timestamp)
    elif outcome != "PROVIDER_UNAVAILABLE":
        move(state, "VALIDATING", actor, reason, result["evidence"], timestamp)
        move(state, "REVIEW" if status == "REVIEW_PENDING" else "IN_PROGRESS", actor, reason, result["evidence"], timestamp)
    state.update(status=status, reason=reason, pending=None)
    state["discoveries"].extend({"attempt_id": attempt["id"], **item} for item in result["discoveries"])


def apply(state, event):
    data, timestamp = event["data"], event["timestamp"]
    if state is None:
        if event["kind"] != "INIT":
            raise ValueError("Ledger must start with INIT")
        exact(data, {"packet", "graph", "policy", "router_config", "anchor", "architect"})
        wp.require_valid(data["packet"])
        graph_check(data["packet"], data["graph"])
        shape("policy", data["policy"])
        router.validate_config(data["router_config"])
        if data["packet"]["state"] != "READY" or not isinstance(data["anchor"], str) or not re.fullmatch(r"[a-f0-9]{64}", data["anchor"]) or not isinstance(data["architect"], str) or not data["architect"].strip():
            raise ValueError("INIT needs a READY packet, approval anchor and architect identity")
        contract = wp.current(data["packet"])["contract"]
        cap = int(contract["retry_budget"]["max_attempts"])
        overrides = contract["retry_budget"].get("max_attempts_by_tier", {})
        return {"packet": copy.deepcopy(data["packet"]), "graph": copy.deepcopy(data["graph"]),
                "policy": copy.deepcopy(data["policy"]), "router_policy": data["router_config"]["policy"],
                "anchor": data["anchor"], "architect": data["architect"], "total_cap": cap,
                "caps": {str(t): min(cap, int(overrides.get(str(t), data["policy"]["max_attempts_by_tier"][str(t)]))) for t in range(5)},
                "repairs": 0, "resumptions": 0, "diagnoses": 0, "latest_diagnosis": None, "attempts": [], "pending": None, "status": "READY", "reason": "INITIALIZED", "discoveries": [], "review_rejections": []}
    if event["kind"] in {"DISPATCH", "HALT"}:
        exact(data, {"config", "options", "plan"})
        expected = plan(state, data["config"], data["options"])
        if wp.canonical(expected) != wp.canonical(data["plan"]):
            raise ValueError("Recorded dispatch plan does not reproduce")
        if event["kind"] == "HALT":
            if expected["status"] == "DISPATCH":
                raise ValueError("HALT cannot contain a dispatch")
            state.update(status=expected["status"], reason=expected["reason"])
            return state
        if expected["status"] != "DISPATCH":
            raise ValueError("Dispatch violates a controller limit")
        decision = expected["routing"]["decision"]
        attempt = {"id": decision["decision_id"], **decision["selected"], "revision": binding(state["packet"])["revision"],
                   "contract_hash": binding(state["packet"])["contract_hash"], "config_hash": decision["config_hash"],
                   "issued_at": timestamp, "deadline": (instant(timestamp) + timedelta(seconds=int(state["policy"]["attempt_timeout_seconds"]))).isoformat(),
                   "result": None, "routing_outcome": None, "fingerprint": None}
        if state["packet"]["state"] == "READY":
            move(state, "IN_PROGRESS", "worker:" + attempt["resource_id"], "Dispatch reserved", [attempt["id"]], timestamp)
        state["attempts"].append(attempt)
        state.update(status="IN_PROGRESS", reason="DISPATCH_RESERVED", pending=attempt["id"])
    elif event["kind"] == "RESULT":
        apply_result(state, data, timestamp)
        state["attempts"][-1]["result_event_sequence"] = event["sequence"]
    elif event["kind"] == "APPROVAL_HOLD":
        exact(data, {"reason"})
        if state["pending"] or state["status"] not in ACTIVE or not isinstance(data["reason"], str) or not data["reason"].strip():
            raise ValueError("Approval hold requires an unreserved active controller")
        state["packet"] = wp.transition(state["packet"], "NEEDS_DECISION", "architect", state["architect"],
                                        "Current bootstrap approval is unavailable or changed", [data["reason"]], timestamp=timestamp)
        state.update(status="NEEDS_DECISION", reason="CURRENT_APPROVAL_REQUIRED")
    elif event["kind"] == "DIAGNOSIS":
        exact(data, {"actor", "diagnosis", "verified_anchor"})
        diagnosis = data["diagnosis"]
        shape("diagnosis", diagnosis)
        if state["pending"] or state["status"] not in {"NEEDS_ARCHITECT", "ARCHITECTURE_HOLD", "BLOCKED"}:
            raise ValueError("Architect diagnosis requires a resolved controller hold")
        if data["actor"] != state["architect"] or diagnosis["architecture_fingerprint"] != state["anchor"]:
            raise ValueError("Architect identity or architecture binding differs from INIT")
        classification = diagnosis["classification"]
        if state["diagnoses"] >= state["policy"]["max_architect_diagnoses"] and classification != "ARCHITECTURE_CHANGE":
            raise ValueError("Architect diagnosis budget exhausted")
        recovered = diagnosis.get("resolved_providers", [])
        if recovered and classification != "RESUME_WORK":
            raise ValueError("Provider recovery is only allowed in an explicit blocker resumption")
        if classification != "REPAIR_CONTRACT" and diagnosis["revised_contract"] is not None:
            raise ValueError("Only a contract-repair diagnosis may provide a replacement contract")
        if classification == "ARCHITECTURE_CHANGE":
            state["packet"] = wp.transition(state["packet"], "NEEDS_DECISION", "architect", data["actor"], diagnosis["reason"], diagnosis["evidence"], timestamp=timestamp)
            state.update(status="NEEDS_DECISION", reason="EXPLICIT_USER_APPROVAL_REQUIRED")
        elif classification == "BLOCKED":
            # A deferral cannot downgrade an architecture/scope/repetition hold.
            state["reason"] = "ARCHITECT_BLOCKED"
        elif classification == "RESUME_WORK":
            if state["status"] != "BLOCKED" or data["verified_anchor"] != state["anchor"]:
                raise ValueError("Only ordinary resolved blockers may resume under unchanged ACTIVE approval")
            if state["resumptions"] >= state["policy"]["max_blocker_resumptions"]:
                raise ValueError("Blocker resumption budget exhausted")
            unavailable = {a["provider_id"] for a in state["attempts"] if a["routing_outcome"] == "PROVIDER_UNAVAILABLE"}
            if set(recovered) - unavailable:
                raise ValueError("Recovered providers must have recorded unavailable attempts")
            for attempt in state["attempts"]:
                if attempt["provider_id"] in recovered and attempt["routing_outcome"] == "PROVIDER_UNAVAILABLE":
                    attempt["routing_outcome"] = "PROVIDER_RECOVERED"
            if state["attempts"] and state["attempts"][-1]["routing_outcome"] == "BLOCKED":
                # Preserve the raw result; this event explicitly records the blocker resolution.
                state["attempts"][-1]["routing_outcome"] = "FAIL"
            packet = state["packet"]
            if packet["state"] == "BLOCKED":
                for target in ("ARCHITECTED", "READY"):
                    packet = wp.transition(packet, target, "architect", data["actor"], diagnosis["reason"], diagnosis["evidence"], current_graph(state, packet), timestamp)
            state.update(packet=packet, status="READY", reason="BLOCKER_RESOLVED", resumptions=state["resumptions"] + 1)
        else:
            if data["verified_anchor"] != state["anchor"]:
                raise ValueError("Contract repair requires unchanged current ACTIVE approval")
            if state["repairs"] >= state["policy"]["max_contract_repairs"] or len(state["attempts"]) >= state["total_cap"]:
                raise ValueError("Contract repair/task attempt budget exhausted")
            revised = diagnosis["revised_contract"]
            errors = wp.validate_contract(revised, state["packet"]["domain_profile"])
            if errors:
                raise ValueError("\n".join(errors))
            old = wp.current(state["packet"])["contract"]
            if any(old[field] != revised[field] for field in PROTECTED):
                raise ValueError("Contract repair changes a protected scope/interface/architecture field")
            if old.get("review") != revised.get("review"):
                # Risk is protected above for the same reason: a repair exists to fix wording,
                # never to lower the acceptance gates the original risk classification requires.
                raise ValueError("Contract repair cannot change the assigned acceptance gates")
            if revised["retry_budget"] != old["retry_budget"]:
                raise ValueError("Contract repair cannot change or reset retry limits")
            packet = wp.revise(state["packet"], revised, data["actor"], diagnosis["reason"], timestamp)
            for target in ("ARCHITECTED", "READY"):
                graph = current_graph(state, packet)
                packet = wp.transition(packet, target, "architect", data["actor"], diagnosis["reason"], diagnosis["evidence"], graph, timestamp)
            state.update(packet=packet, status="READY", reason="CONTRACT_REPAIRED", repairs=state["repairs"] + 1)
        if classification != "ARCHITECTURE_CHANGE":
            state["diagnoses"] += 1
        state["latest_diagnosis"] = {"event_sequence": event["sequence"], "classification": classification,
                                     "reason": diagnosis["reason"], "evidence": diagnosis["evidence"]}
    elif event["kind"] == "REVIEW":
        exact(data, {"decision"})
        apply_review(state, data["decision"], timestamp)
    else:
        raise ValueError("Unknown ledger event kind")
    return state


def rejection_fingerprint(failures):
    normalized = sorted(({"kind": f["kind"], "failed_ref": normalize(f["failed_ref"]),
                          "what_failed": normalize(f["what_failed"])} for f in failures),
                        key=lambda item: (item["kind"], item["failed_ref"], item["what_failed"]))
    return router.digest({"review_failures": normalized})


def apply_review(state, decision, timestamp):
    """Record an independent acceptance decision; the gates themselves live in the acceptance ledger."""
    shape("review_decision", decision)
    if state["pending"] or state["status"] != "REVIEW_PENDING":
        raise ValueError("A review decision requires an unreserved controller awaiting review")
    verdict, actor = decision["verdict"], decision["reviewer"]["actor"]
    if (verdict == "REJECT_BOUNDED") != bool(decision["contract_failures"]):
        raise ValueError("Exactly a bounded rejection names contract failures")
    contract = wp.current(state["packet"])["contract"]
    known = ({entry["id"] for entry in contract["acceptance_criteria"]}
             | {check["id"] for check in contract["validation"]})
    scope_refs = (set(contract["scope"]["allowed"]) | set(contract["scope"]["prohibited"])
                  | set(contract["architecture_boundaries"]))
    for failure in decision["contract_failures"]:
        refs = scope_refs if failure["kind"] == "scope" else known
        if failure["failed_ref"] not in refs:
            raise ValueError("A contract failure must name an existing criterion, validation or scope rule")
    if verdict == "APPROVE":
        state["packet"] = wp.transition(state["packet"], "ACCEPTED", "reviewer", actor, decision["summary"],
                                        decision["evidence"], current_graph(state), timestamp)
        state.update(status="ACCEPTED", reason="INDEPENDENT_ACCEPTANCE_RECORDED")
    elif verdict == "REJECT_BOUNDED":
        fingerprint = rejection_fingerprint(decision["contract_failures"])
        repeated = any(r["fingerprint"] == fingerprint for r in state["review_rejections"])
        state["review_rejections"].append({"review_id": decision["review_id"], "fingerprint": fingerprint,
                                           "summary": decision["summary"], "evidence": decision["evidence"],
                                           "contract_failures": copy.deepcopy(decision["contract_failures"])})
        if state["attempts"] and state["attempts"][-1]["routing_outcome"] == "PASS":
            # Preserve the raw result; the rejection overturns the objective PASS, so the
            # router may route the bounded corrective attempt within the same frozen budget.
            state["attempts"][-1].update(routing_outcome="FAIL", fingerprint=fingerprint)
        if repeated:
            state["packet"] = wp.transition(state["packet"], "ESCALATED", "reviewer", actor,
                                            decision["summary"], decision["evidence"], timestamp=timestamp)
            state.update(status="NEEDS_ARCHITECT", reason="REPEATED_REVIEW_REJECTION")
        else:
            state["packet"] = wp.transition(state["packet"], "IN_PROGRESS", "reviewer", actor, decision["summary"],
                                            decision["evidence"], current_graph(state), timestamp)
            state.update(status="IN_PROGRESS", reason="REVIEW_REJECTED")
    elif verdict == "NEEDS_EVIDENCE":
        state["reason"] = "REVIEW_NEEDS_EVIDENCE"
    elif verdict == "NEEDS_ESCALATION":
        state["packet"] = wp.transition(state["packet"], "ESCALATED", "reviewer", actor,
                                        decision["summary"], decision["evidence"], timestamp=timestamp)
        state.update(status="NEEDS_ARCHITECT", reason="REVIEW_ESCALATED")
    else:
        state["packet"] = wp.transition(state["packet"], "ARCHITECTURE_CONFLICT", "reviewer", actor,
                                        decision["summary"], decision["evidence"], timestamp=timestamp)
        state.update(status="ARCHITECTURE_HOLD", reason="ARCHITECT_DIAGNOSIS_REQUIRED")


def replay(directory):
    paths = sorted(Path(directory).iterdir())
    if not paths:
        raise ValueError("Empty feedback ledger")
    state, previous, previous_time = None, None, None
    for sequence, path in enumerate(paths, 1):
        if path.name != f"{sequence:08d}.json" or path.is_symlink() or not path.is_file():
            raise ValueError("Feedback ledger has a gap, unexpected file or unsafe entry")
        event = wp.read_json(path)
        exact(event, {"sequence", "previous", "kind", "timestamp", "data", "hash"})
        if isinstance(event["sequence"], bool) or event["sequence"] != sequence or event["previous"] != previous:
            raise ValueError("Feedback ledger sequence/hash chain is broken")
        claimed = event.pop("hash")
        if router.digest(event) != claimed:
            raise ValueError("Feedback ledger event hash differs")
        current_time = instant(event["timestamp"])
        if previous_time and current_time < previous_time:
            raise ValueError("Feedback ledger timestamps descend")
        state = apply(state, event)
        previous, previous_time = claimed, current_time
    return state, sequence, previous


def sync_directory(directory):
    # File fsync alone does not guarantee persistence of a new directory entry.
    if os.name == "posix":
        descriptor = os.open(os.fspath(directory), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def append(directory, kind, data, timestamp=None, previous_state=None):
    # Exclusive sequence creation is the compare-and-swap: only one contender wins.
    state, sequence, previous = previous_state or (None, 0, None)
    event = {"sequence": sequence + 1, "previous": previous, "kind": kind,
             "timestamp": timestamp or wp.now(), "data": copy.deepcopy(data)}
    instant(event["timestamp"])
    if sequence:
        prior = wp.read_json(Path(directory) / f"{sequence:08d}.json")
        if instant(event["timestamp"]) < instant(prior["timestamp"]):
            raise ValueError("Event timestamp predates current ledger")
    next_state = apply(copy.deepcopy(state), event)
    event["hash"] = router.digest(event)
    serialized = json.dumps(event, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with (Path(directory) / f"{sequence + 1:08d}.json").open("x", encoding="utf-8", newline="\n") as output:
        output.write(serialized)
        output.flush()
        os.fsync(output.fileno())
    sync_directory(directory)
    return next_state


def initialize(directory, packet, graph, policy, config, root, architect, timestamp=None):
    wp.require_valid(packet)
    anchor = active_anchor(root, packet["domain_profile"])
    data = {"packet": packet, "graph": graph, "policy": policy, "router_config": config,
            "anchor": anchor, "architect": architect}
    # Validate before creating the ledger. A partial initialization fails closed.
    apply(None, {"kind": "INIT", "data": data, "timestamp": timestamp or wp.now()})
    # The caller supplies an existing parent; persist the ledger name there too.
    Path(directory).mkdir(exist_ok=False)
    sync_directory(Path(directory).parent)
    return append(directory, "INIT", data, timestamp)


def reserve(directory, config, options, root, timestamp=None):
    prior = replay(directory)
    state = prior[0]
    if state["pending"] or state["status"] not in ACTIVE:
        raise ValueError(f"Controller hold or pending dispatch: {state['status']}")
    try:
        if active_anchor(root, state["packet"]["domain_profile"]) != state["anchor"]:
            raise ValueError("Approved architecture differs from this task's INIT")
    except (OSError, ValueError) as exc:
        append(directory, "APPROVAL_HOLD", {"reason": str(exc)}, timestamp, prior)
        return {"status": "NEEDS_DECISION", "reason": "CURRENT_APPROVAL_REQUIRED", "dispatch_id": None,
                "deadline": None, "context": None, "routing": None}
    proposed = plan(state, config, options)
    next_state = append(directory, "DISPATCH" if proposed["status"] == "DISPATCH" else "HALT",
                        {"config": config, "options": options, "plan": proposed}, timestamp, prior)
    return {**proposed, "dispatch_id": next_state["pending"],
            "deadline": next_state["attempts"][-1]["deadline"] if next_state["pending"] else None}


def complete(directory, result, timestamp=None):
    # Recording late/cancelled/failed work remains possible after activation is revoked.
    return append(directory, "RESULT", result, timestamp, replay(directory))


def review(directory, decision, timestamp=None):
    # An acceptance decision may be recorded after activation is revoked, like a late result.
    return append(directory, "REVIEW", {"decision": decision}, timestamp, replay(directory))


def diagnose(directory, diagnosis, actor, root, timestamp=None):
    prior = replay(directory)
    shape("diagnosis", diagnosis)
    anchor = active_anchor(root, prior[0]["packet"]["domain_profile"]) if diagnosis["classification"] in {"REPAIR_CONTRACT", "RESUME_WORK"} else None
    return append(directory, "DIAGNOSIS", {"actor": actor, "diagnosis": diagnosis, "verified_anchor": anchor}, timestamp, prior)


def summary(state):
    return {"binding": binding(state["packet"]), "status": state["status"], "reason": state["reason"],
            "pending_dispatch": state["pending"], "total_attempts": len(state["attempts"]),
            "total_cap": state["total_cap"], "tier_counts": tier_counts(state), "tier_caps": state["caps"],
            "contract_repairs": state["repairs"], "blocker_resumptions": state["resumptions"], "failure_groups": failure_groups(state),
            "architect_diagnoses": state["diagnoses"], "remaining_architect_diagnoses": state["policy"]["max_architect_diagnoses"] - state["diagnoses"],
            "latest_diagnosis": state["latest_diagnosis"], "review_rejections": state["review_rejections"],
            "attempts": state["attempts"], "issue_proposals": state["discoveries"]}


def render(state):
    def reference(text):
        return {"preview": text[:200], "sha256": router.digest(text), "truncated": len(text) > 200}

    def evidence(items):
        return {"count": len(items), "first_references": [reference(item) for item in items[:2]]}

    view = {key: value for key, value in summary(state).items() if key not in {"attempts", "failure_groups", "issue_proposals", "latest_diagnosis", "review_rejections"}}
    view["review_rejections"] = [{"review_id": r["review_id"], "fingerprint": r["fingerprint"],
                                  "summary": reference(r["summary"])} for r in state["review_rejections"]]
    view["attempts"] = [{"attempt_id": a["id"], "tier": a["tier"], "resource_id": a["resource_id"],
                         "routing_outcome": a["routing_outcome"], "fingerprint": a["fingerprint"],
                         "record": f"{int(a['result_event_sequence']):08d}.json" if a.get("result_event_sequence") else "pending",
                         "summary": reference(a["result"]["summary"]) if a["result"] else None,
                         "evidence": evidence(a["result"]["evidence"]) if a["result"] else None}
                        for a in state["attempts"]]
    view["failure_groups"] = [{"fingerprint": g["fingerprint"], "count": g["count"], "tiers": g["tiers"]} for g in failure_groups(state)]
    view["issue_proposal_count"] = len(state["discoveries"])
    if state["latest_diagnosis"]:
        diagnosis = state["latest_diagnosis"]
        view["latest_diagnosis"] = {"classification": diagnosis["classification"], "record": f"{int(diagnosis['event_sequence']):08d}.json",
                                    "reason": reference(diagnosis["reason"]), "evidence": evidence(diagnosis["evidence"])}
    body = json.dumps(view, indent=2, ensure_ascii=False, allow_nan=False)
    if len(body) > 60000:
        raise ValueError("Feedback comment exceeds the export limit; use immutable event references")
    fence = "`" * max(3, 1 + max((len(run) for run in re.findall(r"`+", body)), default=0))
    return f"# Feedback ledger — {state['packet']['task_id']}\n\nRecorded local evidence; external outcomes require their own verification.\n\n{fence}json\n{body}\n{fence}\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("ledger", type=Path)
    for key in ("packet", "policy", "config", "root"):
        init.add_argument("--" + key, required=True, type=Path)
    init.add_argument("--graph", nargs="+", required=True, type=Path)
    init.add_argument("--architect", required=True)
    next_parser = commands.add_parser("next")
    next_parser.add_argument("ledger", type=Path)
    for key in ("config", "options", "root"):
        next_parser.add_argument("--" + key, required=True, type=Path)
    finish = commands.add_parser("complete")
    finish.add_argument("ledger", type=Path)
    finish.add_argument("result", type=Path)
    decide = commands.add_parser("review")
    decide.add_argument("ledger", type=Path)
    decide.add_argument("decision", type=Path)
    diagnostic = commands.add_parser("diagnose")
    diagnostic.add_argument("ledger", type=Path)
    diagnostic.add_argument("diagnosis", type=Path)
    diagnostic.add_argument("--actor", required=True)
    diagnostic.add_argument("--root", required=True, type=Path)
    for command in ("status", "context", "render", "packet"):
        sub = commands.add_parser(command)
        sub.add_argument("ledger", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            state = initialize(args.ledger, wp.read_json(args.packet), [wp.read_json(p) for p in args.graph],
                               wp.read_json(args.policy), wp.read_json(args.config), args.root, args.architect)
        elif args.command == "next":
            decision = reserve(args.ledger, wp.read_json(args.config), wp.read_json(args.options), args.root)
            print(json.dumps(decision, indent=2, ensure_ascii=False))
            return 0 if decision["status"] == "DISPATCH" else 2
        elif args.command == "complete":
            state = complete(args.ledger, wp.read_json(args.result))
        elif args.command == "review":
            state = review(args.ledger, wp.read_json(args.decision))
        elif args.command == "diagnose":
            state = diagnose(args.ledger, wp.read_json(args.diagnosis), args.actor, args.root)
        else:
            state = replay(args.ledger)[0]
        if args.command == "render":
            print(render(state), end="")
        else:
            output = worker_context(state) if args.command == "context" else state["packet"] if args.command == "packet" else summary(state)
            print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, router.DecimalException) as exc:
        print(f"Feedback control refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
