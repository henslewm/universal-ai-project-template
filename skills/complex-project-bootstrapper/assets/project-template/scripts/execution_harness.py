#!/usr/bin/env python3
"""Prepare and ingest bounded worker runs for a replaceable execution harness; never invoke a model."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import feedback
import model_router as router
import work_packet as wp

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDERS = {"provider", "model", "rules", "brief", "report", "workspace", "rundir"}
ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]{0,99}")
# Conservative shapes for material that must never reach configuration, briefs, reports or logs.
SECRETS = (
    re.compile(r"(?i)\b(api[_-]?key|secret|passwd|password|token|authorization|bearer)\b\s*[:=]"),
    re.compile(r"\b(sk|rk|pk)-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)\baws_secret_access_key\b"),
)
REPORT_FIELDS = {"dispatch_id", "outcome", "summary", "scope_status", "architecture_conflict",
                 "validation", "evidence", "discoveries", "api_cost_usd", "cost_evidence"}


def check_fields():
    """The exact fields a reported validation check needs, read from the controller's own schema."""
    return sorted(feedback.SCHEMA["$defs"]["validation_check"]["required"])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def secret_free(value, where):
    text = value if isinstance(value, str) else wp.canonical(value)
    for pattern in SECRETS:
        require(pattern.search(text) is None, f"{where} must not contain credential-like material")
    return value


def config_valid(config):
    schema = wp.read_json(ROOT / "config/execution-harness.schema.json")
    errors = wp.schema_errors(wp.Draft202012Validator(schema), config)
    require(not errors, "; ".join(errors))
    secret_free(config, "Harness configuration")
    ids = [harness["id"] for harness in config["harnesses"]]
    require(len(set(ids)) == len(ids), "Duplicate harness id")
    for harness in config["harnesses"]:
        for argument in [harness["command"]] + harness["argv"]:
            for name in re.findall(r"\{([^{}]*)\}", argument):
                require(name in PLACEHOLDERS, f"Unsupported placeholder {{{name}}}; allowed: " + ", ".join(sorted(PLACEHOLDERS)))
        require("{" not in harness["command"], "The harness command itself cannot be templated")
        require(any("{brief}" in argument for argument in harness["argv"]), "The harness must receive the brief")
        require(any("{report}" in argument for argument in harness["argv"]), "The harness must write a report")
    resources = [binding["resource_id"] for binding in config["bindings"]]
    require(len(set(resources)) == len(resources), "Duplicate routed resource binding")
    for binding in config["bindings"]:
        require(binding["harness_id"] in set(ids), "Binding names an unknown harness")
        require(binding["credential_env"] is None or ENV_NAME.fullmatch(binding["credential_env"]),
                "A credential must be referenced by environment-variable name only")
        require(binding["api_base"] is None or re.fullmatch(r"https?://[A-Za-z0-9.:_/-]{1,280}", binding["api_base"]),
                "Unsafe API base URL")
    return config


def binding_for(config, routing):
    require(config["enabled"], "Execution harness dispatch is disabled")
    decision = routing["decision"]
    require(decision["status"] == "ROUTED", "Only a routed dispatch can be prepared for a worker")
    resource = decision["selected"]["resource_id"]
    matches = [binding for binding in config["bindings"] if binding["resource_id"] == resource]
    require(len(matches) == 1, f"No harness binding for routed resource {resource}")
    binding = matches[0]
    harness = next(item for item in config["harnesses"] if item["id"] == binding["harness_id"])
    return binding, harness


def brief(context, routing, binding, dispatch_id):
    """Render only what the packet already permits, plus the report contract."""
    contract = context["contract"]
    document = {
        "schema_version": "1.0",
        "dispatch_id": dispatch_id,
        "binding": context["binding"],
        "harness": {"resource_id": binding["resource_id"], "provider": binding["provider"],
                    "model": binding["model"], "routed_model": routing["decision"]["selected"]["model"],
                    "tier": routing["decision"]["selected"]["tier"],
                    "reasoning_effort": routing["decision"]["selected"]["reasoning_effort"]},
        "bounds": {"remaining_task_attempts": context["remaining_task_attempts"],
                   "tier_counts": context["tier_counts"], "tier_caps": context["tier_caps"],
                   "controller_status": context["controller_status"]},
        "contract": contract,
        "architect_guidance": context["architect_guidance"],
        "prior_failures": context["recent_failures"],
        "failure_groups": context["failure_groups"],
        "worker_rule": context["worker_rule"],
        "report_contract": {
            "write_to": "{report}",
            "required_fields": sorted(REPORT_FIELDS),
            "validation_check_fields": check_fields(),
            "outcomes": ["PASS", "FAIL", "BLOCKED", "NEEDS_ESCALATION",
                         "ARCHITECTURE_CONFLICT", "PROVIDER_UNAVAILABLE"],
            "scope_status_values": ["within", "violated", "unknown"],
            "rules": [
                "Report exactly these fields as one JSON object; any other field is refused.",
                "dispatch_id must be the value above; a report without it is refused.",
                "Report one validation check per contract validation id, and no other ids.",
                "Each validation check is an object with exactly the fields in validation_check_fields."
                " The contract's validation id goes in check_id, not id. passed is a boolean."
                " failure_code, expected and actual are strings and may be empty. evidence is a list of strings.",
                "outcome is one of outcomes; scope_status is one of scope_status_values.",
                "api_cost_usd is a number and cost_evidence is a string; state them plainly.",
                "Claim PASS only when every check passed and scope_status is within.",
                "Record anything outside this contract as a discovery; never widen scope or edit the contract.",
                "Never include credentials, tokens or private keys in any field.",
            ],
        },
    }
    # Measure and scan the canonical form, but hand the worker an indented file: a line-based
    # reader truncates one very long line, and a worker must not need a workaround to read its brief.
    return document, wp.canonical(document), json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def invocation(harness, binding, paths):
    values = {"provider": binding["provider"], "model": binding["model"],
              "rules": str(paths["rules"]), "brief": str(paths["brief"]),
              "report": str(paths["report"]), "workspace": str(paths["workspace"]),
              "rundir": str(paths["rundir"])}
    argv = [harness["command"]] + [argument.format(**values) for argument in harness["argv"]]
    environment = [binding["credential_env"]] if binding["credential_env"] else []
    return {"argv": argv, "required_environment": environment, "api_base": binding["api_base"],
            "adapter": harness["adapter"], "harness_id": harness["id"]}


