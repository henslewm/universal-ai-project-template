#!/usr/bin/env python3
"""Validate bootstrap state and explicit autonomy activation.

Standard-library only so the gate can run before project dependencies are installed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROFILES = {"software-hardware", "family-law", "civil-rights-nc"}
STATES = {"NEW", "ORIENTING", "INTAKE", "ARCHITECTING", "AWAITING_APPROVAL", "ACTIVE", "NEEDS_INPUT", "BLOCKED", "REVISION_REQUESTED", "ARCHIVED"}
FINGERPRINT_FIELDS = ("domain_profile", "project", "architecture", "sources", "risks", "routing", "human_gates")


def architecture_fingerprint(data: dict[str, Any]) -> str:
    material = {key: data.get(key) for key in FINGERPRINT_FIELDS}
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"schema_version", "domain_profile", "state", "project", "architecture", "sources", "risks", "routing", "human_gates", "approval"}
    missing = sorted(required - data.keys())
    if missing:
        errors.append("missing required top-level fields: " + ", ".join(missing))
        return errors
    if data["schema_version"] != "1.0":
        errors.append("schema_version must be 1.0")
    if data["domain_profile"] not in PROFILES:
        errors.append("domain_profile must be one of: " + ", ".join(sorted(PROFILES)))
    if data["state"] not in STATES:
        errors.append("invalid bootstrap state")

    project = data.get("project") or {}
    for field in ("name", "objective"):
        if not str(project.get(field, "")).strip():
            errors.append(f"project.{field} is required")
    if not project.get("definition_of_done"):
        errors.append("project.definition_of_done must contain at least one observable criterion")
    for field in ("non_goals", "constraints"):
        if field not in project or not isinstance(project[field], list):
            errors.append(f"project.{field} must be a list")

    architecture = data.get("architecture") or {}
    if not str(architecture.get("summary", "")).strip():
        errors.append("architecture.summary is required")
    for field in ("boundaries", "milestones"):
        if not architecture.get(field):
            errors.append(f"architecture.{field} must contain at least one item")
    if "dependencies" not in architecture or not isinstance(architecture["dependencies"], list):
        errors.append("architecture.dependencies must be a list")
    if not data.get("sources"):
        errors.append("at least one authoritative source/evidence location is required")
    if not str((data.get("routing") or {}).get("policy", "")).strip():
        errors.append("routing.policy is required")
    if not data.get("human_gates"):
        errors.append("human_gates must contain at least one reserved/intervention condition")

    approval = data.get("approval") or {}
    if data["state"] == "ACTIVE":
        if approval.get("approved") is not True:
            errors.append("ACTIVE requires explicit approval.approved=true")
        if not str(approval.get("approved_by") or "").strip():
            errors.append("ACTIVE requires approval.approved_by")
        if not str(approval.get("approved_at") or "").strip():
            errors.append("ACTIVE requires approval.approved_at")
        expected = architecture_fingerprint(data)
        if approval.get("architecture_fingerprint") != expected:
            errors.append("ACTIVE architecture fingerprint does not match the approved architecture")
    elif approval.get("approved") is True:
        errors.append("approval.approved=true is only valid when state is ACTIVE")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate bootstrap/autonomy activation state")
    parser.add_argument("path", nargs="?", default="config/bootstrap.json")
    parser.add_argument("--fingerprint", action="store_true", help="print the current material architecture fingerprint")
    args = parser.parse_args()
    path = Path(args.path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BOOTSTRAP INVALID: {exc}", file=sys.stderr)
        return 2
    if args.fingerprint:
        print(architecture_fingerprint(data))
        return 0
    errors = validate(data)
    if errors:
        print("BOOTSTRAP INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"BOOTSTRAP VALID: state={data['state']} domain={data['domain_profile']}")
    if data["state"] == "ACTIVE":
        print("AUTONOMY ACTIVATED: explicit approval and architecture fingerprint verified")
    else:
        print("AUTONOMY NOT ACTIVE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
