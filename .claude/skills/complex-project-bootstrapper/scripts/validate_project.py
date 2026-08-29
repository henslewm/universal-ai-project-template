#!/usr/bin/env python3
"""Validate the universal AI project repository structure and configuration."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = [
    "MASTER_INSTRUCTIONS.md", "MASTER_CHATGPT.md", "MASTER_CODEX.md",
    "MASTER_CLAUDE.md", "MASTER_CLAUDE_CODE.md", "AGENTS.md", "CLAUDE.md",
    "PROJECT_CHARTER.md", "PROJECT_STATE.md", "OPEN_LOOPS.md", "DECISIONS.md",
    "FACTS_AND_ASSUMPTIONS.md", "SOURCE_INDEX.md", "RISK_REGISTER.md",
    "HANDOFF_CURRENT.md", "CONNECTOR_PLAN.md", "SKILL_PLAN.md",
    "config/project.json", ".chatgpt/PROJECT_INSTRUCTIONS.md",
    ".claude-web/PROJECT_INSTRUCTIONS.md", ".codex/config.toml",
    ".claude/settings.json", "prompts/BOOTSTRAP_NEW_PROJECT.md",
    "skills/complex-project-bootstrapper/SKILL.md",
    ".agents/skills/complex-project-bootstrapper/SKILL.md",
    ".claude/skills/complex-project-bootstrapper/SKILL.md",
]

PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}")
SECRET_NAMES = re.compile(r"(^|/)(\.env(\..*)?|.*\.(pem|key|p12|pfx)|credentials.*\.json|service-account.*\.json)$", re.I)


def error(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED:
        path = ROOT / rel
        if not path.exists():
            error(errors, f"Missing required path: {rel}")
        elif path.is_file() and path.stat().st_size == 0:
            error(errors, f"Required file is empty: {rel}")

    project_path = ROOT / "config/project.json"
    project: dict = {}
    if project_path.exists():
        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
        except Exception as exc:
            error(errors, f"Invalid config/project.json: {exc}")

    if project:
        for key in ["template_mode", "project_name", "project_slug", "objective", "success_criteria", "deliverables", "risk_tier", "sensitivity", "ai_clients", "connectors"]:
            if key not in project:
                error(errors, f"config/project.json missing key: {key}")
        if not bool(project.get("template_mode", True)):
            slug = str(project.get("project_slug", ""))
            if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", slug):
                error(errors, f"Invalid project_slug: {slug!r}")
            if project.get("risk_tier") not in {"low", "medium", "high", "critical"}:
                error(errors, "risk_tier must be low, medium, high, or critical")
            if project.get("sensitivity") not in {"public", "internal", "private", "restricted"}:
                error(errors, "sensitivity must be public, internal, private, or restricted")

    try:
        json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    except Exception as exc:
        error(errors, f"Invalid .claude/settings.json: {exc}")

    try:
        tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
    except Exception as exc:
        error(errors, f"Invalid .codex/config.toml: {exc}")

    claude_text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8") if (ROOT / "CLAUDE.md").exists() else ""
    for match in re.findall(r"^@([^\s]+)", claude_text, flags=re.M):
        if not (ROOT / match).exists():
            error(errors, f"CLAUDE.md imports missing file: {match}")

    template_mode = bool(project.get("template_mode", True)) if project else True
    if not template_mode:
        # Check only files that bootstrap_project.py must tailor. The repository also
        # intentionally carries reusable example/template assets and documentation
        # containing literal {{PLACEHOLDER}} examples. Scanning every text file would
        # incorrectly reject a valid generated project.
        generated_control_files = [
            "config/project.json",
            "PROJECT_CHARTER.md",
            "PROJECT_STATE.md",
            "OPEN_LOOPS.md",
            "FACTS_AND_ASSUMPTIONS.md",
            "SOURCE_INDEX.md",
            "RISK_REGISTER.md",
            "CONNECTOR_PLAN.md",
            "SKILL_PLAN.md",
            "HANDOFF_CURRENT.md",
            "CHANGELOG.md",
        ]
        for rel in generated_control_files:
            path = ROOT / rel
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if PLACEHOLDER.search(text):
                error(errors, f"Unresolved placeholder in generated project: {rel}")

    for path in ROOT.rglob("*"):
        if path.is_file():
            rel = path.relative_to(ROOT).as_posix()
            if SECRET_NAMES.search(rel):
                error(errors, f"Potential secret file must not be tracked: {rel}")

    canonical = ROOT / "skills/complex-project-bootstrapper/SKILL.md"
    for rel in [
        ".agents/skills/complex-project-bootstrapper/SKILL.md",
        ".claude/skills/complex-project-bootstrapper/SKILL.md",
    ]:
        native = ROOT / rel
        if canonical.exists() and native.exists() and canonical.read_bytes() != native.read_bytes():
            error(errors, f"Native skill copy differs from canonical: {rel}; run scripts/sync_skills.py")

    if not (ROOT / "HANDOFF_CURRENT.md").exists():
        warnings.append("No current handoff")

    if errors:
        print("VALIDATION FAILED")
        for item in errors:
            print(f"ERROR: {item}")
        for item in warnings:
            print(f"WARNING: {item}")
        return 1

    print("VALIDATION PASSED")
    print(f"Repository: {ROOT}")
    print(f"Mode: {'template' if template_mode else 'generated project'}")
    print(f"Required paths checked: {len(REQUIRED)}")
    for item in warnings:
        print(f"WARNING: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