def rules_text():
    return (ROOT / "templates/harness/BOUNDED_WORKER_RULES.md").read_text(encoding="utf-8")


def dispatch(directory, config, router_config, request, root, destination):
    """Reserve one bounded attempt and write the worker brief; never run the harness."""
    config_valid(config)
    require(config["enabled"], "Execution harness dispatch is disabled")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    reserved = feedback.reserve(directory, router_config, request, root)
    if reserved["status"] != "DISPATCH":
        return {"status": reserved["status"], "reason": reserved["reason"], "dispatch_id": reserved["dispatch_id"],
                "prepared": False, "destination": str(destination)}
    try:
        binding, harness = binding_for(config, reserved["routing"])
        document, rendered, readable = brief(reserved["context"], reserved["routing"], binding, reserved["dispatch_id"])
        require(len(rendered) <= config["limits"]["brief_max_chars"], "Brief exceeds its configured bound")
        secret_free(rendered, "Worker brief")
    except ValueError as exc:
        # The reservation is already spent, so close it with honest evidence rather than leaving it pending.
        feedback.complete(directory, {
            "dispatch_id": reserved["dispatch_id"], "outcome": "PROVIDER_UNAVAILABLE",
            "summary": "Harness preparation refused; no worker was dispatched and no model was invoked.",
            "scope_status": "unknown", "architecture_conflict": False, "validation": [],
            "evidence": [f"harness-preparation-refused: {exc}"], "discoveries": [],
            "api_cost_usd": 0, "cost_evidence": "No provider call was made; preparation failed first."})
        return {"status": "HARNESS_UNAVAILABLE", "reason": str(exc), "dispatch_id": reserved["dispatch_id"],
                "prepared": False, "attempt_closed": True, "destination": str(destination),
                "executed": False, "execution_authorized": False}
    paths = {"rundir": destination, "brief": destination / "brief.json",
             "rules": destination / "BOUNDED_WORKER_RULES.md",
             "report": destination / "report.json", "workspace": destination / "workspace"}
    paths["workspace"].mkdir()
    wp.write_new(paths["brief"], readable)
    wp.write_new(paths["rules"], rules_text())
    plan = invocation(harness, binding, paths)
    wp.write_new(destination / "invocation.json", json.dumps(plan, indent=2, ensure_ascii=False))
    return {"status": "PREPARED", "reason": reserved["reason"], "dispatch_id": reserved["dispatch_id"],
            "deadline": reserved["deadline"], "prepared": True, "destination": str(destination),
            "invocation": plan, "brief_chars": len(rendered),
            "validation_ids": [check["id"] for check in document["contract"]["validation"]],
            "executed": False, "execution_authorized": False}


def report_valid(report, contract, dispatch_id, limits, size):
    require(size <= limits["report_max_bytes"], "Worker report exceeds its configured bound")
    feedback.exact(report, REPORT_FIELDS)
    secret_free(report, "Worker report")
    require(report["dispatch_id"] == dispatch_id, "Report does not match the reserved dispatch")
    expected = [check["id"] for check in contract["validation"]]
    reported = [check["check_id"] for check in report["validation"]]
    require(len(set(reported)) == len(reported), "Duplicate validation id in the worker report")
    require(set(reported) == set(expected), "Report every contract validation check and no other id")
    require(isinstance(report["evidence"], list) and report["evidence"], "A worker report requires evidence")
    if report["outcome"] == "PASS":
        require(all(check["passed"] for check in report["validation"]), "PASS requires every validation check to pass")
        require(report["scope_status"] == "within", "PASS requires scope_status within")
        require(not report["architecture_conflict"], "An architecture conflict cannot be reported as PASS")
    return report


