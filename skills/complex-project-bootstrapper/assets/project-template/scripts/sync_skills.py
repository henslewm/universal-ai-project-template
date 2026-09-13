#!/usr/bin/env python3
"""Synchronize bootstrap entrypoints, native skills and the standalone template."""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / 'skills/complex-project-bootstrapper'
# 'Claude outputs' is where the Claude desktop app saves session artifacts when the working
# folder is this repository; those are personal working files, never template payload.
EXCLUDED = {'.git', '__pycache__', '.pytest_cache', '.venv', 'venv', 'dist', 'build', 'assets',
            'Claude outputs'}


def files_under(root: Path):
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in EXCLUDED)
        for name in sorted(files):
            if not name.endswith(('.pyc', '.zip')) and name not in {'bootstrap-answers.local.json', 'bootstrap.json', 'bootstrap.json.tmp', 'BOOTSTRAP_REVIEW.md'}:
                yield Path(directory) / name


def sync(check: bool = False) -> list[str]:
    differences = []

    def copy(source: Path, target: Path):
        if target.exists() and source.read_bytes() == target.read_bytes():
            return
        differences.append(target.relative_to(ROOT).as_posix())
        if not check:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    for name in ('bootstrap_project.py', 'bootstrap_gate.py', 'validate_bootstrap.py', 'validate_project.py'):
        copy(ROOT / 'scripts' / name, SKILL / 'scripts' / name)
    for source in files_under(SKILL):
        for native in ('.agents/skills', '.claude/skills'):
            copy(source, ROOT / native / SKILL.name / source.relative_to(SKILL))
    asset = SKILL / 'assets/project-template'
    for source in files_under(ROOT):
        copy(source, asset / source.relative_to(ROOT))
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail on payload drift without writing files')
    args = parser.parse_args()
    differences = sync(args.check)
    if args.check and differences:
        print('BOOTSTRAP PAYLOAD DRIFT\n' + '\n'.join(differences))
        return 1
    print(f'Bootstrap payloads {"verified" if args.check else "synchronized"}; {len(differences)} files differed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
