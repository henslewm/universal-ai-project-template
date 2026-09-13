#!/usr/bin/env python3
"""Software + hardware domain rules: keep simulated success and hardware verification distinct.

This module owns nothing the controllers already own. It adds structure to a
software-hardware contract's `domain` block, decides which validations are machine-runnable
and which must be observed on physical hardware, and derives the hardware status a task has
actually earned from its acceptance ledger. It executes nothing and invokes no model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    raise SystemExit("Domain tools require: python -m pip install -r requirements-work-packets.txt")

ROOT = Path(__file__).resolve().parent.parent
PROFILE = "software-hardware"
SCHEMA = json.loads((ROOT / "config/domains/software-hardware.schema.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)
# The ladder, lowest rung first. A rung at or below integration is reproduced by re-executing a
# declared command; a rung above it exists only as an observation of physical hardware.
LEVELS = tuple(SCHEMA["$defs"]["validation_level"]["enum"])
MACHINE_LEVELS = frozenset(LEVELS[:LEVELS.index("integration") + 1])
HARDWARE_LEVELS = frozenset(LEVELS[LEVELS.index("integration") + 1:])
COMPONENTS = tuple(SCHEMA["$defs"]["component"]["enum"])
UNVERIFIED, VERIFIED, NOT_FACING = "UNVERIFIED_ON_HARDWARE", "VERIFIED_ON_HARDWARE", "NOT_HARDWARE_FACING"
DIGEST_PREFIX = "hardware-evidence:sha256="
# Lines a hardware-rung attestation must carry; each is derived from the bound evidence record.
EVIDENCE_KEYS = ("level", "device", "firmware", "observed_at", "outcome", "operator")


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _validator(name):
    return Draft202012Validator({"$defs": SCHEMA["$defs"], "$ref": f"#/$defs/{name}"})


def _schema_errors(name, value) -> list[str]:
    return [f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}"
            for e in sorted(_validator(name).iter_errors(value), key=lambda e: str(list(e.absolute_path)))]


def validate_contract_domain(contract: dict) -> list[str]:
    """Cross-field rules over a schema-valid common contract; returns error strings."""
    domain = contract.get("domain")
    errors = _schema_errors("contract_domain", domain)
    if errors:
        return errors
    sources = {entry["id"] for entry in contract["sources"]}
    validation_ids = [check["id"] for check in contract["validation"]]
    levels = domain["validation_levels"]
    mapped, declared = set(levels), set(validation_ids)
    if mapped != declared:
        missing, extra = sorted(declared - mapped), sorted(mapped - declared)
        if missing:
            errors.append("validation_levels: every validation needs exactly one rung; unmapped: " + ", ".join(missing))
        if extra:
            errors.append("validation_levels: names validations the contract does not declare: " + ", ".join(extra))
    for check in contract["validation"]:
        level = levels.get(check["id"])
        if level is None:
            continue
        has_command = check.get("command") is not None
        if level in MACHINE_LEVELS and not has_command:
            errors.append(f"validation/{check['id']}: a {level} check must declare a command; "
                          "attestation cannot stand in for a runnable check")
        if level in HARDWARE_LEVELS and has_command:
            errors.append(f"validation/{check['id']}: a {level} check must not declare a command; "
                          "a re-executed command is a simulation, not hardware")
    for index, item in enumerate(domain["hardware_assumptions"]):
        if item["source_id"] not in sources:
            errors.append(f"hardware_assumptions/{index}: unknown source {item['source_id']}")
    for reference in domain["protocol_references"]:
        if reference not in sources:
            errors.append(f"protocol_references: unknown source {reference}")
    hardware_facing = bool(domain["hardware_assumptions"])
    hardware_checks = sorted(v for v, level in levels.items() if level in HARDWARE_LEVELS)
    if hardware_facing:
        if domain["hardware_status"] != UNVERIFIED:
            errors.append(f"hardware_status: a packet with hardware assumptions is {UNVERIFIED} until the ledger earns otherwise")
        if not domain["protocol_references"]:
            errors.append("protocol_references: a packet with hardware assumptions must cite its protocol or interface specification")
    else:
        if domain["hardware_status"] != NOT_FACING:
            errors.append(f"hardware_status: a packet with no hardware assumptions is {NOT_FACING}; "
                          "declare the assumptions if hardware behavior matters")
        if hardware_checks:
            errors.append("validation_levels: a packet with no hardware assumptions cannot carry a hardware-rung check: "
                          + ", ".join(hardware_checks))
    if domain["component"] == "hardware_adapter" and not hardware_facing:
        errors.append("component: a hardware adapter without a declared hardware assumption is a contradiction")
    return errors


def evidence_digest(record: dict) -> str:
    return hashlib.sha256(canonical(record).encode("utf-8")).hexdigest()


def validate_hardware_evidence(record: dict) -> dict:
    errors = _schema_errors("hardware_evidence", record)
    if errors:
        raise ValueError("hardware evidence: " + "; ".join(errors))
    canonical(record)
    return record


def evidence_lines(record: dict) -> list[str]:
    """The attestation evidence an operator hands to `acceptance.py attest` for this record."""
    validate_hardware_evidence(record)
    values = {"level": record["level"], "device": record["device_identity"],
              "firmware": record["firmware_version"], "observed_at": record["observed_at"],
              "outcome": record["outcome"], "operator": record["operator"]}
    return [DIGEST_PREFIX + evidence_digest(record)] + [f"{key}={values[key]}" for key in EVIDENCE_KEYS]


def parsed_evidence(lines) -> tuple[str | None, dict]:
    digests, values = [], {}
    for line in lines:
        if line.startswith(DIGEST_PREFIX):
            digests.append(line[len(DIGEST_PREFIX):])
        elif "=" in line:
            key, _, value = line.partition("=")
            if key in EVIDENCE_KEYS:
                values.setdefault(key, value)
    return (digests[0] if len(digests) == 1 else None), values


def validate_attestation(contract: dict, attestation: dict) -> None:
    """Refuse a hardware-rung attestation that does not bind a passing hardware evidence record."""
    level = contract["domain"]["validation_levels"].get(attestation["validation_id"])
    if level not in HARDWARE_LEVELS:
        return  # A machine rung has a command; the controller already refuses attesting over it.
    digest, values = parsed_evidence(attestation["evidence"])
    if digest is None or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError(f"A {level} attestation must carry exactly one {DIGEST_PREFIX}<digest> line "
                         "binding its hardware evidence record")
    missing = [key for key in EVIDENCE_KEYS if not values.get(key, "").strip()]
    if missing:
        raise ValueError(f"A {level} attestation must carry the bound record's " + ", ".join(missing))
    if values["level"] != level:
        raise ValueError(f"Hardware evidence was recorded at {values['level']} but the contract requires {level}")
    if values["outcome"] != "pass":
        raise ValueError("A failed hardware observation is reported through the worker, never attested")
    if values["operator"].strip().casefold() != attestation["operator"].strip().casefold():
        raise ValueError("The attesting operator must be the operator who recorded the hardware evidence")


def _find_record(evidence_dir: Path, digest: str):
    for path in sorted(evidence_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(record, dict) and evidence_digest(record) == digest:
            return path, record
    return None, None


def status(ledger, evidence_dir=None) -> dict:
    """Derive the hardware status a task has earned; a compile or simulation pass never upgrades it."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import acceptance  # noqa: E402 — lazily, so the domain module never imports the controllers eagerly.
    state = acceptance.replay(ledger)[0]
    binding = state["binding"]
    if binding["domain_profile"] != PROFILE:
        raise ValueError(f"Ledger profile is {binding['domain_profile']}, not {PROFILE}")
    domain = state["contract"]["domain"]
    levels = domain["validation_levels"]
    gate = acceptance.deterministic_status(state)
    checks = []
    problems = []
    for check in state["contract"]["validation"]:
        identifier = check["id"]
        entry = {"validation_id": identifier, "level": levels[identifier], "gate": gate[identifier],
                 "machine_runnable": levels[identifier] in MACHINE_LEVELS, "evidence_digest": None,
                 "evidence_verified": None}
        attestation = state["attestations"].get(identifier)
        if attestation is not None:
            entry["evidence_digest"] = parsed_evidence(attestation["evidence"])[0]
            if evidence_dir is not None and levels[identifier] in HARDWARE_LEVELS:
                path, record = _find_record(Path(evidence_dir), entry["evidence_digest"] or "")
                bound = (record is not None and record["task_id"] == binding["task_id"]
                         and record["validation_id"] == identifier and record["level"] == levels[identifier]
                         and record["outcome"] == "pass")
                entry["evidence_verified"] = bound
                entry["evidence_path"] = str(path) if path else None
                if not bound:
                    problems.append(f"{identifier}: no matching hardware evidence record for its attested digest")
        checks.append(entry)
    hardware_ids = [c["validation_id"] for c in checks if not c["machine_runnable"]]
    if domain["hardware_status"] == NOT_FACING:
        earned, reason = NOT_FACING, "The contract declares no hardware assumption."
    elif state["status"] != "ACCEPTED":
        earned, reason = UNVERIFIED, f"Acceptance ledger is {state['status']}, not ACCEPTED."
    elif not hardware_ids:
        earned, reason = UNVERIFIED, "No validation reaches a hardware rung; machine-runnable checks cannot verify hardware."
    elif problems:
        earned, reason = UNVERIFIED, "; ".join(problems)
    elif all(gate[v] == "ATTESTED" for v in hardware_ids):
        earned, reason = VERIFIED, "Accepted with every hardware-rung validation attested against a bound evidence record."
    else:
        earned, reason = UNVERIFIED, "A hardware-rung validation lacks an attestation."
    satisfied = [c["level"] for c in checks if c["gate"] in {"PASSED", "ATTESTED"}]
    highest = max(satisfied, key=LEVELS.index) if satisfied else None
    return {"task_id": binding["task_id"], "revision": binding["revision"], "ledger_status": state["status"],
            "declared_hardware_status": domain["hardware_status"], "earned_hardware_status": earned,
            "reason": reason, "component": domain["component"], "highest_level_satisfied": highest,
            "validations": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate-contract", help="Apply the domain rules to a contract JSON")
    check.add_argument("contract", type=Path)
    evidence = commands.add_parser("hardware-evidence",
                                   help="Validate a hardware evidence record and print the attestation lines it binds")
    evidence.add_argument("record", type=Path)
    evidence.add_argument("--validation-id", help="Refuse a record recorded for a different validation")
    derive = commands.add_parser("status", help="Derive the earned hardware status from an acceptance ledger")
    derive.add_argument("ledger", type=Path)
    derive.add_argument("--evidence-dir", type=Path, help="Verify attested digests against record files here")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-contract":
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import work_packet as wp
            contract = wp.read_json(args.contract)
            errors = wp.validate_contract(contract, PROFILE)
            if errors:
                raise ValueError("; ".join(errors))
            domain = contract["domain"]
            result = {"valid": True, "component": domain["component"],
                      "declared_hardware_status": domain["hardware_status"],
                      "validation_levels": domain["validation_levels"],
                      "note": "Structure only; no check was executed and no hardware behavior is established."}
        elif args.command == "hardware-evidence":
            record = json.loads(args.record.read_text(encoding="utf-8-sig"))
            validate_hardware_evidence(record)
            if args.validation_id and record["validation_id"] != args.validation_id:
                raise ValueError(f"Record is for {record['validation_id']}, not {args.validation_id}")
            result = {"valid": True, "digest": evidence_digest(record), "outcome": record["outcome"],
                      "attest_evidence": evidence_lines(record),
                      "note": "An operator declaration the controller cannot authenticate; the digest binds it."}
        else:
            result = status(args.ledger, args.evidence_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Domain rule refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
