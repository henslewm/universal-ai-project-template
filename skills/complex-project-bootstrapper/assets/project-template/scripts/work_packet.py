#!/usr/bin/env python3
"""Validate and record work contracts locally; never execute or authorize work."""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    raise SystemExit("Work-packet tools require: python -m pip install -r requirements-work-packets.txt")

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "config/work-packet.schema.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)
FORMATS = FormatChecker()


@FORMATS.checks("date-time", raises=ValueError)
def valid_timestamp(value):
    # jsonschema's optional RFC3339 package is not assumed to be installed.
    # Register our supported timestamp check explicitly so formats cannot silently pass.
    if not isinstance(value, str):
        return True  # The schema's type rule reports nonstrings.
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", value):
        return False
    datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
    return True


VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FORMATS)
CONTRACT_VALIDATOR = Draft202012Validator(
    {"$schema": SCHEMA["$schema"], "$defs": SCHEMA["$defs"], "$ref": "#/$defs/contract"},
    format_checker=FORMATS,
)
ADVANCED = {"READY", "IN_PROGRESS", "VALIDATING", "REVIEW", "ACCEPTED", "MERGED", "VERIFIED"}
PAUSED = {"BLOCKED", "ESCALATED", "NEEDS_DECISION", "ARCHITECTURE_CONFLICT", "FAILED"}
EDGES = {
    ("PROPOSED", "ARCHITECTED"): {"architect"},
    ("ARCHITECTED", "READY"): {"architect"},
    ("READY", "IN_PROGRESS"): {"worker"},
    ("IN_PROGRESS", "VALIDATING"): {"worker"},
    ("VALIDATING", "IN_PROGRESS"): {"worker"},
    ("VALIDATING", "REVIEW"): {"worker"},
    ("REVIEW", "IN_PROGRESS"): {"reviewer"},
    ("REVIEW", "ACCEPTED"): {"reviewer"},
    ("ACCEPTED", "MERGED"): {"integrator"},
    ("ACCEPTED", "VERIFIED"): {"integrator"},
    ("MERGED", "VERIFIED"): {"integrator"},
}
for paused in PAUSED:
    EDGES[(paused, "ARCHITECTED")] = {"architect"}
for source in {"PROPOSED", "ARCHITECTED", "READY", "IN_PROGRESS", "VALIDATING", "REVIEW"} | PAUSED:
    for target, roles in {
        "BLOCKED": {"architect", "worker", "reviewer"},
        "ESCALATED": {"architect", "worker", "reviewer"},
        "NEEDS_DECISION": {"architect"},
        "ARCHITECTURE_CONFLICT": {"architect", "worker", "reviewer"},
        "FAILED": {"architect", "worker", "reviewer"},
        "SUPERSEDED": {"architect"},
    }.items():
        if source != target:
            EDGES[(source, target)] = roles


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def fingerprint(task_id: str, profile: str, version: int, contract: dict) -> str:
    bound = {"schema_version": "1.0", "task_id": task_id, "domain_profile": profile,
             "version": version, "contract": contract}
    return hashlib.sha256(canonical(bound).encode("utf-8")).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def schema_errors(validator, value) -> list[str]:
    return [f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}"
            for e in sorted(validator.iter_errors(value), key=lambda e: str(list(e.absolute_path)))]


def validate_contract(contract) -> list[str]:
    errors = schema_errors(CONTRACT_VALIDATOR, contract)
    if errors:
        return errors
    routing = contract["routing"]
    if routing["min_tier"] > routing["max_tier"]:
        errors.append("routing: min_tier exceeds max_tier")
    tiers = contract["escalation_path"]
    if any(t <= routing["min_tier"] or t > routing["max_tier"] for t in tiers) or tiers != sorted(tiers):
        errors.append("escalation_path: tiers must strictly increase above min_tier and within max_tier")
    for tier, cap in contract["retry_budget"].get("max_attempts_by_tier", {}).items():
        if int(tier) not in [routing["min_tier"]] + tiers:
            errors.append("retry_budget: per-tier override is outside the authorized worker path")
        if cap > contract["retry_budget"]["max_attempts"]:
            errors.append("retry_budget: per-tier override exceeds the total attempt limit")
    criteria = [entry["id"] for entry in contract["acceptance_criteria"]]
    for field in ("acceptance_criteria", "validation", "sources"):
        ids = [entry["id"] for entry in contract[field]]
        if len(ids) != len(set(ids)):
            errors.append(f"{field}: duplicate IDs")
    covered = set()
    for check in contract["validation"]:
        covered.update(check["criterion_ids"])
        for criterion in check["criterion_ids"]:
            if criterion not in criteria:
                errors.append(f"validation/{check['id']}: unknown criterion {criterion}")
    if set(criteria) - covered:
        errors.append("acceptance_criteria: every criterion needs a specified validation")
    # Legal/domain extension content is data, not proof of authority or safety.
    return errors


