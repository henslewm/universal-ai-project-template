#!/usr/bin/env python3
"""Prepare, review, and explicitly activate a project's bootstrap foundation."""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_bootstrap import (DOMAIN_FIELDS, PROFILES, activation_errors,
                                architecture_fingerprint, document_hashes, validate)


def inactive_approval() -> dict:
    return {"approved": False, "approved_by": None, "approved_at": None, "architecture_fingerprint": None}


def profile_from_template(root: Path) -> str:
    text = (root / "DOMAIN_PROFILE.md").read_text(encoding="utf-8")
    for title, profile in (("North Carolina Family Law", "family-law"), ("North Carolina Civil Rights", "civil-rights-nc"), ("Software + Hardware", "software-hardware"), ("Software and Hardware", "software-hardware")):
        if title in text.splitlines()[0]:
            return profile
    raise ValueError("Select --profile; template profile could not be identified")


def collect_intake(known: dict[str, Any], profile: str) -> dict[str, Any]:
    """Only ask missing fields; agents recover verified sources before calling this."""
    data = copy.deepcopy(known)
    data["domain_profile"] = profile
    print(f"\nProfile: {profile}. Reusing supplied/durable intake; blank answers remain unresolved.")
    for key, question, is_list in (
        ("project_name", "Project name", False), ("objective", "Desired outcome", False),
        ("success_criteria", "Observable definition of done (semicolon-separated)", True),
        ("out_of_scope", "Explicit non-goals (semicolon-separated; state none if none)", True),
        ("constraints", "Time/cost priorities, privacy/security and other constraints (semicolon-separated)", True),
        ("source_locations", "Authoritative source locations (semicolon-separated)", True),
        ("owner", "Project owner", False),
        ("risk_tier", "Risk tier: low, medium, high, critical", False),
        ("sensitivity", "Sensitivity: public, internal, private, restricted", False),
    ):
        if not data.get(key):
            value = input(question + ": ").strip()
            data[key] = [item.strip() for item in value.split(";") if item.strip()] if is_list else value
    proposal = data.setdefault("bootstrap", {})
    domain = proposal.setdefault("domain", {})
    print("\nDomain orientation")
    for key, question in DOMAIN_FIELDS[profile].items():
        if not domain.get(key):
            domain[key] = input(question + ": ").strip()
    # Component architecture is proposed by the architect, not invented by a CLI.
    print("\nIntake recorded. The architect must complete the proposal and present it for review.")
    return data


def new_state(answers: dict, proposal: dict, root: Path) -> dict:
    return {
        "schema_version": "1.0", "domain_profile": answers["domain_profile"], "state": "INTAKE",
        "project": {"name": answers["project_name"], "objective": answers["objective"],
                    "definition_of_done": answers["success_criteria"], "non_goals": answers["out_of_scope"], "constraints": answers["constraints"]},
        "architecture": proposal.get("architecture", {"summary": "", "boundaries": [], "milestones": [], "dependencies": []}),
        "sources": answers["source_locations"], "risks": proposal.get("risks", []),
        "routing": proposal.get("routing", {"policy": ""}), "workflow": proposal.get("workflow", {"policy": ""}),
        "human_gates": proposal.get("human_gates", []), "domain": proposal.get("domain", {}),
        "unresolved": proposal.get("unresolved", []), "configuration": copy.deepcopy(answers),
        "documents": document_hashes(root), "approval": inactive_approval(),
    }


