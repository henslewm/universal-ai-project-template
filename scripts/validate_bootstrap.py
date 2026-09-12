#!/usr/bin/env python3
"""Validate bootstrap state and explicit project activation."""
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


def activation_errors(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    project = data.get("project") or {}
    architecture = data.get("architecture") or {}
    required_values = [
        (project.get("name"), "project.name"),
        (project.get("objective"), "project.objective"),
        (project.get("definition_of_done"), "project.definition_of_done"),
        (architecture.get("summary"), "architecture.summary"),
        (architecture.get("boundaries"), "architecture.boundaries"),
        (architecture.get("milestones"), "architecture.milestones"),
        (data.get("sources"), "sources"),
        ((data.get("routing") or {}).get("policy"), "routing.policy"),
        (data.get("human_gates"), "human_gates"),
    ]
    for value, name in required_values:
        if not value:
            errors.append(f"{name} is required before ACTIVE")
    if not isinstance(project.get("non_goals"), list):
        errors.append("project.non_goals must be a list")
    if not isinstance(project.get("constraints"), list):
        errors.append("project.constraints must be a list")
    if not isinstance(architecture.get("dependencies"), list):
        errors.append("architecture.dependencies must be a list")
    return errors


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"schema_version", "domain_profile", "state", "project", "architecture", "sources", "risks", "routing", "human_gates", "approval"}
    missing = sorted(required - data.keys())
    if missing:
        return ["missing required top-level fields: " + ", ".join(missing)]
    if data["schema_version"] != "1.0":
        errors.append("schema_version must be 1.0")
    if data["domain_profile"] not in PROFILES:
        errors.append("invalid domain_profile")
    if data["state"] not in STATES:
        errors.append("invalid bootstrap state")
    if not isinstance(data.get("project"), dict): errors.append("project must be an object")
    if not isinstance(data.get("architecture"), dict): errors.append("architecture must be an object")
    if not isinstance(data.get("sources"), list): errors.append("sources must be a list")
    if not isinstance(data.get("risks"), list): errors.append("risks must be a list")
    if not isinstance(data.get("routing"), dict): errors.append("routing must be an object")
    if not isinstance(data.get("human_gates"), list): errors.append("human_gates must be a list")
    if not isinstance(data.get("approval"), dict): errors.append("approval must be an object")

    approval = data.get("approval") or {}
    if data["state"] == "ACTIVE":
        errors.extend(activation_errors(data))
        if approval.get("approved") is not True:
            errors.append("ACTIVE requires explicit approval.approved=true")
        if not str(approval.get("approved_by") or "").strip():
            errors.append("ACTIVE requires approval.approved_by")
        if not str(approval.get("approved_at") or "").strip():
            errors.append("ACTIVE requires approval.approved_at")
        if approval.get("architecture_fingerprint") != architecture_fingerprint(data):
            errors.append("ACTIVE architecture fingerprint does not match current material architecture")
    elif approval.get("approved") is True:
        errors.append("approval.approved=true is only valid with state ACTIVE")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="config/bootstrap.json")
    parser.add_argument("--fingerprint", action="store_true")
    parser.add_argument("--require-active", action="store_true", help="fail unless the approved state is ACTIVE")
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BOOTSTRAP INVALID: {exc}", file=sys.stderr)
        return 2
    if args.fingerprint:
        print(architecture_fingerprint(data))
        return 0
    errors = validate(data)
    if args.require_active and data.get("state") != "ACTIVE":
        errors.append("project is not ACTIVE")
    if errors:
        print("BOOTSTRAP INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"BOOTSTRAP VALID: state={data['state']} domain={data['domain_profile']}")
    print("PROJECT ACTIVE" if data["state"] == "ACTIVE" else "PROJECT NOT ACTIVE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
