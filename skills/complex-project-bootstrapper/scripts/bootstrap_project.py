#!/usr/bin/env python3
"""Create a tailored project repository from the universal AI project template."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

EXCLUDE_NAMES = {
    ".git", "dist", "build", "__pycache__", ".pytest_cache",
    "universal-ai-project-template.zip", "skill.zip"
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-._")
    return slug or "ai-project"


def split_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,;\n]", value) if item.strip()]


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or default


def normalize_answers(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("project_name") or raw.get("name") or "AI Project").strip()
    raw["project_name"] = name
    raw["project_slug"] = slugify(str(raw.get("project_slug") or name))
    raw["objective"] = str(raw.get("objective") or "Define and complete the project outcome.").strip()
    raw["problem_statement"] = str(raw.get("problem_statement") or raw["objective"]).strip()

    list_fields = [
        "success_criteria", "deliverables", "ai_clients", "connectors", "source_locations",
        "repeatable_workflows", "output_formats", "constraints", "out_of_scope"
    ]
    for field in list_fields:
        value = raw.get(field, [])
        if isinstance(value, str):
            value = split_list(value)
        raw[field] = [str(item).strip() for item in value if str(item).strip()]

    raw["success_criteria"] = raw["success_criteria"] or ["The required deliverables satisfy the project charter and validation passes."]
    raw["deliverables"] = raw["deliverables"] or ["Project-specific analysis or implementation", "Current handoff and state records"]
    raw["ai_clients"] = raw["ai_clients"] or ["chatgpt", "codex", "claude", "claude-code"]
    raw["connectors"] = raw["connectors"] or ["github", "web"]
    raw["output_formats"] = raw["output_formats"] or ["markdown"]
    raw["domain"] = str(raw.get("domain") or "other").strip().lower()
    raw["risk_tier"] = str(raw.get("risk_tier") or "medium").strip().lower()
    raw["sensitivity"] = str(raw.get("sensitivity") or "private").strip().lower()
    raw["target_date"] = str(raw.get("target_date") or "").strip()
    raw["jurisdiction_or_version"] = str(raw.get("jurisdiction_or_version") or "").strip()
    raw["owner"] = str(raw.get("owner") or os.environ.get("USER") or "Project owner").strip()
    raw["connector_permissions"] = dict(raw.get("connector_permissions") or {})
    for connector in raw["connectors"]:
        raw["connector_permissions"].setdefault(connector, "read")
    if "github" in raw["connectors"]:
        raw["connector_permissions"].setdefault("github", "read-and-project-write")
    raw["template_mode"] = False
    raw["template_version"] = "1.0.0"
    raw["created"] = date.today().isoformat()
    return raw


def interactive_answers() -> dict[str, Any]:
    print("\nAnswer the minimum project intake. Comma-separate multiple items.\n")
    name = ask("1. Project name")
    objective = ask("   One-sentence desired outcome")
    success = ask("2. Observable definition of done")
    deliverables = ask("   Required deliverables")
    target = ask("   Target date or urgency", "")
    domain = ask("3. Domain", "other")
    jurisdiction = ask("   Jurisdiction, product version, or governing standard", "")
    risk = ask("   Risk tier: low, medium, high, critical", "medium")
    sensitivity = ask("   Sensitivity: public, internal, private, restricted", "private")
    sources = ask("4. Authoritative source locations", "")
    clients = ask("5. AI clients", "chatgpt,codex,claude,claude-code")
    connectors = ask("6. Connectors", "github,web")
    workflows = ask("7. Repeated workflows that may deserve skills", "")
    formats = ask("   Required output formats", "markdown")
    constraints = ask("8. Non-negotiable constraints or approval gates", "")
    out_of_scope = ask("   Explicitly out of scope", "")
    owner = ask("   Project owner", os.environ.get("USER", "Project owner"))
    return normalize_answers({
        "project_name": name,
        "objective": objective,
        "problem_statement": objective,
        "success_criteria": split_list(success),
        "deliverables": split_list(deliverables),
        "target_date": target,
        "domain": domain,
        "jurisdiction_or_version": jurisdiction,
        "risk_tier": risk,
        "sensitivity": sensitivity,
        "source_locations": split_list(sources),
        "ai_clients": split_list(clients),
        "connectors": split_list(connectors),
        "repeatable_workflows": split_list(workflows),
        "output_formats": split_list(formats),
        "constraints": split_list(constraints),
        "out_of_scope": split_list(out_of_scope),
        "owner": owner,
    })


def locate_template_root(explicit: str | None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not (root / ".ai-project-template").exists():
            raise SystemExit(f"Not a recognized template root: {root}")
        return root

    script = Path(__file__).resolve()

    # A standalone packaged skill carries its own template asset.
    skill_candidate = script.parent.parent / "assets" / "project-template"
    if (skill_candidate / ".ai-project-template").exists():
        return skill_candidate

    # A project-scoped native skill lives several levels below the repository
    # root, so walk upward until the template marker is found. This also covers
    # the root-level scripts/bootstrap_project.py entrypoint.
    for candidate in script.parents:
        if (candidate / ".ai-project-template").exists():
            return candidate

    raise SystemExit("Could not locate the project template. Use --template-root.")


def ignore_copy(directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in EXCLUDE_NAMES}
    path = Path(directory)
    # Prevent recursive template assets when copying from a packaged skill or repo.
    if path.name == "assets" and "project-template" in names:
        ignored.add("project-template")
    return ignored


def copy_template(source: Path, destination: Path) -> None:
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit(f"Destination exists and is not empty: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignore_copy)
    git_dir = destination / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)


def bullets(items: list[str], empty: str = "- None specified.") -> str:
    return "\n".join(f"- {item}" for item in items) if items else empty


def connector_rows(answers: dict[str, Any]) -> str:
    descriptions = {
        "github": ("Repository state, issues, history, and project files", "Project repo", "No force push; project writes only when requested"),
        "web": ("Current public facts and primary authority", "Public sources", "Read only"),
        "google-drive": ("Authoritative documents and folders", "Named or relevant Drive scope", "Read by default"),
        "gmail": ("Communications, evidence, and open loops", "Relevant senders/date range/terms", "No send without explicit request"),
        "google-calendar": ("Deadlines, hearings, meetings, and availability", "Relevant calendars/date window", "No create/update without explicit request"),
        "google-contacts": ("Identity and recipient resolution", "Named people/organizations", "Read only"),
        "midpage": ("Case law and legal authority", "Relevant jurisdiction and issue", "Read only"),
    }
    rows = []
    for connector in answers["connectors"]:
        use, scope, policy = descriptions.get(connector, ("Project-specific external data", "Narrow task scope", "Read by default"))
        permission = answers["connector_permissions"].get(connector, "read")
        rows.append(f"| {connector} | {use} | {scope} | {permission}; {policy} |")
    return "\n".join(rows)


def skill_recommendations(answers: dict[str, Any]) -> list[tuple[str, str, str]]:
    recs: list[tuple[str, str, str]] = [
        ("complex-project-bootstrapper", "Included custom skill", "Initialize or retrofit this project consistently")
    ]
    formats = {item.lower() for item in answers["output_formats"]}
    for key, skill in [
        ("pdf", "PDF processing"), ("docx", "DOCX document"), ("word", "DOCX document"),
        ("xlsx", "Spreadsheet"), ("spreadsheet", "Spreadsheet"),
        ("pptx", "Presentation"), ("slides", "Presentation"),
        ("image", "Image generation/editing")
    ]:
        if any(key in fmt for fmt in formats):
            recs.append((skill, "Existing trusted skill", f"Required output includes {key}"))
    if answers["risk_tier"] in {"high", "critical"} or answers["domain"] in {"legal", "research", "science", "scientific"}:
        recs.append(("source-evidence-ledger", "Custom candidate", "High-risk/source-intensive work benefits from a fixed provenance workflow"))
    for workflow in answers["repeatable_workflows"]:
        recs.append((slugify(workflow)[:50], "Custom candidate", f"Repeated workflow: {workflow}"))
    seen = set()
    unique = []
    for item in recs:
        if item[0] not in seen:
            seen.add(item[0])
            unique.append(item)
    return unique


def write_project_files(dest: Path, answers: dict[str, Any]) -> None:
    (dest / "config/project.json").write_text(json.dumps(answers, indent=2) + "\n", encoding="utf-8")
    today = date.today().isoformat()
    target = answers["target_date"] or "Not fixed"
    jurisdiction = answers["jurisdiction_or_version"] or "Not specified"

    charter = f"""# Project Charter

