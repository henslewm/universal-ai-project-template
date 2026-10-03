#!/usr/bin/env python3
"""Prepare, review, and explicitly activate a project's bootstrap foundation."""
from __future__ import annotations

if __name__ == "__main__":  # A Ctrl+C while the imports below load also exits 130 (#31).
    import cli_exit
    cli_exit.guard_startup()

import argparse
import copy
import json
import os
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cli_exit
from validate_bootstrap import (DOMAIN_FIELDS, PROFILES, activation_errors, apply_no_hardware,
                                HARDWARE_ONLY_FIELDS, architecture_fingerprint, document_hashes, validate)


def inactive_approval() -> dict:
    return {"approved": False, "approved_by": None, "approved_at": None, "architecture_fingerprint": None}


def profile_from_template(root: Path) -> str:
    text = (root / "DOMAIN_PROFILE.md").read_text(encoding="utf-8")
    for title, profile in (("Software + Hardware", "software-hardware"), ("Software and Hardware", "software-hardware")):
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
    # Asked only while a hardware-only field is still unanswered, so a supplied intake is never re-asked.
    if "hardware_in_scope" not in data and any(not domain.get(key) for key in HARDWARE_ONLY_FIELDS):
        data["hardware_in_scope"] = input("Does the project involve hardware? [Y/n]: ").strip().lower() not in {"n", "no"}
    if data.get("hardware_in_scope") is False:
        apply_no_hardware(domain)
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


BANNER_WIDTH = 72


def approval_banner(data: dict, fingerprint: str) -> str:
    """Plain-ASCII frame shown directly above the approval prompts; presentation only."""
    def wrapped(text: str, indent: str = " ", hanging: str = " ") -> list[str]:
        return textwrap.wrap(text, BANNER_WIDTH - 1, initial_indent=indent, subsequent_indent=hanging,
                             break_long_words=False, break_on_hyphens=False)

    def field(label: str, value: str) -> list[str]:
        # Package values are user-authored. Escape everything outside printable ASCII, so nothing reaches the
        # terminal that it could act on or render wider than one column; the review above shows the original text.
        visible = "".join(ch if ch.isascii() and ch.isprintable() else ch.encode("unicode_escape").decode("ascii")
                          for ch in value)
        return textwrap.wrap(visible, BANNER_WIDTH - 15, initial_indent=f" {label:<13}", subsequent_indent=" " * 14,
                             break_on_hyphens=False) or [f" {label}"]

    heavy, light = "=" * BANNER_WIDTH, "-" * BANNER_WIDTH
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    lines = [heavy, " FOUNDATION APPROVAL", heavy]
    lines += field("State:", f"{data.get('state')} (autonomy is OFF)")
    lines += field("Profile:", str(data.get("domain_profile")))
    lines += field("Project:", str(project.get("name")))
    lines += [" Package fingerprint (SHA-256):", "   " + fingerprint, light, " If you approve this exact package:"]
    for item in ("State becomes ACTIVE and autonomy turns ON for this foundation.",
                 "Routine work within the approved scope may proceed without approval for each step.",
                 "Reserved human actions, material architecture changes and consequential external actions "
                 "still need explicit authority. Tool and connector permissions do not expand.",
                 "Any later change to the fingerprinted foundation invalidates this approval."):
        lines += wrapped(item, "  - ", "    ")
    lines += [light, " To approve, enter your identity, then type exactly:", "   APPROVE " + fingerprint]
    lines += wrapped("Only the user may approve this exact foundation. Anything else, including a blank line, "
                     "end of input or Ctrl+C, refuses approval and leaves autonomy OFF.")
    lines.append(heavy)
    return "\n".join(lines)


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
    print(approval_banner(data, fingerprint))
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
    raise SystemExit(cli_exit.run(main))