def current(packet: dict) -> dict:
    return packet["revision_history"][-1]


def event_error(event: dict, state: str | None, revision: int, implementers: set[str]) -> str | None:
    target, role = event["to"], event["role"]
    if event["from"] != state:
        return "from state does not match preceding event"
    if event["kind"] == "create":
        if state is not None or revision != 0 or event["revision"] != 1 or target != "PROPOSED" or role != "architect":
            return "creation must start revision 1 at PROPOSED with architect role"
    elif event["kind"] == "revision":
        if state is None or event["revision"] != revision + 1 or target != "PROPOSED" or role != "architect":
            return "revision must append one version and reset to PROPOSED with architect role"
    else:
        if event["revision"] != revision:
            return "transition cannot change contract revision"
        if role not in EDGES.get((state, target), set()):
            return f"illegal transition/role: {state} -> {target} by {role}"
        if target in {"REVIEW", "ACCEPTED", "MERGED", "VERIFIED"} or state in PAUSED or state == "REVIEW":
            if not event["evidence"]:
                return "transition requires evidence references"
        if target == "ACCEPTED" and event["actor"].strip().casefold() in implementers:
            return "an implementation actor cannot accept its own revision"
    return None


def validate(packet) -> list[str]:
    errors = schema_errors(VALIDATOR, packet)
    if errors:
        return errors
    snapshots = packet["revision_history"]
    previous_time = None
    for number, snapshot in enumerate(snapshots, 1):
        if snapshot["version"] != number:
            errors.append("revision_history: versions must be consecutive starting at 1")
        errors.extend(f"revision {number}: {e}" for e in validate_contract(snapshot["contract"]))
        if packet["task_id"] in snapshot["contract"]["dependencies"]:
            errors.append(f"revision {number}: task cannot depend on itself")
        expected = fingerprint(packet["task_id"], packet["domain_profile"], number, snapshot["contract"])
        if snapshot["hash"] != expected:
            errors.append(f"revision {number}: contract hash mismatch")
        stamp = datetime.fromisoformat(snapshot["timestamp"].upper().replace("Z", "+00:00"))
        if previous_time is not None and stamp < previous_time:
            errors.append("revision_history: timestamps must not move backwards")
        previous_time = stamp
    state, revision, implementers, previous_time = None, 0, set(), None
    for number, event in enumerate(packet["events"], 1):
        if event["sequence"] != number:
            errors.append("events: sequences must be consecutive starting at 1")
        problem = event_error(event, state, revision, implementers)
        if problem:
            errors.append(f"event {number}: {problem}")
        if event["revision"] > len(snapshots):
            errors.append(f"event {number}: unknown revision")
        else:
            snapshot = snapshots[int(event["revision"]) - 1]
            if event["contract_hash"] != snapshot["hash"]:
                errors.append(f"event {number}: contract hash does not match its revision")
            if event["kind"] in {"create", "revision"}:
                for field in ("actor", "timestamp", "reason"):
                    if event[field] != snapshot[field]:
                        errors.append(f"event {number}: {field} differs from revision record")
                implementers = set()
        stamp = datetime.fromisoformat(event["timestamp"].upper().replace("Z", "+00:00"))
        if previous_time is not None and stamp < previous_time:
            errors.append("events: timestamps must not move backwards")
        previous_time = stamp
        if event["to"] == "IN_PROGRESS" and event["role"] == "worker":
            implementers.add(event["actor"].strip().casefold())
        if event["role"] == "worker" and event["to"] in {"VALIDATING", "REVIEW"}:
            implementers.add(event["actor"].strip().casefold())
        state, revision = event["to"], event["revision"]
    if state != packet["state"] or revision != len(snapshots):
        errors.append("packet state/current revision does not match replayed events")
    return errors


def require_valid(packet) -> None:
    errors = validate(packet)
    if errors:
        raise ValueError("; ".join(errors))