## Project

- **Name:** {answers['project_name']}
- **Slug:** {answers['project_slug']}
- **Domain:** {answers['domain']}
- **Jurisdiction / version:** {jurisdiction}
- **Risk tier:** {answers['risk_tier']}
- **Sensitivity:** {answers['sensitivity']}
- **Owner:** {answers['owner']}
- **Target date:** {target}

## Problem statement

{answers['problem_statement']}

## Desired outcome

{answers['objective']}

## Definition of done

{bullets(answers['success_criteria'])}

## Required deliverables

{bullets(answers['deliverables'])}

## Scope

### In scope

- Work necessary to achieve the desired outcome and deliverables.

### Out of scope

{bullets(answers['out_of_scope'])}

## Constraints and approval gates

{bullets(answers['constraints'])}

- Preserve authoritative source material and provenance.
- Keep secrets and unapproved restricted material out of Git.
- Require explicit approval for consequential external writes.

## Decision rights

- The user owns goals, scope, legal/business choices, and consequential external actions.
- AI tools may research, analyze, draft, organize, validate, and make reversible repository changes within granted permissions.
- Material adverse facts, conflicts, and high-impact assumptions must be surfaced.
"""
    (dest / "PROJECT_CHARTER.md").write_text(charter, encoding="utf-8")

    state = f"""# Project State

