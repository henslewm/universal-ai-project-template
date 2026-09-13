#!/usr/bin/env python3
"""Validate bootstrap state and explicit project activation; no dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

PROFILES = {"software-hardware", "family-law", "civil-rights-nc"}
STATES = {"NEW", "ORIENTING", "INTAKE", "ARCHITECTING", "AWAITING_APPROVAL", "ACTIVE", "NEEDS_INPUT", "BLOCKED", "REVISION_REQUESTED", "ARCHIVED"}
FINGERPRINT_FIELDS = ("schema_version", "domain_profile", "project", "architecture", "sources", "risks", "routing", "workflow", "human_gates", "domain", "unresolved", "configuration", "documents")
BOUND_DOCUMENTS = ("PROJECT_CHARTER.md", "CONNECTOR_PLAN.md", "SKILL_PLAN.md", "DOMAIN_PROFILE.md")
DOMAIN_FIELDS = {
    "software-hardware": {
        "baseline": "Existing repository, software baseline and known-good state, with source references",
        "hardware_identity": "Exact hardware models, board revisions and firmware versions in scope",
        "interfaces": "Protocols and interfaces (bus, wire format, transport, timing) with versions",
        "specifications": "Authoritative manuals, datasheets and specifications, and where they are held",
        "environment": "Host, toolchain and deployment environment for the software",
        "known_paths": "Known-good and known-failing paths or workflows, with how each was observed",
        "validation_resources": "Test fixtures, simulators, loopback and hardware-in-loop resources available",
        "physical_access": "Physical-access constraints: who can operate the hardware, when, and safety limits",
        "architecture_boundaries": "Architecture boundaries whose change requires user approval",
    },
    "family-law": {
        "posture": "Court/case posture, controlling orders and source references",
        "objectives_and_deadlines": "Ranked objectives, disputed issues, pending matters and deadlines",
        "evidence": "Evidence/discovery sources and preservation constraints",
    },
    "civil-rights-nc": {
        "posture": "Forum/jurisdiction and procedural history with source references",
        "defendants_and_theories": "Potential defendants, roles/capacities and alleged rights/theories",
        "evidence_and_remedies": "Evidence sources, limitations/accrual posture and requested remedies",
    },
}


def meaningful(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    candidate = value.strip().lstrip("[(*#- ")
    placeholder = re.match(
        r"(?:tbd|t\.b\.d\.?|todo|fixme|not[ -]specified|"
        r"to[ -]be[ -](?:determined|decided|defined|confirmed|provided|specified))(?=$|[\s:.,;)\]-])",
        candidate, flags=re.I,
    )
    return (not placeholder and candidate.lower().rstrip(" .:)]") not in {"unknown", "unresolved"}
            and not re.search(r"\{\{.*?\}\}", value))


def architecture_fingerprint(data: dict[str, Any]) -> str:
    material = {key: data.get(key) for key in FINGERPRINT_FIELDS}
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def document_hashes(root: Path) -> dict[str, str]:
    # Git normalizes text line endings; approval must survive an ordinary clone.
    return {name: hashlib.sha256((root / name).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            for name in BOUND_DOCUMENTS}


def shape_errors(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return ["bootstrap must be an object"]
    errors: list[str] = []
    required = set(FINGERPRINT_FIELDS) | {"state", "approval"}
    if required - data.keys():
        errors.append("missing required top-level fields: " + ", ".join(sorted(required - data.keys())))
    if data.keys() - required:
        errors.append("unknown top-level fields: " + ", ".join(sorted(data.keys() - required)))
    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if not isinstance(data.get("domain_profile"), str) or data["domain_profile"] not in PROFILES:
        errors.append("invalid domain_profile")
    if not isinstance(data.get("state"), str) or data["state"] not in STATES:
        errors.append("invalid bootstrap state")
    objects = {
        "project": {"name": str, "objective": str, "definition_of_done": list, "non_goals": list, "constraints": list},
        "architecture": {"summary": str, "boundaries": list, "milestones": list, "dependencies": list},
        "routing": {"policy": str}, "workflow": {"policy": str},
        "approval": {"approved": bool, "approved_by": (str, type(None)), "approved_at": (str, type(None)), "architecture_fingerprint": (str, type(None))},
        "domain": {}, "configuration": {}, "documents": {},
    }
    for section, fields in objects.items():
        obj = data.get(section)
        if not isinstance(obj, dict):
            errors.append(f"{section} must be an object")
            continue
        for name, kind in fields.items():
            value = obj.get(name)
            if name not in obj or not isinstance(value, kind):
                errors.append(f"{section}.{name} has a missing or invalid type")
            elif kind is list and any(not meaningful(item) for item in value):
                errors.append(f"{section}.{name} items must be nonblank strings without placeholders")
    for name in ("sources", "risks", "human_gates", "unresolved"):
        value = data.get(name)
        if not isinstance(value, list) or any(not meaningful(item) for item in value):
            errors.append(f"{name} must be a list of nonblank strings without placeholders")
    return errors


def activation_errors(data: dict[str, Any]) -> list[str]:
    errors = shape_errors(data)
    if errors:
        return errors
    for section, fields in {"project": ("name", "objective", "definition_of_done"), "architecture": ("summary", "boundaries", "milestones"), "routing": ("policy",), "workflow": ("policy",)}.items():
        for field in fields:
            value = data[section][field]
            if not value or (isinstance(value, str) and not meaningful(value)):
                errors.append(f"{section}.{field} is required before review/ACTIVE")
    for field in ("sources", "risks", "human_gates"):
        if not data[field]:
            errors.append(f"{field} is required before review/ACTIVE")
    for field in DOMAIN_FIELDS[data["domain_profile"]]:
        if not meaningful(data["domain"].get(field)):
            errors.append(f"domain.{field} is required before review/ACTIVE")
    if data["unresolved"]:
        errors.append("unresolved architecture blockers must be resolved before review/ACTIVE")
    # Dependencies use milestone names, in prerequisite -> dependent order.
    milestones = data["architecture"]["milestones"]
    if len(set(milestones)) != len(milestones):
        errors.append("architecture.milestones must be unique")
    edges = {name: set() for name in milestones}
    for dependency in data["architecture"]["dependencies"]:
        parts = [part.strip() for part in dependency.split("->")]
        if len(parts) != 2 or any(part not in edges for part in parts):
            errors.append("dependencies must use existing milestone names: prerequisite -> dependent")
        else:
            edges[parts[0]].add(parts[1])
    pending = set(edges)
    while pending:
        ready = {name for name in pending if not any(name in edges[parent] for parent in pending)}
        if not ready:
            errors.append("milestone dependencies contain a cycle")
            break
        pending -= ready
    return errors


def validate(data: Any, root: Path | None = None) -> list[str]:
    errors = shape_errors(data)
    if errors:
        return errors
    if data["state"] in {"AWAITING_APPROVAL", "ACTIVE"}:
        errors.extend(activation_errors(data))
    approval = data["approval"]
    if data["state"] == "ACTIVE":
        if approval["approved"] is not True:
            errors.append("ACTIVE requires explicit approval.approved=true")
        if not meaningful(approval["approved_by"]):
            errors.append("ACTIVE requires approval.approved_by")
        try:
            timestamp = datetime.fromisoformat(approval["approved_at"].replace("Z", "+00:00"))
            if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
                raise ValueError("not UTC")
        except (AttributeError, TypeError, ValueError):
            errors.append("ACTIVE requires approval.approved_at as a UTC date-time")
        if approval["architecture_fingerprint"] != architecture_fingerprint(data):
            errors.append("ACTIVE architecture fingerprint does not match current material architecture")
    elif any(value is not None for key, value in approval.items() if key != "approved") or approval["approved"] is not False:
        errors.append("inactive states require approval false and null approval metadata")
    if root is not None:
        try:
            config = json.loads((root / "config/project.json").read_text(encoding="utf-8"))
            if config != data["configuration"]:
                errors.append("config/project.json differs from approval-bound configuration; revise and review")
            if data["domain_profile"] != config.get("domain_profile"):
                errors.append("domain_profile differs from project configuration")
            for field, config_field in {"name": "project_name", "objective": "objective", "definition_of_done": "success_criteria", "non_goals": "out_of_scope", "constraints": "constraints"}.items():
                if data["project"][field] != config.get(config_field):
                    errors.append(f"project.{field} differs from config/project.json")
            if data["sources"] != config.get("source_locations"):
                errors.append("sources differ from config/project.json")
            if document_hashes(root) != data["documents"]:
                errors.append("approval-bound documents changed; revise and review")
        except (OSError, ValueError, AttributeError) as exc:
            errors.append(f"cannot verify approval-bound project files: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="config/bootstrap.json")
    parser.add_argument("--fingerprint", action="store_true")
    parser.add_argument("--require-active", action="store_true")
    args = parser.parse_args()
    path = Path(args.path).resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"BOOTSTRAP INVALID: {exc}")
        return 2
    root = path.parent.parent if path.parent.name == "config" and path.name == "bootstrap.json" else None
    if args.require_active and root is None:
        print("BOOTSTRAP INVALID: --require-active requires the project's config/bootstrap.json")
        return 1
    errors = validate(data, root)
    if args.require_active and (not isinstance(data, dict) or data.get("state") != "ACTIVE"):
        errors.append("project is not ACTIVE")
    if errors:
        print("BOOTSTRAP INVALID\n" + "\n".join(f"- {error}" for error in errors))
        return 1
    if args.fingerprint:
        print(architecture_fingerprint(data))
    else:
        print(f"BOOTSTRAP VALID: state={data['state']} domain={data['domain_profile']}")
        print("PROJECT ACTIVE" if data["state"] == "ACTIVE" else "PROJECT NOT ACTIVE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