def graph_order(packets: list[dict]) -> list[str]:
    if not packets:
        raise ValueError("dependency graph is empty")
    by_id = {}
    for packet in packets:
        require_valid(packet)
        task_id = packet["task_id"]
        if task_id in by_id:
            raise ValueError(f"duplicate task ID: {task_id}")
        by_id[task_id] = packet
    remaining = {}
    for task_id, packet in by_id.items():
        dependencies = set(current(packet)["contract"]["dependencies"])
        missing = dependencies - by_id.keys()
        if missing:
            raise ValueError(f"{task_id}: missing dependencies: {', '.join(sorted(missing))}")
        if packet["state"] in ADVANCED:
            pending = sorted(d for d in dependencies if by_id[d]["state"] != "VERIFIED")
            if pending:
                raise ValueError(f"{task_id}: dependencies must be VERIFIED: {', '.join(pending)}")
        remaining[task_id] = dependencies
    order = []
    while remaining:
        ready = sorted(task_id for task_id, deps in remaining.items() if not deps)
        if not ready:
            raise ValueError("dependency graph contains a cycle")
        order.extend(ready)
        for task_id in ready:
            del remaining[task_id]
        for dependencies in remaining.values():
            dependencies.difference_update(ready)
    return order


def snapshot(task_id, profile, version, contract, actor, reason, timestamp):
    return {"version": version, "contract": copy.deepcopy(contract),
            "hash": fingerprint(task_id, profile, version, contract),
            "actor": actor, "reason": reason, "timestamp": timestamp}


def append_event(packet, kind, target, role, actor, reason, evidence, timestamp):
    record = current(packet)
    packet["events"].append({"sequence": len(packet["events"]) + 1, "kind": kind,
        "from": packet["state"], "to": target, "revision": record["version"],
        "contract_hash": record["hash"], "actor": actor, "role": role,
        "reason": reason, "evidence": list(evidence), "timestamp": timestamp})
    packet["state"] = target


def create(task_id, profile, contract, actor, reason, timestamp=None):
    stamp = timestamp or now()
    packet = {"schema_version": "1.0", "task_id": task_id, "domain_profile": profile,
              "state": None, "revision_history": [snapshot(task_id, profile, 1, contract, actor, reason, stamp)],
              "events": []}
    append_event(packet, "create", "PROPOSED", "architect", actor, reason, [], stamp)
    require_valid(packet)
    return packet


def revise(packet, contract, actor, reason, timestamp=None):
    require_valid(packet)
    if contract == current(packet)["contract"]:
        raise ValueError("revision does not change the contract")
    result = copy.deepcopy(packet)
    stamp = timestamp or now()
    result["revision_history"].append(snapshot(packet["task_id"], packet["domain_profile"],
        len(packet["revision_history"]) + 1, contract, actor, reason, stamp))
    append_event(result, "revision", "PROPOSED", "architect", actor, reason, [], stamp)
    require_valid(result)
    return result


def transition(packet, target, role, actor, reason, evidence=(), graph=None, timestamp=None):
    require_valid(packet)
    result = copy.deepcopy(packet)
    append_event(result, "transition", target, role, actor, reason, evidence, timestamp or now())
    require_valid(result)
    if graph is not None:
        for member in graph:
            require_valid(member)
        matches = [p for p in graph if p["task_id"] == packet["task_id"]]
        if len(matches) != 1 or matches[0] != packet:
            raise ValueError("graph must contain exactly the current target packet, including its history/state")
        graph_order([result if p["task_id"] == packet["task_id"] else p for p in graph])
    elif target in ADVANCED and current(packet)["contract"]["dependencies"]:
        raise ValueError("transition requires a complete --graph for this packet's dependencies")
    return result