- **Status:** Active — initialized
- **Last verified:** {today}
- **Current phase:** Foundation
- **Active branch:** main
- **Primary objective:** {answers['objective']}

## Current verified state

- Project repository initialized from the universal template.
- Charter, connector plan, skill plan, and platform adapters were tailored from intake.
- Domain: {answers['domain']}; risk: {answers['risk_tier']}; sensitivity: {answers['sensitivity']}.

## Work completed

- Project intake normalized and written to `config/project.json`.
- Native instructions retained for the selected AI clients.
- Initial connector and skill recommendations recorded.

## Current focus

- Confirm authoritative source access.
- Index the first controlling sources.
- Convert the highest-priority deliverable into a bounded task.

## Next three actions

1. Review and approve `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, and `SKILL_PLAN.md`.
2. Add or connect the authoritative sources listed in `SOURCE_INDEX.md`.
3. Create the first task with observable success criteria and begin execution.
"""
    (dest / "PROJECT_STATE.md").write_text(state, encoding="utf-8")

    (dest / "OPEN_LOOPS.md").write_text(f"""# Open Loops

| ID | Priority | Open item | Owner | Next action | Dependency | Due | Status |
|---|---|---|---|---|---|---|---|
| OL-001 | High | Approve project foundation | {answers['owner']} | Review charter, connectors, and skills | Intake | {target} | Open |
| OL-002 | High | Establish authoritative source access | {answers['owner']} | Connect or index the first controlling sources | Access permissions | — | Open |
| OL-003 | Medium | Define first bounded execution task | {answers['owner']} | Create task from highest-priority deliverable | Approved charter | — | Open |
""", encoding="utf-8")

    (dest / "FACTS_AND_ASSUMPTIONS.md").write_text(f"""# Facts, Assumptions, Allegations, and Unknowns

## Verified facts

- Project name: {answers['project_name']}.
- Desired outcome: {answers['objective']}.
- Intake was recorded on {today}.

## Working assumptions

- The repository will remain private unless the user changes visibility.
- Connector access is read-only except where `CONNECTOR_PLAN.md` explicitly states otherwise.

## Allegations or disputed claims

- None recorded during project initialization.

## Unknowns requiring resolution

- Which source controls each material disputed or version-sensitive fact.
- Whether all listed external systems are accessible in each selected AI client.
- Which repeated workflows justify custom skills after first use.
""", encoding="utf-8")

    sources = [
        "| SRC-001 | Repository | Project repository | This repository | Project control plane | Private | Current | " + today + " | Initial commit | Canonical project state |"
    ]
    for idx, source in enumerate(answers["source_locations"], start=2):
        sources.append(f"| SRC-{idx:03d} | External source | {source} | {source} | To be assessed | Restricted to approved access | — | Not yet verified | — | Confirm authority and scope |")
    (dest / "SOURCE_INDEX.md").write_text("""# Source Index

| Source ID | Type | Title / description | Location | Authority | Access | Date range | Last verified | Hash / version | Notes |
|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(sources) + "\n", encoding="utf-8")

    risk_rows = [
        "| R-001 | Chat or model state diverges from repository | Medium | High | Conflicting summaries | Startup reads and closeout updates | Project owner | Open |",
        "| R-002 | Sensitive information enters Git without approval | Low | Critical | Unexpected files or secrets in status | Private repo, ignore rules, source index, review | Project owner | Open |",
        "| R-003 | Connector or agent exceeds intended authority | Low | High | Unexpected write prompt/action | Read-only defaults and explicit approval | Project owner | Open |",
    ]
    if answers["risk_tier"] in {"high", "critical"}:
        risk_rows.append("| R-004 | High-impact conclusion or action is based on incomplete/adverse evidence | Medium | Critical | Missing controlling source or counterauthority | Independent review and source ledger | Project owner | Open |")
    (dest / "RISK_REGISTER.md").write_text("""# Risk Register

| Risk ID | Risk | Likelihood | Impact | Early warning | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|
""" + "\n".join(risk_rows) + "\n", encoding="utf-8")

    (dest / "CONNECTOR_PLAN.md").write_text(f"""# Connector Plan

## Selected connectors

| Connector / source | Use | Scope | Permission posture |
|---|---|---|---|
{connector_rows(answers)}

## Rules

- Use only connectors selected above unless the user approves an addition.
- Prefer the narrowest useful search or folder/date scope.
- Record material sources in `SOURCE_INDEX.md`.
- Availability is not authority for a consequential write.
- Sends, filings, publishing, purchases, deletions, permission changes, and other external modifications require explicit current instruction.
""", encoding="utf-8")

    recs = skill_recommendations(answers)
    skill_rows = "\n".join(f"| {name} | {kind} | {reason} | Review / enable when needed |" for name, kind, reason in recs)
    (dest / "SKILL_PLAN.md").write_text(f"""# Skill Plan

## Selected and candidate skills

| Skill | Type | Reason | Status |
|---|---|---|---|
{skill_rows}

## Decision rule

Enable an existing trusted skill when it fits the workflow. Create a custom skill only when inputs, outputs, connector needs, and a repeatable procedure are concrete. Review source and permissions before installing a public skill.
""", encoding="utf-8")

    (dest / "HANDOFF_CURRENT.md").write_text(f"""# Current Handoff

- **Prepared:** {today}
- **From:** Project bootstrap workflow
- **To:** First execution session
- **Branch / verified commit:** main / commit pending until Git initialization completes

## Active objective

{answers['objective']}

## Completed and verified

- Project-specific charter, state, connector plan, skill plan, risks, source index, and platform adapters were generated from intake.
- Repository validation must pass before execution begins.

## Sources relied upon

- User-provided intake in `config/project.json`.
- Universal template instructions and platform adapters.

## Unresolved risks, contradictions, or unknowns

- Authoritative sources have not yet been verified.
- Connector availability may vary by client.
- Custom-skill candidates require real workflow examples before creation.

## Exact next action

Review the charter and connect/index the first controlling sources, then define the first bounded task.

## Do not assume

- Do not assume external connectors are authenticated.
- Do not assume any GitHub push, external write, or source verification occurred unless separately confirmed.
""", encoding="utf-8")

    (dest / "CHANGELOG.md").write_text(f"""# Changelog

## {today} — Project initialized

- Generated `{answers['project_name']}` from universal template v1.0.0.
- Tailored charter, state, connectors, skills, risks, sources, and handoff.
""", encoding="utf-8")


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)


def initialize_git(dest: Path) -> str:
    if not shutil.which("git"):
        return "Git not installed; repository not initialized."
    run(["git", "init", "-b", "main"], dest)
    run(["git", "add", "."], dest)
    result = run(["git", "commit", "-m", "chore: initialize AI project workspace"], dest, check=False)
    if result.returncode != 0:
        # Set local-only identity if no global identity exists, then retry.
        run(["git", "config", "user.name", "AI Project Bootstrapper"], dest)
        run(["git", "config", "user.email", "bootstrapper@local.invalid"], dest)
        result = run(["git", "commit", "-m", "chore: initialize AI project workspace"], dest, check=False)
    if result.returncode != 0:
        return "Git initialized but initial commit failed: " + (result.stderr.strip() or result.stdout.strip())
    sha = run(["git", "rev-parse", "HEAD"], dest).stdout.strip()
    handoff = dest / "HANDOFF_CURRENT.md"
    text = handoff.read_text(encoding="utf-8").replace(
        "main / commit pending until Git initialization completes", f"main / {sha}"
    )
    handoff.write_text(text, encoding="utf-8")
    run(["git", "add", "HANDOFF_CURRENT.md"], dest)
    run(["git", "commit", "-m", "docs: record verified initial commit"], dest, check=False)
    final_sha = run(["git", "rev-parse", "HEAD"], dest).stdout.strip()
    return f"Git initialized and committed at {final_sha}."


def publish_github(dest: Path, owner: str | None, visibility: str) -> str:
    if not shutil.which("gh"):
        return "GitHub CLI not installed; publish manually with the command shown below."
    auth = run(["gh", "auth", "status"], dest, check=False)
    if auth.returncode != 0:
        return "GitHub CLI is not authenticated; run `gh auth login`."
    slug = json.loads((dest / "config/project.json").read_text(encoding="utf-8"))["project_slug"]
    repo_name = f"{owner}/{slug}" if owner else slug
    cmd = ["gh", "repo", "create", repo_name, f"--{visibility}", "--source", ".", "--remote", "origin", "--push"]
    result = run(cmd, dest, check=False)
    if result.returncode != 0:
        return "GitHub publish failed: " + (result.stderr.strip() or result.stdout.strip())
    return "GitHub repository created and pushed: " + (result.stdout.strip() or repo_name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interactive", action="store_true", help="Ask the concise intake questions")
    parser.add_argument("--answers", help="Path to JSON answers")
    parser.add_argument("--destination", required=True, help="New project directory")
    parser.add_argument("--template-root", help="Explicit template root")
    parser.add_argument("--no-git", action="store_true", help="Do not initialize Git")
    parser.add_argument("--github", action="store_true", help="Create and push a GitHub repository with gh")
    parser.add_argument("--github-owner", help="GitHub owner; defaults to authenticated user")
    parser.add_argument("--visibility", choices=["private", "public", "internal"], default="private")
    args = parser.parse_args()

    if args.answers:
        raw = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        answers = normalize_answers(raw)
    elif args.interactive:
        answers = interactive_answers()
    else:
        parser.error("Use --interactive or --answers <file>.")

    source = locate_template_root(args.template_root)
    destination = Path(args.destination).expanduser().resolve()
    copy_template(source, destination)
    write_project_files(destination, answers)

    validator = destination / "scripts" / "validate_project.py"
    validation = run([sys.executable, str(validator)], destination, check=False)
    if validation.returncode != 0:
        print(validation.stdout)
        print(validation.stderr, file=sys.stderr)
        raise SystemExit("Generated project failed validation.")

    git_status = "Git initialization skipped."
    if not args.no_git:
        git_status = initialize_git(destination)

    publish_status = "GitHub publish not requested."
    if args.github:
        publish_status = publish_github(destination, args.github_owner, args.visibility)

    print("\nProject created successfully")
    print(f"Path: {destination}")
    print(f"Name: {answers['project_name']}")
    print(f"Connectors: {', '.join(answers['connectors'])}")
    print(f"AI clients: {', '.join(answers['ai_clients'])}")
    print("Validation: PASS")
    print(git_status)
    print(publish_status)
    print("\nNext steps:")
    print("1. Review PROJECT_CHARTER.md, CONNECTOR_PLAN.md, and SKILL_PLAN.md.")
    print("2. Connect/index the first authoritative sources.")
    print("3. Create the first bounded task and begin work.")
    if not args.github:
        owner = args.github_owner or "OWNER"
        print("\nPublish command:")
        print(f"gh repo create {owner}/{answers['project_slug']} --{args.visibility} --source {destination} --remote origin --push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