def render_review(data: dict, root: Path | None = None) -> str:
    errors = activation_errors(data)
    lines = ["# Bootstrap Foundation Review", "", f"State: {data['state']} — autonomy is OFF until explicit activation.",
             f"Profile: {data['domain_profile']}", f"Architecture fingerprint: `{architecture_fingerprint(data)}`", ""]
    for title, key in (("Charter", "project"), ("Architecture and milestone dependency graph", "architecture"),
                       ("Sources and evidence map", "sources"), ("Risks", "risks"), ("Routing and cost policy", "routing"),
                       ("GitHub workflow and routine permissions", "workflow"), ("Reserved human actions", "human_gates"),
                       ("Domain orientation", "domain"), ("Unresolved blockers", "unresolved"),
                       ("Project configuration and disclosed defaults", "configuration"), ("Bound document hashes", "documents")):
        lines += [f"## {title}", "", "```json", json.dumps(data[key], indent=2, ensure_ascii=False), "```", ""]
    lines += ["## Readiness", ""] + ([f"- {error}" for error in errors] or ["- Ready for an explicit user decision."])
    if root is not None:
        for name in data["documents"]:
            lines += ["", f"## Bound document: {name}", "", (root / name).read_text(encoding="utf-8")]
    return "\n".join(lines) + "\n"


def write_state(root: Path, data: dict) -> None:
    target = root / "config/bootstrap.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, target)


def update_project_status(root: Path, status: str) -> None:
    path = root / "PROJECT_STATE.md"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^- \*\*Status:\*\*.*$", f"- **Status:** {status}", text, flags=re.M)
    path.write_text(text, encoding="utf-8")


def review(root: Path) -> dict:
    data = json.loads((root / "config/bootstrap.json").read_text(encoding="utf-8"))
    # An explicit review operation is also the revision path; old approval is revoked.
    data["state"] = "REVISION_REQUESTED"
    data["approval"] = inactive_approval()
    write_state(root, data)
    update_project_status(root, "SETUP — autonomy OFF")
    data["configuration"] = json.loads((root / "config/project.json").read_text(encoding="utf-8"))
    data["documents"] = document_hashes(root)
    errors = validate(data, root) + activation_errors(data)
    if errors:
        (root / "BOOTSTRAP_REVIEW.md").write_text(render_review(data, root), encoding="utf-8")
        raise ValueError("Review blocked:\n- " + "\n- ".join(dict.fromkeys(errors)))
    data["state"] = "AWAITING_APPROVAL"
    write_state(root, data)
    (root / "BOOTSTRAP_REVIEW.md").write_text(render_review(data, root), encoding="utf-8")
    return data


def activate(root: Path) -> dict:
    path = root / "config/bootstrap.json"
    original = path.read_bytes()
    data = json.loads(original)
    errors = validate(data, root) + activation_errors(data)
    if errors or data.get("state") != "AWAITING_APPROVAL":
        raise ValueError("Activation requires a valid AWAITING_APPROVAL package. " + "; ".join(errors))
    print(render_review(data, root))
    fingerprint = architecture_fingerprint(data)
    print("Only the user may approve this exact foundation. Entering anything else leaves autonomy OFF.")
    identity = input("Approving user identity: ").strip()
    decision = input(f"Type APPROVE {fingerprint}: ").strip()
    if not identity or decision != f"APPROVE {fingerprint}":
        raise ValueError("Approval not given; autonomy remains OFF")
    if path.read_bytes() != original or validate(data, root):
        raise ValueError("Foundation changed during approval; review it again")
    data["state"] = "ACTIVE"
    data["approval"] = {"approved": True, "approved_by": identity, "approved_at": datetime.now(timezone.utc).isoformat(), "architecture_fingerprint": fingerprint}
    errors = validate(data, root)
    if errors:
        raise ValueError("; ".join(errors))
    write_state(root, data)
    # Keep the review packet as the exact pre-approval proposal. The receipt is in config/bootstrap.json.
    update_project_status(root, "ACTIVE — approved foundation")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["review", "activate"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        data = review(args.root.resolve()) if args.command == "review" else activate(args.root.resolve())
    except (OSError, ValueError, TypeError, KeyError, EOFError) as exc:
        print(f"BOOTSTRAP BLOCKED: {exc}")
        return 1
    print(f"Bootstrap state: {data['state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