def markdown_text(value: str) -> str:
    value = html.escape(value, quote=False)
    value = re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value)
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def render(packet) -> str:
    require_valid(packet)
    latest = current(packet)
    lines = [f"# {packet['task_id']} — {markdown_text(latest['contract']['title'])}", "",
        f"Profile: {packet['domain_profile']} · Revision: {latest['version']} · Recorded state: {packet['state']}", "",
        f"Contract SHA-256: `{latest['hash']}`", "",
        "> Generated from the canonical JSON packet. State and evidence references are recorded assertions;",
        "> they do not authorize execution or independently prove tests, review, or merge.", ""]

    def bullets(value, indent=0):
        prefix = "  " * indent
        if isinstance(value, dict):
            if not value:
                lines.append(prefix + "- None specified.")
            for key in sorted(value):
                child = value[key]
                label = markdown_text(key.replace("_", " ").capitalize())
                if isinstance(child, (list, dict)):
                    lines.append(prefix + f"- **{label}:**")
                    bullets(child, indent + 1)
                else:
                    lines.append(prefix + f"- **{label}:** {markdown_text(str(child))}")
        elif isinstance(value, list):
            if not value:
                lines.append(prefix + "- None specified.")
            for child in value:
                if isinstance(child, dict):
                    lines.append(prefix + "- Record:")
                    bullets(child, indent + 1)
                else:
                    lines.append(prefix + "- " + markdown_text(str(child)))
        else:
            lines.append(markdown_text(str(value)))

    for key in SCHEMA["$defs"]["contract"]["properties"]:
        value = latest["contract"][key]
        if key != "title":
            lines.extend([f"## {key.replace('_', ' ').capitalize()}", ""])
            if key == "domain":
                # Extension data has arbitrary JSON keys/types/nesting. A JSON block
                # preserves distinctions such as null vs "null" and 1 vs "1".
                extension = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
                longest = max((len(run) for run in re.findall(r"`+", extension)), default=0)
                fence = "`" * max(3, longest + 1)
                lines.extend([fence + "json", extension, fence])
            else:
                bullets(value)
            lines.append("")
    lines.extend(["## Revision provenance", ""])
    for item in packet["revision_history"]:
        lines.append(f"- Version {item['version']}: `{item['hash']}` — {markdown_text(item['actor'])}; "
                     f"{markdown_text(item['timestamp'])}; {markdown_text(item['reason'])}")
    lines.extend(["", "## Latest recorded event", ""])
    bullets(packet["events"][-1])
    return "\n".join(lines) + "\n"


def read_json(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"non-finite JSON number: {value}")

    result = json.loads(Path(path).read_text(encoding="utf-8-sig"),
                        object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    canonical(result)  # Reject overflow such as 1e999, including in extension data.
    return result


def write_new(path, text):
    # Exclusive creation preserves input and all earlier revisions on any normal refusal.
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate", help="Validate packet structure and local history")
    check.add_argument("packet")
    graph = commands.add_parser("graph", help="Validate a complete graph and print deterministic order")
    graph.add_argument("packets", nargs="+")
    issue = commands.add_parser("render", help="Render a GitHub issue body without publishing it")
    issue.add_argument("packet")
    issue.add_argument("--output")
    for name in ("create", "revise", "transition"):
        cmd = commands.add_parser(name)
        cmd.add_argument("input", help="Contract JSON for create; packet JSON otherwise")
        cmd.add_argument("--actor", required=True)
        cmd.add_argument("--reason", required=True)
        cmd.add_argument("--output", required=True, help="A new file; existing files are never overwritten")
        if name == "create":
            cmd.add_argument("--task-id", required=True)
            cmd.add_argument("--profile", required=True)
        elif name == "revise":
            cmd.add_argument("--contract", required=True, help="Revised contract JSON")
        else:
            cmd.add_argument("--to", required=True)
            cmd.add_argument("--role", required=True, choices=["architect", "worker", "reviewer", "integrator"])
            cmd.add_argument("--evidence", action="append", default=[])
            cmd.add_argument("--graph", nargs="+")
    args = parser.parse_args(argv)
    try:
        if args.command == "graph":
            print("GRAPH VALID — recorded dependency order: " + " -> ".join(graph_order([read_json(p) for p in args.packets])))
            return 0
        data = read_json(args.packet if args.command in {"validate", "render"} else args.input)
        if args.command == "validate":
            require_valid(data)
            print("PACKET VALID — structure/history only; no execution authorization or independent evidence verification")
            return 0
        if args.command == "render":
            output = render(data)
            if args.output:
                write_new(args.output, output)
            else:
                print(output, end="")
            return 0
        if args.command == "create":
            result = create(args.task_id, args.profile, data, args.actor, args.reason)
        elif args.command == "revise":
            result = revise(data, read_json(args.contract), args.actor, args.reason)
        else:
            result = transition(data, args.to, args.role, args.actor, args.reason, args.evidence,
                                [read_json(p) for p in args.graph] if args.graph else None)
        write_new(args.output, json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        print(f"RECORDED {result['task_id']} revision {current(result)['version']} at {result['state']}; no work executed")
        return 0
    except (OSError, ValueError, RecursionError) as exc:
        print(f"WORK PACKET INVALID: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