def ingest(directory, config, report_path):
    """Validate a worker report against its contract, then record it in the task ledger."""
    config_valid(config)
    state = feedback.replay(directory)[0]
    require(state["pending"], "No reserved dispatch is awaiting a report")
    path = Path(report_path)
    # A worker that wrote nothing is a real outcome, but never an inferred one: say so with `abandon`.
    require(path.is_file(), f"No worker report at {path}; record the attempt with abandon instead of inferring it")
    report = wp.read_json(path)
    report_valid(report, wp.current(state["packet"])["contract"], state["pending"],
                 config["limits"], path.stat().st_size)
    recorded = feedback.complete(directory, report)
    return {"status": recorded["status"], "outcome": report["outcome"], "dispatch_id": report["dispatch_id"],
            "attempts_used": len(recorded["attempts"]), "remaining_task_attempts": recorded["total_cap"] - len(recorded["attempts"]),
            "evidence_preserved": bool(recorded["attempts"][-1].get("fingerprint")) or report["outcome"] == "PASS",
            "independent_acceptance": False}


def verify_report(config, brief_path, report_path):
    """Validate a worker report against its own brief, without a task ledger.

    Used for an operator-run harness demonstration: it proves the report contract holds
    for a real worker run, and deliberately records nothing and accepts nothing.
    """
    config_valid(config)
    document = wp.read_json(Path(brief_path))
    feedback.exact(document, {"schema_version", "dispatch_id", "binding", "harness", "bounds",
                              "contract", "architect_guidance", "prior_failures",
                              "failure_groups", "worker_rule", "report_contract"})
    path = Path(report_path)
    report = wp.read_json(path)
    report_valid(report, document["contract"], document["dispatch_id"],
                 config["limits"], path.stat().st_size)
    return {"valid": True, "dispatch_id": report["dispatch_id"], "outcome": report["outcome"],
            "scope_status": report["scope_status"],
            "validation_ids": sorted(check["check_id"] for check in report["validation"]),
            "checks_passed": sum(1 for check in report["validation"] if check["passed"]),
            "checks_total": len(report["validation"]), "discoveries": len(report["discoveries"]),
            "recorded_in_ledger": False, "independent_acceptance": False}


def abandon(directory, config, reason):
    """Close a dispatched attempt that produced no usable report, with an explicit recorded reason.

    Absence of a report is never interpreted on its own. The operator states what happened, the
    attempt is recorded as a failure with that evidence and its fingerprint, and the feedback
    controller decides whether the budget allows another attempt or the architect is needed.
    """
    config_valid(config)
    state = feedback.replay(directory)[0]
    require(state["pending"], "No reserved dispatch is awaiting a report")
    text = str(reason).strip()
    require(20 <= len(text) <= 2000, "Abandoning an attempt requires a specific recorded reason")
    secret_free(text, "Abandonment reason")
    recorded = feedback.complete(directory, {
        "dispatch_id": state["pending"], "outcome": "FAIL",
        "summary": "Dispatched worker produced no usable report; the attempt was abandoned with a recorded reason.",
        "scope_status": "unknown", "architecture_conflict": False, "validation": [],
        "evidence": [f"attempt-abandoned: {text}"], "discoveries": [], "api_cost_usd": 0,
        "cost_evidence": "The worker reported no accounting, so no cost is asserted."})
    return {"status": recorded["status"], "outcome": "FAIL", "dispatch_id": state["pending"],
            "attempts_used": len(recorded["attempts"]),
            "remaining_task_attempts": recorded["total_cap"] - len(recorded["attempts"]),
            "fingerprint": recorded["attempts"][-1].get("fingerprint"),
            "evidence_preserved": True, "independent_acceptance": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate-config")
    prepare = commands.add_parser("dispatch")
    prepare.add_argument("ledger", type=Path)
    prepare.add_argument("destination", type=Path)
    prepare.add_argument("--router-config", required=True, type=Path)
    prepare.add_argument("--request", required=True, type=Path)
    take = commands.add_parser("ingest")
    take.add_argument("ledger", type=Path)
    take.add_argument("report", type=Path)
    give_up = commands.add_parser("abandon")
    give_up.add_argument("ledger", type=Path)
    give_up.add_argument("--reason", required=True)
    check = commands.add_parser("verify-report")
    check.add_argument("brief", type=Path)
    check.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        config = wp.read_json(args.config)
        if args.command == "validate-config":
            config_valid(config)
            result = {"valid": True, "harnesses": [item["id"] for item in config["harnesses"]],
                      "enabled": config["enabled"], "credentials_embedded": False}
        elif args.command == "abandon":
            result = abandon(args.ledger, config, args.reason)
        elif args.command == "verify-report":
            result = verify_report(config, args.brief, args.report)
        elif args.command == "dispatch":
            result = dispatch(args.ledger, config, wp.read_json(args.router_config),
                              wp.read_json(args.request), args.root, args.destination)
        else:
            result = ingest(args.ledger, config, args.report)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("valid", True) and result.get("status") != "BLOCKED" else 2
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Execution harness refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
