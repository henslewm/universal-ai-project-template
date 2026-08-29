#!/usr/bin/env python3
"""Copy canonical project skills into Codex and Claude Code discovery paths."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = ROOT / "skills"
TARGET_ROOTS = [ROOT / ".agents/skills", ROOT / ".claude/skills"]


def main() -> int:
    for target_root in TARGET_ROOTS:
        target_root.mkdir(parents=True, exist_ok=True)
        for skill in SOURCE_ROOT.iterdir():
            if not skill.is_dir() or not (skill / "SKILL.md").exists():
                continue
            target = target_root / skill.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(skill, target, ignore=shutil.ignore_patterns("project-template"))
            print(f"Synced {skill.name} -> {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
